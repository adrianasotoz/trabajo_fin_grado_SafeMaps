# Sistema de Cálculo de Rutas Seguras en Entornos Urbanos Mediante Análisis Espacial

TFG de Ingeniería Informática — Universidad, Madrid.

Sistema que calcula rutas peatonales seguras en Madrid combinando la red viaria de OpenStreetMap con datos de iluminación pública, accidentes/atropellos y vulnerabilidad territorial para generar un índice de seguridad por tramo, y ofrece un visor web con buscador de direcciones para comparar la ruta más rápida con la más segura entre dos puntos.

---

## Estado del proyecto

| Componente | Estado |
|---|---|
| Estructura del proyecto | ✅ Hecho |
| Descarga de red viaria OSM | ✅ Hecho |
| Base de datos PostgreSQL + PostGIS + pgRouting | ✅ Hecho |
| ETL de fuentes de datos (OSM, farolas, accidentes, vulnerabilidad, distritos) | ✅ Hecho |
| Índice de seguridad por tramo | ✅ Hecho |
| Algoritmo de rutas (pgRouting) | ✅ Hecho |
| Visor web (Leaflet + Flask) | ✅ Hecho |

---

## Fuentes de datos

| Fuente | Datos | Estado |
|---|---|---|
| OpenStreetMap | Red viaria peatonal | ✅ Cargado en BD |
| Geoportal Madrid | Iluminación pública (farolas) | ✅ Cargado en BD |
| Datos Abiertos Madrid | Accidentes y atropellos (2023-2025) | ✅ Cargado en BD |
| Índice Iguala Madrid | Vulnerabilidad territorial por distrito | ✅ Cargado en BD |
| Geoportal Madrid | Límites administrativos de distritos | ✅ Cargado en BD |

---

## Estructura del proyecto

```
tfg_rutas_seguras/
├── data/
│   ├── raw/          # Datos originales descargados: osm, farolas, accidentes, iguala, distritos (no versionados)
│   └── processed/    # Datos transformados, p. ej. rutas de ejemplo (no versionados)
├── docs/             # Documentación y memoria del TFG
├── notebooks/        # Análisis exploratorio en Jupyter
├── scripts/          # Scripts ETL y de procesamiento, numerados por orden de ejecución
│   ├── 01_download_osm.py
│   ├── 02_load_osm_to_db.py
│   ├── 03_load_farolas.py
│   ├── 04_load_accidentes.py
│   ├── 05_load_vulnerabilidad.py
│   ├── 06_load_distritos.py
│   ├── 07_calcular_indice_seguridad.py
│   ├── 08_calcular_ruta.py
│   └── rutas.py      # Lógica de cálculo de rutas, reutilizada por 08 y por web/app.py
├── sql/              # Esquemas SQL, uno por fuente de datos
├── web/              # Visor web con Leaflet
│   ├── app.py
│   └── templates/index.html
├── requirements.txt
└── README.md
```

---

## Requisitos previos

- Python 3.10+
- PostgreSQL 16 con extensiones PostGIS 3.4 y pgRouting 3.6

---

## Instalación

```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/tfg_rutas_seguras.git
cd tfg_rutas_seguras

# Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

Crea un archivo `.env` en la raíz del proyecto con las credenciales de la base de datos `safe_maps`:

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=safe_maps
DB_USER=tu_usuario
DB_PASSWORD=tu_contraseña
```

---

## Uso

Cada script crea el esquema SQL que necesita (`sql/`) y es idempotente: si los datos ya están cargados no hace nada, salvo que se cambie `OVERWRITE = True` al inicio del script.

### 1. Descargar la red viaria de Madrid desde OSM

```bash
python scripts/01_download_osm.py
```

Genera en `data/raw/osm/`: `madrid_walk.graphml`, `madrid_edges.geojson`, `madrid_nodes.geojson` y `resumen.txt`.

### 2-6. Cargar los datos en la base de datos

```bash
python scripts/02_load_osm_to_db.py         # Red viaria (nodes, edges)
python scripts/03_load_farolas.py           # Iluminación pública
python scripts/04_load_accidentes.py        # Accidentes y atropellos
python scripts/05_load_vulnerabilidad.py    # Vulnerabilidad territorial por distrito
python scripts/06_load_distritos.py         # Polígonos de distritos + edges.cod_distrito
```

Cada uno de estos scripts espera los datos originales ya descargados en su carpeta correspondiente dentro de `data/raw/` (excepto OSM y distritos, que se descargan automáticamente).

### 7. Calcular el índice de seguridad por tramo

```bash
python scripts/07_calcular_indice_seguridad.py
```

Combina siniestralidad, atropellos, iluminación y vulnerabilidad territorial en `edges.indice_peligrosidad` (0-1) y en un coste penalizado `edges.cost_seguro` para pgRouting.

### 8. Calcular una ruta desde línea de comandos

```bash
python scripts/08_calcular_ruta.py
```

Calcula la ruta más rápida y la más segura entre dos puntos de ejemplo y las guarda en `data/processed/rutas_ejemplo.geojson`.

### Visor web

```bash
python web/app.py
```

Abre `http://127.0.0.1:5000/`. Marca el origen y el destino escribiendo una dirección (autocompletado vía Nominatim/OSM), usando el botón de geolocalización, o haciendo clic directamente en el mapa. Requiere conexión a internet para el buscador (llama a `nominatim.openstreetmap.org`).

El visor tiene dos modos, seleccionables en la parte superior del panel:

- **Simple** — muestra solo la ruta recomendada (la más segura), con distancia, duración estimada a pie y una insignia de nivel de seguridad (Muy segura / Segura / Moderada / Precaución).
- **Detallado** — dibuja ambas rutas (rápida y segura) y una tabla comparativa tramo a tramo: distancia, duración, peligrosidad media, iluminación, accidentes cercanos, atropellos registrados y vulnerabilidad del distrito, con indicadores en verde/rojo de en qué mejora o empeora la ruta segura frente a la rápida.

Otros detalles: botón para intercambiar origen y destino, y `GET /api/geocode` / `GET /api/geocode/inverso` como proxy propio a Nominatim (autocompletado y clic en el mapa).
