"""Command-line entry point for the TTC graph analysis project."""

from __future__ import annotations

import argparse
from pathlib import Path

from data_loader import build_graph_from_gtfs
from graph import Graph
from metrics import EdgeRecommendation, NetworkMetrics, compute_network_metrics, find_best_new_connection, top_k_central_stations


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Analyze and optimize the Toronto TTC network using graph algorithms.",
    )
    parser.add_argument("--data-dir", type=Path, default=Path("data"), help="Directory containing GTFS files.")
    parser.add_argument("--stops-file", type=str, default="stops.txt", help="GTFS stops file name.")
    parser.add_argument("--stop-times-file", type=str, default="stop_times.txt", help="GTFS stop_times file name.")
    parser.add_argument("--routes-file", type=str, default="routes.txt", help="GTFS routes file name.")
    parser.add_argument("--trips-file", type=str, default="trips.txt", help="GTFS trips file name.")
    parser.add_argument(
        "--max-distance-km",
        type=float,
        default=2.0,
        help="Maximum geographic distance for candidate new edges. Default is 2.0 km.",
    )
    parser.add_argument(
        "--html-output",
        type=Path,
        default=Path("output/ttc_network_analysis.html"),
        help="Path where the Plotly HTML visualization should be written.",
    )
    parser.add_argument(
        "--no-visualization",
        action="store_true",
        help="Skip writing the Plotly visualization HTML file.",
    )
    parser.add_argument(
        "--include-all-routes",
        action="store_true",
        help="Analyze the full TTC feed instead of defaulting to subway routes only.",
    )
    return parser.parse_args()


def validate_input_files(stops_path: Path, stop_times_path: Path, routes_path: Path, trips_path: Path) -> None:
    """Raise a helpful error if any required GTFS files are missing."""
    missing_paths = [path for path in (stops_path, stop_times_path, routes_path, trips_path) if not path.exists()]
    if missing_paths:
        missing_text = ", ".join(str(path) for path in missing_paths)
        raise FileNotFoundError(f"Missing required GTFS file(s): {missing_text}")


def format_station_label(graph: Graph, node_id: str) -> str:
    """Return a human-readable label for a node."""
    station = graph.stations.get(node_id)
    return station.name if station is not None else node_id


def print_summary(graph: Graph, graph_metrics: NetworkMetrics, top_stations: list[tuple[str, float]]) -> None:
    """Print the main metric summary for the project."""
    print("TTC Network Summary")
    print("-" * 40)
    print(f"Stations analyzed: {graph.node_count()}")
    print(f"Average shortest path: {graph_metrics.average_shortest_path:.3f}")
    print(f"Diameter: {graph_metrics.diameter:.3f}")
    print(f"Global efficiency: {graph_metrics.global_efficiency:.6f}")
    print()
    print("Top 5 stations by centrality:")

    for node_id, score in top_stations:
        print(f"  - {format_station_label(graph, node_id)}: {score:.3f}")


def print_recommendation(graph: Graph, recommendation: EdgeRecommendation | None) -> None:
    """Print the best proposed new edge, if one was found."""
    print()
    print("Best New Connection")
    print("-" * 40)

    if recommendation is None:
        print("No candidate edge recommendation was produced.")
        return

    print(f"Source: {format_station_label(graph, recommendation.source)}")
    print(f"Target: {format_station_label(graph, recommendation.target)}")
    print(f"Estimated weight: {recommendation.weight:.3f} seconds")
    print(f"Improvement: {recommendation.improvement_percent:.2f}%")


def maybe_write_visualization(
    graph: Graph,
    graph_metrics: NetworkMetrics,
    recommendation: EdgeRecommendation | None,
    html_output: Path,
) -> None:
    """Write the interactive Plotly figure if visualization is enabled."""
    from visualization import save_network_figure

    output_path = save_network_figure(
        graph,
        graph_metrics.betweenness_centrality,
        recommendation,
        html_output,
    )
    print()
    print(f"Visualization saved to: {output_path}")


def main() -> None:
    """Run the TTC graph analysis workflow."""
    args = parse_args()
    data_dir = args.data_dir
    stops_path = data_dir / args.stops_file
    stop_times_path = data_dir / args.stop_times_file
    routes_path = data_dir / args.routes_file
    trips_path = data_dir / args.trips_file

    validate_input_files(stops_path, stop_times_path, routes_path, trips_path)
    route_types = None if args.include_all_routes else {"1"}
    graph = build_graph_from_gtfs(
        stops_path,
        stop_times_path,
        routes_path,
        trips_path,
        route_types=route_types,
    )
    graph_metrics = compute_network_metrics(graph)
    top_stations = top_k_central_stations(graph_metrics.betweenness_centrality, k=5)
    recommendation = find_best_new_connection(graph, max_distance_km=args.max_distance_km)

    print_summary(graph, graph_metrics, top_stations)
    print_recommendation(graph, recommendation)

    if not args.no_visualization:
        maybe_write_visualization(graph, graph_metrics, recommendation, args.html_output)


if __name__ == "__main__":
    main()
