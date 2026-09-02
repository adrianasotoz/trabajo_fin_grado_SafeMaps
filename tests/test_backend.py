"""IT1-IT3: pruebas de integración del backend y la base de datos (Sección 6.5, IT1-IT3)."""

from concurrent.futures import ThreadPoolExecutor

import pytest
import requests
from sqlalchemy import text

from rutas import calcular_ruta

PUERTA_DEL_SOL = (-3.7038, 40.4168)
ATOCHA = (-3.6906, 40.4067)


def test_peticiones_concurrentes_a_api_ruta(live_server):
    """IT1: N peticiones concurrentes a /api/ruta se resuelven todas sin error
    (ThreadPoolExecutor + conexión aislada por hilo, Sección 4.5)."""

    def pedir_ruta():
        return requests.get(
            f"{live_server}/api/ruta",
            params={
                "origen_lon": PUERTA_DEL_SOL[0],
                "origen_lat": PUERTA_DEL_SOL[1],
                "destino_lon": ATOCHA[0],
                "destino_lat": ATOCHA[1],
            },
            timeout=15,
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        respuestas = list(pool.map(lambda _: pedir_ruta(), range(8)))

    for r in respuestas:
        assert r.status_code == 200
        datos = r.json()
        assert set(datos.keys()) == {"rapida", "segura"}
        assert datos["rapida"]["distancia_m"] > 0
        assert datos["segura"]["distancia_m"] > 0


def test_pgr_dijkstra_resuelve_coordenadas_en_el_limite_del_grafo(engine):
    """IT2: pgr_dijkstra encuentra ruta entre los nodos más extremos del grafo
    (norte y sur), sin devolver un conjunto vacío por quedar fuera de la
    ventana geográfica acotada (Sección 3.6)."""
    with engine.connect() as conn:
        sur = conn.execute(text("SELECT x, y FROM nodes ORDER BY y ASC LIMIT 1")).one()
        norte = conn.execute(text("SELECT x, y FROM nodes ORDER BY y DESC LIMIT 1")).one()

        ruta = calcular_ruta(conn, (sur.x, sur.y), (norte.x, norte.y), criterio="rapida")

        assert ruta["distancia_m"] > 0

        primer_edge = conn.execute(
            text("SELECT count(*) FROM edges WHERE indice_peligrosidad IS NOT NULL LIMIT 1")
        ).scalar()
        assert primer_edge is not None


def test_calcular_ruta_mismo_origen_destino_falla_de_forma_controlada(engine):
    with engine.connect() as conn:
        with pytest.raises(ValueError):
            calcular_ruta(conn, PUERTA_DEL_SOL, PUERTA_DEL_SOL, criterio="rapida")


def test_deduplicacion_proxy_geocodificacion(live_server):
    """IT3: /api/geocode combina CartoCiudad y Nominatim sin duplicados por
    cercanía de coordenadas ni por texto mostrado (Sección 4.5)."""
    r = requests.get(f"{live_server}/api/geocode", params={"q": "Atocha, Madrid"}, timeout=15)
    assert r.status_code == 200
    resultados = r.json()

    assert isinstance(resultados, list)
    assert len(resultados) <= 8

    claves_coords = [(round(x["lat"], 4), round(x["lon"], 4)) for x in resultados]
    claves_texto = [(x["principal"].lower(), x["secundario"].lower()) for x in resultados]
    assert len(claves_coords) == len(set(claves_coords))
    assert len(claves_texto) == len(set(claves_texto))
