"""UT1-UT3: pruebas unitarias/de regresión de los scripts ETL (Sección 6.5, UT1-UT3)."""

import subprocess
import sys

import geopandas as gpd
from shapely.geometry import Point
from sqlalchemy import text

from geo_utils import filtrar_dentro_de_madrid

PUERTA_DEL_SOL = (-3.7038, 40.4168)  # dentro de Madrid
BARCELONA = (2.1734, 41.3851)  # claramente fuera de Madrid


def test_filtrar_dentro_de_madrid(base_dir):
    """UT2: descarta puntos fuera del límite municipal, conserva los de dentro."""
    puntos = gpd.GeoDataFrame(
        {"nombre": ["sol", "barcelona"]},
        geometry=[Point(*PUERTA_DEL_SOL), Point(*BARCELONA)],
        crs="EPSG:4326",
    )

    filtrado, n_descartados = filtrar_dentro_de_madrid(puntos, base_dir)

    assert n_descartados == 1
    assert list(filtrado["nombre"]) == ["sol"]


def test_idempotencia_accidentes_no_duplica(engine, base_dir):
    """UT1: con OVERWRITE=False, re-ejecutar el ETL no debe alterar la tabla ya cargada."""
    with engine.connect() as conn:
        n_antes = conn.execute(text("SELECT count(*) FROM accidentes")).scalar()
    assert n_antes > 0, "la tabla accidentes debe estar ya cargada para esta prueba"

    resultado = subprocess.run(
        [sys.executable, str(base_dir / "scripts/04_load_accidentes.py")],
        cwd=base_dir,
        capture_output=True,
        text=True,
        timeout=60,
    )

    with engine.connect() as conn:
        n_despues = conn.execute(text("SELECT count(*) FROM accidentes")).scalar()

    assert resultado.returncode == 0
    assert "no se hace nada" in resultado.stdout
    assert n_despues == n_antes


def test_indice_peligrosidad_acotado_percentil_99(engine):
    """UT3: el recorte al percentil 99 (Sección 3.5) mantiene indice_peligrosidad en [0, 1]."""
    with engine.connect() as conn:
        fuera_de_rango = conn.execute(
            text(
                "SELECT count(*) FROM edges "
                "WHERE indice_peligrosidad IS NOT NULL "
                "AND (indice_peligrosidad < 0 OR indice_peligrosidad > 1)"
            )
        ).scalar()
        total = conn.execute(
            text("SELECT count(*) FROM edges WHERE indice_peligrosidad IS NOT NULL")
        ).scalar()

    assert total > 0, "el índice de peligrosidad debe estar ya calculado para esta prueba"
    assert fuera_de_rango == 0
