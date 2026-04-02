"""CSC111 Winter 2026 Project 2: TTC Graph Analysis Main

Module Description
==================
This module serves as the desktop application entry point for the TTC network
analysis project. It parses arguments, validates the GTFS data paths, and
launches the Tkinter interface for the Toronto TTC network.

Copyright and Usage Information
===============================

This file is Copyright (c) 2026 Aarav Chhabra, Brian Yin, Sam Wang, and Kevin Liu
"""

from __future__ import annotations
from pathlib import Path
from gui import launch_app


def validate_input_files(stops_path: Path, stop_times_path: Path, routes_path: Path, trips_path: Path) -> None:
    """Raise a helpful error if any required GTFS files are missing."""
    missing_paths = [path for path in (stops_path, stop_times_path, routes_path, trips_path) if not path.exists()]
    if missing_paths:
        missing_text = ", ".join(str(path) for path in missing_paths)
        raise FileNotFoundError(f"Missing required GTFS file(s): {missing_text}")


def main() -> None:
    """Launch the TTC desktop application."""
    data_dir = Path("data")
    stops_file = "stops.txt"
    stop_times_file = "stop_times.txt"
    routes_file = "routes.txt"
    trips_file = "trips.txt"

    stops_path = data_dir / stops_file
    stop_times_path = data_dir / stop_times_file
    routes_path = data_dir / routes_file
    trips_path = data_dir / trips_file

    validate_input_files(stops_path, stop_times_path, routes_path, trips_path)

    launch_app(
        data_dir=data_dir,
        stops_file=stops_file,
        stop_times_file=stop_times_file,
        routes_file=routes_file,
        trips_file=trips_file,
    )


if __name__ == "__main__":
    main()
