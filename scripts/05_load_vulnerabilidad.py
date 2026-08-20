import os

import pandas as pd
from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy import create_engine, text

BASE = Path(__file__).parent.parent
OVERWRITE = False  # Cambiar a True para vaciar y recargar la tabla aunque ya tenga datos

COLUMNAS = {
    "Codigo distrito": "cod_distrito",
    "Nombre distrito": "nombre_distrito",
    "Fecha datos": "anio",
    "Indice de Vulnerabilidad Territorial Agregado": "ivt_agregado",
    "Índice de Vulnerabilidad Bienestar Social e Igualdad": "ivt_bienestar_social_igualdad",
    "Índice de Vulnerabilidad Medio Ambiente Urbano y Movilidad": "ivt_medio_ambiente_movilidad",
    "Índice de Vulnerabilidad Educación y Cultura": "ivt_educacion_cultura",
    "Índice de Vulnerabilidad Economía y Empleo": "ivt_economia_empleo",
    "Índice de Vulnerabilidad Salud": "ivt_salud",
}

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

schema_sql = (BASE / "sql/04_vulnerabilidad.sql").read_text()
with engine.begin() as conn:
    conn.execute(text(schema_sql))

with engine.connect() as conn:
    ya_cargado = conn.execute(text("SELECT count(*) FROM vulnerabilidad_distritos")).scalar() > 0

if ya_cargado and not OVERWRITE:
    print("Vulnerabilidad por distrito ya cargada en la BD, no se hace nada (OVERWRITE=False).")
else:
    if ya_cargado:
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE vulnerabilidad_distritos"))

    xlsx_path = BASE / "data/raw/iguala/iguala_distritos_vulnerabilidad.xlsx"
    datos = pd.read_excel(xlsx_path, sheet_name="Vul. esferas distritos")[list(COLUMNAS)]
    datos = datos.rename(columns=COLUMNAS)

    # El fichero trae una fila por distrito y año (2020-2024); nos quedamos con
    # el año más reciente para tener un único valor de referencia por distrito.
    datos = datos[datos["anio"] == datos["anio"].max()]

    datos.to_sql("vulnerabilidad_distritos", engine, if_exists="append", index=False)
    print(f"Vulnerabilidad por distrito cargada: {len(datos)} distritos (año {datos['anio'].iloc[0]}).")
