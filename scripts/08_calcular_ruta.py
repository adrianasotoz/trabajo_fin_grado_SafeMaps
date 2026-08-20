import json
import os

from dotenv import load_dotenv
from pathlib import Path
from shapely import wkt
from shapely.geometry import LineString, mapping
from shapely.ops import linemerge
from sqlalchemy import create_engine, text

BASE = Path(__file__).parent.parent

load_dotenv(BASE / ".env")

engine = create_engine(
    "postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}".format(
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=os.environ["DB_PORT"],
        dbname=os.environ["DB_NAME"],
    )
)

# Consultas de pgr_dijkstra para cada criterio de ruta: distancia real
# ("cost"/"reverse_cost") o coste penalizado por peligrosidad ("cost_seguro").
QUERY_EDGES = {
    "rapida": "SELECT id, source, target, cost, reverse_cost FROM edges",
    "segura": "SELECT id, source, target, cost_seguro AS cost, reverse_cost_seguro AS reverse_cost FROM edges",
}


def nodo_mas_cercano(conn, lon, lat):
    return conn.execute(
        text(
            """
            SELECT osmid FROM nodes
            ORDER BY geom <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
            LIMIT 1
            """
        ).bindparams(lon=lon, lat=lat)
    ).scalar()


def calcular_ruta(conn, origen, destino, criterio="segura"):
    """Calcula una ruta peatonal entre dos puntos (lon, lat) en WGS84.

    criterio: "rapida" (solo distancia) o "segura" (distancia penalizada
    por indice_peligrosidad, ver scripts/07_calcular_indice_seguridad.py).
    Devuelve un dict con la geometría (GeoJSON LineString), la distancia
    real recorrida y el indice de peligrosidad medio (ponderado por
    longitud) de los tramos de la ruta.
    """
    origen_id = nodo_mas_cercano(conn, *origen)
    destino_id = nodo_mas_cercano(conn, *destino)

    filas = conn.execute(
        text(
            """
            SELECT r.edge, ST_AsText(e.geom) AS geom_wkt, e.length, e.indice_peligrosidad
            FROM pgr_dijkstra(:query, :origen_id, :destino_id, directed => false) r
            JOIN edges e ON e.id = r.edge
            ORDER BY r.seq
            """
        ).bindparams(query=QUERY_EDGES[criterio], origen_id=origen_id, destino_id=destino_id)
    ).fetchall()

    if not filas:
        raise ValueError("No se ha encontrado ruta entre los puntos indicados.")

    segmentos = [wkt.loads(fila.geom_wkt) for fila in filas]
    geometria = linemerge(segmentos)
    if geometria.geom_type != "LineString":
        # Tramos que pgRouting recorre en dirección inversa pueden dejar la
        # unión desordenada; como respaldo se concatenan en el orden de la ruta.
        coords = []
        for seg in segmentos:
            coords.extend(seg.coords)
        geometria = LineString(coords)

    distancia_m = sum(fila.length for fila in filas)
    peligrosidad_media = sum(fila.length * fila.indice_peligrosidad for fila in filas) / distancia_m

    return {
        "criterio": criterio,
        "distancia_m": round(distancia_m, 1),
        "peligrosidad_media": round(peligrosidad_media, 4),
        "num_tramos": len(filas),
        "geometry": mapping(geometria),
    }


if __name__ == "__main__":
    # Ejemplo: de Puerta del Sol a Plaza de Castilla.
    ORIGEN = (-3.7038, 40.4168)
    DESTINO = (-3.6890, 40.4660)

    with engine.connect() as conn:
        rutas = {criterio: calcular_ruta(conn, ORIGEN, DESTINO, criterio) for criterio in QUERY_EDGES}

    for criterio, ruta in rutas.items():
        print(
            f"Ruta {criterio}: {ruta['distancia_m']} m, "
            f"{ruta['num_tramos']} tramos, "
            f"peligrosidad media {ruta['peligrosidad_media']}"
        )

    salida = BASE / "data/processed/rutas_ejemplo.geojson"
    salida.parent.mkdir(parents=True, exist_ok=True)
    coleccion = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {k: v for k, v in ruta.items() if k != "geometry"}, "geometry": ruta["geometry"]}
            for ruta in rutas.values()
        ],
    }
    salida.write_text(json.dumps(coleccion))
    print(f"Rutas guardadas en {salida}")
