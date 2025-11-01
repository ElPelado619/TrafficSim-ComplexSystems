#!/usr/bin/env python3
"""Interactive zone editor for the microcentro network.

This script allows users to draw polygonal zones on top of the microcentro
street network, associate them with network nodes, and persist the resulting
configuration as the JSON structure consumed by the O-D generator.

Usage example:

    python tools/zone_builder.py --graph data/microcentro.graphml \
        --zones data/microcentro_zones.json

Controls:
    * Draw a polygon by left-clicking points; double-click to finish.
    * After closing a polygon you will be prompted for the zone name and
      (optionally) production/attraction factors.
    * Press the 's' key to save the current zone definitions.
    * Press the 'u' key to undo (remove) the most recently added/edited zone.
    * Press the 'd' key to delete a zone by name.
    * Press the 'c' key to clear all zones after confirmation.
    * Press the 'q' key to quit the editor.
"""
from __future__ import annotations

import argparse
import json
import sys
from itertools import cycle
from pathlib import Path
from typing import Dict, Iterable, Optional

import matplotlib.pyplot as plt
import numpy as np
import osmnx as ox
from matplotlib import patches
from matplotlib.path import Path as MplPath
from matplotlib.widgets import PolygonSelector

try:
    import tkinter as tk
    from tkinter import messagebox, simpledialog
except Exception:  # noqa: BLE001 - Tk puede no estar disponible en algunos entornos
    tk = None
    messagebox = None
    simpledialog = None

# Make project root importable to reuse helper utilities
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import generador_od  # noqa: E402  (import after path mutation)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Editor interactivo de zonas para el microcentro")
    parser.add_argument(
        "--graph",
        type=Path,
        default=Path("data/microcentro.graphml"),
        help="Archivo GraphML del grafo base",
    )
    parser.add_argument(
        "--zones",
        type=Path,
        help="Archivo JSON existente con zonas para cargar y editar",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Ignora las zonas existentes aunque se provea --zones",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/O-D-maps/microcentro_zones.json"),
        help="Ruta del archivo JSON de salida (por defecto data/O-D-maps/microcentro_zones.json)",
    )
    parser.add_argument(
        "--auto-save",
        action="store_true",
        help="Guarda automáticamente al salir si hubo cambios",
    )
    return parser.parse_args()


def monotonic_chain(points: Iterable[tuple[float, float]]) -> list[tuple[float, float]]:
    """Compute the convex hull of a set of 2D points using the monotonic chain algorithm."""
    pts = sorted(set(points))
    if len(pts) <= 1:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list[tuple[float, float]] = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)

    upper: list[tuple[float, float]] = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    hull = lower[:-1] + upper[:-1]
    return hull if hull else pts


