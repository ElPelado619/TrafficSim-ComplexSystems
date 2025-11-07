#!/usr/bin/env python3
"""Interactive traffic light editor for the microcentro network.

This script allows users to visualize candidate nodes for traffic lights
and exclude specific intersections before running genetic optimization.

Usage example:

    python tools/traffic_light_editor.py --graph data/microcentro.graphml \
        --exclusions data/traffic_light_exclusions.json \
        --min-degree 3

Controls:
    * Press the 'm' key to toggle between traffic light and street editing modes.
    * Left-click on a node (traffic light mode) or edge (street mode) to toggle exclusion.
    * Press the 's' key to save the current exclusion list.
    * Press the 'c' key to clear all exclusions after confirmation.
    * Press the 'r' key to reset to candidate nodes/edges only.
    * Press the 'q' key to quit the editor.
"""
from __future__ import annotations

import argparse
import json
import sys
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import osmnx as ox
from matplotlib.backend_bases import MouseEvent


class EditMode(Enum):
    """Modes for the traffic light editor."""
    TRAFFIC_LIGHTS = "traffic_lights"
    STREETS = "streets"

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
        help="Archivo JSON con nodos y calles excluidos para cargar y editar",
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
    """Interactive editor for traffic light node selection and street deletion."""

    def __init__(
        self,
        graph: nx.MultiDiGraph,
        output_path: Path,
        min_degree: int = 3,
        existing_exclusions: Optional[Dict] = None,
    ) -> None:
        self.graph = graph
        self.output_path = output_path
        self.min_degree = min_degree
        self._tk_root = None

        # Current editing mode
        self.mode = EditMode.TRAFFIC_LIGHTS

        # Identificar todos los nodos candidatos
        self.candidate_nodes = identify_candidate_nodes(graph, min_degree)
        
        # Nodos excluidos (no tendrán semáforos)
        if existing_exclusions and "excluded_nodes" in existing_exclusions:
            self.excluded_nodes: Set[int] = set(existing_exclusions["excluded_nodes"])
        else:
            self.excluded_nodes: Set[int] = set()
        
        # Calles excluidas (serán eliminadas del grafo)
        if existing_exclusions and "excluded_edges" in existing_exclusions:
            self.excluded_edges: Set[Tuple[int, int, int]] = set(
                tuple(edge) for edge in existing_exclusions["excluded_edges"]
            )
        else:
            self.excluded_edges: Set[Tuple[int, int, int]] = set()
        
        # Asegurar que los nodos excluidos estén en los candidatos
        self.excluded_nodes = self.excluded_nodes.intersection(self.candidate_nodes)
        
        # Asegurar que las calles excluidas existan en el grafo
        existing_edge_keys = set()
        for u, v, key in self.graph.edges(keys=True):
            existing_edge_keys.add((u, v, key))
        self.excluded_edges = self.excluded_edges.intersection(existing_edge_keys)
        
        self.changed = False

        # Preparar coordenadas de nodos
        self.node_coords: Dict[int, tuple[float, float]] = {
            node: (data['x'], data['y'])
            for node, data in self.graph.nodes(data=True)
            if node in self.candidate_nodes
        }

        # Preparar coordenadas de calles (punto medio de cada edge)
        self.edge_coords: Dict[Tuple[int, int, int], tuple[float, float]] = {}
        self.edge_lines: Dict[Tuple[int, int, int], tuple[float, float, float, float]] = {}
        for u, v, key in self.graph.edges(keys=True):
            u_data = self.graph.nodes[u]
            v_data = self.graph.nodes[v]
            u_x, u_y = u_data['x'], u_data['y']
            v_x, v_y = v_data['x'], v_data['y']
            
            # Punto medio para detección de clicks
            mid_x = (u_x + v_x) / 2
            mid_y = (u_y + v_y) / 2
            self.edge_coords[(u, v, key)] = (mid_x, mid_y)
            
            # Línea completa para visualización
            self.edge_lines[(u, v, key)] = (u_x, u_y, v_x, v_y)

        # Crear figura
        self.fig, self.ax = plt.subplots(figsize=(14, 14))
        
        # Inicializar referencias a los artistas dibujados
        self.included_scatter = None
        self.excluded_scatter = None
        self.excluded_edge_lines = []

        # Dibujar grafo base y elementos
        self._draw_base_graph()
        self._draw_elements()

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
        """Maneja clicks en el canvas para seleccionar/deseleccionar elementos."""
        if event.inaxes != self.ax:
            return
        
        if event.button != 1:  # Solo click izquierdo
            return

        click_x, click_y = event.xdata, event.ydata
        if click_x is None or click_y is None:
            return

        if self.mode == EditMode.TRAFFIC_LIGHTS:
            self._handle_node_click(click_x, click_y)
        else:  # EditMode.STREETS
            self._handle_edge_click(click_x, click_y)

    def _handle_node_click(self, click_x: float, click_y: float) -> None:
        """Maneja clicks en nodos para el modo de semáforos."""
        min_dist = float('inf')
        closest_node = None

        for node_id, (x, y) in self.node_coords.items():
            dist = (x - click_x) ** 2 + (y - click_y) ** 2
            if dist < min_dist:
                min_dist = dist
                closest_node = node_id

        # Umbral de distancia para considerar el click
        threshold = 0.0001
        if closest_node is not None and min_dist < threshold:
            # Toggle exclusion status
            if closest_node in self.excluded_nodes:
                self.excluded_nodes.remove(closest_node)
                print(f"✅ Nodo {closest_node} incluido para semáforo")
            else:
                self.excluded_nodes.add(closest_node)
                print(f"❌ Nodo {closest_node} excluido de semáforos")
            
            self.changed = True
            self._draw_elements()

    def _handle_edge_click(self, click_x: float, click_y: float) -> None:
        """Maneja clicks en calles para el modo de calles."""
        min_dist = float('inf')
        closest_edge = None

        for edge_id, (x, y) in self.edge_coords.items():
            dist = (x - click_x) ** 2 + (y - click_y) ** 2
            if dist < min_dist:
                min_dist = dist
                closest_edge = edge_id

        # Umbral de distancia para considerar el click
        threshold = 0.0001
        if closest_edge is not None and min_dist < threshold:
            # Toggle exclusion status
            if closest_edge in self.excluded_edges:
                self.excluded_edges.remove(closest_edge)
                u, v, key = closest_edge
                print(f"✅ Calle {u}-{v} (key={key}) incluida")
            else:
                self.excluded_edges.add(closest_edge)
                u, v, key = closest_edge
                print(f"❌ Calle {u}-{v} (key={key}) excluida")
            
            self.changed = True
            self._draw_base_graph()
            self._draw_elements()

    def _on_key(self, event) -> None:
        """Maneja eventos de teclado."""
        if event.key == "s":
            self.save()
        elif event.key == "c":
            self._clear_all()
        elif event.key == "r":
            self._reset_to_candidates()
        elif event.key == "m":
            self._toggle_mode()
        elif event.key == "q":
            print("Cerrando editor...")
            plt.close(self.fig)

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------
    def _draw_base_graph(self) -> None:
        """Dibuja el grafo base con calles normales y excluidas."""
        self.ax.clear()
        
        # Reset artist references since we cleared the axes
        self.included_scatter = None
        self.excluded_scatter = None
        self.excluded_edge_lines = []
        
        # Dibujar todas las calles primero
        ox.plot_graph(
            self.graph,
            ax=self.ax,
            show=False,
            close=False,
            node_size=2,
            edge_color="lightgray",
            edge_linewidth=0.4,
        )
        
        # Dibujar calles excluidas en rojo y punteado
        for u, v, key in self.excluded_edges:
            if (u, v, key) in self.edge_lines:
                x1, y1, x2, y2 = self.edge_lines[(u, v, key)]
                line = self.ax.plot([x1, x2], [y1, y2], 
                                   color='red', linewidth=2, linestyle='--', 
                                   alpha=0.8, zorder=5)[0]
                self.excluded_edge_lines.append(line)

    def _draw_elements(self) -> None:
        """Dibuja los elementos según el modo actual."""
        if self.mode == EditMode.TRAFFIC_LIGHTS:
            self._draw_nodes()
        else:  # EditMode.STREETS
            self._draw_edges()
        self._update_title()

    def _draw_nodes(self) -> None:
        """Dibuja los nodos candidatos con colores según su estado."""
        # Remover scatter plots anteriores solo si existen y son válidos
        if self.included_scatter is not None:
            try:
                self.included_scatter.remove()
            except (ValueError, NotImplementedError):
                pass
            self.included_scatter = None
        if self.excluded_scatter is not None:
            try:
                self.excluded_scatter.remove()
            except (ValueError, NotImplementedError):
                pass
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
                label=f'Semáforos incluidos ({len(included_nodes)})',
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
                label=f'Semáforos excluidos ({len(self.excluded_nodes)})',
                picker=True,
            )

        # Actualizar leyenda
        self.ax.legend(loc='upper right', fontsize=10)
        self.fig.canvas.draw_idle()

    def _draw_edges(self) -> None:
        """Dibuja las calles con colores según su estado de exclusión."""
        # Remover scatter plots de nodos solo si existen y son válidos
        if self.included_scatter is not None:
            try:
                self.included_scatter.remove()
            except (ValueError, NotImplementedError):
                pass
            self.included_scatter = None
        if self.excluded_scatter is not None:
            try:
                self.excluded_scatter.remove()
            except (ValueError, NotImplementedError):
                pass
            self.excluded_scatter = None

        # Dibujar puntos medios de calles para interacción
        all_edges = set(self.edge_coords.keys())
        included_edges = all_edges - self.excluded_edges
        
        if included_edges:
            included_coords = np.array([self.edge_coords[edge] for edge in included_edges])
            self.included_scatter = self.ax.scatter(
                included_coords[:, 0],
                included_coords[:, 1],
                s=30,
                color='blue',
                alpha=0.5,
                edgecolors='darkblue',
                linewidths=1,
                zorder=10,
                label=f'Calles incluidas ({len(included_edges)})',
                picker=True,
            )

        if self.excluded_edges:
            excluded_coords = np.array([self.edge_coords[edge] for edge in self.excluded_edges])
            self.excluded_scatter = self.ax.scatter(
                excluded_coords[:, 0],
                excluded_coords[:, 1],
                s=30,
                color='red',
                alpha=0.7,
                edgecolors='darkred',
                linewidths=1,
                zorder=10,
                label=f'Calles excluidas ({len(self.excluded_edges)})',
                picker=True,
            )

        # Actualizar leyenda
        self.ax.legend(loc='upper right', fontsize=10)
        self.fig.canvas.draw_idle()

    def _update_title(self) -> None:
        """Actualiza el título con las estadísticas actuales y el modo."""
        if self.mode == EditMode.TRAFFIC_LIGHTS:
            included_count = len(self.candidate_nodes) - len(self.excluded_nodes)
            mode_text = "MODO: Semáforos"
            stats_text = f"{len(self.candidate_nodes)} candidatos, {included_count} incluidos, {len(self.excluded_nodes)} excluidos"
            instructions = "Click en un nodo para incluir/excluir."
        else:  # EditMode.STREETS
            all_edges_count = len(self.edge_coords)
            included_count = all_edges_count - len(self.excluded_edges)
            mode_text = "MODO: Calles"
            stats_text = f"{all_edges_count} calles, {included_count} incluidas, {len(self.excluded_edges)} excluidas"
            instructions = "Click en una calle para incluir/excluir."
        
        self.ax.set_title(
            f"{mode_text} - {stats_text}\n"
            f"{instructions} [m] cambiar modo, [s] guardar, [c] limpiar, [r] resetear, [q] salir"
        )
        self.fig.canvas.draw_idle()

    # ------------------------------------------------------------------
    # Action helpers
    # ------------------------------------------------------------------
    def _toggle_mode(self) -> None:
        """Alterna entre modo de semáforos y modo de calles."""
        if self.mode == EditMode.TRAFFIC_LIGHTS:
            self.mode = EditMode.STREETS
            print("🔄 Cambiando a modo CALLES")
        else:
            self.mode = EditMode.TRAFFIC_LIGHTS
            print("🔄 Cambiando a modo SEMÁFOROS")
        
        self._draw_base_graph()
        self._draw_elements()

    def _clear_all(self) -> None:
        """Excluye todos los elementos según el modo actual."""
        if self.mode == EditMode.TRAFFIC_LIGHTS:
            self._clear_all_nodes()
        else:
            self._clear_all_edges()

    def _clear_all_nodes(self) -> None:
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
        self._draw_elements()
        print("🧹 Todos los nodos candidatos fueron excluidos.")

    def _clear_all_edges(self) -> None:
        """Excluye todas las calles."""
        root = self._ensure_tk_root()
        if root is None or messagebox is None:
            print("⚠️  No hay cuadros de diálogo disponibles. Confirme manualmente.")
            answer = input("¿Excluir todas las calles? [y/N]: ").strip().lower()
            if answer not in {"y", "yes", "s", "si"}:
                print("Operación cancelada.")
                return
        else:
            confirm = messagebox.askyesno(
                "Excluir todas",
                "¿Excluir todas las calles?",
                parent=root,
                default=messagebox.NO,
            )
            if not confirm:
                print("Operación cancelada.")
                return

        self.excluded_edges = set(self.edge_coords.keys())
        self.changed = True
        self._draw_base_graph()
        self._draw_elements()
        print("🧹 Todas las calles fueron excluidas.")

    def _reset_to_candidates(self) -> None:
        """Resetea las exclusiones según el modo actual."""
        if self.mode == EditMode.TRAFFIC_LIGHTS:
            self._reset_nodes()
        else:
            self._reset_edges()

    def _reset_nodes(self) -> None:
        """Resetea las exclusiones de nodos (incluye todos los candidatos)."""
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
        self._draw_elements()
        print("🔄 Se incluyeron todos los nodos candidatos.")

    def _reset_edges(self) -> None:
        """Resetea las exclusiones de calles (incluye todas las calles)."""
        root = self._ensure_tk_root()
        if root is None or messagebox is None:
            print("⚠️  No hay cuadros de diálogo disponibles. Confirme manualmente.")
            answer = input("¿Resetear e incluir todas las calles? [y/N]: ").strip().lower()
            if answer not in {"y", "yes", "s", "si"}:
                print("Operación cancelada.")
                return
        else:
            confirm = messagebox.askyesno(
                "Resetear",
                "¿Limpiar exclusiones e incluir todas las calles?",
                parent=root,
                default=messagebox.NO,
            )
            if not confirm:
                print("Operación cancelada.")
                return

        self.excluded_edges.clear()
        self.changed = True
        self._draw_base_graph()
        self._draw_elements()
        print("🔄 Se incluyeron todas las calles.")

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def serialize(self) -> dict:
        """Serializa las exclusiones a un diccionario."""
        return {
            "excluded_nodes": sorted(int(node) for node in self.excluded_nodes),
            "excluded_edges": sorted([int(u), int(v), int(k)] for u, v, k in self.excluded_edges),
            "total_candidates": len(self.candidate_nodes),
            "total_edges": len(self.edge_coords),
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
        included_nodes = len(self.candidate_nodes) - len(self.excluded_nodes)
        included_edges = len(self.edge_coords) - len(self.excluded_edges)
        print(f"💾 Exclusiones guardadas en {path}")
        print(f"   Semáforos: {included_nodes} incluidos, {len(self.excluded_nodes)} excluidos")
        print(f"   Calles: {included_edges} incluidas, {len(self.excluded_edges)} excluidas")

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


def load_exclusions(path: Path) -> Dict:
    """Carga las exclusiones desde un archivo JSON."""
    if not path.exists():
        return {}
    
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    
    return data


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
        excluded_nodes = existing_exclusions.get("excluded_nodes", [])
        excluded_edges = existing_exclusions.get("excluded_edges", [])
        print(f"Cargadas {len(excluded_nodes)} exclusiones de nodos y {len(excluded_edges)} exclusiones de calles desde {args.exclusions}")

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
    print(f"✓ {len(editor.edge_coords)} calles totales")
    print(f"✓ {len(editor.excluded_edges)} calles ya excluidas")
    print(f"✓ Iniciando en modo: {editor.mode.value}")
    
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
