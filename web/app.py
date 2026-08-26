import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))

import requests  # noqa: E402
from flask import Flask, jsonify, render_template, request  # noqa: E402
from rutas import QUERY_EDGES, calcular_ruta, engine  # noqa: E402

app = Flask(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org"
NOMINATIM_HEADERS = {"User-Agent": "TFG-RutasSeguras-Madrid/1.0"}
# Caja delimitadora aproximada del municipio de Madrid, para priorizar/acotar
# los resultados de geocodificación.
MADRID_VIEWBOX = "-3.9,40.55,-3.5,40.30"

CARTOCIUDAD_URL = "https://www.cartociudad.es/geocoder/api/geocoder/candidates"
MADRID_MUNICODE = "28079"

_POSTCODE_RE = re.compile(r"^\d{5}$")
_COMPONENTES_REDUNDANTES = {"España", "Comunidad de Madrid"}


def _resultado(principal, secundario, lon, lat):
    """Un resultado de sugerencia con línea principal/secundaria (estilo Google Maps)
    y un `nombre` de una sola línea para rellenar el campo de texto al seleccionarlo.
    """
    nombre = f"{principal}, {secundario}" if secundario else principal
    return {"principal": principal, "secundario": secundario, "nombre": nombre, "lon": lon, "lat": lat}


def _buscar_cartociudad(q):
    """Direcciones calle+número exactas (Catastro, vía CartoCiudad/IGN).

    Nominatim solo resuelve un housenumber si existe un POI de OSM con ese
    número exacto; para la mayoría de portales residenciales de Madrid no es
    el caso. CartoCiudad se basa en Catastro y sí lo resuelve siempre.
    """
    # CartoCiudad no aplica ningún sesgo geográfico a la búsqueda de texto libre
    # (a diferencia de Nominatim, al que sí acotamos con viewbox/bounded), por lo
    # que sin esta pista antepone calles homónimas de otros municipios.
    q_acotada = q if "madrid" in q.lower() else f"{q}, Madrid"

    try:
        resp = requests.get(CARTOCIUDAD_URL, params={"q": q_acotada}, timeout=5)
        resp.raise_for_status()
        datos = resp.json()
    except (requests.RequestException, ValueError):
        app.logger.exception("Fallo consultando CartoCiudad (geocode)")
        return None

    resultados = []
    for r in datos if isinstance(datos, list) else []:
        try:
            if r.get("muniCode") != MADRID_MUNICODE or not r.get("portalNumber"):
                continue
            numero = str(r["portalNumber"])
            calle = r["address"].split(",")[0].strip()
            if calle.endswith(numero):
                calle = calle[: -len(numero)].strip()
            principal = f"{calle.title()}, {numero}"
            resultados.append(_resultado(principal, "Madrid", float(r["lng"]), float(r["lat"])))
        except (KeyError, TypeError, ValueError):
            continue
    return resultados[:5]


def _buscar_nominatim(q):
    """Nombres de establecimientos/lugares (POIs) y direcciones genéricas (OSM)."""
    try:
        resp = requests.get(
            f"{NOMINATIM_URL}/search",
            params={
                "q": q,
                "format": "json",
                "limit": 5,
                "countrycodes": "es",
                "viewbox": MADRID_VIEWBOX,
                "bounded": 1,
            },
            headers=NOMINATIM_HEADERS,
            timeout=5,
        )
        resp.raise_for_status()
        datos = resp.json()
    except requests.RequestException:
        app.logger.exception("Fallo consultando Nominatim (geocode)")
        return None

    resultados = []
    for r in datos:
        try:
            partes = [p.strip() for p in r["display_name"].split(",")]
            principal = r.get("name") or partes[0]
            resto = partes[1:] if partes[0] == principal else partes
            resto = [p for p in resto if p and not _POSTCODE_RE.match(p) and p not in _COMPONENTES_REDUNDANTES]
            secundario = ", ".join(resto[:3])
            resultados.append(_resultado(principal, secundario, float(r["lon"]), float(r["lat"])))
        except (KeyError, ValueError):
            continue
    return resultados


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/ruta")
def api_ruta():
    try:
        origen = (float(request.args["origen_lon"]), float(request.args["origen_lat"]))
        destino = (float(request.args["destino_lon"]), float(request.args["destino_lat"]))
    except (KeyError, ValueError):
        return jsonify({"error": "Parámetros esperados: origen_lon, origen_lat, destino_lon, destino_lat"}), 400

    try:
        with engine.connect() as conn:
            rutas = {criterio: calcular_ruta(conn, origen, destino, criterio) for criterio in QUERY_EDGES}
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        app.logger.exception("Fallo calculando la ruta")
        return jsonify({"error": "No se ha podido calcular la ruta. Inténtalo de nuevo."}), 503

    return jsonify(rutas)


@app.get("/api/geocode")
def api_geocode():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "Falta el parámetro q"}), 400

    with ThreadPoolExecutor(max_workers=2) as pool:
        futuro_cartociudad = pool.submit(_buscar_cartociudad, q)
        futuro_nominatim = pool.submit(_buscar_nominatim, q)
        resultado_cartociudad = futuro_cartociudad.result()
        resultado_nominatim = futuro_nominatim.result()

    if resultado_cartociudad is None and resultado_nominatim is None:
        return jsonify({"error": "No se pudo contactar con los servicios de geocodificación"}), 502

    # CartoCiudad (Catastro) primero: resuelve el número de portal exacto,
    # que Nominatim solo acierta si hay un POI de OSM con ese housenumber.
    candidatos = (resultado_cartociudad or []) + (resultado_nominatim or [])

    resultados = []
    vistos = set()
    for r in candidatos:
        # Dos resultados se consideran el mismo tanto si sus coordenadas casi
        # coinciden como si el texto mostrado es idéntico: algunos POIs de
        # Nominatim comparten nombre/dirección con coordenadas que difieren
        # solo unos metros y caen a ambos lados del redondeo de coordenadas.
        clave_coords = (round(r["lat"], 4), round(r["lon"], 4))
        clave_texto = (r["principal"].lower(), r["secundario"].lower())
        if clave_coords in vistos or clave_texto in vistos:
            continue
        vistos.add(clave_coords)
        vistos.add(clave_texto)
        resultados.append(r)
    return jsonify(resultados[:8])


@app.get("/api/geocode/inverso")
def api_geocode_inverso():
    try:
        lon = float(request.args["lon"])
        lat = float(request.args["lat"])
    except (KeyError, ValueError):
        return jsonify({"error": "Parámetros esperados: lon, lat"}), 400

    try:
        resp = requests.get(
            f"{NOMINATIM_URL}/reverse",
            params={"lon": lon, "lat": lat, "format": "json", "zoom": 18},
            headers=NOMINATIM_HEADERS,
            timeout=5,
        )
        resp.raise_for_status()
    except requests.RequestException:
        app.logger.exception("Fallo consultando Nominatim (geocode inverso)")
        return jsonify({"nombre": f"{lat:.5f}, {lon:.5f}", "lon": lon, "lat": lat})

    datos = resp.json()
    nombre = datos.get("display_name", f"{lat:.5f}, {lon:.5f}")
    return jsonify({"nombre": nombre, "lon": lon, "lat": lat})


if __name__ == "__main__":
    app.run(debug=True)
