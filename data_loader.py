"""CSC111 Winter 2026 Project 2: TTC Data Loader

Module Description
==================
This module provides utilities for loading Toronto Transit Commission (TTC) GTFS data files and building the graph 
representation used throughout the project. It includes data classes and functions for parsing GTFS files and 
constructing the network graph.

Copyright and Usage Information
===============================

This file is Copyright (c) 2026 Aarav Chhabra, Brian Yin, Sam Wang, and Kevin Liu
"""

from __future__ import annotations

import csv
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from graph import Graph, Station



@dataclass(slots=True, frozen=True)
class StopTimeRecord:
    """Represent a single row from stop_times.txt.

    Instance Attributes:
        - trip_id: The trip ID for this stop time record.
        - arrival_time: The scheduled arrival time at the stop.
        - departure_time: The scheduled departure time from the stop.
        - stop_id: The GTFS stop ID for this record.
        - stop_sequence: The sequence number of the stop within the trip.
    """

    trip_id: str
    arrival_time: str
    departure_time: str
    stop_id: str
    stop_sequence: int



@dataclass(slots=True, frozen=True)
class RouteRecord:
    """Represent a single row from routes.txt.

    Instance Attributes:
        - route_id: The unique route ID.
        - route_short_name: The short name of the route.
        - route_long_name: The long name of the route.
        - route_type: The type of route (e.g., subway, bus).
    """

    route_id: str
    route_short_name: str
    route_long_name: str
    route_type: str



@dataclass(slots=True, frozen=True)
class TripRecord:
    """Represent a single row from trips.txt.

    Instance Attributes:
        - route_id: The route ID for this trip.
        - service_id: The service ID for this trip.
        - trip_id: The unique trip ID.
    """

    route_id: str
    service_id: str
    trip_id: str


def parse_time_to_seconds(time_str: str) -> int:
    """Convert a GTFS time string like ``HH:MM:SS`` to total seconds.

    Preconditions:
        - time_str.count(":") == 2
    """
    hours, minutes, seconds = (int(part) for part in time_str.strip().split(":"))
    return hours * 3600 + minutes * 60 + seconds


def load_stops(stops_path: str | Path) -> dict[str, Station]:
    """Load raw stop metadata keyed by GTFS stop ID."""
    stops = {}

    with Path(stops_path).open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            stop_id = row["stop_id"].strip()
            stop_name = row["stop_name"].strip()
            if not stop_id or not stop_name:
                continue

            stops[stop_id] = Station(
                stop_id=stop_id,
                name=stop_name,
                latitude=float(row["stop_lat"]),
                longitude=float(row["stop_lon"]),
            )

    return stops


def load_stop_times(stop_times_path: str | Path) -> list[StopTimeRecord]:
    """Load rows from ``stop_times.txt``."""
    records = []

    with Path(stop_times_path).open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            trip_id = row["trip_id"].strip()
            stop_id = row["stop_id"].strip()
            if not trip_id or not stop_id:
                continue

            records.append(
                StopTimeRecord(
                    trip_id=trip_id,
                    arrival_time=row["arrival_time"].strip(),
                    departure_time=row["departure_time"].strip(),
                    stop_id=stop_id,
                    stop_sequence=int(row["stop_sequence"]),
                )
            )

    return records


def load_routes(routes_path: str | Path) -> list[RouteRecord]:
    """Load route metadata from ``routes.txt``.

    The route data is not required for the core graph construction in this
    version, but it is loaded for completeness and future extension.
    """
    routes = []

    with Path(routes_path).open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            routes.append(
                RouteRecord(
                    route_id=row.get("route_id", "").strip(),
                    route_short_name=row.get("route_short_name", "").strip(),
                    route_long_name=row.get("route_long_name", "").strip(),
                    route_type=row.get("route_type", "").strip(),
                )
            )

    return routes


def load_trips(trips_path: str | Path) -> list[TripRecord]:
    """Load trip metadata from ``trips.txt``."""
    trips = []

    with Path(trips_path).open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            trip_id = row.get("trip_id", "").strip()
            route_id = row.get("route_id", "").strip()
            service_id = row.get("service_id", "").strip()
            if not trip_id or not route_id:
                continue

            trips.append(
                TripRecord(
                    route_id=route_id,
                    service_id=service_id,
                    trip_id=trip_id,
                )
            )

    return trips


def load_route_ids_by_type(routes_path: str | Path, route_types: set[str]) -> set[str]:
    """Return the route IDs whose GTFS ``route_type`` is in ``route_types``."""
    route_ids = set()

    with Path(routes_path).open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            route_type = row.get("route_type", "").strip()
            route_id = row.get("route_id", "").strip()
            if route_id and route_type in route_types:
                route_ids.add(route_id)

    return route_ids


def load_trip_ids_for_routes(trips_path: str | Path, route_ids: set[str]) -> set[str]:
    """Return the trip IDs whose route appears in ``route_ids``."""
    trip_ids = set()

    with Path(trips_path).open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            route_id = row.get("route_id", "").strip()
            trip_id = row.get("trip_id", "").strip()
            if trip_id and route_id in route_ids:
                trip_ids.add(trip_id)

    return trip_ids


