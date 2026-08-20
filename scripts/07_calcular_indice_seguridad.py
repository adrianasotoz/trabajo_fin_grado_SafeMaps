import os

from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy import create_engine, text

BASE = Path(__file__).parent.parent
OVERWRITE = False  # Cambiar a True para recalcular el índice aunque ya exista

# Pesos del índice de peligrosidad (suman 1). Atropellos y siniestralidad
# general pesan más por ser el indicador más directo y reciente del riesgo
# real en el tramo; la iluminación actúa como factor protector; la
# vulnerabilidad territorial es una señal más indirecta (socioeconómica, a
# nivel de distrito) y por eso pesa menos.
W_ATROPELLOS = 0.35
W_ACCIDENTES = 0.30
W_ILUMINACION = 0.20
W_VULNERABILIDAD = 0.15

# Cuánto penaliza el coste "seguro" a los tramos más peligrosos: el tramo con
# indice_peligrosidad = 1 cuesta (1 + ALPHA) veces su longitud real.
ALPHA = 4

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

schema_sql = (BASE / "sql/06_indice_seguridad.sql").read_text()
with engine.begin() as conn:
    conn.execute(text(schema_sql))

with engine.connect() as conn:
    ya_calculado = (
        conn.execute(text("SELECT count(*) FROM edges WHERE cost_seguro IS NOT NULL")).scalar() > 0
    )

if ya_calculado and not OVERWRITE:
    print("Índice de seguridad ya calculado, no se hace nada (OVERWRITE=False).")
else:
    with engine.connect() as conn:
        # Topes al percentil 99 para que los tramos casi puntuales (longitud
        # cercana a 0, con densidades por 100m desproporcionadas) no dominen
        # la normalización.
        cap_luz, cap_acc, cap_atropello = conn.execute(
            text(
                """
                SELECT percentile_cont(0.99) WITHIN GROUP (ORDER BY farolas_100m),
                       percentile_cont(0.99) WITHIN GROUP (ORDER BY accidentes_100m),
                       percentile_cont(0.99) WITHIN GROUP (ORDER BY num_atropellos)
                FROM edges
                """
            )
        ).fetchone()
        ivt_min, ivt_max = conn.execute(
            text("SELECT min(ivt_agregado), max(ivt_agregado) FROM vulnerabilidad_distritos")
        ).fetchone()

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE edges e
                SET indice_peligrosidad =
                      :w_acc * LEAST(e.accidentes_100m, :cap_acc) / :cap_acc
                    + :w_atr * LEAST(e.num_atropellos, :cap_atropello) / :cap_atropello
                    + :w_luz * (1 - LEAST(e.farolas_100m, :cap_luz) / :cap_luz)
                    + :w_vuln * (v.ivt_agregado - :ivt_min) / (:ivt_max - :ivt_min)
                FROM vulnerabilidad_distritos v
                WHERE v.cod_distrito = e.cod_distrito
                """
            ).bindparams(
                w_acc=W_ACCIDENTES,
                w_atr=W_ATROPELLOS,
                w_luz=W_ILUMINACION,
                w_vuln=W_VULNERABILIDAD,
                cap_acc=cap_acc,
                cap_atropello=cap_atropello,
                cap_luz=cap_luz,
                ivt_min=ivt_min,
                ivt_max=ivt_max,
            )
        )
        conn.execute(
            text(
                """
                UPDATE edges
                SET cost_seguro = length * (1 + :alpha * indice_peligrosidad),
                    reverse_cost_seguro = length * (1 + :alpha * indice_peligrosidad)
                """
            ).bindparams(alpha=ALPHA)
        )
    print("Índice de peligrosidad y coste seguro calculados para todos los tramos.")
