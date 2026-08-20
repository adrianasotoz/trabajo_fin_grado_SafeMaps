import os

import osmnx as ox
from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy import create_engine, text

BASE = Path(__file__).parent.parent
OVERWRITE = False  # Cambiar a True para vaciar y recargar las tablas aunque ya tengan datos

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

schema_sql = (BASE / "sql/01_schema.sql").read_text()
with engine.begin() as conn:
    conn.execute(text(schema_sql))

with engine.connect() as conn:
    ya_cargado = conn.execute(text("SELECT count(*) FROM nodes")).scalar() > 0

if ya_cargado and not OVERWRITE:
    print("Datos ya cargados en la BD, no se hace nada (OVERWRITE=False).")
else:
    if ya_cargado:
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE edges, nodes RESTART IDENTITY"))

    graphml_path = BASE / "data/raw/osm/madrid_walk.graphml"
    G = ox.load_graphml(graphml_path)
    nodes, edges = ox.graph_to_gdfs(G)

    def a_texto(valor):
        # osmnx puede fusionar tramos al simplificar el grafo y dejar listas
        # en campos como osmid, highway o name en lugar de un único valor.
        return str(valor) if isinstance(valor, list) else valor

    nodes = nodes.reset_index()[["osmid", "x", "y", "highway", "street_count", "geometry"]]
    nodes = nodes.rename(columns={"geometry": "geom"}).set_geometry("geom")

    edges = edges.reset_index()[
        ["u", "v", "key", "osmid", "highway", "name", "oneway", "length", "geometry"]
    ]
    edges["osmid"] = edges["osmid"].apply(a_texto).astype(str)
    edges["highway"] = edges["highway"].apply(a_texto)
    edges["name"] = edges["name"].apply(a_texto)
    edges["source"] = edges["u"]
    edges["target"] = edges["v"]
    edges["cost"] = edges["length"]
    edges["reverse_cost"] = edges["length"]
    edges = edges.rename(columns={"geometry": "geom"}).set_geometry("geom")

    nodes.to_postgis("nodes", engine, if_exists="append", index=False)
    edges.to_postgis("edges", engine, if_exists="append", index=False)

    print(f"Nodos cargados: {len(nodes)}")
    print(f"Tramos cargados: {len(edges)}")
