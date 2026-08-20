import json

from rutas import BASE, QUERY_EDGES, calcular_ruta, engine

if __name__ == "__main__":
    # Ejemplo: de Puerta del Sol a Plaza de Castilla.
    ORIGEN = (-3.7038, 40.4168)
    DESTINO = (-3.6890, 40.4660)

    with engine.connect() as conn:
        rutas = {criterio: calcular_ruta(conn, ORIGEN, DESTINO, criterio) for criterio in QUERY_EDGES}

    for criterio, ruta in rutas.items():
        print(
            f"Ruta {criterio}: {ruta['distancia_m']} m, "
            f"{ruta['num_tramos']} tramos, "
            f"peligrosidad media {ruta['peligrosidad_media']}"
        )

    salida = BASE / "data/processed/rutas_ejemplo.geojson"
    salida.parent.mkdir(parents=True, exist_ok=True)
    coleccion = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {k: v for k, v in ruta.items() if k != "geometry"}, "geometry": ruta["geometry"]}
            for ruta in rutas.values()
        ],
    }
    salida.write_text(json.dumps(coleccion))
    print(f"Rutas guardadas en {salida}")