def load_trip_route_ids(
    trips_path: str | Path,
    allowed_route_ids: set[str] | None = None,
) -> dict[str, str]:
    """Return a mapping from trip ID to the GTFS route ID for that trip."""
    trip_route_ids = {}

    with Path(trips_path).open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            route_id = row.get("route_id", "").strip()
            trip_id = row.get("trip_id", "").strip()
            if not route_id or not trip_id:
                continue
            if allowed_route_ids is not None and route_id not in allowed_route_ids:
                continue

            trip_route_ids[trip_id] = route_id

    return trip_route_ids


_STATION_SUFFIX_PATTERNS = (
    re.compile(r"\s*-\s*(?:Eastbound|Westbound|Northbound|Southbound) Platform(?: Towards .+)?$"),
    re.compile(r"\s*-\s*Subway Platform$"),
    re.compile(r"\s*-\s*LRT Platform$"),
    re.compile(r"\s*-\s*Platform [A-Z]$"),
    re.compile(r"\s+(?:Eastbound|Westbound|Northbound|Southbound) Platform$"),
    re.compile(r"\s+Subway Platform$"),
    re.compile(r"\s+LRT Platform$"),
)
INTERCHANGE_DISTANCE_THRESHOLD_KM = 0.12
INTERCHANGE_TRANSFER_SECONDS = 90.0


def normalize_station_name(stop_name: str) -> str:
    """Collapse platform-specific TTC stop names into a physical station name."""
    normalized = stop_name.strip()
    for pattern in _STATION_SUFFIX_PATTERNS:
        normalized = pattern.sub("", normalized)
    return normalized


def group_stop_times_by_trip(stop_times: list[StopTimeRecord]) -> dict[str, list[StopTimeRecord]]:
    """Group stop-time records by trip and sort them by stop sequence."""
    grouped = defaultdict(list)

    for record in stop_times:
        grouped[record.trip_id].append(record)

    for trip_records in grouped.values():
        trip_records.sort(key=lambda record: record.stop_sequence)

    return dict(grouped)


def load_relevant_stop_times_by_trip(
    stop_times_path: str | Path,
    allowed_trip_ids: set[str] | None = None,
) -> dict[str, list[StopTimeRecord]]:
    """Load and group relevant stop-times without materializing the whole file first."""
    grouped = defaultdict(list)

    with Path(stop_times_path).open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            trip_id = row["trip_id"].strip()
            if allowed_trip_ids is not None and trip_id not in allowed_trip_ids:
                continue

            stop_id = row["stop_id"].strip()
            if not trip_id or not stop_id:
                continue

            grouped[trip_id].append(
                StopTimeRecord(
                    trip_id=trip_id,
                    arrival_time=row["arrival_time"].strip(),
                    departure_time=row["departure_time"].strip(),
                    stop_id=stop_id,
                    stop_sequence=int(row["stop_sequence"]),
                )
            )

    for trip_records in grouped.values():
        trip_records.sort(key=lambda record: record.stop_sequence)

    return dict(grouped)


def aggregate_stations_by_name(raw_stops: dict[str, Station]) -> tuple[dict[str, Station], dict[str, str]]:
    """Collapse GTFS stop IDs into station-level nodes keyed by station name.

    Many GTFS feeds include multiple stop IDs that correspond to the same
    station or platform grouping. This project works at the station level, so
    we aggregate by ``stop_name`` and average the coordinates.
    """
    grouped_points = defaultdict(list)

    for stop in raw_stops.values():
        station_name = normalize_station_name(stop.name)
        grouped_points[station_name].append((stop.stop_id, stop.latitude, stop.longitude))

    station_map = {}
    stop_id_to_station_id = {}

    for station_name, points in grouped_points.items():
        avg_lat = sum(point[1] for point in points) / len(points)
        avg_lon = sum(point[2] for point in points) / len(points)
        station_id = station_name
        station_map[station_id] = Station(
            stop_id=station_id,
            name=station_name,
            latitude=avg_lat,
            longitude=avg_lon,
        )

        for original_stop_id, _lat, _lon in points:
            stop_id_to_station_id[original_stop_id] = station_id

    return station_map, stop_id_to_station_id


def _travel_time_between(current_stop: StopTimeRecord, next_stop: StopTimeRecord) -> int:
    """Return the scheduled travel time between consecutive stop-time records."""
    current_departure = parse_time_to_seconds(current_stop.departure_time)
    next_departure = parse_time_to_seconds(next_stop.departure_time)

    if next_departure < current_departure:
        next_arrival = parse_time_to_seconds(next_stop.arrival_time)
        current_arrival = parse_time_to_seconds(current_stop.arrival_time)
        current_departure = max(current_departure, current_arrival)
        next_departure = max(next_departure, next_arrival)

    return max(1, next_departure - current_departure)


