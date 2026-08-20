import os

import geopandas as gpd
from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy import create_engine, text

BASE = Path(__file__).parent.parent
OVERWRITE = False  # Cambiar a True para vaciar y recargar la tabla aunque ya tenga datos
BUFFER_M = 20  # Radio (metros) en el que se cuentan farolas cercanas a cada tramo

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

schema_sql = (BASE / "sql/02_farolas.sql").read_text()
with engine.begin() as conn:
    conn.execute(text(schema_sql))

with engine.connect() as conn:
    farolas_cargadas = conn.execute(text("SELECT count(*) FROM farolas")).scalar() > 0
    indice_calculado = (
        conn.execute(text("SELECT count(*) FROM edges WHERE num_farolas IS NOT NULL")).scalar()
        > 0
    )

if farolas_cargadas and not OVERWRITE:
    print("Farolas ya cargadas en la BD, no se hace nada (OVERWRITE=False).")
else:
    if farolas_cargadas:
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE farolas RESTART IDENTITY"))

    shp_path = BASE / "data/raw/farolas/20220408_DATOS_ABIERTOS_UNIDAD_LUMINOSA_.shp"
    farolas = gpd.read_file(shp_path)
    if farolas.crs is None:
        farolas = farolas.set_crs("EPSG:25830")
    farolas = farolas.to_crs("EPSG:4326")

    farolas = farolas.rename(
        columns={
            "tipo_bloqu": "tipo_bloque",
            "VIA_CLASE": "via_clase",
            "VIA_NOMBRE": "via_nombre",
            "NUMERO": "numero",
            "DISTRITO": "distrito",
            "BARRIO": "barrio",
            "geometry": "geom",
        }
    )[["tipo_bloque", "via_clase", "via_nombre", "numero", "distrito", "barrio", "geom"]]
    farolas = farolas.set_geometry("geom")

    farolas.to_postgis("farolas", engine, if_exists="append", index=False)
    print(f"Farolas cargadas: {len(farolas)}")
    indice_calculado = False  # farolas recargadas => hay que recalcular el índice

if indice_calculado and not OVERWRITE:
    print("Índice de iluminación por tramo ya calculado, no se hace nada (OVERWRITE=False).")
else:
    # ST_DWithin en geography usaría el radio en metros de forma exacta, pero no
    # puede aprovechar el índice GIST(geom) ya creado sobre geometry y convierte
    # el cruce en un nested loop completo (524k x 233k filas). Con un radio tan
    # pequeño (20m) la distorsión de usar grados directamente sobre geometry es
    # despreciable y sí usa el índice espacial.
    buffer_deg = BUFFER_M / 111320.0

    with engine.begin() as conn:
        conn.execute(text("UPDATE edges SET num_farolas = 0, farolas_100m = 0"))
        conn.execute(
            text(
                """
                UPDATE edges e
                SET num_farolas = sub.n,
                    farolas_100m = sub.n / (e.length / 100.0)
                FROM (
                    SELECT e2.id, count(f.id) AS n
                    FROM edges e2
                    JOIN farolas f
                      ON ST_DWithin(f.geom, e2.geom, :buffer_deg)
                    GROUP BY e2.id
                ) sub
                WHERE e.id = sub.id AND e.length > 0
                """
            ).bindparams(buffer_deg=buffer_deg)
        )
    print(f"Índice de iluminación calculado para los tramos (radio {BUFFER_M}m).")
