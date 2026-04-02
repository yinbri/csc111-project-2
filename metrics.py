"""CSC111 Winter 2026 Project 2: TTC Network Metrics

Module Description
==================
This module implements graph algorithms and computes network metrics for the Toronto TTC project.
It provides functions for centrality, shortest paths, and recommendations for improving the transit network.

Copyright and Usage Information
===============================

This file is Copyright (c) 2026 Aarav Chhabra, Brian Yin, Sam Wang, and Kevin Liu
"""

from __future__ import annotations
import heapq
import math
from dataclasses import dataclass
from graph import Graph


@dataclass(slots=True)
class PathResults:
    """Store the result of running Dijkstra from one source node.

    Instance Attributes:
        - source: The source node ID.
        - distances: A mapping from node IDs to their shortest path distance from the source.
        - previous: A mapping from node IDs to their predecessor on the shortest path.
        - predecessors: A mapping from node IDs to a list of their predecessors on shortest paths.
        - path_counts: A mapping from node IDs to the number of shortest paths from the source.
        - visit_order: The order in which nodes were visited during Dijkstra's algorithm.
    """

    source: str
    distances: dict[str, float]
    previous: dict[str, str | None]
    predecessors: dict[str, list[str]]
    path_counts: dict[str, float]
    visit_order: list[str]


@dataclass(slots=True)
class NetworkMetrics:
    """Bundle the main graph metrics reported by the program.

    Instance Attributes:
        - average_shortest_path: The average shortest path length in the network.
        - diameter: The diameter (longest shortest path) of the network.
        - global_efficiency: The global efficiency of the network.
        - betweenness_centrality: A mapping from node IDs to their betweenness centrality score.
    """

    average_shortest_path: float
    diameter: float
    global_efficiency: float
    betweenness_centrality: dict[str, float]


@dataclass(slots=True)
class EdgeRecommendation:
    """Represent the best new edge found for one optimization objective.

    Instance Attributes:
        - metric_name: The metric this recommendation optimizes.
        - source: The source node ID for the recommended edge.
        - target: The target node ID for the recommended edge.
        - weight: The estimated weight (travel time) for the new edge.
        - baseline_value: The metric value before adding the edge.
        - new_value: The metric value after adding the edge.
        - goal: Whether larger or smaller values are better for this metric.
    """

    metric_name: str
    source: str
    target: str
    weight: float
    baseline_value: float
    new_value: float
    goal: str = "maximize"

    @property
    def improvement(self) -> float:
        """Return the raw improvement for this recommendation's objective."""
        if self.goal == "minimize":
            return self.baseline_value - self.new_value
        return self.new_value - self.baseline_value

    @property
    def improvement_percent(self) -> float:
        """Return the percentage improvement relative to the baseline value."""
        if self.baseline_value == 0:
            return math.inf if self.improvement > 0 else 0.0
        return (self.improvement / self.baseline_value) * 100.0


@dataclass(slots=True)
class EdgeRecommendationSet:
    """Bundle the best candidate edge found for each reported metric."""

    average_shortest_path: EdgeRecommendation | None
    diameter: EdgeRecommendation | None
    global_efficiency: EdgeRecommendation | None
    maximum_betweenness: EdgeRecommendation | None


def dijkstra(graph: Graph, source: str) -> PathResults:
    """Compute single-source shortest paths with Dijkstra's algorithm.

    Preconditions:
        - source in graph.adjacency
    """
    nodes = graph.nodes()
    distances = {node: math.inf for node in nodes}
    previous = {node: None for node in nodes}
    predecessors = {node: [] for node in nodes}
    path_counts = {node: 0.0 for node in nodes}
    visit_order: list[str] = []

    distances[source] = 0.0
    path_counts[source] = 1.0
    priority_queue: list[tuple[float, str]] = [(0.0, source)]

    while priority_queue:
        current_distance, current_node = heapq.heappop(priority_queue)
        if current_distance > distances[current_node]:
            continue

        visit_order.append(current_node)

        for neighbor, weight in graph.neighbors(current_node).items():
            candidate_distance = current_distance + weight

            if candidate_distance < distances[neighbor] - 1e-12:
                distances[neighbor] = candidate_distance
                previous[neighbor] = current_node
                predecessors[neighbor] = [current_node]
                path_counts[neighbor] = path_counts[current_node]
                heapq.heappush(priority_queue, (candidate_distance, neighbor))
            elif math.isclose(candidate_distance, distances[neighbor], rel_tol=1e-12, abs_tol=1e-12):
                predecessors[neighbor].append(current_node)
                path_counts[neighbor] += path_counts[current_node]
                if previous[neighbor] is None or current_node < previous[neighbor]:
                    previous[neighbor] = current_node

    return PathResults(
        source=source,
        distances=distances,
        previous=previous,
        predecessors=predecessors,
        path_counts=path_counts,
        visit_order=visit_order,
    )


