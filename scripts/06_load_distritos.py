import os

import geopandas as gpd
from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy import create_engine, text

BASE = Path(__file__).parent.parent
OVERWRITE = False  # Cambiar a True para vaciar y recargar la tabla aunque ya tenga datos

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

schema_sql = (BASE / "sql/05_distritos.sql").read_text()
with engine.begin() as conn:
    conn.execute(text(schema_sql))

with engine.connect() as conn:
    distritos_cargados = conn.execute(text("SELECT count(*) FROM distritos")).scalar() > 0
    join_hecho = (
        conn.execute(text("SELECT count(*) FROM edges WHERE cod_distrito IS NOT NULL")).scalar() > 0
    )

if distritos_cargados and not OVERWRITE:
    print("Distritos ya cargados en la BD, no se hace nada (OVERWRITE=False).")
else:
    if distritos_cargados:
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE distritos"))

    shp_path = BASE / "data/raw/distritos/DISTRITOS.shp"
    distritos = gpd.read_file(shp_path).to_crs("EPSG:4326")
    distritos = distritos.rename(
        columns={"COD_DIS": "cod_distrito", "NOMBRE": "nombre", "Area": "area_m2", "geometry": "geom"}
    )[["cod_distrito", "nombre", "area_m2", "geom"]]
    distritos["cod_distrito"] = distritos["cod_distrito"].astype(int)
    distritos = distritos.set_geometry("geom")

    distritos.to_postgis("distritos", engine, if_exists="append", index=False)
    print(f"Distritos cargados: {len(distritos)}")
    join_hecho = False  # distritos recargados => hay que rehacer el join con edges

if join_hecho and not OVERWRITE:
    print("Tramos ya asignados a distrito, no se hace nada (OVERWRITE=False).")
else:
    with engine.begin() as conn:
        conn.execute(text("UPDATE edges SET cod_distrito = NULL"))
        # Distrito que contiene el centroide del tramo.
        conn.execute(
            text(
                """
                UPDATE edges e
                SET cod_distrito = sub.cod_distrito
                FROM (
                    SELECT e2.id, d.cod_distrito
                    FROM edges e2
                    JOIN distritos d ON ST_Within(ST_Centroid(e2.geom), d.geom)
                ) sub
                WHERE e.id = sub.id
                """
            )
        )
        # Tramos cuyo centroide no cae en ningún distrito (p. ej. justo en el
        # límite exterior del municipio): se asignan al distrito más cercano.
        conn.execute(
            text(
                """
                UPDATE edges e
                SET cod_distrito = sub.cod_distrito
                FROM (
                    SELECT e2.id, d.cod_distrito
                    FROM edges e2
                    CROSS JOIN LATERAL (
                        SELECT cod_distrito
                        FROM distritos
                        ORDER BY geom <-> ST_Centroid(e2.geom)
                        LIMIT 1
                    ) d
                    WHERE e2.cod_distrito IS NULL
                ) sub
                WHERE e.id = sub.id
                """
            )
        )
    print("Tramos asignados a distrito (edges.cod_distrito).")
