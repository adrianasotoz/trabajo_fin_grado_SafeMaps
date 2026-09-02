"""Utilidades geoespaciales compartidas por los scripts ETL y sus tests."""

import geopandas as gpd

DISTRITOS_SHP = "data/raw/distritos/DISTRITOS.shp"


def limite_madrid(base_dir):
    """Polígono (EPSG:4326) de la unión de los 21 distritos de Madrid."""
    return gpd.read_file(base_dir / DISTRITOS_SHP).to_crs("EPSG:4326").union_all()


def filtrar_dentro_de_madrid(gdf, base_dir):
    """Descarta las filas de `gdf` (EPSG:4326) cuyo punto cae fuera de Madrid.

    Devuelve (gdf_filtrado, n_descartados).
    """
    limite = limite_madrid(base_dir)
    n_antes = len(gdf)
    dentro = gdf[gdf.within(limite)]
    return dentro, n_antes - len(dentro)
