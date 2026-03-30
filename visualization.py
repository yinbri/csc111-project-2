"""Plotly-based visualization helpers for the TTC network project."""

from __future__ import annotations

import plotly.graph_objects as go

from graph import Graph
from metrics import EdgeRecommendation


def build_edge_trace(graph: Graph) -> go.Scatter:
    """Create a Plotly trace for the graph's edges.

    TODO:
        Deduplicate reverse edges if the graph is treated as undirected.
    """
    x_values: list[float] = []
    y_values: list[float] = []

    for source, target, _weight in graph.edges():
        if source not in graph.stations or target not in graph.stations:
            continue

        source_station = graph.stations[source]
        target_station = graph.stations[target]

        x_values.extend([source_station.longitude, target_station.longitude, None])
        y_values.extend([source_station.latitude, target_station.latitude, None])

    return go.Scatter(
        x=x_values,
        y=y_values,
        mode="lines",
        line={"width": 1, "color": "#7f8c8d"},
        hoverinfo="none",
        name="Existing connections",
    )


def build_node_trace(graph: Graph, centrality: dict[str, float]) -> go.Scatter:
    """Create a Plotly trace for graph nodes.

    Hover text should include:
        - station name
        - degree
        - centrality score
    """
    x_values: list[float] = []
    y_values: list[float] = []
    marker_colors: list[float] = []
    hover_text: list[str] = []

    for node in graph.nodes():
        station = graph.stations.get(node)
        if station is None:
            continue

        score = centrality.get(node, 0.0)
        x_values.append(station.longitude)
        y_values.append(station.latitude)
        marker_colors.append(score)
        hover_text.append(
            f"{station.name}<br>"
            f"Degree: {graph.degree(node)}<br>"
            f"Centrality: {score:.3f}"
        )

    return go.Scatter(
        x=x_values,
        y=y_values,
        mode="markers",
        hoverinfo="text",
        text=hover_text,
        name="Stations",
        marker={
            "size": 10,
            "color": marker_colors,
            "colorscale": "Viridis",
            "colorbar": {"title": "Centrality"},
            "line": {"width": 0.5, "color": "#2c3e50"},
        },
    )


def build_recommended_edge_trace(graph: Graph, recommendation: EdgeRecommendation | None) -> go.Scatter | None:
    """Create a trace for the suggested new edge, highlighted in red."""
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
        line={"width": 3, "color": "#e74c3c"},
        hoverinfo="text",
        text=(
            f"Suggested new connection:<br>"
            f"{source_station.name} ↔ {target_station.name}<br>"
            f"Estimated weight: {recommendation.weight:.2f}"
        ),
        name="Recommended connection",
    )


def create_network_figure(
    graph: Graph,
    centrality: dict[str, float],
    recommendation: EdgeRecommendation | None = None,
) -> go.Figure:
    """Create the interactive Plotly figure for the network.

    TODO:
        Tune layout styling to match your final presentation quality.
    """
    traces = [
        build_edge_trace(graph),
        build_node_trace(graph, centrality),
    ]

    recommended_trace = build_recommended_edge_trace(graph, recommendation)
    if recommended_trace is not None:
        traces.append(recommended_trace)

    figure = go.Figure(data=traces)
    figure.update_layout(
        title="TTC Transit Network Analysis",
        showlegend=True,
        xaxis={"title": "Longitude", "showgrid": False, "zeroline": False},
        yaxis={"title": "Latitude", "showgrid": False, "zeroline": False},
        plot_bgcolor="white",
    )
    return figure


def show_network_figure(
    graph: Graph,
    centrality: dict[str, float],
    recommendation: EdgeRecommendation | None = None,
) -> None:
    """Build and display the Plotly visualization."""
    figure = create_network_figure(graph, centrality, recommendation)
    figure.show()
