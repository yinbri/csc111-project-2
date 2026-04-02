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
    """Represent the best new edge found by the optimization search.

    Instance Attributes:
        - source: The source node ID for the recommended edge.
        - target: The target node ID for the recommended edge.
        - weight: The estimated weight (travel time) for the new edge.
        - baseline_efficiency: The network's global efficiency before adding the edge.
        - new_efficiency: The network's global efficiency after adding the edge.
    """

    source: str
    target: str
    weight: float
    baseline_efficiency: float
    new_efficiency: float

    @property
    def improvement(self) -> float:
        """Return the raw improvement in global efficiency."""
        return self.new_efficiency - self.baseline_efficiency

    @property
    def improvement_percent(self) -> float:
        """Return the efficiency improvement percentage."""
        if self.baseline_efficiency == 0:
            return math.inf if self.new_efficiency > 0 else 0.0
        return (self.improvement / self.baseline_efficiency) * 100.0


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
    baseline_efficiency: float | None = None,
    candidate_nodes: list[str] | None = None,
) -> EdgeRecommendation | None:
    """Brute-force search for the best edge to add to the graph.

    Preconditions:
        - len(graph.adjacency) > 1
        - candidate_nodes is None or all(n in graph.stations for n in candidate_nodes)
    """
    if graph.node_count() < 2:
        return None

    if baseline_efficiency is None:
        baseline_efficiency = graph_global_efficiency(graph)

    best_recommendation: EdgeRecommendation | None = None
    nodes = candidate_nodes[:] if candidate_nodes is not None else graph.nodes()

    for index, source in enumerate(nodes):
        source_station = graph.stations.get(source)
        if source_station is None:
            continue

        for target in nodes[index + 1:]:
            if graph.has_edge(source, target):
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
            if max_distance_km is not None and distance_km > max_distance_km:
                continue

            candidate_weight = estimate_candidate_edge_weight(graph, source, target)
            trial_graph = graph.copy()
            trial_graph.add_edge(source, target, candidate_weight)
            new_efficiency = graph_global_efficiency(trial_graph)

            recommendation = EdgeRecommendation(
                source=source,
                target=target,
                weight=candidate_weight,
                baseline_efficiency=baseline_efficiency,
                new_efficiency=new_efficiency,
            )

            if (
                best_recommendation is None
                or recommendation.improvement > best_recommendation.improvement
            ):
                best_recommendation = recommendation

    return best_recommendation


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
