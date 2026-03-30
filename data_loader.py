"""Utilities for loading TTC GTFS data into the project graph.

This file is focused on file parsing and graph construction, not on analytics.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from graph import Graph, Station


@dataclass(slots=True)
class StopTimeRecord:
    """Represent a single row from ``stop_times.txt``.

    Attributes:
        trip_id: GTFS trip identifier.
        arrival_time: Scheduled arrival time as raw text.
        departure_time: Scheduled departure time as raw text.
        stop_id: GTFS stop identifier.
        stop_sequence: Position of the stop within the trip.
    """

    trip_id: str
    arrival_time: str
    departure_time: str
    stop_id: str
    stop_sequence: int


def parse_time_to_seconds(time_str: str) -> int:
    """Convert a GTFS time string like ``HH:MM:SS`` into seconds.

    TODO:
        Support times beyond 24:00:00, which GTFS may use for trips that
        continue after midnight.
    """
    hours, minutes, seconds = (int(part) for part in time_str.split(":"))
    return hours * 3600 + minutes * 60 + seconds


def load_stops(stops_path: str | Path) -> dict[str, Station]:
    """Load station metadata from ``stops.txt``.

    TODO:
        Consider filtering the dataset to subway stations only if the full TTC
        GTFS feed is too large for the project runtime budget.
    """
    stations: dict[str, Station] = {}

    with Path(stops_path).open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            station = Station(
                stop_id=row["stop_id"],
                name=row["stop_name"],
                latitude=float(row["stop_lat"]),
                longitude=float(row["stop_lon"]),
            )
            stations[station.stop_id] = station

    return stations


def load_stop_times(stop_times_path: str | Path) -> list[StopTimeRecord]:
    """Load stop-time rows from ``stop_times.txt``.

    TODO:
        If performance becomes an issue, stream and group records per trip
        instead of materializing the entire file at once.
    """
    records: list[StopTimeRecord] = []

    with Path(stop_times_path).open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            records.append(
                StopTimeRecord(
                    trip_id=row["trip_id"],
                    arrival_time=row["arrival_time"],
                    departure_time=row["departure_time"],
                    stop_id=row["stop_id"],
                    stop_sequence=int(row["stop_sequence"]),
                )
            )

    return records


def load_routes(routes_path: str | Path) -> list[dict[str, str]]:
    """Load route metadata from ``routes.txt``.

    TODO:
        Replace the loose dict return type with a dataclass if route metadata
        becomes important to graph filtering or visualization.
    """
    with Path(routes_path).open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        return list(reader)


def group_stop_times_by_trip(stop_times: list[StopTimeRecord]) -> dict[str, list[StopTimeRecord]]:
    """Group stop times by trip and sort each trip by ``stop_sequence``."""
    grouped: dict[str, list[StopTimeRecord]] = {}

    for record in stop_times:
        grouped.setdefault(record.trip_id, []).append(record)

    for trip_records in grouped.values():
        trip_records.sort(key=lambda record: record.stop_sequence)

    return grouped


def build_graph_from_gtfs(
    stops_path: str | Path,
    stop_times_path: str | Path,
    routes_path: str | Path | None = None,
) -> Graph:
    """Build a weighted graph from GTFS input files.

    The current plan is:
        1. Load station metadata.
        2. Load stop sequences for each trip.
        3. Connect consecutive stops with travel-time weights.

    TODO:
        Decide how to aggregate repeated edges across many trips.
        Common choices:
            - keep the minimum travel time
            - keep the average travel time
            - count frequency and store multiple statistics
    """
    graph = Graph()
    stations = load_stops(stops_path)

    for station in stations.values():
        graph.add_station(station)

    stop_times = load_stop_times(stop_times_path)
    trips = group_stop_times_by_trip(stop_times)

    if routes_path is not None:
        # Placeholder hook for future route-based filtering or labeling.
        _routes = load_routes(routes_path)
        # TODO: Use route information to limit analysis to specific TTC lines.

    for trip_id, records in trips.items():
        _ = trip_id
        for index in range(len(records) - 1):
            current_stop = records[index]
            next_stop = records[index + 1]

            current_departure = parse_time_to_seconds(current_stop.departure_time)
            next_departure = parse_time_to_seconds(next_stop.departure_time)
            travel_time = max(0, next_departure - current_departure)

            # TODO: Replace this naive overwrite policy with a proper edge
            # aggregation strategy once the project decides on one.
            graph.add_edge(current_stop.stop_id, next_stop.stop_id, travel_time)

    return graph
