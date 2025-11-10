"""Example script to launch multiple traffic simulations in parallel.

Each scenario tweaks the density and the random slowing probability while
keeping the same traffic-light configuration.  Results are collected from the
worker processes and printed as a compact summary.
"""

from __future__ import annotations

import itertools
import multiprocessing as mp
import sys
from pathlib import Path

# Allow direct execution without installing the package.
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parallel_simulation import run_simulations_in_parallel


def _build_scenarios() -> list[dict]:
    """Generate a modest parameter grid for demonstration purposes."""
    graph_path = Path("data/map_reduced.osm")
    if not graph_path.exists():
        raise FileNotFoundError(f"Graph file not found: {graph_path}")

    traffic_lights_path = Path("data/traffic_lights.json")
    base_kwargs = {
        "graph_file": str(graph_path),
        "traffic_lights_file": str(traffic_lights_path) if traffic_lights_path.exists() else None,
        "steps": 60,
        "warmup_steps": 15,
        "save_statistics": True,  # Generar gráficos de estadísticas
        "statistics_output_dir": "data/runs/parallel_stats",  # Directorio base para guardar
    }

    densities = [0.10, 0.20, 0.30]
    p_slow_values = [0.10, 0.30, 0.50]

    scenarios: list[dict] = []
    for idx, (density, p_slow) in enumerate(itertools.product(densities, p_slow_values), start=1):
        scenario = base_kwargs | {
            "label": f"density_{density:.2f}_pslow_{p_slow:.2f}",
            "density": density,
            "p_slow": p_slow,
            "random_seed": idx,
        }
        scenarios.append(scenario)
    return scenarios


def main() -> None:
    scenarios = _build_scenarios()
    workers = min(len(scenarios), max(1, mp.cpu_count() - 1))
    print(f"Launching {len(scenarios)} simulations using {workers} worker(s)...\n")

    results = run_simulations_in_parallel(scenarios, processes=workers)

    for item in results:
        label = item.get("label", "<unnamed>")
        if item.get("status") != "ok":
            print(f"❌ [{label}] ERROR -> {item.get('error')}")
            continue
        metrics = item["metrics"]
        print(
            f"📊 [{label}] final_avg_velocity={metrics['final_avg_velocity']:.3f} "
            f"mean_avg_velocity={metrics['mean_avg_velocity']:.3f} "
            f"final_stopped_ratio={metrics['final_stopped_ratio']:.3f} "
            f"vehicles_final={metrics['vehicles_final']}"
        )
        
        # Mostrar archivos de estadísticas si se generaron
        if "statistics_files" in item:
            stats_files = item["statistics_files"]
            print(f"   📈 Estadísticas guardadas: {len(stats_files)} archivos")
            for f in stats_files[:3]:  # Mostrar primeros 3
                print(f"      - {f}")
            if len(stats_files) > 3:
                print(f"      ... y {len(stats_files) - 3} más")
        elif "statistics_error" in item:
            print(f"   ⚠️  Error al guardar estadísticas: {item['statistics_error']}")
        else:
            print("   📈 Estadísticas no guardadas (save_statistics=False)")

    print("\nDone.")


if __name__ == "__main__":
    main()
