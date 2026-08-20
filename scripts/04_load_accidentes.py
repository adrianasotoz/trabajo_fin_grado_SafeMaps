import os

import geopandas as gpd
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path
from shapely.geometry import Point
from sqlalchemy import create_engine, text

BASE = Path(__file__).parent.parent
OVERWRITE = False  # Cambiar a True para vaciar y recargar la tabla aunque ya tenga datos
BUFFER_M = 20  # Radio (metros) en el que se cuentan accidentes cercanos a cada tramo

# De más a menos grave; el resto (incl. "Se desconoce" y sin dato) se trata como desconocido.
ORDEN_LESIVIDAD = [
    "Fallecido 24 horas",
    "Ingreso superior a 24 horas",
    "Ingreso inferior o igual a 24 horas",
    "Asistencia sanitaria inmediata en centro de salud o mutua",
    "Atención en urgencias sin posterior ingreso",
    "Asistencia sanitaria ambulatoria con posterioridad",
    "Asistencia sanitaria sólo en el lugar del accidente",
    "Sin asistencia sanitaria",
    "Se desconoce",
]
RANGO_LESIVIDAD = {valor: rango for rango, valor in enumerate(ORDEN_LESIVIDAD)}

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

schema_sql = (BASE / "sql/03_accidentes.sql").read_text()
with engine.begin() as conn:
    conn.execute(text(schema_sql))

with engine.connect() as conn:
    accidentes_cargados = conn.execute(text("SELECT count(*) FROM accidentes")).scalar() > 0
    indice_calculado = (
        conn.execute(text("SELECT count(*) FROM edges WHERE num_accidentes IS NOT NULL")).scalar()
        > 0
    )

if accidentes_cargados and not OVERWRITE:
    print("Accidentes ya cargados en la BD, no se hace nada (OVERWRITE=False).")
else:
    if accidentes_cargados:
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE accidentes RESTART IDENTITY"))

    csv_paths = sorted((BASE / "data/raw/accidentes").glob("accidentes_*.csv"))
    personas = pd.concat(
        (pd.read_csv(p, sep=";", encoding="utf-8-sig") for p in csv_paths), ignore_index=True
    )
    personas = personas.dropna(subset=["coordenada_x_utm", "coordenada_y_utm"])

    personas["atropello_persona"] = (personas["tipo_persona"] == "Peatón") | (
        personas["tipo_accidente"] == "Atropello a persona"
    )
    personas["rango_lesividad"] = personas["lesividad"].map(RANGO_LESIVIDAD).fillna(len(ORDEN_LESIVIDAD))

    peor_lesividad = (
        personas.loc[personas.groupby("num_expediente")["rango_lesividad"].idxmin()]
        .set_index("num_expediente")["lesividad"]
        .rename("lesividad_max")
    )

    accidentes = personas.groupby("num_expediente").agg(
        fecha=("fecha", "first"),
        hora=("hora", "first"),
        cod_distrito=("cod_distrito", "first"),
        distrito=("distrito", "first"),
        tipo_accidente=("tipo_accidente", "first"),
        atropello_peaton=("atropello_persona", "any"),
        coordenada_x_utm=("coordenada_x_utm", "first"),
        coordenada_y_utm=("coordenada_y_utm", "first"),
    )
    accidentes = accidentes.join(peor_lesividad).reset_index()

    accidentes["fecha"] = pd.to_datetime(accidentes["fecha"], format="%d/%m/%Y").dt.date
    accidentes["hora"] = pd.to_datetime(accidentes["hora"], format="%H:%M:%S").dt.time
    accidentes["cod_distrito"] = accidentes["cod_distrito"].astype("Int64")

    geometry = [
        Point(xy) for xy in zip(accidentes["coordenada_x_utm"], accidentes["coordenada_y_utm"])
    ]
    accidentes = gpd.GeoDataFrame(accidentes, geometry=geometry, crs="EPSG:25830").to_crs("EPSG:4326")
    accidentes = accidentes.rename(columns={"geometry": "geom"}).set_geometry("geom")[
        [
            "num_expediente",
            "fecha",
            "hora",
            "cod_distrito",
            "distrito",
            "tipo_accidente",
            "lesividad_max",
            "atropello_peaton",
            "geom",
        ]
    ]

    accidentes.to_postgis("accidentes", engine, if_exists="append", index=False)
    print(f"Accidentes cargados: {len(accidentes)}")
    indice_calculado = False  # accidentes recargados => hay que recalcular el índice

if indice_calculado and not OVERWRITE:
    print("Índice de siniestralidad por tramo ya calculado, no se hace nada (OVERWRITE=False).")
else:
    # Mismo razonamiento que en 03_load_farolas.py: con un radio pequeño (20m) usar
    # grados directamente sobre geometry (en vez de geography) permite aprovechar el
    # índice GIST(geom) y la distorsión resultante es despreciable.
    buffer_deg = BUFFER_M / 111320.0

    with engine.begin() as conn:
        conn.execute(
            text("UPDATE edges SET num_accidentes = 0, accidentes_100m = 0, num_atropellos = 0")
        )
        conn.execute(
            text(
                """
                UPDATE edges e
                SET num_accidentes = sub.n,
                    accidentes_100m = sub.n / (e.length / 100.0),
                    num_atropellos = sub.n_atropellos
                FROM (
                    SELECT e2.id,
                           count(a.id) AS n,
                           count(a.id) FILTER (WHERE a.atropello_peaton) AS n_atropellos
                    FROM edges e2
                    JOIN accidentes a
                      ON ST_DWithin(a.geom, e2.geom, :buffer_deg)
                    GROUP BY e2.id
                ) sub
                WHERE e.id = sub.id AND e.length > 0
                """
            ).bindparams(buffer_deg=buffer_deg)
        )
    print(f"Índice de siniestralidad calculado para los tramos (radio {BUFFER_M}m).")
