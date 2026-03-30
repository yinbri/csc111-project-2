"""Command-line entry point for the TTC graph analysis project.

This file wires together:
    - GTFS loading
    - metric computation
    - edge recommendation
    - Plotly visualization
"""

from __future__ import annotations

from pathlib import Path

from data_loader import build_graph_from_gtfs
from metrics import (
    compute_network_metrics,
    find_best_new_connection,
    top_k_central_stations,
)
from visualization import show_network_figure


def print_summary(graph_metrics: object, top_stations: list[tuple[str, float]]) -> None:
    """Print the main metric summary for the project report.

    TODO:
        Replace the loose ``object`` annotation with ``NetworkMetrics`` if you
        want stricter typing and import clarity in this module.
    """
    print("TTC Network Summary")
    print("-" * 40)
    print(f"Average shortest path: {graph_metrics.average_shortest_path:.3f}")
    print(f"Diameter: {graph_metrics.diameter:.3f}")
    print(f"Global efficiency: {graph_metrics.global_efficiency:.6f}")
    print()
    print("Top 5 stations by centrality:")

    for station_id, score in top_stations:
        print(f"  - {station_id}: {score:.3f}")


def print_recommendation(recommendation: object | None) -> None:
    """Print the best proposed new edge, if one was found.

    TODO:
        Replace the loose ``object`` annotation with ``EdgeRecommendation`` once
        the module interface is finalized.
    """
    print()
    print("Best New Connection")
    print("-" * 40)

    if recommendation is None:
        print("No candidate edge recommendation was produced.")
        return

    print(f"Source: {recommendation.source}")
    print(f"Target: {recommendation.target}")
    print(f"Estimated weight: {recommendation.weight:.3f}")
    print(f"Improvement: {recommendation.improvement_percent:.2f}%")


def main() -> None:
    """Run the TTC graph analysis workflow.

    TODO:
        Replace these placeholder file paths with:
            - command-line arguments
            - a config file
            - or constants pointing at your GTFS data directory
    """
    data_dir = Path("data")
    stops_path = data_dir / "stops.txt"
    stop_times_path = data_dir / "stop_times.txt"
    routes_path = data_dir / "routes.txt"

    # TODO: Add friendly error handling for missing files before parsing.
    graph = build_graph_from_gtfs(stops_path, stop_times_path, routes_path)
    graph_metrics = compute_network_metrics(graph)
    top_stations = top_k_central_stations(graph_metrics.betweenness_centrality, k=5)
    recommendation = find_best_new_connection(graph)

    print_summary(graph_metrics, top_stations)
    print_recommendation(recommendation)
    show_network_figure(graph, graph_metrics.betweenness_centrality, recommendation)


if __name__ == "__main__":
    main()
