import osmnx as ox

polygon = -68.86471, -32.90063, -68.82711, -32.88276

graph = ox.graph_from_bbox(polygon, network_type='drive')

# Guardar el grafo en un archivo GraphML
ox.save_graphml(graph, "data/independencia.graphml")

print("Grafo guardado en data/independencia.graphml")

# Opcional: Visualizar el grafo
ox.plot_graph(graph)

