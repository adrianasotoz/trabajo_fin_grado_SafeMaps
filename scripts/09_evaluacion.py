"""Evaluación comparativa entre la ruta rápida y la ruta segura.

Calcula ambos criterios de enrutamiento (Sección 3.5 de la memoria) sobre un
conjunto de pares origen-destino representativos de Madrid, y vuelca los
resultados en data/processed/evaluacion_rutas.csv para su análisis en el
Capítulo 6 (Pruebas y validación).
"""

import csv

from rutas import BASE, QUERY_EDGES, calcular_ruta, engine

# Pares origen-destino (lon, lat) elegidos para cubrir distancias cortas,
# medias y largas, y distritos con distinto nivel de vulnerabilidad
# territorial (Sección 5... / Tabla vulnerabilidad_distritos).
CASOS = [
    ("Puerta del Sol -> Atocha", (-3.7038, 40.4169), (-3.6903, 40.4066)),
    ("Callao -> Puerta de Alcalá", (-3.7052, 40.4200), (-3.6883, 40.4204)),
    ("Nuevos Ministerios -> Cuatro Caminos", (-3.6926, 40.4459), (-3.7068, 40.4457)),
    ("Plaza Elíptica -> Puente de Vallecas", (-3.7143, 40.3839), (-3.6608, 40.3930)),
    ("Moncloa -> Ciudad Universitaria", (-3.7196, 40.4356), (-3.7276, 40.4459)),
    ("Villaverde Alto -> Usera", (-3.7017, 40.3459), (-3.7062, 40.3839)),
    ("Chamartín -> Hortaleza", (-3.6829, 40.4725), (-3.6412, 40.4680)),
    ("Vicálvaro -> Villa de Vallecas", (-3.6055, 40.4039), (-3.6122, 40.3760)),
]

CAMPOS = [
    "caso", "criterio", "distancia_m", "duracion_min", "num_tramos",
    "peligrosidad_media", "iluminacion_media", "accidentes_media",
    "atropellos_total", "vulnerabilidad_media",
]

if __name__ == "__main__":
    filas = []
    with engine.connect() as conn:
        for nombre, origen, destino in CASOS:
            for criterio in QUERY_EDGES:
                ruta = calcular_ruta(conn, origen, destino, criterio)
                ruta["caso"] = nombre
                filas.append({k: ruta[k] for k in CAMPOS})
                print(
                    f"{nombre:42s} [{criterio:6s}] "
                    f"{ruta['distancia_m']:>7.1f} m  "
                    f"{ruta['duracion_min']:>5.1f} min  "
                    f"p={ruta['peligrosidad_media']:.4f}  "
                    f"atropellos={ruta['atropellos_total']}"
                )

    salida = BASE / "data/processed/evaluacion_rutas.csv"
    salida.parent.mkdir(parents=True, exist_ok=True)
    with open(salida, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS)
        writer.writeheader()
        writer.writerows(filas)
    print(f"\nResultados guardados en {salida}")
