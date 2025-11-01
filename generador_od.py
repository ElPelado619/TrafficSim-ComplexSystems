"""Utility to build an Origin-Destination (O-D) demand matrix for the
microcentro network using a gravity model.

Example CLI usage::

    python generador_od.py --zone-file data/microcentro_zones.json \
        --output data/microcentro_od_matrix.json --beta 0.015

The zone file is a JSON object where keys are zone names and values are
objects with a mandatory ``nodes`` list plus optional ``production`` and
``attraction`` scalars. Optionally, dedicated production/attraction files
can be supplied to override the embedded factors.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Dict, Iterable, Mapping, MutableMapping

import networkx as nx
import osmnx as ox

ZoneNodes = Dict[str, Iterable[int]]
ZoneFactors = Dict[str, float]
ZonePolygons = Dict[str, list[tuple[float, float]]]


def load_graph(graph_path: Path) -> nx.MultiDiGraph:
    """Load the base networkx graph from disk."""
    if not graph_path.exists():
        raise FileNotFoundError(f"Graph file not found: {graph_path}")
    graph = ox.load_graphml(graph_path)
    if not graph.is_directed():
        graph = graph.to_directed()
    return graph


def load_zone_file(zone_path: Path) -> tuple[ZoneNodes, ZoneFactors, ZoneFactors, ZonePolygons]:
    """Parse the zone definition JSON file."""
    if not zone_path.exists():
        raise FileNotFoundError(f"Zone definition file not found: {zone_path}")

    with zone_path.open("r", encoding="utf-8") as fh:
        raw_data = json.load(fh)

    if not isinstance(raw_data, Mapping) or not raw_data:
        raise ValueError("Zone file must be a non-empty JSON object")

    zones: ZoneNodes = {}
    productions: ZoneFactors = {}
    attractions: ZoneFactors = {}
    polygons: ZonePolygons = {}

    for zone_name, payload in raw_data.items():
        if not isinstance(zone_name, str):
            raise ValueError("Zone names must be strings")

        if isinstance(payload, Mapping):
            nodes = payload.get("nodes")
            if nodes is None:
                raise ValueError(f"Zone '{zone_name}' is missing the 'nodes' field")
            productions_value = payload.get("production")
            attraction_value = payload.get("attraction")
            polygon_value = payload.get("polygon")
        elif isinstance(payload, list):
            nodes = payload
            productions_value = None
            attraction_value = None
            polygon_value = None
        else:
            raise ValueError(
                "Each zone entry must be either a list of node ids or an object "
                "with 'nodes', optionally 'production' and 'attraction'"
            )

        try:
            zones[zone_name] = [int(n) for n in nodes]
        except Exception as exc:  # noqa: BLE001 - protect clarity of traceback
            raise ValueError(f"Zone '{zone_name}' contains non-integer node ids") from exc

        if productions_value is not None:
            productions[zone_name] = float(productions_value)
        if attraction_value is not None:
            attractions[zone_name] = float(attraction_value)
        if polygon_value is not None:
            try:
                polygon_points = [
                    (float(point[0]), float(point[1]))
                    for point in polygon_value
                    if isinstance(point, (list, tuple)) and len(point) == 2
                ]
            except Exception as exc:  # noqa: BLE001
                raise ValueError(f"Zone '{zone_name}' polygon must be a list of coordinate pairs") from exc
            if len(polygon_points) < 3:
                raise ValueError(f"Zone '{zone_name}' polygon must contain at least three points")
            polygons[zone_name] = polygon_points

    return zones, productions, attractions, polygons


def load_factor_file(path: Path | None, label: str) -> ZoneFactors:
    """Load a JSON mapping of zone -> scalar factor."""
    if path is None:
        return {}
    if not path.exists():
        raise FileNotFoundError(f"{label.title()} file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, Mapping):
        raise ValueError(f"{label.title()} file must contain a JSON object")
    try:
        return {str(zone): float(value) for zone, value in data.items()}
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"{label.title()} values must be numeric") from exc


def merge_factors(
    zones: ZoneNodes,
    base_productions: ZoneFactors,
    base_attractions: ZoneFactors,
    prod_override: ZoneFactors,
    attr_override: ZoneFactors,
) -> tuple[ZoneFactors, ZoneFactors]:
    """Merge embedded factor values with optional overrides."""
    productions: ZoneFactors = {}
    attractions: ZoneFactors = {}

    for zone_name in zones:
        prod_value = prod_override.get(zone_name, base_productions.get(zone_name))
        attr_value = attr_override.get(zone_name, base_attractions.get(zone_name))
        if prod_value is None:
            raise ValueError(f"Missing production factor for zone '{zone_name}'")
        if attr_value is None:
            raise ValueError(f"Missing attraction factor for zone '{zone_name}'")
        productions[zone_name] = float(prod_value)
        attractions[zone_name] = float(attr_value)

    return productions, attractions


def validate_zone_nodes(graph: nx.MultiDiGraph, zones: ZoneNodes) -> None:
    """Ensure every configured node exists in the graph."""
    missing_by_zone: MutableMapping[str, list[int]] = {}
    graph_nodes = set(graph.nodes)
    for zone_name, node_ids in zones.items():
        missing = [node for node in node_ids if node not in graph_nodes]
        if missing:
            missing_by_zone[zone_name] = missing
    if missing_by_zone:
        pretty = ", ".join(
            f"{zone}: {sorted(missing_ids)}" for zone, missing_ids in missing_by_zone.items()
        )
        raise ValueError(f"Zone definitions reference nodes not present in the graph: {pretty}")


def compute_zone_costs(
    graph: nx.MultiDiGraph,
    zones: ZoneNodes,
    weight_attr: str,
) -> Dict[str, Dict[str, float]]:
    """Shortest-path travel cost between each pair of zones."""
    costs: Dict[str, Dict[str, float]] = {}
    for origin, origin_nodes in zones.items():
        lengths = nx.multi_source_dijkstra_path_length(graph, origin_nodes, weight=weight_attr)
        zone_costs: Dict[str, float] = {}
        for destination, destination_nodes in zones.items():
            min_cost = math.inf
            for node in destination_nodes:
                cost = lengths.get(node, math.inf)
                if cost < min_cost:
                    min_cost = cost
            zone_costs[destination] = min_cost
        costs[origin] = zone_costs
    return costs


def impedance(cost: float, friction: str, beta: float, gamma: float) -> float:
    """Compute impedance weight for the provided travel cost."""
    if not math.isfinite(cost) or cost < 0:
        return 0.0
    if friction == "exponential":
        return math.exp(-beta * cost)
    if friction == "power":
        if cost == 0:
            return 0.0
        return cost ** (-gamma)
    raise ValueError(f"Unsupported friction function: {friction}")


def gravity_matrix(
    zones: ZoneNodes,
    productions: ZoneFactors,
    attractions: ZoneFactors,
    costs: Dict[str, Dict[str, float]],
    friction: str,
    beta: float,
    gamma: float,
    allow_self_trips: bool,
) -> Dict[str, Dict[str, float]]:
    """Build the O-D matrix using a singly constrained gravity model."""
    matrix: Dict[str, Dict[str, float]] = {zone: {} for zone in zones}

    for origin in zones:
        total_weight = 0.0
        weights: Dict[str, float] = {}
        for destination in zones:
            if destination == origin and not allow_self_trips:
                continue
            cost = costs[origin][destination]
            impedance_value = impedance(cost, friction, beta, gamma)
            weight = attractions[destination] * impedance_value
            if weight > 0:
                weights[destination] = weight
                total_weight += weight
        if total_weight == 0:
            for destination in zones:
                matrix[origin][destination] = 0.0
            continue
        for destination in zones:
            if destination == origin and not allow_self_trips:
                matrix[origin][destination] = 0.0
                continue
            contribution = weights.get(destination, 0.0)
            share = contribution / total_weight if total_weight else 0.0
            matrix[origin][destination] = productions[origin] * share
    return matrix


def save_matrix(matrix: Dict[str, Dict[str, float]], output_path: Path) -> None:
    """Persist the matrix as JSON with sorted keys for reproducibility."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ordered = {
        origin: {
            destination: float(value) for destination, value in sorted(destinations.items())
        }
        for origin, destinations in sorted(matrix.items())
    }
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(ordered, fh, indent=2, sort_keys=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an O-D matrix via a gravity model")
    parser.add_argument(
        "--graph",
        default="data/microcentro.graphml",
        type=Path,
        help="Path to the graphml file describing the microcentro network",
    )
    parser.add_argument(
        "--zone-file",
        required=True,
        type=Path,
        help="JSON file with zone definitions and optional factors",
    )
    parser.add_argument(
        "--productions",
        type=Path,
        help="Optional JSON mapping zone -> production overriding the zone file",
    )
    parser.add_argument(
        "--attractions",
        type=Path,
        help="Optional JSON mapping zone -> attraction overriding the zone file",
    )
    parser.add_argument(
        "--output",
        default="data/microcentro_od_matrix.json",
        type=Path,
        help="Output JSON file for the generated matrix",
    )
    parser.add_argument(
        "--weight",
        default="length",
        help="Edge attribute used as travel cost weight",
    )
    parser.add_argument(
        "--friction",
        choices=["exponential", "power"],
        default="exponential",
        help="Type of impedance function used in the gravity model",
    )
    parser.add_argument(
        "--beta",
        type=float,
        default=0.01,
        help="Beta coefficient for the exponential friction function",
    )
    parser.add_argument(
        "--gamma",
        type=float,
        default=2.0,
        help="Gamma exponent for the power friction function",
    )
    parser.add_argument(
        "--allow-self-trips",
        action="store_true",
        help="Allow trips whose origin and destination are the same zone",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    graph = load_graph(args.graph)
    zones, embedded_prod, embedded_attr, _ = load_zone_file(args.zone_file)
    validate_zone_nodes(graph, zones)

    prod_override = load_factor_file(args.productions, "productions")
    attr_override = load_factor_file(args.attractions, "attractions")
    productions, attractions = merge_factors(
        zones,
        embedded_prod,
        embedded_attr,
        prod_override,
        attr_override,
    )

    costs = compute_zone_costs(graph, zones, args.weight)
    matrix = gravity_matrix(
        zones,
        productions,
        attractions,
        costs,
        friction=args.friction,
        beta=args.beta,
        gamma=args.gamma,
        allow_self_trips=args.allow_self_trips,
    )

    save_matrix(matrix, args.output)

    total_demand = sum(productions.values())
    print(f"Generated O-D matrix for {len(zones)} zones")
    print(f"Total production distributed: {total_demand:.2f}")
    print(f"Matrix saved to: {args.output}")


if __name__ == "__main__":
    main()
