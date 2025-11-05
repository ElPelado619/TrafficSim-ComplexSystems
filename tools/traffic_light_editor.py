#!/usr/bin/env python3
"""Interactive traffic light editor for the microcentro network.

This script allows users to visualize candidate nodes for traffic lights
and exclude specific intersections before running genetic optimization.

Usage example:

    python tools/traffic_light_editor.py --graph data/microcentro.graphml \
        --exclusions data/traffic_light_exclusions.json \
        --min-degree 3

Controls:
    * Left-click on a node to toggle its exclusion status.
    * Press the 's' key to save the current exclusion list.
    * Press the 'c' key to clear all exclusions after confirmation.
    * Press the 'r' key to reset to candidate nodes only.
    * Press the 'q' key to quit the editor.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Optional, Set

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import osmnx as ox
from matplotlib.backend_bases import MouseEvent

try:
    import tkinter as tk
    from tkinter import messagebox
except Exception:  # noqa: BLE001 - Tk puede no estar disponible en algunos entornos
    tk = None
    messagebox = None

# Make project root importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Editor interactivo de semáforos para el microcentro"
    )
    parser.add_argument(
        "--graph",
        type=Path,
        default=Path("data/microcentro.graphml"),
        help="Archivo GraphML del grafo base",
    )
    parser.add_argument(
        "--exclusions",
        type=Path,
        help="Archivo JSON con nodos excluidos para cargar y editar",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/traffic_light_exclusions.json"),
        help="Ruta del archivo JSON de salida (por defecto data/traffic_light_exclusions.json)",
    )
    parser.add_argument(
        "--min-degree",
        type=int,
        default=3,
        help="Grado mínimo de nodo para considerarlo candidato a semáforo",
    )
    parser.add_argument(
        "--auto-save",
        action="store_true",
        help="Guarda automáticamente al salir si hubo cambios",
    )
    return parser.parse_args()


def identify_candidate_nodes(graph: nx.MultiDiGraph, min_degree: int = 3) -> Set[int]:
    """Identifica nodos candidatos para semáforos (intersecciones importantes)."""
    candidates = set()
    
    # Identificar nodos que son parte de rotondas
    roundabout_nodes = set()
    for u, v, key, data in graph.edges(keys=True, data=True):
        if 'junction' in data:
            junction_type = data['junction']
            if junction_type in ['roundabout', 'circular']:
                roundabout_nodes.add(u)
                roundabout_nodes.add(v)
    
    for node_id in graph.nodes():
        # Excluir nodos que son parte de rotondas
        if node_id in roundabout_nodes:
            continue
        
        # Contar grado del nodo (entradas + salidas)
        in_degree = graph.in_degree(node_id)
        out_degree = graph.out_degree(node_id)
        total_degree = in_degree + out_degree
        
        # Considerar nodos con suficiente conectividad
        if total_degree >= min_degree:
            candidates.add(node_id)
    
    return candidates


class TrafficLightEditor:
    """Interactive editor for traffic light node selection."""

    def __init__(
        self,
        graph: nx.MultiDiGraph,
        output_path: Path,
        min_degree: int = 3,
        existing_exclusions: Optional[Set[int]] = None,
    ) -> None:
        self.graph = graph
        self.output_path = output_path
        self.min_degree = min_degree
        self._tk_root = None

        # Identificar todos los nodos candidatos
        self.candidate_nodes = identify_candidate_nodes(graph, min_degree)
        
        # Nodos excluidos (no tendrán semáforos)
        self.excluded_nodes: Set[int] = existing_exclusions or set()
        
        # Asegurar que los nodos excluidos estén en los candidatos
        self.excluded_nodes = self.excluded_nodes.intersection(self.candidate_nodes)
        
        self.changed = False

        # Preparar coordenadas de nodos
        self.node_coords: Dict[int, tuple[float, float]] = {
            node: (data['x'], data['y'])
            for node, data in self.graph.nodes(data=True)
            if node in self.candidate_nodes
        }

        # Crear figura
        self.fig, self.ax = plt.subplots(figsize=(14, 14))
        ox.plot_graph(
            self.graph,
            ax=self.ax,
            show=False,
            close=False,
            node_size=2,
            edge_color="lightgray",
            edge_linewidth=0.4,
        )

        self.ax.set_title(
            f"Editor de Semáforos - {len(self.candidate_nodes)} candidatos, "
            f"{len(self.excluded_nodes)} excluidos\n"
            "Click en un nodo para incluir/excluir. "
            "[s] guardar, [c] limpiar, [r] resetear, [q] salir"
        )

        # Inicializar referencias a los artistas dibujados
        self.included_scatter = None
        self.excluded_scatter = None

        # Dibujar nodos candidatos
        self._draw_nodes()

        # Conectar eventos
        self.fig.canvas.mpl_connect("button_press_event", self._on_click)
        self.fig.canvas.mpl_connect("key_press_event", self._on_key)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def _ensure_tk_root(self) -> Optional[object]:
        if tk is None:
            return None
        if self._tk_root is None:
            root = tk.Tk()
            root.withdraw()
            self._tk_root = root
        return self._tk_root

    def _on_click(self, event: MouseEvent) -> None:
        """Maneja clicks en el canvas para seleccionar/deseleccionar nodos."""
        if event.inaxes != self.ax:
            return
        
        if event.button != 1:  # Solo click izquierdo
            return

        # Encontrar el nodo más cercano al click
        click_x, click_y = event.xdata, event.ydata
        if click_x is None or click_y is None:
            return

        min_dist = float('inf')
        closest_node = None

        for node_id, (x, y) in self.node_coords.items():
            dist = (x - click_x) ** 2 + (y - click_y) ** 2
            if dist < min_dist:
                min_dist = dist
                closest_node = node_id

        # Umbral de distancia para considerar el click (en unidades del gráfico)
        threshold = 0.0001  # Ajustar según sea necesario
        if closest_node is not None and min_dist < threshold:
            # Toggle exclusion status
            if closest_node in self.excluded_nodes:
                self.excluded_nodes.remove(closest_node)
                print(f"✅ Nodo {closest_node} incluido para semáforo")
            else:
                self.excluded_nodes.add(closest_node)
                print(f"❌ Nodo {closest_node} excluido de semáforos")
            
            self.changed = True
            self._draw_nodes()
            self._update_title()

    def _on_key(self, event) -> None:
        """Maneja eventos de teclado."""
        if event.key == "s":
            self.save()
        elif event.key == "c":
            self._clear_all()
        elif event.key == "r":
            self._reset_to_candidates()
        elif event.key == "q":
            print("Cerrando editor...")
            plt.close(self.fig)

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------
    def _draw_nodes(self) -> None:
        """Dibuja los nodos candidatos con colores según su estado."""
        # Remover scatter plots anteriores
        if self.included_scatter is not None:
            self.included_scatter.remove()
            self.included_scatter = None
        if self.excluded_scatter is not None:
            self.excluded_scatter.remove()
            self.excluded_scatter = None

        # Separar nodos incluidos y excluidos
        included_nodes = self.candidate_nodes - self.excluded_nodes
        
        if included_nodes:
            included_coords = np.array([self.node_coords[n] for n in included_nodes])
            self.included_scatter = self.ax.scatter(
                included_coords[:, 0],
                included_coords[:, 1],
                s=50,
                color='green',
                alpha=0.6,
                edgecolors='darkgreen',
                linewidths=1,
                zorder=10,
                label=f'Incluidos ({len(included_nodes)})',
                picker=True,
            )

        if self.excluded_nodes:
            excluded_coords = np.array([self.node_coords[n] for n in self.excluded_nodes])
            self.excluded_scatter = self.ax.scatter(
                excluded_coords[:, 0],
                excluded_coords[:, 1],
                s=50,
                color='red',
                alpha=0.6,
                edgecolors='darkred',
                linewidths=1,
                zorder=10,
                label=f'Excluidos ({len(self.excluded_nodes)})',
                picker=True,
            )

        # Actualizar leyenda
        self.ax.legend(loc='upper right', fontsize=10)
        
        self.fig.canvas.draw_idle()

    def _update_title(self) -> None:
        """Actualiza el título con las estadísticas actuales."""
        included_count = len(self.candidate_nodes) - len(self.excluded_nodes)
        self.ax.set_title(
            f"Editor de Semáforos - {len(self.candidate_nodes)} candidatos, "
            f"{included_count} incluidos, {len(self.excluded_nodes)} excluidos\n"
            "Click en un nodo para incluir/excluir. "
            "[s] guardar, [c] limpiar, [r] resetear, [q] salir"
        )
        self.fig.canvas.draw_idle()

    # ------------------------------------------------------------------
    # Action helpers
    # ------------------------------------------------------------------
    def _clear_all(self) -> None:
        """Excluye todos los nodos candidatos."""
        root = self._ensure_tk_root()
        if root is None or messagebox is None:
            print("⚠️  No hay cuadros de diálogo disponibles. Confirme manualmente.")
            answer = input("¿Excluir todos los nodos? [y/N]: ").strip().lower()
            if answer not in {"y", "yes", "s", "si"}:
                print("Operación cancelada.")
                return
        else:
            confirm = messagebox.askyesno(
                "Excluir todos",
                "¿Excluir todos los nodos candidatos?",
                parent=root,
                default=messagebox.NO,
            )
            if not confirm:
                print("Operación cancelada.")
                return

        self.excluded_nodes = self.candidate_nodes.copy()
        self.changed = True
        self._draw_nodes()
        self._update_title()
        print("🧹 Todos los nodos candidatos fueron excluidos.")
        if self.output_path is not None:
            self.save(self.output_path)

    def _reset_to_candidates(self) -> None:
        """Resetea las exclusiones (incluye todos los candidatos)."""
        root = self._ensure_tk_root()
        if root is None or messagebox is None:
            print("⚠️  No hay cuadros de diálogo disponibles. Confirme manualmente.")
            answer = input("¿Resetear e incluir todos los candidatos? [y/N]: ").strip().lower()
            if answer not in {"y", "yes", "s", "si"}:
                print("Operación cancelada.")
                return
        else:
            confirm = messagebox.askyesno(
                "Resetear",
                "¿Limpiar exclusiones e incluir todos los candidatos?",
                parent=root,
                default=messagebox.NO,
            )
            if not confirm:
                print("Operación cancelada.")
                return

        self.excluded_nodes.clear()
        self.changed = True
        self._draw_nodes()
        self._update_title()
        print("🔄 Se incluyeron todos los nodos candidatos.")
        if self.output_path is not None:
            self.save(self.output_path)

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def serialize(self) -> dict:
        """Serializa las exclusiones a un diccionario."""
        return {
            "excluded_nodes": sorted(int(node) for node in self.excluded_nodes),
            "total_candidates": len(self.candidate_nodes),
            "min_degree": self.min_degree,
        }

    def save(self, path: Optional[Path] = None) -> None:
        """Guarda las exclusiones en un archivo JSON."""
        path = path or self.output_path
        if path is None:
            print("❌ No se especificó archivo de salida.")
            return
        
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self.serialize()
        
        with path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        
        self.changed = False
        included_count = len(self.candidate_nodes) - len(self.excluded_nodes)
        print(f"💾 Exclusiones guardadas en {path}")
        print(f"   {included_count} nodos incluidos, {len(self.excluded_nodes)} excluidos")

    def run(self) -> None:
        """Ejecuta el editor (muestra la ventana interactiva)."""
        plt.show()

    def shutdown(self) -> None:
        """Limpia recursos."""
        if self._tk_root is not None:
            try:
                self._tk_root.destroy()
            except Exception:  # noqa: BLE001
                pass
            self._tk_root = None


def load_exclusions(path: Path) -> Set[int]:
    """Carga las exclusiones desde un archivo JSON."""
    if not path.exists():
        return set()
    
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    
    return set(data.get("excluded_nodes", []))


def main() -> None:
    args = parse_args()

    # Cargar grafo
    if args.graph.suffix == '.osm':
        graph = ox.graph_from_xml(str(args.graph))
    else:
        graph = ox.load_graphml(str(args.graph))
    
    if not graph.is_directed():
        graph = graph.to_directed()

    # Cargar exclusiones existentes
    existing_exclusions = None
    if args.exclusions and args.exclusions.exists():
        existing_exclusions = load_exclusions(args.exclusions)
        print(f"Cargadas {len(existing_exclusions)} exclusiones desde {args.exclusions}")

    output_path = args.output or args.exclusions or Path("data/traffic_light_exclusions.json")

    print(f"Identificando nodos candidatos (grado mínimo: {args.min_degree})...")
    editor = TrafficLightEditor(
        graph,
        output_path,
        min_degree=args.min_degree,
        existing_exclusions=existing_exclusions,
    )
    
    print(f"✓ {len(editor.candidate_nodes)} nodos candidatos identificados")
    print(f"✓ {len(editor.excluded_nodes)} nodos ya excluidos")
    
    try:
        editor.run()
    finally:
        editor.shutdown()

    if editor.changed:
        if args.auto_save:
            editor.save(output_path)
        else:
            answer = input("¿Guardar cambios? [y/N]: ").strip().lower()
            if answer in {"y", "yes", "s", "si"}:
                editor.save(output_path)
            else:
                print("Cambios descartados (no se guardó el archivo).")


if __name__ == "__main__":
    main()
