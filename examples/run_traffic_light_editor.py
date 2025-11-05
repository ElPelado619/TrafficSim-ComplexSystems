#!/usr/bin/env python3
"""
Ejemplo de uso del editor interactivo de semáforos.

Este script demuestra cómo usar el editor de semáforos para
seleccionar nodos antes de la optimización genética.
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.traffic_light_editor import TrafficLightEditor, load_exclusions
import osmnx as ox


def main():
    """Ejecuta un ejemplo simple del editor de semáforos."""
    
    # Configuración
    graph_file = Path("data/microcentro.graphml")
    exclusions_file = Path("data/traffic_light_exclusions.json")
    min_degree = 3
    
    # Verificar que el archivo del grafo existe
    if not graph_file.exists():
        print(f"❌ Error: No se encontró el archivo del grafo: {graph_file}")
        print("   Asegúrate de tener los datos necesarios en el directorio data/")
        return 1
    
    print("=" * 60)
    print("Editor de Semáforos - Ejemplo")
    print("=" * 60)
    print()
    print("Este ejemplo te permite:")
    print("  1. Visualizar todos los nodos candidatos para semáforos")
    print("  2. Hacer click en nodos para incluirlos/excluirlos")
    print("  3. Guardar tus selecciones")
    print()
    print("Controles:")
    print("  - Click izquierdo: Toggle incluir/excluir nodo")
    print("  - [s]: Guardar cambios")
    print("  - [c]: Excluir todos")
    print("  - [r]: Incluir todos")
    print("  - [q]: Salir")
    print()
    print("=" * 60)
    print()
    
    # Cargar el grafo
    print(f"Cargando grafo desde: {graph_file}")
    if graph_file.suffix == '.osm':
        graph = ox.graph_from_xml(str(graph_file))
    else:
        graph = ox.load_graphml(str(graph_file))
    
    if not graph.is_directed():
        graph = graph.to_directed()
    
    print(f"✓ Grafo cargado: {len(graph.nodes)} nodos, {len(graph.edges)} aristas")
    print()
    
    # Cargar exclusiones existentes si hay
    existing_exclusions = None
    if exclusions_file.exists():
        existing_exclusions = load_exclusions(exclusions_file)
        print(f"✓ Cargadas {len(existing_exclusions)} exclusiones desde {exclusions_file}")
    else:
        print(f"ℹ️  No hay exclusiones previas. Se creará el archivo al guardar.")
    
    print()
    print(f"Identificando nodos candidatos (grado mínimo: {min_degree})...")
    
    # Crear el editor
    editor = TrafficLightEditor(
        graph,
        exclusions_file,
        min_degree=min_degree,
        existing_exclusions=existing_exclusions,
    )
    
    print(f"✓ {len(editor.candidate_nodes)} nodos candidatos identificados")
    included = len(editor.candidate_nodes) - len(editor.excluded_nodes)
    print(f"✓ {included} nodos incluidos, {len(editor.excluded_nodes)} excluidos")
    print()
    print("Abriendo editor interactivo...")
    print()
    
    # Ejecutar el editor
    try:
        editor.run()
    finally:
        editor.shutdown()
    
    # Guardar si hubo cambios
    if editor.changed:
        print()
        print("=" * 60)
        answer = input("¿Deseas guardar los cambios? [s/N]: ").strip().lower()
        if answer in {"s", "si", "y", "yes"}:
            editor.save(exclusions_file)
            print(f"✓ Cambios guardados en: {exclusions_file}")
            print()
            print("Puedes usar este archivo con el generador de semáforos:")
            print(f"  python generador_semaforos.py --exclusions {exclusions_file}")
        else:
            print("✗ Cambios descartados")
        print("=" * 60)
    else:
        print()
        print("No se realizaron cambios.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
