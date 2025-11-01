#!/usr/bin/env python3
"""Escenario de simulación que utiliza la matriz O-D del microcentro."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import osmnx as ox
from matplotlib.animation import FuncAnimation
from matplotlib.colors import Normalize

# Añadir la raíz del repositorio para importar módulos locales
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.traffic_simulation import TrafficSimulation
import generador_od


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simular microcentro usando una matriz O-D precomputada")
    parser.add_argument(
        "--graph",
        type=Path,
        default=Path("data/microcentro.graphml"),
        help="Archivo GraphML con la red vial del microcentro",
    )
    parser.add_argument(
        "--zones",
        type=Path,
        default=Path("data/microcentro_zones.json"),
        help="Archivo JSON con la definición de zonas",
    )
    parser.add_argument(
        "--od",
        type=Path,
        default=Path("data/microcentro_od_matrix.json"),
        help="Archivo JSON con la matriz O-D generada",
    )
    parser.add_argument(
        "--productions-file",
        type=Path,
        help="Archivo JSON con factores de producción (sobrescribe los de la definición de zonas)",
    )
    parser.add_argument(
        "--attractions-file",
        type=Path,
        help="Archivo JSON con factores de atracción (sobrescribe los de la definición de zonas)",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=0.01,
        help="Factor de escala para convertir demanda en vehículos (1.0 = demanda tal cual)",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=120,
        help="Pasos de simulación a ejecutar",
    )
    parser.add_argument(
        "--report-every",
        type=int,
        default=20,
        help="Frecuencia de reporte en pasos de simulación",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Semilla aleatoria para reproducibilidad",
    )
    parser.add_argument(
        "--cell-length",
        type=float,
        default=7.5,
        help="Longitud de celda (metros) usada en la discretización",
    )
    parser.add_argument(
        "--v-max",
        type=int,
        default=5,
        help="Velocidad máxima (celdas por paso)",
    )
    parser.add_argument(
        "--p-slow",
        type=float,
        default=0.3,
        help="Probabilidad de desaceleración aleatoria",
    )
    parser.add_argument(
        "--animation-gif",
        type=Path,
        help="Ruta del archivo GIF para guardar la animación del tráfico",
    )
    parser.add_argument(
        "--animation-interval",
        type=int,
        default=150,
        help="Intervalo en milisegundos entre frames en la animación",
    )
    parser.add_argument(
        "--save-prefix",
        type=str,
        help="Prefijo para guardar gráficos (p.ej. 'resultados/microcentro')",
    )
    parser.add_argument(
        "--attraction-map",
        type=Path,
        help="Archivo de salida (PNG) para visualizar la atracción relativa por zona",
    )
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="No mostrar gráficos interactivos al finalizar",
    )
    return parser.parse_args()


def render_animation(
    graph,
    frames,
    output_path: Path,
    interval_ms: int,
    v_max: int,
    show: bool,
):
    """Renderiza y guarda una animación del estado de la simulación."""
    if not frames:
        print("No hay frames disponibles para la animación; se omite la exportación.")
        return

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 12))
    ox.plot_graph(graph, ax=ax, show=False, close=False, node_size=0, edge_linewidth=0.5, edge_color="gray")

    vmax = max(1, v_max)
    scatter = ax.scatter(
        [],
        [],
        c=[],
        s=25,
        cmap="RdYlGn",
        vmin=0,
        vmax=vmax,
        edgecolors="black",
        linewidths=0.5,
        zorder=5,
    )
    scatter.set_clim(0, vmax)
    title = ax.set_title("")

    def init():
        scatter.set_offsets(np.empty((0, 2)))
        scatter.set_array(np.array([]))
        return scatter, title

    def update(idx):
        positions = frames[idx]
        if positions:
            coords = np.array([[lon, lat] for lon, lat, *_ in positions])
            velocities = np.array([velocity for *_, velocity in positions])
            scatter.set_offsets(coords)
            scatter.set_array(velocities)
        else:
            scatter.set_offsets(np.empty((0, 2)))
            scatter.set_array(np.array([]))
        title.set_text(f"Paso {idx}/{len(frames) - 1}")
        return scatter, title

    anim = FuncAnimation(
        fig,
        update,
        init_func=init,
        frames=len(frames),
        interval=interval_ms,
        blit=True,
        repeat=False,
    )

    plt.colorbar(scatter, ax=ax, label="Velocidad")
    plt.tight_layout()

    fps = max(1, int(1000 / interval_ms)) if interval_ms else 10
    anim.save(output_path, writer="pillow", fps=fps)
    print(f" - Animación: {output_path}")

    if show:
        plt.show()
    else:
        plt.close(fig)


def render_zone_attraction_map(
    graph,
    zones,
    attractions,
    output_path: Path,
    show: bool,
):
    """Genera un mapa estático resaltando la atracción relativa por zona."""
    if not zones:
        print("No hay zonas definidas para generar el mapa de atracción.")
        return

    values = np.array([attractions.get(zone) for zone in zones if attractions.get(zone) is not None], dtype=float)
    if values.size == 0:
        print("No se encontraron valores de atracción para visualizar.")
        return

    if np.allclose(values, values[0]):
        vmin = values[0] - 1 if values[0] else 0
        vmax = values[0] + 1 if values[0] else 1
    else:
        vmin = float(values.min())
        vmax = float(values.max())

    norm = Normalize(vmin=vmin, vmax=vmax)
    cmap = plt.cm.Reds

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 12))
    ox.plot_graph(graph, ax=ax, show=False, close=False, node_size=0, edge_linewidth=0.5, edge_color="lightgray")

    for zone_name, node_ids in zones.items():
        attraction = attractions.get(zone_name)
        if attraction is None:
            continue
        node_ids = [node_id for node_id in node_ids if node_id in graph]
        if not node_ids:
            continue
        coords = np.array([[graph.nodes[node]["x"], graph.nodes[node]["y"]] for node in node_ids])
        centroid = coords.mean(axis=0)
        color = cmap(norm(attraction))

        ax.scatter(
            coords[:, 0],
            coords[:, 1],
            color=color,
            s=30,
            alpha=0.6,
            edgecolors="none",
            zorder=6,
        )
        ax.scatter(
            centroid[0],
            centroid[1],
            color=color,
            s=220,
            edgecolors="black",
            linewidths=1.0,
            zorder=7,
        )
        ax.text(
            centroid[0],
            centroid[1],
            f"{zone_name}\nA={attraction:.0f}",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.75),
            zorder=8,
        )

    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    plt.colorbar(sm, ax=ax, label="Atracción")
    ax.set_title("Atracción relativa por zona")
    plt.tight_layout()

    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f" - Mapa de atracción: {output_path}")

    if show:
        plt.show()
    else:
        plt.close(fig)


def main() -> None:
    args = parse_args()

    sim = TrafficSimulation(
        graph_file=str(args.graph),
        cell_length=args.cell_length,
        v_max=args.v_max,
        p_slow=args.p_slow,
    )

    zones, base_productions, base_attractions = generador_od.load_zone_file(args.zones)
    prod_override = generador_od.load_factor_file(args.productions_file, "productions")
    attr_override = generador_od.load_factor_file(args.attractions_file, "attractions")
    productions, attractions = generador_od.merge_factors(
        zones,
        base_productions,
        base_attractions,
        prod_override,
        attr_override,
    )
    generador_od.validate_zone_nodes(sim.graph, zones)

    if not args.od.exists():
        raise FileNotFoundError(f"No se encontró la matriz O-D en {args.od}")

    with args.od.open("r", encoding="utf-8") as fh:
        od_matrix = json.load(fh)

    print("Cargando matriz O-D y generando vehículos iniciales...")
    vehicles_created = sim.spawn_from_od_matrix(zones, od_matrix, scale=args.scale, random_seed=args.seed)
    print(f"Vehículos iniciales generados: {vehicles_created}")

    frames = None
    if args.animation_gif:
        frames = [sim.get_vehicle_positions()]

    for step in range(1, args.steps + 1):
        sim.step()
        if frames is not None:
            frames.append(sim.get_vehicle_positions())
        if args.report_every and step % args.report_every == 0:
            avg_velocity = sim.avg_velocities[-1] if sim.avg_velocities else 0.0
            print(
                f"Paso {step:4d} | vehículos en red = {len(sim.vehicles):4d} | "
                f"velocidad promedio = {avg_velocity:.2f}"
            )

    if args.animation_gif:
        print("Generando animación del tráfico...")
        render_animation(
            sim.graph,
            frames,
            args.animation_gif,
            args.animation_interval,
            sim.v_max,
            show=not args.no_show,
        )

    if args.save_prefix:
        print("Guardando visualizaciones...")
        ax = sim.plot_state(show=False)
        state_path = Path(f"{args.save_prefix}_state.png")
        ax.figure.savefig(state_path, dpi=150, bbox_inches="tight")
        plt.close(ax.figure)

        fig, _ = sim.plot_statistics(show=False)
        stats_path = Path(f"{args.save_prefix}_stats.png")
        fig.savefig(stats_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        print(f" - Estado final: {state_path}")
        print(f" - Estadísticas: {stats_path}")

    if args.attraction_map:
        print("Generando mapa de atracción zonal...")
        render_zone_attraction_map(
            sim.graph,
            zones,
            attractions,
            args.attraction_map,
            show=not args.no_show,
        )

    if not args.no_show:
        sim.plot_state()
        sim.plot_statistics()


if __name__ == "__main__":
    main()
