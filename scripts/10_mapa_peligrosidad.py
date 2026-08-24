"""Genera el mapa del índice de peligrosidad por tramo para la memoria del TFG.

Consulta edges.geom e indice_peligrosidad, reproyecta a un sistema métrico
(ETRS89/UTM 30N) para no distorsionar la geometría de Madrid, y vuelca el
resultado en docs/imagenes/mapa_peligrosidad.png (Figura del Capítulo 3).
"""

import os

import geopandas as gpd
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy import create_engine

BASE = Path(__file__).parent.parent
OUT_PATH = BASE / "docs/imagenes/mapa_peligrosidad.png"

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

if __name__ == "__main__":
    edges = gpd.read_postgis(
        "SELECT geom, indice_peligrosidad FROM edges WHERE indice_peligrosidad IS NOT NULL",
        engine,
        geom_col="geom",
    )
    edges = edges.to_crs("EPSG:25830")
    print(f"Tramos a dibujar: {len(edges)}")

    fig, ax = plt.subplots(figsize=(10, 10))
    edges.plot(
        ax=ax,
        column="indice_peligrosidad",
        cmap="RdYlGn_r",
        linewidth=0.35,
        legend=True,
        legend_kwds={"label": "Índice de peligrosidad", "shrink": 0.6},
    )
    ax.set_axis_off()
    ax.set_title("Índice de peligrosidad por tramo — red peatonal de Madrid")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=200, bbox_inches="tight")
    print(f"Mapa guardado en {OUT_PATH}")
