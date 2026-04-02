# TTC Transit Network Analysis

This project analyzes and optimizes the Toronto TTC transit network using a
custom weighted graph implementation built from GTFS data.

## Features

- Builds a station-level weighted graph from GTFS stop, route, trip, and stop-time data
- Uses Dijkstra's algorithm for weighted shortest paths
- Computes:
  - average shortest path length
  - network diameter
  - global efficiency
  - betweenness centrality
- Brute-forces the best new connection to improve global efficiency
- Generates an interactive Plotly visualization with:
  - station hover info
  - centrality coloring
  - recommended new edge highlighted in red

## Files

- `main.py`: Command-line entry point
- `graph.py`: Core graph and station classes
- `data_loader.py`: GTFS parsing and graph construction
- `metrics.py`: Algorithms and analytics
- `visualization.py`: Plotly visualization helpers
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

Run the default analysis:

```bash
python3 main.py
```

By default, the program analyzes the TTC subway network only, which matches the
original project proposal and keeps the optimization search fast enough for a
TA to run from scratch. To include streetcars as well:

```bash
python3 main.py --include-streetcars
```

To analyze the full TTC feed instead:

```bash
python3 main.py --include-all-routes
```

Optional arguments:

```bash
python3 main.py --max-distance-km 5 --html-output output/network.html
python3 main.py --no-visualization
```

The optimizer defaults to considering candidate new edges within 2 km. For
larger route selections, it limits the recommendation search to the most
central stations so the program remains practical to run from scratch.

## Output

The program prints:

- average shortest path
- diameter
- global efficiency
- top 5 stations by centrality
- best new edge and percent improvement

When visualization is enabled, it also writes an HTML Plotly file to the
configured output path.
