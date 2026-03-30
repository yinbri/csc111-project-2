"""Utilities for loading TTC GTFS data and building the project graph."""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from graph import Graph, Station


@dataclass(slots=True, frozen=True)
class StopTimeRecord:
    """Represent a single row from ``stop_times.txt``."""

    trip_id: str
    arrival_time: str
    departure_time: str
    stop_id: str
    stop_sequence: int


@dataclass(slots=True, frozen=True)
class RouteRecord:
    """Represent a single row from ``routes.txt``."""

    route_id: str
    route_short_name: str
    route_long_name: str
    route_type: str


def parse_time_to_seconds(time_str: str) -> int:
    """Convert a GTFS time string like ``HH:MM:SS`` to total seconds.

    GTFS allows hour values beyond 24 for after-midnight service, and this
    parser supports that directly.
    """
    hours, minutes, seconds = (int(part) for part in time_str.strip().split(":"))
    return hours * 3600 + minutes * 60 + seconds


def load_stops(stops_path: str | Path) -> dict[str, Station]:
    """Load raw stop metadata keyed by GTFS stop ID."""
    stops: dict[str, Station] = {}

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
    records: list[StopTimeRecord] = []

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
    routes: list[RouteRecord] = []

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


def group_stop_times_by_trip(stop_times: list[StopTimeRecord]) -> dict[str, list[StopTimeRecord]]:
    """Group stop-time records by trip and sort them by stop sequence."""
    grouped: dict[str, list[StopTimeRecord]] = defaultdict(list)

    for record in stop_times:
        grouped[record.trip_id].append(record)

    for trip_records in grouped.values():
        trip_records.sort(key=lambda record: record.stop_sequence)

    return dict(grouped)


def aggregate_stations_by_name(raw_stops: dict[str, Station]) -> tuple[dict[str, Station], dict[str, str]]:
    """Collapse GTFS stop IDs into station-level nodes keyed by station name.

    Many GTFS feeds include multiple stop IDs that correspond to the same
    station or platform grouping. This project works at the station level, so
    we aggregate by ``stop_name`` and average the coordinates.
    """
    grouped_points: dict[str, list[tuple[str, float, float]]] = defaultdict(list)

    for stop in raw_stops.values():
        grouped_points[stop.name].append((stop.stop_id, stop.latitude, stop.longitude))

    station_map: dict[str, Station] = {}
    stop_id_to_station_id: dict[str, str] = {}

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


def build_graph_from_gtfs(
    stops_path: str | Path,
    stop_times_path: str | Path,
    routes_path: str | Path | None = None,
) -> Graph:
    """Build a station-level weighted graph from GTFS files.

    Consecutive stops within each trip become edges, and repeated edges are
    aggregated by their average observed travel time.
    """
    raw_stops = load_stops(stops_path)
    station_map, stop_id_to_station_id = aggregate_stations_by_name(raw_stops)

    if routes_path is not None and Path(routes_path).exists():
        load_routes(routes_path)

    graph = Graph()
    for station in station_map.values():
        graph.add_station(station)

    stop_times = load_stop_times(stop_times_path)
    trips = group_stop_times_by_trip(stop_times)
    edge_totals: dict[frozenset[str], float] = defaultdict(float)
    edge_counts: dict[frozenset[str], int] = defaultdict(int)

    for records in trips.values():
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

    for edge_key, total_weight in edge_totals.items():
        source, target = tuple(edge_key)
        average_weight = total_weight / edge_counts[edge_key]
        graph.add_edge(source, target, average_weight, bidirectional=True)

    return graph