class ZoneEditor:
    """Interactive builder that maps polygons to graph nodes."""

    def __init__(self, graph, output_path: Path, existing_data: Optional[dict] = None) -> None:
        self.graph = graph
        self.output_path = output_path
        self._tk_root = None

        self.zone_nodes: Dict[str, set[int]] = {}
        self.zone_polygons: Dict[str, list[tuple[float, float]]] = {}
        self.zone_productions: Dict[str, float] = {}
        self.zone_attractions: Dict[str, float] = {}
        self.zone_order: list[str] = []
        self.zone_artists: Dict[str, list] = {}
        self.changed = False

        if existing_data:
            self._ingest_existing(existing_data)

        self.fig, self.ax = plt.subplots(figsize=(12, 12))
        ox.plot_graph(
            self.graph,
            ax=self.ax,
            show=False,
            close=False,
            node_size=4,
            edge_color="lightgray",
            edge_linewidth=0.5,
        )

        self.ax.set_title(
            "Editor de zonas - dibuja un polígono (doble click para cerrar)."
            "\nTeclas: [s] guardar, [u] deshacer, [d] borrar zona, [q] salir"
        )

        self.color_cycle = cycle(plt.cm.tab20.colors)
        self.zone_colors: Dict[str, tuple[float, float, float, float]] = {}
        for zone in self.zone_order:
            self.zone_colors[zone] = next(self.color_cycle)

        # Draw existing zones after color assignment
        for zone in self.zone_order:
            self._draw_zone(zone)

        self.selector = None
        self._install_selector()
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

    def _prompt_text(self, title: str, prompt: str, default: Optional[str] = None) -> Optional[str]:
        root = self._ensure_tk_root()
        if root is None or simpledialog is None:
            print("⚠️  No hay soporte para cuadros de diálogo (Tkinter ausente). Zona cancelada.")
            return None
        result = simpledialog.askstring(title, prompt, initialvalue=default or "", parent=root)
        if result is None:
            return None
        return result.strip()

    def _prompt_float(self, title: str, prompt: str, default: Optional[float]) -> Optional[float]:
        root = self._ensure_tk_root()
        if root is None or simpledialog is None:
            print("⚠️  No hay soporte para cuadros de diálogo (Tkinter ausente). Se mantiene el valor por defecto.")
            return default
        return simpledialog.askfloat(title, prompt, initialvalue=default, parent=root)

    def _on_polygon_complete(self, vertices: list[tuple[float, float]]) -> None:
        if len(vertices) < 3:
            print("Se requieren al menos 3 puntos para definir una zona.")
            return

        path = MplPath(vertices)
        nodes_inside = [
            node
            for node, data in self.graph.nodes(data=True)
            if path.contains_point((data["x"], data["y"]))
        ]

        if not nodes_inside:
            print("⚠️  El polígono no contiene nodos del grafo. Zona no creada.")
            return

        zone_name = self._prompt_text("Nueva zona", "Nombre de la zona:")
        if not zone_name:
            print("⚠️  Zona cancelada (nombre vacío o diálogo cerrado).")
            return

        if zone_name not in self.zone_colors:
            self.zone_colors[zone_name] = next(self.color_cycle)

        production = self._prompt_float(
            "Producción",
            "Factor de producción (P):",
            self.zone_productions.get(zone_name),
        )
        attraction = self._prompt_float(
            "Atracción",
            "Factor de atracción (A):",
            self.zone_attractions.get(zone_name),
        )

        self.zone_nodes[zone_name] = set(nodes_inside)
        self.zone_polygons[zone_name] = [(float(x), float(y)) for x, y in vertices]
        if production is not None:
            self.zone_productions[zone_name] = production
        elif zone_name in self.zone_productions:
            del self.zone_productions[zone_name]
        if attraction is not None:
            self.zone_attractions[zone_name] = attraction
        elif zone_name in self.zone_attractions:
            del self.zone_attractions[zone_name]

        if zone_name in self.zone_order:
            self.zone_order.remove(zone_name)
        self.zone_order.append(zone_name)

        self._draw_zone(zone_name)
        self.changed = True
        print(f"✅ Zona '{zone_name}' registrada con {len(nodes_inside)} nodos.")
        if self.output_path is not None:
            self.save(self.output_path)
        self._reset_selector()

    def _on_key(self, event) -> None:
        if event.key == "s":
            self.save()
        elif event.key == "u":
            self._undo_last()
        elif event.key == "d":
            self._delete_zone_prompt()
        elif event.key == "c":
            self._clear_all()
        elif event.key == "q":
            print("Cerrando editor...")
            self.selector.set_active(False)
            self.selector.disconnect_events()
            plt.close(self.fig)

    # ------------------------------------------------------------------
    # Zone management helpers
    # ------------------------------------------------------------------
    def _ingest_existing(self, data: dict) -> None:
        for zone_name, payload in data.items():
            nodes = payload.get("nodes", [])
            polygon = payload.get("polygon")
            production = payload.get("production")
            attraction = payload.get("attraction")

            self.zone_nodes[zone_name] = {int(node) for node in nodes}
            if polygon:
                self.zone_polygons[zone_name] = [
                    (float(point[0]), float(point[1])) for point in polygon if len(point) == 2
                ]
            if production is not None:
                self.zone_productions[zone_name] = float(production)
            if attraction is not None:
                self.zone_attractions[zone_name] = float(attraction)
            self.zone_order.append(zone_name)

    def _remove_zone_artists(self, zone_name: str) -> None:
        artists = self.zone_artists.pop(zone_name, [])
        for artist in artists:
            try:
                artist.remove()
            except ValueError:
                pass

    def _draw_zone(self, zone_name: str) -> None:
        self._remove_zone_artists(zone_name)

        nodes = self.zone_nodes.get(zone_name, set())
        color = self.zone_colors.setdefault(zone_name, next(self.color_cycle))
        coords = np.array([[self.graph.nodes[node]["x"], self.graph.nodes[node]["y"]] for node in nodes]) if nodes else None

        artists = []
        polygon = self.zone_polygons.get(zone_name)
        if polygon is None and coords is not None and len(coords) >= 3:
            polygon = monotonic_chain([tuple(row) for row in coords])

        if polygon and len(polygon) >= 3:
            polygon_patch = patches.Polygon(
                polygon,
                closed=True,
                facecolor=color,
                edgecolor="black",
                linewidth=1.0,
                alpha=0.35,
                zorder=5,
            )
            self.ax.add_patch(polygon_patch)
            artists.append(polygon_patch)

        if coords is not None and len(coords):
            scatter = self.ax.scatter(
                coords[:, 0],
                coords[:, 1],
                s=12,
                color=color,
                alpha=0.7,
                edgecolors="none",
                zorder=6,
            )
            artists.append(scatter)
            centroid = coords.mean(axis=0)
            label = self.ax.text(
                centroid[0],
                centroid[1],
                zone_name,
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
                color="black",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.75),
                zorder=7,
            )
            artists.append(label)

        self.zone_artists[zone_name] = artists
        self.fig.canvas.draw_idle()

    def _install_selector(self) -> None:
        selector_kwargs = {"useblit": True}
        try:
            selector = PolygonSelector(
                self.ax,
                self._on_polygon_complete,
                lineprops={"color": "orange", "linewidth": 1.5, "alpha": 0.8},
                markerprops={"marker": "o", "markersize": 4, "mec": "orange", "mfc": "orange", "alpha": 0.8},
                **selector_kwargs,
            )
        except TypeError:
            selector = PolygonSelector(
                self.ax,
                self._on_polygon_complete,
                **selector_kwargs,
            )
        self.selector = selector
        self._style_selector()

    def _remove_selector_visuals(self) -> None:
        if self.selector is None:
            return
        for attr in ("_line", "_polygon"):
            artist = getattr(self.selector, attr, None)
            if artist is not None:
                try:
                    artist.remove()
                except ValueError:
                    pass
        handles = getattr(self.selector, "_handles", None)
        if handles:
            for handle in handles:
                try:
                    handle.remove()
                except ValueError:
                    pass

    def _reset_selector(self) -> None:
        if self.selector is not None:
            try:
                self.selector.set_active(False)
            except Exception:  # noqa: BLE001
                pass
            try:
                self.selector.disconnect_events()
            except Exception:  # noqa: BLE001
                pass
            self._remove_selector_visuals()
        self._install_selector()
        self.fig.canvas.draw_idle()

    def _style_selector(self) -> None:
        """Aplica estilo consistente al selector de polígonos."""
        line = getattr(self.selector, "_line", None)
        if line is not None:
            line.set_color("orange")
            line.set_alpha(0.8)
            line.set_linewidth(1.5)
        handles = getattr(self.selector, "_handles", None)
        if handles:
            for handle in handles:
                handle.set_marker("o")
                handle.set_markersize(4)
                handle.set_markeredgecolor("orange")
                handle.set_markerfacecolor("orange")
                handle.set_alpha(0.8)

    def _clear_all(self) -> None:
        if not self.zone_order:
            print("No hay zonas para limpiar.")
            return
        root = self._ensure_tk_root()
        if root is None or messagebox is None:
            print("⚠️  No hay cuadros de diálogo disponibles para confirmar la acción. Operación cancelada.")
            return
        confirm = messagebox.askyesno(
            "Limpiar zonas",
            "¿Eliminar todas las zonas?",
            parent=root,
            default=messagebox.NO,
        )
        if not confirm:
            print("Operación cancelada.")
            return
        for zone in list(self.zone_order):
            self.zone_nodes.pop(zone, None)
            self.zone_polygons.pop(zone, None)
            self.zone_productions.pop(zone, None)
            self.zone_attractions.pop(zone, None)
            self._remove_zone_artists(zone)
        self.zone_order.clear()
        self.fig.canvas.draw_idle()
        self.changed = True
        if self.output_path is not None:
            self.save(self.output_path)
        self._reset_selector()
        print("🧹 Todas las zonas fueron eliminadas.")

    def _undo_last(self) -> None:
        if not self.zone_order:
            print("No hay zonas para deshacer.")
            return
        zone_name = self.zone_order.pop()
        self.zone_nodes.pop(zone_name, None)
        self.zone_polygons.pop(zone_name, None)
        self.zone_productions.pop(zone_name, None)
        self.zone_attractions.pop(zone_name, None)
        self._remove_zone_artists(zone_name)
        self.fig.canvas.draw_idle()
        self.changed = True
        print(f"↩️  Zona '{zone_name}' eliminada.")
        if self.output_path is not None:
            self.save(self.output_path)
        self._reset_selector()

    def _delete_zone_prompt(self) -> None:
        zone_name = self._prompt_text("Eliminar zona", "Nombre de la zona a borrar:")
        if not zone_name:
            print("Nombre vacío; cancelado.")
            return
        if zone_name not in self.zone_nodes:
            print(f"No se encontró la zona '{zone_name}'.")
            return
        self.zone_order = [z for z in self.zone_order if z != zone_name]
        self.zone_nodes.pop(zone_name, None)
        self.zone_polygons.pop(zone_name, None)
        self.zone_productions.pop(zone_name, None)
        self.zone_attractions.pop(zone_name, None)
        self._remove_zone_artists(zone_name)
        self.fig.canvas.draw_idle()
        self.changed = True
        print(f"🗑️  Zona '{zone_name}' eliminada.")
        if self.output_path is not None:
            self.save(self.output_path)
        self._reset_selector()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def serialize(self) -> dict:
        payload: Dict[str, dict] = {}
        for zone_name in self.zone_order:
            nodes = sorted(int(node) for node in self.zone_nodes.get(zone_name, set()))
            entry: Dict[str, object] = {"nodes": nodes}
            polygon = self.zone_polygons.get(zone_name)
            if polygon:
                entry["polygon"] = [[float(x), float(y)] for x, y in polygon]
            if zone_name in self.zone_productions:
                entry["production"] = float(self.zone_productions[zone_name])
            if zone_name in self.zone_attractions:
                entry["attraction"] = float(self.zone_attractions[zone_name])
            payload[zone_name] = entry
        return payload

    def save(self, path: Optional[Path] = None) -> None:
        path = path or self.output_path
        if path is None:
            print("❌ No se especificó archivo de salida; usa --output o --zones.")
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self.serialize()
        with path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
        self.changed = False
        print(f"💾 Zonas guardadas en {path}")

    def run(self) -> None:
        plt.show()

    def shutdown(self) -> None:
        if self._tk_root is not None:
            try:
                self._tk_root.destroy()
            except Exception:  # noqa: BLE001
                pass
            self._tk_root = None


def main() -> None:
    args = parse_args()

    graph = generador_od.load_graph(args.graph)

    existing_data = None
    if not args.skip_existing and args.zones and args.zones.exists():
        zones, productions, attractions, polygons = generador_od.load_zone_file(args.zones)
        existing_data = {}
        for zone_name, node_list in zones.items():
            entry = {"nodes": list(node_list)}
            if zone_name in productions:
                entry["production"] = productions[zone_name]
            if zone_name in attractions:
                entry["attraction"] = attractions[zone_name]
            if zone_name in polygons:
                entry["polygon"] = polygons[zone_name]
            existing_data[zone_name] = entry

    output_path = args.output or args.zones or Path("data/O-D-maps/microcentro_zones.json")

    editor = ZoneEditor(graph, output_path, existing_data)
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
