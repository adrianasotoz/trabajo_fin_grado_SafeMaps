import osmnx as ox          # librería para trabajar con datos de OpenStreetMap
import geopandas as gpd     # librería para trabajar con datos geoespaciales
from pathlib import Path

BASE = Path(__file__).parent.parent

ox.settings.log_console = True  # Mostrar mensajes de log en terminal

# Descargar la red peatonal de Madrid
G = ox.graph_from_place("Madrid, Spain", network_type="walk") # Walk para caminos peatonales

# Alternativa menos pesada: solo un distrito
# G = ox.graph_from_place("Centro, Madrid, Spain", network_type="walk")

# Convertir el grafo a GeoDataFrames de nodos y aristas
nodes, edges = ox.graph_to_gdfs(G)

# Guardar para no repetir la descarga
ox.save_graphml(G, filepath=BASE / "data/raw/madrid_walk.graphml")
edges.to_file(BASE / "data/raw/madrid_edges.geojson", driver="GeoJSON") # GeoJSON mejor que Shapefile por espacio
nodes.to_file(BASE / "data/raw/madrid_nodes.geojson", driver="GeoJSON")

# Resumen de descarga
resumen = f"Zona: Madrid, Spain\nNodos: {len(nodes)}\nAristas: {len(edges)}\n"
(BASE / "data/raw/resumen.txt").write_text(resumen)

print(f"Nodos: {len(nodes)}")
print(f"Aristas: {len(edges)}")

