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

import argparse
from pathlib import Path

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
    return parser.parse_args()


def validate_input_files(stops_path: Path, stop_times_path: Path, routes_path: Path, trips_path: Path) -> None:
    """Raise a helpful error if any required GTFS files are missing."""
    missing_paths = [path for path in (stops_path, stop_times_path, routes_path, trips_path) if not path.exists()]
    if missing_paths:
        missing_text = ", ".join(str(path) for path in missing_paths)
        raise FileNotFoundError(f"Missing required GTFS file(s): {missing_text}")


def main() -> None:
    """Launch the TTC desktop application."""
    args = parse_args()
    data_dir = args.data_dir
    stops_path = data_dir / args.stops_file
    stop_times_path = data_dir / args.stop_times_file
    routes_path = data_dir / args.routes_file
    trips_path = data_dir / args.trips_file

    validate_input_files(stops_path, stop_times_path, routes_path, trips_path)
    from gui import launch_app

    launch_app(
        data_dir=data_dir,
        stops_file=args.stops_file,
        stop_times_file=args.stop_times_file,
        routes_file=args.routes_file,
        trips_file=args.trips_file,
    )


if __name__ == "__main__":
    main()
