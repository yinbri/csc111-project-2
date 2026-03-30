"""Plotly-based visualization helpers for the TTC network project."""

from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go

from graph import Graph
from metrics import EdgeRecommendation


def build_edge_trace(graph: Graph) -> go.Scatter:
    """Create the Plotly trace for the network's existing edges."""
    x_values: list[float | None] = []
    y_values: list[float | None] = []

    for source, target, _weight in graph.undirected_edges():
        source_station = graph.stations.get(source)
        target_station = graph.stations.get(target)
        if source_station is None or target_station is None:
            continue

        x_values.extend([source_station.longitude, target_station.longitude, None])
        y_values.extend([source_station.latitude, target_station.latitude, None])

    return go.Scatter(
        x=x_values,
        y=y_values,
        mode="lines",
        line={"width": 1.5, "color": "#95a5a6"},
        hoverinfo="none",
        name="Existing connections",
    )


def build_node_trace(graph: Graph, centrality: dict[str, float]) -> go.Scatter:
    """Create the Plotly trace for graph nodes."""
    x_values: list[float] = []
    y_values: list[float] = []
    marker_colors: list[float] = []
    marker_sizes: list[float] = []
    hover_text: list[str] = []

    max_centrality = max(centrality.values(), default=0.0)

    for node in graph.nodes():
        station = graph.stations.get(node)
        if station is None:
            continue

        score = centrality.get(node, 0.0)
        scaled_size = 10.0 if max_centrality == 0 else 10.0 + 12.0 * (score / max_centrality)
        x_values.append(station.longitude)
        y_values.append(station.latitude)
        marker_colors.append(score)
        marker_sizes.append(scaled_size)
        hover_text.append(
            f"{station.name}<br>"
            f"Degree: {graph.degree(node)}<br>"
            f"Centrality Score: {score:.3f}"
        )

    return go.Scatter(
        x=x_values,
        y=y_values,
        mode="markers",
        hoverinfo="text",
        text=hover_text,
        name="Stations",
        marker={
            "size": marker_sizes,
            "color": marker_colors,
            "colorscale": "Viridis",
            "colorbar": {"title": "Centrality"},
            "line": {"width": 0.8, "color": "#2c3e50"},
        },
    )


def build_recommended_edge_trace(graph: Graph, recommendation: EdgeRecommendation | None) -> go.Scatter | None:
    """Create a trace for the recommended new connection."""
    if recommendation is None:
        return None

    source_station = graph.stations.get(recommendation.source)
    target_station = graph.stations.get(recommendation.target)
    if source_station is None or target_station is None:
        return None

    return go.Scatter(
        x=[source_station.longitude, target_station.longitude],
        y=[source_station.latitude, target_station.latitude],
        mode="lines",
        line={"width": 4, "color": "#e74c3c"},
        hoverinfo="text",
        text=(
            f"Suggested new connection<br>"
            f"{source_station.name} ↔ {target_station.name}<br>"
            f"Estimated travel time: {recommendation.weight:.1f} seconds<br>"
            f"Efficiency improvement: {recommendation.improvement_percent:.2f}%"
        ),
        name="Recommended connection",
    )


def create_network_figure(
    graph: Graph,
    centrality: dict[str, float],
    recommendation: EdgeRecommendation | None = None,
) -> go.Figure:
    """Create the interactive Plotly figure for the network."""
    traces: list[go.Scatter] = [build_edge_trace(graph), build_node_trace(graph, centrality)]
    recommended_trace = build_recommended_edge_trace(graph, recommendation)
    if recommended_trace is not None:
        traces.append(recommended_trace)

    figure = go.Figure(data=traces)
    figure.update_layout(
        title="TTC Transit Network Analysis",
        showlegend=True,
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis={"title": "Longitude", "showgrid": False, "zeroline": False},
        yaxis={"title": "Latitude", "showgrid": False, "zeroline": False, "scaleanchor": "x", "scaleratio": 1},
        margin={"l": 40, "r": 40, "t": 60, "b": 40},
    )
    return figure


def save_network_figure(
    graph: Graph,
    centrality: dict[str, float],
    recommendation: EdgeRecommendation | None,
    output_path: str | Path,
) -> Path:
    """Write the visualization to an HTML file and return its path."""
    figure = create_network_figure(graph, centrality, recommendation)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.write_html(str(output))
    return output


def show_network_figure(
    graph: Graph,
    centrality: dict[str, float],
    recommendation: EdgeRecommendation | None = None,
) -> None:
    """Display the interactive Plotly figure in a browser or notebook."""
    create_network_figure(graph, centrality, recommendation).show()
