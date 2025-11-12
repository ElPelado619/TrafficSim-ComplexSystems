"""Utilities to execute sets of traffic simulations in parallel.

This module centralises the logic required to spawn independent simulations
with different parameters so the jobs can be fanned out through
``multiprocessing.Pool``.  The public entry point ``run_simulation_with_params``
accepts a plain mapping/dict describing the scenario and returns a JSON-friendly
summary of the run.  ``run_simulations_in_parallel`` is a thin helper that
creates the pool and gathers the results.
"""

from __future__ import annotations

import contextlib
import csv
import io
import json
import multiprocessing as mp
import random
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

import numpy as np

from .traffic_simulation import TrafficSimulation


def _run_quietly(func, verbose: bool, *args, **kwargs):
    """Invoke ``func`` while silencing stdout when ``verbose`` is False."""
    if verbose:
        return func(*args, **kwargs)
    with contextlib.redirect_stdout(io.StringIO()):
        return func(*args, **kwargs)


def _load_zones(zones_path: Path) -> Dict[str, List[int]]:
    """Extract the mapping zone -> list of node ids from a JSON payload."""
    with zones_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if isinstance(data, dict):
        if "zones" in data and isinstance(data["zones"], dict):
            data = data["zones"]
        if all(isinstance(value, dict) and "nodes" in value for value in data.values()):
            return {name: list(map(int, value["nodes"])) for name, value in data.items()}
        if all(isinstance(value, list) for value in data.values()):
            return {name: list(map(int, value)) for name, value in data.items()}

    raise ValueError(f"Unsupported zone file format in {zones_path}")


def _maybe_spawn_from_od(
    simulation: TrafficSimulation,
    config: Mapping[str, Any],
) -> Optional[int]:
    """Initialise vehicles from an origin-destination matrix when requested."""
    zones_file = config.get("od_zones_file")
    od_matrix_file = config.get("od_matrix_file")
    if not zones_file or not od_matrix_file:
        return None

    zones_path = Path(zones_file)
    matrix_path = Path(od_matrix_file)
    scale = float(config.get("od_scale", 1.0))
    random_seed = config.get("od_random_seed")
    max_attempts = int(config.get("od_max_attempts", 5))

    zones = _load_zones(zones_path)
    with matrix_path.open("r", encoding="utf-8") as handle:
        od_matrix = json.load(handle)

    return simulation.spawn_from_od_matrix(
        zones,
        od_matrix,
        scale=scale,
        random_seed=random_seed,
        max_attempts=max_attempts,
    )


def _save_time_series_csv(
    simulation: TrafficSimulation,
    output_path: Path,
    label: str = "",
) -> str:
    """Save time series data from simulation to a CSV file.

    Parameters
    ----------
    simulation : TrafficSimulation
        The simulation object containing the time series data
    output_path : Path
        Directory where to save the CSV file
    label : str
        Label for the scenario (used in filename)

    Returns
    -------
    str
        Path to the saved CSV file
    """
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    # Create filename
    safe_label = label.replace("/", "_").replace(" ", "_") if label else "unnamed"
    csv_file = output_path / f"time_series_{safe_label}.csv"

    # Prepare data
    max_length = max(
        len(simulation.avg_velocities),
        len(simulation.vehicle_stopped_ratio),
        len(simulation.stopped_vehicles_count),
        len(simulation.edge_densities),
        len(simulation.congestion_points),
    )

    # Pad shorter lists with None
    def pad_list(lst, length):
        return lst + [None] * (length - len(lst))

    avg_velocities = pad_list(simulation.avg_velocities, max_length)
    stopped_ratios = pad_list(simulation.vehicle_stopped_ratio, max_length)
    stopped_counts = pad_list(simulation.stopped_vehicles_count, max_length)
    edge_densities = pad_list(simulation.edge_densities, max_length)
    congestion_points = pad_list(simulation.congestion_points, max_length)

    # Write CSV
    with csv_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "time_step",
            "avg_velocity",
            "stopped_ratio",
            "stopped_vehicles_count",
            "edge_density",
            "congestion_points"
        ])

        for i in range(max_length):
            writer.writerow([
                i + 1,  # time_step (1-based)
                avg_velocities[i],
                stopped_ratios[i],
                stopped_counts[i],
                edge_densities[i],
                congestion_points[i],
            ])

    return str(csv_file)


