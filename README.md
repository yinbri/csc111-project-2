# TTC Transit Network Analysis

This project analyzes and optimizes the Toronto TTC transit network using a
custom weighted graph implementation built from GTFS data and presents the
results in a Python Tkinter desktop application.

## Features

- Builds a station-level weighted graph from GTFS stop, route, trip, and stop-time data
- Uses Dijkstra's algorithm for weighted shortest paths
- Launches an interactive Tkinter window for analysis and path exploration
- Computes:
  - average shortest path length
  - network diameter
  - global efficiency
  - betweenness centrality
- Brute-forces the best new connection to improve global efficiency
- Lets users type two station names and highlight a shortest path in the GUI

## Files

- `main.py`: Desktop app entry point
- `gui.py`: Tkinter window and canvas visualization
- `graph.py`: Core graph and station classes
- `data_loader.py`: GTFS parsing and graph construction
- `metrics.py`: Algorithms and analytics
- `requirements.txt`: Python dependency list

## Setup

Install the dependency:

```bash
pip install -r requirements.txt
```

Add your GTFS files to the `data/` directory:

- `data/stops.txt`
- `data/stop_times.txt`
- `data/routes.txt`
- `data/trips.txt`

## Usage

Run the desktop application:

```bash
python3 main.py
```

The GUI opens with the subway network loaded by default. Inside the window, the
user can:

- adjust the maximum candidate edge distance
- inspect the recommended new connection
- type two station names to display the shortest path on the map canvas

## Output

The program shows:

- average shortest path
- diameter
- global efficiency
- top 5 stations by centrality
- best new edge and percent improvement
- a canvas view of the network
- a highlighted shortest path between any two typed station names