def _distance_km_between(station_a: Station, station_b: Station) -> float:
    """Return the haversine distance between two stations in kilometers."""
    earth_radius_km = 6371.0
    lat1_rad = math.radians(station_a.latitude)
    lon1_rad = math.radians(station_a.longitude)
    lat2_rad = math.radians(station_b.latitude)
    lon2_rad = math.radians(station_b.longitude)
    delta_lat = lat2_rad - lat1_rad
    delta_lon = lon2_rad - lon1_rad

    a_value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c_value = 2 * math.atan2(math.sqrt(a_value), math.sqrt(1 - a_value))
    return earth_radius_km * c_value


def _identify_station_complexes(graph: Graph) -> list[set[str]]:
    """Return interchange complexes built from shared lines and close split stations."""
    parent = {node_id: node_id for node_id in graph.nodes()}

    def find(node_id: str) -> str:
        while parent[node_id] != node_id:
            parent[node_id] = parent[parent[node_id]]
            node_id = parent[node_id]
        return node_id

    def union(first: str, second: str) -> None:
        first_root = find(first)
        second_root = find(second)
        if first_root != second_root:
            parent[second_root] = first_root

    nodes = graph.nodes()
    for node_id in nodes:
        if len(graph.route_ids_for(node_id)) > 1:
            union(node_id, node_id)

    for index, first in enumerate(nodes):
        first_routes = graph.route_ids_for(first)
        first_station = graph.stations[first]
        for second in nodes[index + 1:]:
            second_routes = graph.route_ids_for(second)
            if not first_routes or not second_routes or first_routes & second_routes:
                continue

            second_station = graph.stations[second]
            distance_km = _distance_km_between(first_station, second_station)
            if distance_km <= INTERCHANGE_DISTANCE_THRESHOLD_KM:
                union(first, second)

    groups = defaultdict(set)
    for node_id in nodes:
        groups[find(node_id)].add(node_id)

    return [group for group in groups.values() if len(group) > 1 or len(graph.route_ids_for(next(iter(group)))) > 1]


def build_graph_from_gtfs(
    stops_path: str | Path,
    stop_times_path: str | Path,
    routes_path: str | Path | None = None,
    trips_path: str | Path | None = None,
    route_types: set[str] | None = None,
) -> Graph:
    """Build a station-level weighted graph from GTFS files.

    Consecutive stops within each trip become edges, and repeated edges are
    aggregated by their average observed travel time.
    """
    raw_stops = load_stops(stops_path)
    station_map, stop_id_to_station_id = aggregate_stations_by_name(raw_stops)

    allowed_trip_ids: set[str] | None = None
    trip_route_ids: dict[str, str] = {}
    if (
        routes_path is not None
        and trips_path is not None
        and Path(routes_path).exists()
        and Path(trips_path).exists()
        and route_types is not None
    ):
        route_ids = load_route_ids_by_type(routes_path, route_types)
        allowed_trip_ids = load_trip_ids_for_routes(trips_path, route_ids)
        trip_route_ids = load_trip_route_ids(trips_path, route_ids)

    trips = load_relevant_stop_times_by_trip(stop_times_path, allowed_trip_ids)
    edge_totals = defaultdict(float)
    edge_counts = defaultdict(int)
    used_station_ids = set()
    station_route_ids = defaultdict(set)

    for trip_id, records in trips.items():
        route_id = trip_route_ids.get(trip_id, "")
        for index in range(len(records) - 1):
            current_stop = records[index]
            next_stop = records[index + 1]

            source = stop_id_to_station_id.get(current_stop.stop_id)
            target = stop_id_to_station_id.get(next_stop.stop_id)
            if source is None or target is None or source == target:
                continue

            travel_time = _travel_time_between(current_stop, next_stop)
            edge_key = frozenset((source, target))
            edge_totals[edge_key] += travel_time
            edge_counts[edge_key] += 1
            used_station_ids.add(source)
            used_station_ids.add(target)
            if route_id:
                station_route_ids[source].add(route_id)
                station_route_ids[target].add(route_id)

    graph = Graph()
    for station_id in used_station_ids:
        station = station_map.get(station_id)
        if station is not None:
            graph.add_station(station)
            for route_id in station_route_ids.get(station_id, set()):
                graph.add_route_id(station_id, route_id)

    for edge_key, total_weight in edge_totals.items():
        source, target = tuple(edge_key)
        average_weight = total_weight / edge_counts[edge_key]
        graph.add_edge(source, target, average_weight, bidirectional=True)

    for complex_nodes in _identify_station_complexes(graph):
        complex_id = "+".join(sorted(complex_nodes))
        for node_id in complex_nodes:
            graph.set_complex_id(node_id, complex_id)

        complex_list = sorted(complex_nodes)
        for index, source in enumerate(complex_list):
            for target in complex_list[index + 1:]:
                if not graph.has_edge(source, target):
                    graph.add_edge(source, target, INTERCHANGE_TRANSFER_SECONDS, bidirectional=True)

    return graph


if __name__ == "__main__":
    import doctest
    import python_ta
    doctest.testmod()
    python_ta.check_all(config={
        'extra-imports': ['csv', 're', 'collections', 'dataclasses', 'pathlib', 'graph'],
        'allowed-io': [],
        'max-line-length': 120
    })
