# Sistema de Cálculo de Rutas Seguras en Entornos Urbanos Mediante Análisis Espacial

TFG de Ingeniería Informática — Universidad, Madrid.

Sistema que calcula rutas peatonales seguras en Madrid combinando la red viaria de OpenStreetMap con datos de iluminación pública, criminalidad y accidentes para generar un índice de seguridad por tramo.

---

## Estado del proyecto

| Componente | Estado |
|---|---|
| Estructura del proyecto | ✅ Hecho |
| Descarga de red viaria OSM | ✅ Hecho |
| Base de datos PostgreSQL + PostGIS | 🔄 En desarrollo |
| ETL de fuentes de datos | 🔄 En desarrollo |
| Algoritmo de rutas (pgRouting) | 🔄 En desarrollo |
| Visor web (Leaflet) | 🔄 En desarrollo |

---

## Fuentes de datos

| Fuente | Datos | Estado |
|---|---|---|
| OpenStreetMap | Red viaria peatonal | ✅ Conectado |
| Geoportal Madrid | Iluminación pública | Próximamente |
| Datos Abiertos Madrid | Criminalidad por distritos | Próximamente |
| Datos Abiertos Madrid | Accidentes y atropellos | Próximamente |

---

## Estructura del proyecto

```
tfg_rutas_seguras/
├── data/
│   ├── raw/          # Datos originales descargados (no versionados)
│   └── processed/    # Datos transformados (no versionados)
├── docs/             # Documentación y memoria del TFG
├── notebooks/        # Análisis exploratorio en Jupyter
├── scripts/          # Scripts ETL y de procesamiento
│   └── 01_download_osm.py
├── sql/              # Esquemas y consultas SQL
├── web/              # Visor web con Leaflet
├── requirements.txt
└── README.md
```

---

## Requisitos previos

- Python 3.10+
- PostgreSQL con extensiones PostGIS y pgRouting *(próximamente)*

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

---

## Uso

### Descargar la red viaria de Madrid desde OSM

```bash
python scripts/01_download_osm.py
```

Genera en `data/raw/`:
- `madrid_walk.graphml` — grafo de la red peatonal
- `madrid_edges.geojson` — aristas
- `madrid_nodes.geojson` — nodos
- `resumen.txt` — estadísticas de la descarga

> Para forzar una nueva descarga aunque los archivos ya existan, cambia `OVERWRITE = True` en el script.