def reconstruct_path(previous: dict[str, str | None], source: str, target: str) -> list[str]:
    """Reconstruct one shortest path from ``source`` to ``target``.

    Preconditions:
        - source in previous
        - target in previous
    """
    path: list[str] = []
    current: str | None = target

    while current is not None:
        path.append(current)
        if current == source:
            break
        current = previous[current]

    path.reverse()
    if not path or path[0] != source:
        return []
    return path


def shortest_path_between(graph: Graph, source: str, target: str) -> tuple[list[str], float]:
    """Return one shortest path and its total distance from ``source`` to ``target``.

    If ``target`` is unreachable from ``source``, return ``([], math.inf)``.

    Preconditions:
        - source in graph.adjacency
        - target in graph.adjacency
    """
    results = dijkstra(graph, source)
    distance = results.distances.get(target, math.inf)
    if math.isinf(distance):
        return ([], math.inf)

    return (reconstruct_path(results.previous, source, target), distance)


def all_pairs_shortest_paths(graph: Graph) -> dict[str, PathResults]:
    """
    Run Dijkstra from every node in the graph.

    Preconditions:
        - len(graph.adjacency) > 0
    """
    return {node: dijkstra(graph, node) for node in graph.nodes()}


def average_shortest_path_length(all_pairs: dict[str, PathResults]) -> float:
    """Return the average shortest path length across reachable ordered pairs."""
    total_distance = 0.0
    reachable_pairs = 0

    for source, result in all_pairs.items():
        for target, distance in result.distances.items():
            if source == target or math.isinf(distance):
                continue
            total_distance += distance
            reachable_pairs += 1

    if reachable_pairs == 0:
        return math.inf
    return total_distance / reachable_pairs


def network_diameter(all_pairs: dict[str, PathResults]) -> float:
    """Return the largest finite shortest-path distance in the graph."""
    diameter = 0.0

    for source, result in all_pairs.items():
        for target, distance in result.distances.items():
            if source == target or math.isinf(distance):
                continue
            diameter = max(diameter, distance)

    return diameter


def global_efficiency(all_pairs: dict[str, PathResults]) -> float:
    """Compute the graph's global efficiency, treating unreachable pairs as 0."""
    node_count = len(all_pairs)
    if node_count < 2:
        return 0.0

    efficiency_sum = 0.0

    for source, result in all_pairs.items():
        for target, distance in result.distances.items():
            if source == target or math.isinf(distance) or distance == 0:
                continue
            efficiency_sum += 1.0 / distance

    return efficiency_sum / (node_count * (node_count - 1))


def graph_global_efficiency(graph: Graph) -> float:
    """Compute global efficiency directly from the graph."""
    return global_efficiency(all_pairs_shortest_paths(graph))


def maximum_betweenness_centrality(centrality: dict[str, float]) -> float:
    """Return the maximum node betweenness score in ``centrality``."""
    return max(centrality.values(), default=0.0)


def betweenness_centrality(graph: Graph, all_pairs: dict[str, PathResults] | None = None) -> dict[str, float]:
    """Compute weighted betweenness centrality using Brandes' algorithm.

    Preconditions:
        - len(graph.adjacency) > 0
    """
    if all_pairs is None:
        all_pairs = all_pairs_shortest_paths(graph)

    centrality = {node: 0.0 for node in graph.nodes()}

    for source, result in all_pairs.items():
        dependency = {node: 0.0 for node in graph.nodes()}

        for node in reversed(result.visit_order):
            for predecessor in result.predecessors[node]:
                if result.path_counts[node] == 0:
                    continue
                contribution = (
                                       result.path_counts[predecessor] / result.path_counts[node]
                               ) * (1.0 + dependency[node])
                dependency[predecessor] += contribution

            if node != source:
                centrality[node] += dependency[node]

    # The graph is undirected, so each pair is counted twice.
    for node in centrality:
        centrality[node] /= 2.0

    return centrality


