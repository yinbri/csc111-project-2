"""CSC111 Winter 2026 Project 2: TTC Graph Structures

Module Description
==================
This module defines the core graph data structures for representing the Toronto TTC network. It includes 
classes for stations and the weighted graph used for network analysis and optimization.

Copyright and Usage Information
===============================

This file is Copyright (c) 2026 Aarav Chhabra, Brian Yin, Sam Wang, and Kevin Liu
"""

from __future__ import annotations

from dataclasses import dataclass, field



@dataclass(slots=True, frozen=True)
class Station:
    """
    A station-level node in the TTC network.

    Instance Attributes:
        - stop_id: The unique GTFS stop ID for this station.
        - name: The name of the station.
        - latitude: The latitude of the station.
        - longitude: The longitude of the station.
    """
    stop_id: str
    name: str
    latitude: float
    longitude: float


@dataclass
class Graph:
    """
    Weighted graph implemented with adjacency dictionaries.

    The project models a transit network, so this graph is undirected by
    default and edge weights represent travel time in seconds.

    Instance Attributes:
        - adjacency: A dictionary mapping node IDs to their neighbors and edge weights.
        - stations: A dictionary mapping node IDs to their corresponding Station objects.
    """
    adjacency: dict[str, dict[str, float]] = field(default_factory=dict)
    stations: dict[str, Station] = field(default_factory=dict)


    def add_station(self, station: Station) -> None:
        """Add a station node and its metadata to the graph."""
        self.stations[station.stop_id] = station
        self.adjacency.setdefault(station.stop_id, {})


    def add_node(self, node: str) -> None:
        """Add a node to the graph if it does not already exist."""
        self.adjacency.setdefault(node, {})


    def add_edge(self, source: str, target: str, weight: float, *, bidirectional: bool = True) -> None:
        """Add a weighted edge to the graph.

        Raises a ValueError if the weight is negative or either endpoint is empty.
        """
        if not source or not target:
            raise ValueError("source and target must be non-empty node IDs")
        if weight < 0:
            raise ValueError("edge weights must be non-negative")

        self.add_node(source)
        self.add_node(target)
        self.adjacency[source][target] = weight

        if bidirectional:
            self.adjacency[target][source] = weight


    def remove_edge(self, source: str, target: str, *, bidirectional: bool = True) -> None:
        """Remove an edge from the graph if it exists."""
        self.adjacency.get(source, {}).pop(target, None)
        if bidirectional:
            self.adjacency.get(target, {}).pop(source, None)

    def has_edge(self, source: str, target: str) -> bool:
        """Return whether an edge exists from ``source`` to ``target``."""
        return target in self.adjacency.get(source, {})

    def neighbors(self, node: str) -> dict[str, float]:
        """Return the neighbors of ``node`` and their weights."""
        return self.adjacency.get(node, {})

    def degree(self, node: str) -> int:
        """Return the number of adjacent neighbors for ``node``."""
        return len(self.adjacency.get(node, {}))

    def node_count(self) -> int:
        """Return the number of nodes in the graph."""
        return len(self.adjacency)

    def nodes(self) -> list[str]:
        """Return the node IDs in the graph."""
        return list(self.adjacency.keys())

    def undirected_edges(self) -> list[tuple[str, str, float]]:
        """Return a deduplicated list of edges for an undirected graph."""
        output = []
        seen = set()

        for source, neighbors in self.adjacency.items():
            for target, weight in neighbors.items():
                edge_key = frozenset((source, target))
                if edge_key in seen:
                    continue
                seen.add(edge_key)
                output.append((source, target, weight))

        return output

    def average_edge_weight(self) -> float:
        """Return the average weight across undirected edges."""
        edges = self.undirected_edges()
        if not edges:
            return 0.0
        return sum(weight for _, _, weight in edges) / len(edges)

    def copy(self) -> Graph:
        """Return a structural copy of the graph."""
        return Graph(
            adjacency={node: dict(neighbors) for node, neighbors in self.adjacency.items()},
            stations=dict(self.stations),
        )


if __name__ == "__main__":
    import doctest
    import python_ta
    doctest.testmod()
    python_ta.check_all(config={
        'extra-imports': ['dataclasses'],
        'allowed-io': [],
        'max-line-length': 120
    })
