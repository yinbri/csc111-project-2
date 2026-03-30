# TTC Transit Network Project Scaffold

This repository contains a starter framework for analyzing and optimizing the
Toronto TTC transit network using graph algorithms.

## Files

- `main.py`: Entry point that connects loading, analytics, and visualization
- `graph.py`: Core graph and station data structures
- `data_loader.py`: GTFS parsing and graph construction helpers
- `metrics.py`: Shortest paths, efficiency, diameter, centrality, and edge search
- `visualization.py`: Plotly traces and figure assembly

## What Is Included

- Class and function structure
- Type hints
- Docstrings explaining intended behavior
- `TODO` markers where implementation decisions still need to be made
- Comments that point to likely next steps

## Suggested Next Steps

1. Create a `data/` folder and add `stops.txt`, `stop_times.txt`, and `routes.txt`.
2. Implement `estimate_candidate_edge_weight` in `metrics.py`.
3. Replace the placeholder geographic-distance helper with a real formula.
4. Decide how repeated GTFS edges should be aggregated.
5. Improve `betweenness_centrality` if you want more accurate scores.

## Notes

- The scaffold avoids `networkx` for core graph logic as requested.
- `visualization.py` expects `plotly` to be installed in your Python environment.
- Some functions intentionally raise `NotImplementedError` until you choose a
  final strategy for the project.