def compute_network_metrics(graph: Graph) -> NetworkMetrics:
    """Compute all required high-level network metrics.

    Preconditions:
        - len(graph.adjacency) > 0
    """
    all_pairs = all_pairs_shortest_paths(graph)
    return NetworkMetrics(
        average_shortest_path=average_shortest_path_length(all_pairs),
        diameter=network_diameter(all_pairs),
        global_efficiency=global_efficiency(all_pairs),
        betweenness_centrality=betweenness_centrality(graph, all_pairs),
    )


def geographic_distance_hint(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the haversine distance between two coordinates in kilometers.

    Preconditions:
        - -90 <= lat1 <= 90
        - -90 <= lat2 <= 90
        - -180 <= lon1 <= 180
        - -180 <= lon2 <= 180
    """
    earth_radius_km = 6371.0
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    delta_lat = lat2_rad - lat1_rad
    delta_lon = lon2_rad - lon1_rad
    a_value = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c_value = 2 * math.atan2(math.sqrt(a_value), math.sqrt(1 - a_value))
    return earth_radius_km * c_value


def _observed_seconds_per_km(graph: Graph) -> float | None:
    """Estimate travel speed from the graph's existing edges.

    Preconditions:
        - len(graph.adjacency) > 0
    """
    ratios = []

    for source, target, weight in graph.undirected_edges():
        source_station = graph.stations.get(source)
        target_station = graph.stations.get(target)
        if source_station is None or target_station is None:
            continue

        distance_km = geographic_distance_hint(
            source_station.latitude,
            source_station.longitude,
            target_station.latitude,
            target_station.longitude,
        )
        if distance_km <= 0:
            continue

        ratios.append(weight / distance_km)

    if not ratios:
        return None

    return sum(ratios) / len(ratios)


def estimate_candidate_edge_weight(graph: Graph, source: str, target: str) -> float:
    """Estimate the travel-time weight of a hypothetical new connection.

    Preconditions:
        - source in graph.stations
        - target in graph.stations
    """
    source_station = graph.stations[source]
    target_station = graph.stations[target]
    distance_km = geographic_distance_hint(
        source_station.latitude,
        source_station.longitude,
        target_station.latitude,
        target_station.longitude,
    )

    seconds_per_km = _observed_seconds_per_km(graph)
    if seconds_per_km is None:
        average_weight = graph.average_edge_weight()
        return max(average_weight, 60.0) if average_weight > 0 else max(distance_km * 120.0, 60.0)

    return max(distance_km * seconds_per_km, 60.0)


def find_best_new_connection(
        graph: Graph,
        max_distance_km: float | None = None,
        min_distance_km: float = 0.0,
        min_existing_path_seconds: float = 0.0,
        exclude_same_route: bool = False,
        baseline_efficiency: float | None = None,
        candidate_nodes: list[str] | None = None,
) -> EdgeRecommendation | None:
    """Return the best edge for improving global efficiency.

    This wrapper preserves the original API while delegating to the
    multi-objective search implementation.
    """
    recommendations = find_best_new_connections(
        graph=graph,
        max_distance_km=max_distance_km,
        min_distance_km=min_distance_km,
        min_existing_path_seconds=min_existing_path_seconds,
        exclude_same_route=exclude_same_route,
        baseline_metrics=compute_network_metrics(graph) if baseline_efficiency is None else None,
        candidate_nodes=candidate_nodes,
        baseline_efficiency=baseline_efficiency,
    )
    return recommendations.global_efficiency


def find_best_new_connections(
        graph: Graph,
        max_distance_km: float | None = None,
        min_distance_km: float = 0.0,
        min_existing_path_seconds: float = 0.0,
        exclude_same_route: bool = False,
        baseline_metrics: NetworkMetrics | None = None,
        candidate_nodes: list[str] | None = None,
        baseline_efficiency: float | None = None,
) -> EdgeRecommendationSet:
    """Brute-force search for the best edge to add for each supported metric.

    Preconditions:
        - len(graph.adjacency) > 1
        - candidate_nodes is None or all(n in graph.stations for n in candidate_nodes)
    """
    if graph.node_count() < 2:
        return EdgeRecommendationSet(None, None, None, None)

    if baseline_metrics is None:
        baseline_metrics = compute_network_metrics(graph)
    if baseline_efficiency is None:
        baseline_efficiency = baseline_metrics.global_efficiency

    baseline_values = {
        "average_shortest_path": baseline_metrics.average_shortest_path,
        "diameter": baseline_metrics.diameter,
        "global_efficiency": baseline_efficiency,
        "maximum_betweenness": maximum_betweenness_centrality(baseline_metrics.betweenness_centrality),
    }
    metric_goals = {
        "average_shortest_path": "minimize",
        "diameter": "minimize",
        "global_efficiency": "maximize",
        "maximum_betweenness": "minimize",
    }

    best_recommendations: dict[str, EdgeRecommendation | None] = {
        metric_name: None for metric_name in baseline_values
    }
    nodes = candidate_nodes[:] if candidate_nodes is not None else graph.nodes()
    path_cache: dict[str, PathResults] = {}

    for index, source in enumerate(nodes):
        source_station = graph.stations.get(source)
        if source_station is None:
            continue

        if min_existing_path_seconds > 0:
            path_cache[source] = dijkstra(graph, source)

        for target in nodes[index + 1:]:
            if graph.has_edge(source, target):
                continue
            if exclude_same_route and graph.route_ids_for(source) & graph.route_ids_for(target):
                continue
            if graph.complex_id_for(source) == graph.complex_id_for(target):
                continue

            target_station = graph.stations.get(target)
            if target_station is None:
                continue

            distance_km = geographic_distance_hint(
                source_station.latitude,
                source_station.longitude,
                target_station.latitude,
                target_station.longitude,
            )
            if distance_km < min_distance_km:
                continue
            if max_distance_km is not None and distance_km > max_distance_km:
                continue
            if min_existing_path_seconds > 0:
                existing_distance = path_cache[source].distances.get(target, math.inf)
                if not math.isinf(existing_distance) and existing_distance < min_existing_path_seconds:
                    continue

            candidate_weight = estimate_candidate_edge_weight(graph, source, target)
            trial_graph = graph.copy()
            trial_graph.add_edge(source, target, candidate_weight)
            trial_metrics = compute_network_metrics(trial_graph)
            trial_values = {
                "average_shortest_path": trial_metrics.average_shortest_path,
                "diameter": trial_metrics.diameter,
                "global_efficiency": trial_metrics.global_efficiency,
                "maximum_betweenness": maximum_betweenness_centrality(trial_metrics.betweenness_centrality),
            }

            for metric_name, baseline_value in baseline_values.items():
                recommendation = EdgeRecommendation(
                    metric_name=metric_name,
                    source=source,
                    target=target,
                    weight=candidate_weight,
                    baseline_value=baseline_value,
                    new_value=trial_values[metric_name],
                    goal=metric_goals[metric_name],
                )

                current_best = best_recommendations[metric_name]
                if current_best is None or recommendation.improvement > current_best.improvement:
                    best_recommendations[metric_name] = recommendation

    return EdgeRecommendationSet(
        average_shortest_path=best_recommendations["average_shortest_path"],
        diameter=best_recommendations["diameter"],
        global_efficiency=best_recommendations["global_efficiency"],
        maximum_betweenness=best_recommendations["maximum_betweenness"],
    )


def top_k_central_stations(centrality: dict[str, float], k: int = 5) -> list[tuple[str, float]]:
    """Return the top ``k`` stations by centrality score."""
    return sorted(centrality.items(), key=lambda item: item[1], reverse=True)[:k]


if __name__ == "__main__":
    import doctest
    import python_ta

    doctest.testmod()
    python_ta.check_all(config={
        'extra-imports': ['heapq', 'math', 'dataclasses', 'graph'],
        'allowed-io': [],
        'max-line-length': 120
    })