def _prepare_simulation_config(params: Mapping[str, Any]) -> Dict[str, Any]:
    """Normalise raw parameters coming from the caller."""
    config: Dict[str, Any] = dict(params)
    config.setdefault("graph_file", "data/microcentro.graphml")
    config.setdefault("cell_length", 7.5)
    config.setdefault("v_max", 5)
    config.setdefault("p_slow", 0.3)
    config.setdefault("density", 0.2)
    config.setdefault("steps", 100)
    config.setdefault("warmup_steps", 0)
    config.setdefault("collect_time_series", False)
    config.setdefault("verbose", False)
    config.setdefault("save_statistics", False)
    config.setdefault("statistics_output_dir", "data/runs")
    config.setdefault("save_time_series_csv", False)
    return config


def run_simulation_with_params(params: Mapping[str, Any]) -> Dict[str, Any]:
    """Execute one simulation run and summarise the outcome.

    Parameters
    ----------
    params:
        Dictionary describing the scenario.  Supported keys include:

        - ``graph_file``: path to the OSM/GraphML network (default: data/map_reduced.osm)
        - ``cell_length``: discretisation cell size in metres (float)
        - ``v_max``: maximum speed in cells per tick (int)
        - ``p_slow``: random braking probability (float)
        - ``density``: initial density when no O-D matrix is supplied (float)
        - ``steps``: simulation steps after warm-up (int)
        - ``warmup_steps``: optional warm-up steps before measurements (int)
        - ``random_seed``: seed forwarded to ``random`` and ``numpy``
        - ``traffic_lights_file``: JSON file with the traffic light plan
        - ``od_zones_file`` + ``od_matrix_file``: enable O-D initialisation
        - ``od_scale`` / ``od_random_seed`` / ``od_max_attempts``: extras for O-D spawning
        - ``collect_time_series``: include per-step series in the result (bool)
        - ``verbose``: propagate stdout from the simulation helpers (bool)
        - ``label``: arbitrary tag copied to the result for easier identification
        - ``save_statistics``: generate and save statistics plots (bool)
        - ``statistics_output_dir``: base directory for saving statistics plots
        - ``save_time_series_csv``: save time series data to CSV file (bool)

    Returns
    -------
    dict
        Structure ready to be serialised (only built-in Python types).  The
        ``status`` field is ``"ok"`` when the run finished successfully; in case
        of failure the ``error`` message is populated instead of metrics.
    """

    config = _prepare_simulation_config(params)
    label = config.get("label")
    verbose = bool(config.get("verbose"))
    steps = int(config.get("steps", 0))
    warmup_steps = int(config.get("warmup_steps", 0))
    density = config.get("density")
    random_seed = config.get("random_seed")

    result: Dict[str, Any] = {
        "label": label,
        "status": "ok",
        "metrics": {},
    }
    if random_seed is not None:
        random.seed(random_seed)
        np.random.seed(random_seed)
        result["random_seed"] = int(random_seed)

    try:
        simulation = TrafficSimulation(
            graph_file=str(config["graph_file"]),
            cell_length=float(config["cell_length"]),
            v_max=int(config["v_max"]),
            p_slow=float(config["p_slow"]),
        )

        traffic_lights_file = config.get("traffic_lights_file")
        if traffic_lights_file:
            _run_quietly(simulation.load_traffic_lights, verbose, Path(traffic_lights_file))

        initial_vehicles = _maybe_spawn_from_od(simulation, config)
        if initial_vehicles is None:
            if density is None:
                raise ValueError("Either density or an O-D configuration must be provided")
            _run_quietly(simulation.initialize_vehicles, verbose, density=float(density))
            initial_vehicles = len(simulation.vehicles)

        # Warm-up executes before metrics are recorded.
        for _ in range(max(warmup_steps, 0)):
            simulation.step()

        for _ in range(max(steps, 0)):
            simulation.step()

        avg_velocities = simulation.avg_velocities
        stopped_ratio = simulation.vehicle_stopped_ratio
        stopped_count = simulation.stopped_vehicles_count
        densities = simulation.edge_densities
        congestion = simulation.congestion_points

        metrics = {
            "time_steps": int(simulation.time_step),
            "vehicles_initial": int(initial_vehicles or 0),
            "vehicles_final": int(len(simulation.vehicles)),
            "final_avg_velocity": float(avg_velocities[-1]) if avg_velocities else 0.0,
            "mean_avg_velocity": float(np.mean(avg_velocities)) if avg_velocities else 0.0,
            "final_stopped_ratio": float(stopped_ratio[-1]) if stopped_ratio else 0.0,
            "mean_stopped_ratio": float(np.mean(stopped_ratio)) if stopped_ratio else 0.0,
            "final_stopped_vehicles": int(stopped_count[-1]) if stopped_count else 0,
            "final_edge_density": float(densities[-1]) if densities else 0.0,
            "final_congestion_edges": int(congestion[-1]) if congestion else 0,
        }
        result["metrics"] = metrics

        if config.get("collect_time_series"):
            result["timeseries"] = {
                "avg_velocity": [float(value) for value in avg_velocities],
                "stopped_ratio": [float(value) for value in stopped_ratio],
                "stopped_vehicles": [int(value) for value in stopped_count],
                "edge_density": [float(value) for value in densities],
                "congestion_edges": [int(value) for value in congestion],
            }

        result["params_used"] = {
            "graph_file": str(config["graph_file"]),
            "cell_length": float(config["cell_length"]),
            "v_max": int(config["v_max"]),
            "p_slow": float(config["p_slow"]),
            "density": float(density) if density is not None else None,
            "steps": int(steps),
            "warmup_steps": int(warmup_steps),
            "traffic_lights_file": str(traffic_lights_file) if traffic_lights_file else None,
            "od_zones_file": str(config.get("od_zones_file")) if config.get("od_zones_file") else None,
            "od_matrix_file": str(config.get("od_matrix_file")) if config.get("od_matrix_file") else None,
            "od_scale": float(config.get("od_scale", 1.0)) if config.get("od_matrix_file") else None,
            "save_statistics": bool(config.get("save_statistics", False)),
            "statistics_output_dir": str(config.get("statistics_output_dir", "data/runs")),
            "save_time_series_csv": bool(config.get("save_time_series_csv", False)),
        }

    except Exception as exc:  # pylint: disable=broad-except
        result["status"] = "error"
        result["error"] = f"{type(exc).__name__}: {exc}"

    # Save statistics plots if requested
    if result["status"] == "ok" and config.get("save_statistics", False):
        try:
            output_dir_base = Path(config.get("statistics_output_dir", "data/runs"))
            output_dir_base.mkdir(parents=True, exist_ok=True)
            
            # Create unique subdirectory for this scenario
            label = config.get("label", "unnamed")
            scenario_dir = output_dir_base / f"stats_{label.replace('/', '_').replace(' ', '_')}"
            scenario_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate and save statistics plots
            saved_files = simulation.plot_statistics(output_dir=str(scenario_dir), show=False)
            result["statistics_files"] = [str(f) for f in saved_files]
        except Exception as plot_exc:  # pylint: disable=broad-except
            result["statistics_error"] = f"{type(plot_exc).__name__}: {plot_exc}"

    # Save time series CSV if requested
    if result["status"] == "ok" and config.get("save_time_series_csv", False):
        try:
            output_dir_base = Path(config.get("statistics_output_dir", "data/runs"))
            output_dir_base.mkdir(parents=True, exist_ok=True)
            
            # Create unique subdirectory for this scenario
            label = config.get("label", "unnamed")
            scenario_dir = output_dir_base / f"stats_{label.replace('/', '_').replace(' ', '_')}"
            scenario_dir.mkdir(parents=True, exist_ok=True)
            
            # Save time series to CSV
            csv_file = _save_time_series_csv(simulation, scenario_dir, label)
            result["time_series_csv"] = csv_file
        except Exception as csv_exc:  # pylint: disable=broad-except
            result["time_series_csv_error"] = f"{type(csv_exc).__name__}: {csv_exc}"

    return result


def run_simulations_in_parallel(
    scenarios: Iterable[Mapping[str, Any]],
    *,
    processes: Optional[int] = None,
    chunk_size: int = 1,
    start_method: str = "spawn",
) -> List[Dict[str, Any]]:
    """Execute several simulations concurrently via ``multiprocessing.Pool``.

    The function is intentionally lightweight; it simply builds the pool using
    the requested start method (``spawn`` by default for cross-platform
    compatibility) and maps each scenario to ``run_simulation_with_params``.
    Callers on Windows **must** protect their entry point with
    ``if __name__ == "__main__"`` because of the way ``multiprocessing`` works.
    """

    scenario_list = list(scenarios)
    if not scenario_list:
        return []

    ctx = mp.get_context(start_method)
    if processes is None:
        processes = min(len(scenario_list), mp.cpu_count())
    else:
        processes = max(1, min(int(processes), mp.cpu_count()))

    with ctx.Pool(processes=processes) as pool:
        results = pool.map(run_simulation_with_params, scenario_list, chunksize=max(1, int(chunk_size)))

    return results


__all__ = [
    "run_simulation_with_params",
    "run_simulations_in_parallel",
]
