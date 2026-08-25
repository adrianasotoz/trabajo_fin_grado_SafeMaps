import sys
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
    except requests.RequestException:
        app.logger.exception("Fallo consultando Nominatim (geocode)")
        return jsonify({"error": "No se pudo contactar con el servicio de geocodificación"}), 502

    resultados = [
        {"nombre": r["display_name"], "lon": float(r["lon"]), "lat": float(r["lat"])} for r in resp.json()
    ]
    return jsonify(resultados)


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
