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

# Velocidad peatonal media usada para estimar la duración de la ruta.
VELOCIDAD_PEATONAL_MS = 5000 / 3600  # 5 km/h


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
    Devuelve un dict con la geometría (GeoJSON LineString), la distancia y
    duración estimada, y el desglose del índice de seguridad (iluminación,
    accidentes, atropellos, vulnerabilidad) ponderado por longitud, para
    poder explicar en qué mejora una ruta a la otra.
    """
    if criterio not in QUERY_EDGES:
        raise ValueError(f"Criterio desconocido: {criterio!r} (usa 'rapida' o 'segura')")

    origen_id = nodo_mas_cercano(conn, *origen)
    destino_id = nodo_mas_cercano(conn, *destino)

    filas = conn.execute(
        text(
            """
            SELECT r.edge, ST_AsText(e.geom) AS geom_wkt, e.length, e.indice_peligrosidad,
                   e.farolas_100m, e.accidentes_100m, e.num_atropellos, v.ivt_agregado
            FROM pgr_dijkstra(:query, :origen_id, :destino_id, directed => false) r
            JOIN edges e ON e.id = r.edge
            LEFT JOIN vulnerabilidad_distritos v ON v.cod_distrito = e.cod_distrito
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

    def media_ponderada(campo):
        return sum(fila.length * getattr(fila, campo) for fila in filas) / distancia_m

    return {
        "criterio": criterio,
        "distancia_m": round(distancia_m, 1),
        "duracion_min": round(distancia_m / VELOCIDAD_PEATONAL_MS / 60, 1),
        "num_tramos": len(filas),
        "peligrosidad_media": round(media_ponderada("indice_peligrosidad"), 4),
        "iluminacion_media": round(media_ponderada("farolas_100m"), 2),
        "accidentes_media": round(media_ponderada("accidentes_100m"), 2),
        "atropellos_total": sum(fila.num_atropellos for fila in filas),
        "vulnerabilidad_media": round(media_ponderada("ivt_agregado"), 3),
        "geometry": mapping(geometria),
    }
