"""Core graph data structures for the TTC network project.

This module intentionally avoids using ``networkx`` for graph logic.
The goal is to provide a lightweight, student-friendly graph class that
supports weighted edges and the algorithms needed by the project.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Station:
    """Represent a TTC station or stop in the graph.

    Attributes:
        stop_id: Unique GTFS stop identifier.
        name: Human-readable station name.
        latitude: Geographic latitude.
        longitude: Geographic longitude.
    """

    stop_id: str
    name: str
    latitude: float
    longitude: float


@dataclass
class Graph:
    """Weighted graph using adjacency dictionaries.

    Representation invariant:
        - ``adjacency[u][v]`` is the weight of the edge from ``u`` to ``v``.
        - All edge weights are non-negative.
        - Each node in ``adjacency`` may optionally have metadata in ``stations``.

    Design note:
        The project prompt describes the graph as station-based and weighted by
        travel time between consecutive stops. This class is intentionally kept
        generic so that graph algorithms can be tested independently of GTFS
        parsing.
    """

    adjacency: dict[str, dict[str, float]] = field(default_factory=dict)
    stations: dict[str, Station] = field(default_factory=dict)

    def add_station(self, station: Station) -> None:
        """Add a station node to the graph.

        TODO:
            Decide whether duplicate ``stop_id`` values should overwrite
            existing station metadata or raise an error.
        """
        self.stations[station.stop_id] = station
        self.adjacency.setdefault(station.stop_id, {})

    def add_node(self, node: str) -> None:
        """Add a node to the adjacency structure if it does not exist yet."""
        self.adjacency.setdefault(node, {})

    def add_edge(self, source: str, target: str, weight: float, *, bidirectional: bool = True) -> None:
        """Add a weighted edge to the graph.

        Args:
            source: Starting node ID.
            target: Ending node ID.
            weight: Non-negative edge weight, usually travel time in seconds.
            bidirectional: Whether to mirror the edge in the reverse direction.

        TODO:
            Validate the weight and decide how to handle zero-weight edges.
        """
        self.add_node(source)
        self.add_node(target)
        self.adjacency[source][target] = weight

        if bidirectional:
            self.adjacency[target][source] = weight

    def remove_edge(self, source: str, target: str, *, bidirectional: bool = True) -> None:
        """Remove an edge from the graph if present.

        TODO:
            Decide whether missing edges should silently do nothing or raise.
        """
        if source in self.adjacency:
            self.adjacency[source].pop(target, None)

        if bidirectional and target in self.adjacency:
            self.adjacency[target].pop(source, None)

    def has_edge(self, source: str, target: str) -> bool:
        """Return whether an edge exists from ``source`` to ``target``."""
        return target in self.adjacency.get(source, {})

    def neighbors(self, node: str) -> dict[str, float]:
        """Return a mapping of neighbors and edge weights for ``node``."""
        return self.adjacency.get(node, {})

    def degree(self, node: str) -> int:
        """Return the degree of ``node`` based on adjacency entries."""
        return len(self.adjacency.get(node, {}))

    def nodes(self) -> list[str]:
        """Return a list of node IDs in the graph."""
        return list(self.adjacency.keys())

    def edges(self) -> list[tuple[str, str, float]]:
        """Return all edges in the graph.

        TODO:
            If the graph is treated as undirected, deduplicate symmetric edges
            before reporting or visualizing them.
        """
        output: list[tuple[str, str, float]] = []

        for source, neighbors in self.adjacency.items():
            for target, weight in neighbors.items():
                output.append((source, target, weight))

        return output

    def copy(self) -> Graph:
        """Return a shallow structural copy of the graph.

        Note:
            The station objects themselves are reused, which is fine for this
            project because station metadata is expected to be immutable.
        """
        new_graph = Graph()
        new_graph.stations = dict(self.stations)
        new_graph.adjacency = {
            node: dict(neighbors) for node, neighbors in self.adjacency.items()
        }
        return new_graph
