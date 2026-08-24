"""Genera el mapa del índice de peligrosidad por tramo para la memoria del TFG.

Consulta edges.geom e indice_peligrosidad, reproyecta a un sistema métrico
(ETRS89/UTM 30N) para no distorsionar la geometría de Madrid, y vuelca el
resultado en docs/imagenes/mapa_peligrosidad.png (Figura del Capítulo 3).

La paleta es secuencial (YlOrRd, de ColorBrewer): un único recorrido claro
-> oscuro apropiado para una magnitud continua como indice_peligrosidad, a
diferencia de una escala tipo semáforo (verde-amarillo-rojo), que induce a
leerla como si tuviera dos polos en torno a un punto medio.
"""

import os

import geopandas as gpd
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from matplotlib.lines import Line2D
from pathlib import Path
from sqlalchemy import create_engine

BASE = Path(__file__).parent.parent
OUT_PATH = BASE / "docs/imagenes/mapa_peligrosidad.png"

COLOR_FONDO = "#fcfcfb"
COLOR_TEXTO = "#3a3a38"
CMAP = "YlOrRd"

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


def dibujar_escala(ax, x0, y0, longitud_m=5000):
    """Barra de escala sencilla (metros, en el CRS proyectado EPSG:25830)."""
    ax.add_line(Line2D([x0, x0 + longitud_m], [y0, y0], color=COLOR_TEXTO, linewidth=1.4))
    for x in (x0, x0 + longitud_m):
        ax.add_line(Line2D([x, x], [y0 - 250, y0 + 250], color=COLOR_TEXTO, linewidth=1.4))
    ax.text(
        x0 + longitud_m / 2, y0 + 550, f"{longitud_m // 1000} km",
        ha="center", va="bottom", fontsize=9, color=COLOR_TEXTO,
    )


if __name__ == "__main__":
    edges = gpd.read_postgis(
        "SELECT geom, indice_peligrosidad FROM edges WHERE indice_peligrosidad IS NOT NULL",
        engine,
        geom_col="geom",
    )
    edges = edges.to_crs("EPSG:25830")
    # Los tramos más peligrosos se dibujan al final (encima), para que no
    # queden ocultos bajo la mayoría de tramos de bajo riesgo.
    edges = edges.sort_values("indice_peligrosidad")
    print(f"Tramos a dibujar: {len(edges)}")

    plt.rcParams["font.family"] = "serif"

    fig, ax = plt.subplots(figsize=(9, 9))
    fig.patch.set_facecolor(COLOR_FONDO)
    ax.set_facecolor(COLOR_FONDO)

    edges.plot(
        ax=ax,
        column="indice_peligrosidad",
        cmap=CMAP,
        linewidth=edges["indice_peligrosidad"] * 0.9 + 0.3,
        vmin=0,
        vmax=1,
    )

    sm = plt.cm.ScalarMappable(cmap=CMAP, norm=plt.Normalize(vmin=0, vmax=1))
    cbar = fig.colorbar(sm, ax=ax, shrink=0.55, pad=0.02, aspect=25)
    cbar.set_label("Índice de peligrosidad", color=COLOR_TEXTO, fontsize=11)
    cbar.set_ticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    cbar.ax.tick_params(labelcolor=COLOR_TEXTO, labelsize=9)
    cbar.outline.set_visible(False)

    xmin, ymin, xmax, ymax = edges.total_bounds
    dibujar_escala(ax, xmin + (xmax - xmin) * 0.04, ymin + (ymax - ymin) * 0.03)

    ax.set_axis_off()
    ax.set_aspect("equal")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=220, bbox_inches="tight", facecolor=COLOR_FONDO)
    print(f"Mapa guardado en {OUT_PATH}")
