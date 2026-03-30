"""Graph algorithms and network metrics for the TTC project."""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

from graph import Graph


@dataclass(slots=True)
class PathResults:
    """Store the result of running Dijkstra from one source node."""

    source: str
    distances: dict[str, float]
    previous: dict[str, str | None]


@dataclass(slots=True)
class NetworkMetrics:
    """Bundle the high-level metrics reported by the program."""

    average_shortest_path: float
    diameter: float
    global_efficiency: float
    betweenness_centrality: dict[str, float]


@dataclass(slots=True)
class EdgeRecommendation:
    """Represent the best candidate edge discovered by the optimizer."""

    source: str
    target: str
    weight: float
    baseline_efficiency: float
    new_efficiency: float

    @property
    def improvement(self) -> float:
        """Return the raw change in efficiency after adding the edge."""
        return self.new_efficiency - self.baseline_efficiency

    @property
    def improvement_percent(self) -> float:
        """Return the percentage improvement relative to baseline."""
        if self.baseline_efficiency == 0:
            return math.inf
        return (self.improvement / self.baseline_efficiency) * 100.0


def dijkstra(graph: Graph, source: str) -> PathResults:
    """Compute shortest-path distances from ``source`` using Dijkstra.

    TODO:
        Extend this to track the number of shortest paths if you implement a
        more faithful betweenness centrality algorithm later.
    """
    distances = {node: math.inf for node in graph.nodes()}
    previous = {node: None for node in graph.nodes()}
    distances[source] = 0.0

    priority_queue: list[tuple[float, str]] = [(0.0, source)]

    while priority_queue:
        current_distance, current_node = heapq.heappop(priority_queue)

        if current_distance > distances[current_node]:
            continue

        for neighbor, weight in graph.neighbors(current_node).items():
            candidate_distance = current_distance + weight
            if candidate_distance < distances[neighbor]:
                distances[neighbor] = candidate_distance
                previous[neighbor] = current_node
                heapq.heappush(priority_queue, (candidate_distance, neighbor))

    return PathResults(source=source, distances=distances, previous=previous)


def reconstruct_path(previous: dict[str, str | None], source: str, target: str) -> list[str]:
    """Reconstruct one shortest path from ``source`` to ``target``.

    Note:
        This returns only one path, even if multiple shortest paths exist.
        That is acceptable for a first-pass scaffold.
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
    """Run Dijkstra from every node in the graph.

    TODO:
        If runtime becomes too large, restrict analysis to a smaller subgraph
        or add caching where appropriate.
    """
    return {node: dijkstra(graph, node) for node in graph.nodes()}


def average_shortest_path_length(all_pairs: dict[str, PathResults]) -> float:
    """Compute the average shortest path length across reachable node pairs.

    TODO:
        Confirm whether your course expects unreachable pairs to be excluded
        or treated specially in this average.
    """
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
    """Return the maximum finite shortest-path distance in the network."""
    diameter = 0.0

    for source, result in all_pairs.items():
        for target, distance in result.distances.items():
            if source == target or math.isinf(distance):
                continue
            diameter = max(diameter, distance)

    return diameter


def global_efficiency(all_pairs: dict[str, PathResults]) -> float:
    """Compute the graph's global efficiency.

    Formula:
        E = (1 / (N(N - 1))) * sum(1 / d(i, j))

    Unreachable pairs contribute 0.
    """
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


def betweenness_centrality(graph: Graph, all_pairs: dict[str, PathResults] | None = None) -> dict[str, float]:
    """Approximate node betweenness centrality using reconstructed paths.

    This scaffold uses one shortest path per source-target pair. That is a
    simplification of the full definition but is often enough for a first
    project milestone.

    TODO:
        Replace with a full weighted Brandes-style implementation if you want
        more accurate centrality scores for nodes with many tied shortest paths.
    """
    if all_pairs is None:
        all_pairs = all_pairs_shortest_paths(graph)

    scores = {node: 0.0 for node in graph.nodes()}

    for source, result in all_pairs.items():
        for target in graph.nodes():
            if source == target:
                continue

            path = reconstruct_path(result.previous, source, target)
            if len(path) <= 2:
                continue

            for intermediate in path[1:-1]:
                scores[intermediate] += 1.0

    return scores


def compute_network_metrics(graph: Graph) -> NetworkMetrics:
    """Compute the main metrics reported by the CLI."""
    all_pairs = all_pairs_shortest_paths(graph)
    return NetworkMetrics(
        average_shortest_path=average_shortest_path_length(all_pairs),
        diameter=network_diameter(all_pairs),
        global_efficiency=global_efficiency(all_pairs),
        betweenness_centrality=betweenness_centrality(graph, all_pairs),
    )


def geographic_distance_hint(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Estimate the straight-line distance between two coordinates.

    TODO:
        Replace this placeholder with the haversine formula or another
        geodesic approximation if you use distance-based candidate weights.
    """
    _ = (lat1, lon1, lat2, lon2)
    raise NotImplementedError("TODO: implement geographic distance estimate")


def estimate_candidate_edge_weight(graph: Graph, source: str, target: str) -> float:
    """Estimate the weight to assign to a hypothetical new connection.

    TODO:
        Choose a strategy and implement it. Options include:
            - geographic distance converted into travel time
            - average existing edge weight
            - line-specific heuristic
    """
    _ = (graph, source, target)
    raise NotImplementedError("TODO: implement candidate edge weight estimate")


def find_best_new_connection(graph: Graph) -> EdgeRecommendation | None:
    """Brute-force search for the best edge to add to the network.

    TODO:
        Add optional pruning, such as:
            - skipping geographically distant station pairs
            - limiting search to high-centrality candidates
            - caching baseline shortest paths
    """
    baseline_metrics = compute_network_metrics(graph)
    best_recommendation: EdgeRecommendation | None = None
    nodes = graph.nodes()

    for i, source in enumerate(nodes):
        for target in nodes[i + 1:]:
            if graph.has_edge(source, target):
                continue

            candidate_weight = estimate_candidate_edge_weight(graph, source, target)
            trial_graph = graph.copy()
            trial_graph.add_edge(source, target, candidate_weight)

            updated_metrics = compute_network_metrics(trial_graph)
            recommendation = EdgeRecommendation(
                source=source,
                target=target,
                weight=candidate_weight,
                baseline_efficiency=baseline_metrics.global_efficiency,
                new_efficiency=updated_metrics.global_efficiency,
            )

            if (
                best_recommendation is None
                or recommendation.improvement > best_recommendation.improvement
            ):
                best_recommendation = recommendation

    return best_recommendation


def top_k_central_stations(centrality: dict[str, float], k: int = 5) -> list[tuple[str, float]]:
    """Return the top ``k`` nodes by centrality score."""
    return sorted(
        centrality.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:k]
