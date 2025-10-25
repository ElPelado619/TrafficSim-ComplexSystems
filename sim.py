import osmnx as ox

# Cargar el grafo de calles directamente desde tu archivo .osm
# Esto crea una representación matemática de tu mapa
graph = ox.graph_from_xml("data/map.osm")

# Guardar el grafo en un archivo GraphML
ox.save_graphml(graph, "data/map.graphml")

print("Grafo guardado en data/map.graphml")

# Opcional: Visualizar el grafo
ox.plot_graph(graph)

