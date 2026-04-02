"""CSC111 Winter 2026 Project 2: TTC Desktop GUI

Module Description
==================
This module provides a Tkinter desktop interface for the TTC transit network
analysis project. Users can load different TTC route subsets, inspect the
computed network metrics, and search for shortest paths between stations.

Copyright and Usage Information
===============================

This file is Copyright (c) 2026 Aarav Chhabra, Brian Yin, Sam Wang, and Kevin Liu
"""

from __future__ import annotations

import difflib
import math
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox, ttk

from data_loader import build_graph_from_gtfs
from graph import Graph
from metrics import (
    EdgeRecommendation,
    NetworkMetrics,
    compute_network_metrics,
    find_best_new_connection,
    shortest_path_between,
    top_k_central_stations,
)
from visualization_3d import save_3d_network_figure

CANVAS_WIDTH = 900
CANVAS_HEIGHT = 700
CANVAS_PADDING = 36
DEFAULT_MAX_DISTANCE_KM = 2.0
DEFAULT_MIN_DISTANCE_KM = 0.5
DEFAULT_MIN_EXISTING_PATH_SECONDS = 240.0
DEFAULT_CANDIDATE_LIMIT = 30
LARGE_GRAPH_NODE_THRESHOLD = 120
SUBWAY_COLOR = "#1d4ed8"
RECOMMENDATION_COLOR = "#e11d48"
BACKGROUND_COLOR = "#f7f9fc"
MAX_NODE_LABELS = 18


def format_station_label(graph: Graph, node_id: str) -> str:
    """Return a human-readable label for a node."""
    station = graph.stations.get(node_id)
    return station.name if station is not None else node_id


class AutocompleteEntry(ttk.Frame):
    """An entry widget with a live suggestion list."""

    choices: list[str]

    def __init__(self, master: tk.Misc, *, textvariable: tk.StringVar) -> None:
        """Initialize the entry and its suggestion list."""
        super().__init__(master)
        self.columnconfigure(0, weight=1)
        self.choices = []
        self.textvariable = textvariable
        self._is_selecting = False

        self.entry = ttk.Entry(self, textvariable=self.textvariable)
        self.entry.grid(row=0, column=0, sticky="ew")

        self.listbox = tk.Listbox(self, height=6, activestyle="none", exportselection=False)
        self.listbox.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        self.listbox.grid_remove()

        self.textvariable.trace_add("write", self._on_text_change)
        self.entry.bind("<Down>", self._focus_suggestions)
        self.entry.bind("<Return>", self._select_first_suggestion)
        self.entry.bind("<Escape>", self._hide_suggestions)

        self.listbox.bind("<<ListboxSelect>>", self._select_current_suggestion)
        self.listbox.bind("<Double-Button-1>", self._select_current_suggestion)
        self.listbox.bind("<Return>", self._select_current_suggestion)
        self.listbox.bind("<Escape>", self._hide_suggestions)

    def set_choices(self, choices: list[str]) -> None:
        """Update the autocomplete choice list."""
        self.choices = sorted(choices)
        self._refresh_suggestions()

    def get(self) -> str:
        """Return the current text."""
        return self.textvariable.get()

    def clear(self) -> None:
        """Clear the current text and suggestions."""
        self.textvariable.set("")
        self._hide_suggestions()

    def _on_text_change(self, *_args: object) -> None:
        """Refresh visible suggestions when the text changes."""
        if self._is_selecting:
            return
        self._refresh_suggestions()

    def _refresh_suggestions(self) -> None:
        """Populate the suggestion list using the current query."""
        query = self.textvariable.get().strip().casefold()
        matches = self._matching_choices(query)

        self.listbox.delete(0, tk.END)
        for choice in matches:
            self.listbox.insert(tk.END, choice)

        if matches:
            self.listbox.grid()
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(0)
            self.listbox.activate(0)
        else:
            self._hide_suggestions()

    def _matching_choices(self, query: str) -> list[str]:
        """Return the best matching station names for ``query``."""
        if not self.choices:
            return []

        if query == "":
            return self.choices[:8]

        prefix_matches = [choice for choice in self.choices if choice.casefold().startswith(query)]
        contains_matches = [
            choice
            for choice in self.choices
            if query in choice.casefold() and choice not in prefix_matches
        ]
        return (prefix_matches + contains_matches)[:8]

    def _focus_suggestions(self, _event: tk.Event) -> str:
        """Move keyboard focus from the entry into the suggestion list."""
        if self.listbox.winfo_ismapped() and self.listbox.size() > 0:
            self.listbox.focus_set()
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(0)
            self.listbox.activate(0)
        return "break"

    def _select_first_suggestion(self, _event: tk.Event) -> str:
        """Choose the first suggestion when Enter is pressed in the entry."""
        if self.listbox.winfo_ismapped() and self.listbox.size() > 0:
            self._set_text_from_choice(self.listbox.get(0))
            return "break"
        return ""

    def _select_current_suggestion(self, _event: tk.Event) -> str:
        """Choose the highlighted suggestion from the list."""
        selection = self.listbox.curselection()
        if selection:
            self._set_text_from_choice(self.listbox.get(selection[0]))
        return "break"

    def _set_text_from_choice(self, choice: str) -> None:
        """Replace the entry text with the selected suggestion."""
        self._is_selecting = True
        self.textvariable.set(choice)
        self._is_selecting = False
        self._hide_suggestions()
        self.entry.icursor(tk.END)
        self.entry.focus_set()

    def _hide_suggestions(self, _event: tk.Event | None = None) -> str:
        """Hide the suggestion list."""
        self.listbox.selection_clear(0, tk.END)
        self.listbox.grid_remove()
        return "break"


class TransitAnalysisApp:
    """Tkinter application for the TTC network analysis project."""

    data_dir: Path
    stops_file: str
    stop_times_file: str
    routes_file: str
    trips_file: str
    graph: Graph | None
    graph_metrics: NetworkMetrics | None
    recommendation: EdgeRecommendation | None
    candidate_limit: int
    station_name_map: dict[str, str]
    station_names: list[str]
    node_positions: dict[str, tuple[float, float]]
    zoom_scale: float
    pan_x: float
    pan_y: float
    _drag_start_x: int | None
    _drag_start_y: int | None

    def __init__(
        self,
        data_dir: Path,
        stops_file: str,
        stop_times_file: str,
        routes_file: str,
        trips_file: str,
    ) -> None:
        """Initialize the application window and widgets."""
        self.data_dir = data_dir
        self.stops_file = stops_file
        self.stop_times_file = stop_times_file
        self.routes_file = routes_file
        self.trips_file = trips_file
        self.graph = None
        self.graph_metrics = None
        self.recommendation = None
        self.candidate_limit = DEFAULT_CANDIDATE_LIMIT
        self.station_name_map = {}
        self.station_names = []
        self.node_positions = {}
        self.zoom_scale = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self._drag_start_x = None
        self._drag_start_y = None

        self.root = tk.Tk()
        self.root.title("TTC Transit Network Explorer")
        self.root.geometry("1400x860")
        self.root.minsize(1220, 760)

        self.max_distance_var = tk.StringVar(value=f"{DEFAULT_MAX_DISTANCE_KM:.1f}")
        self.status_var = tk.StringVar(value="Loading TTC network...")
        self.metrics_var = tk.StringVar(value="Loading metrics...")
        self.recommendation_var = tk.StringVar(value="Loading recommendation...")
        self.path_summary_var = tk.StringVar(value="Enter two station names to inspect a shortest path.")
        self.path_detail_var = tk.StringVar(value="")

        self.start_station_var = tk.StringVar()
        self.end_station_var = tk.StringVar()

        self._build_layout()

    def _build_layout(self) -> None:
        """Create the window layout and widgets."""
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        sidebar_container = ttk.Frame(self.root, padding=(16, 16, 8, 16))
        sidebar_container.grid(row=0, column=0, sticky="nsew")
        sidebar_container.columnconfigure(0, weight=1)
        sidebar_container.rowconfigure(0, weight=1)

        canvas_frame = ttk.Frame(self.root, padding=(0, 16, 16, 16))
        canvas_frame.grid(row=0, column=1, sticky="nsew")
        canvas_frame.rowconfigure(0, weight=1)
        canvas_frame.columnconfigure(0, weight=1)

        sidebar_canvas = tk.Canvas(
            sidebar_container,
            width=410,
            highlightthickness=0,
            bg=self.root.cget("bg"),
        )
        sidebar_canvas.grid(row=0, column=0, sticky="nsew")

        sidebar_scrollbar = ttk.Scrollbar(sidebar_container, orient="vertical", command=sidebar_canvas.yview)
        sidebar_scrollbar.grid(row=0, column=1, sticky="ns")
        sidebar_canvas.configure(yscrollcommand=sidebar_scrollbar.set)

        sidebar = ttk.Frame(sidebar_canvas, padding=0)
        sidebar.columnconfigure(0, weight=1)
        sidebar_window = sidebar_canvas.create_window((0, 0), window=sidebar, anchor="nw")

        def sync_sidebar_width(event: tk.Event) -> None:
            """Keep the embedded sidebar frame matched to the canvas width."""
            sidebar_canvas.itemconfigure(sidebar_window, width=event.width)

        def update_scroll_region(_event: tk.Event) -> None:
            """Refresh the scrollable region after sidebar layout changes."""
            sidebar_canvas.configure(scrollregion=sidebar_canvas.bbox("all"))

        def scroll_sidebar(event: tk.Event) -> str:
            """Scroll the sidebar with the mouse wheel while the cursor is over it."""
            if event.delta != 0:
                sidebar_canvas.yview_scroll(int(-event.delta / 120), "units")
            return "break"

        sidebar_canvas.bind("<Configure>", sync_sidebar_width)
        sidebar.bind("<Configure>", update_scroll_region)
        sidebar_canvas.bind("<Enter>", lambda _event: sidebar_canvas.bind_all("<MouseWheel>", scroll_sidebar))
        sidebar_canvas.bind("<Leave>", lambda _event: sidebar_canvas.unbind_all("<MouseWheel>"))

        title = ttk.Label(
            sidebar,
            text="TTC Transit Network Explorer",
            font=("TkDefaultFont", 16, "bold"),
        )
        title.grid(row=0, column=0, sticky="w")

        subtitle = ttk.Label(
            sidebar,
            text=(
                "Analyze the network, review the recommended new connection, "
                "and search for shortest paths between subway stations."
            ),
            wraplength=360,
            justify="left",
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(8, 18))

        controls = ttk.LabelFrame(sidebar, text="Analysis Controls", padding=12)
        controls.grid(row=2, column=0, sticky="ew")
        controls.columnconfigure(1, weight=1)

        ttk.Label(controls, text="Max new-edge distance (km)").grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=4,
        )
        ttk.Entry(controls, textvariable=self.max_distance_var).grid(row=0, column=1, sticky="ew", pady=4)

        zoom_frame = ttk.Frame(controls)
        zoom_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(zoom_frame, text="Zoom In", command=lambda: self._adjust_zoom(1.2)).grid(row=0, column=0, sticky="ew")
        ttk.Button(zoom_frame, text="Zoom Out", command=lambda: self._adjust_zoom(1 / 1.2)).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(8, 0),
        )
        ttk.Button(zoom_frame, text="Reset View", command=self._reset_zoom).grid(
            row=0,
            column=2,
            sticky="ew",
            padx=(8, 0),
        )
        zoom_frame.columnconfigure(0, weight=1)
        zoom_frame.columnconfigure(1, weight=1)
        zoom_frame.columnconfigure(2, weight=1)

        ttk.Button(
            controls,
            text="Open Original 3D Map",
            command=self._open_original_3d_map,
        ).grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(8, 0),
        )

        ttk.Button(controls, text="Run Analysis", command=self.run_analysis).grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(10, 0),
        )

        path_panel = ttk.LabelFrame(sidebar, text="Shortest Path Finder", padding=12)
        path_panel.grid(row=3, column=0, sticky="ew", pady=(16, 0))
        path_panel.columnconfigure(0, weight=1)

        ttk.Label(path_panel, text="Start station").grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.start_station_entry = AutocompleteEntry(path_panel, textvariable=self.start_station_var)
        self.start_station_entry.grid(row=1, column=0, sticky="ew")

        ttk.Label(path_panel, text="End station").grid(row=2, column=0, sticky="w", pady=(10, 4))
        self.end_station_entry = AutocompleteEntry(path_panel, textvariable=self.end_station_var)
        self.end_station_entry.grid(row=3, column=0, sticky="ew")

        ttk.Button(path_panel, text="Display Shortest Path", command=self.display_shortest_path).grid(
            row=4,
            column=0,
            sticky="ew",
            pady=(10, 0),
        )

        ttk.Label(path_panel, textvariable=self.path_summary_var, wraplength=360, justify="left").grid(
            row=5,
            column=0,
            sticky="w",
            pady=(10, 0),
        )
        ttk.Label(path_panel, textvariable=self.path_detail_var, wraplength=360, justify="left").grid(
            row=6,
            column=0,
            sticky="w",
            pady=(6, 0),
        )

        metrics_panel = ttk.LabelFrame(sidebar, text="Computed Results", padding=12)
        metrics_panel.grid(row=4, column=0, sticky="nsew", pady=(16, 0))
        metrics_panel.columnconfigure(0, weight=1)
        sidebar.rowconfigure(4, weight=1)

        ttk.Label(metrics_panel, textvariable=self.metrics_var, wraplength=360, justify="left").grid(
            row=0,
            column=0,
            sticky="nw",
        )
        ttk.Separator(metrics_panel).grid(row=1, column=0, sticky="ew", pady=10)
        ttk.Label(metrics_panel, textvariable=self.recommendation_var, wraplength=360, justify="left").grid(
            row=2,
            column=0,
            sticky="nw",
        )

        status = ttk.Label(sidebar, textvariable=self.status_var, wraplength=360, justify="left")
        status.grid(row=5, column=0, sticky="ew", pady=(16, 0))

        self.canvas = tk.Canvas(
            canvas_frame,
            width=CANVAS_WIDTH,
            height=CANVAS_HEIGHT,
            bg=BACKGROUND_COLOR,
            highlightthickness=1,
            highlightbackground="#c5ced9",
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<MouseWheel>", self._zoom_with_mousewheel)
        self.canvas.bind("<ButtonPress-1>", self._start_pan)
        self.canvas.bind("<B1-Motion>", self._perform_pan)
        self.canvas.bind("<ButtonRelease-1>", self._end_pan)

    def run(self) -> None:
        """Start the Tkinter event loop."""
        self.root.after(50, self.run_analysis)
        self.root.mainloop()

    def run_analysis(self) -> None:
        """Load the graph, compute metrics, and refresh the display."""
        max_distance_text = self.max_distance_var.get().strip()
        try:
            max_distance_km = float(max_distance_text)
        except ValueError:
            messagebox.showerror("Invalid Distance", "Please enter a valid number for the maximum distance.")
            return

        self.status_var.set("Loading GTFS data and computing network metrics...")
        self.root.update_idletasks()

        try:
            graph = build_graph_from_gtfs(
                self.data_dir / self.stops_file,
                self.data_dir / self.stop_times_file,
                self.data_dir / self.routes_file,
                self.data_dir / self.trips_file,
                route_types={"1"},
            )
            graph_metrics = compute_network_metrics(graph)
            candidate_nodes = self._select_candidate_nodes(graph, graph_metrics)
            recommendation = find_best_new_connection(
                graph,
                max_distance_km=max_distance_km,
                min_distance_km=DEFAULT_MIN_DISTANCE_KM,
                min_existing_path_seconds=DEFAULT_MIN_EXISTING_PATH_SECONDS,
                exclude_same_route=True,
                baseline_efficiency=graph_metrics.global_efficiency,
                candidate_nodes=candidate_nodes,
            )
        except FileNotFoundError as error:
            messagebox.showerror("Missing Data File", str(error))
            return
        except Exception as error:
            messagebox.showerror("Analysis Error", str(error))
            return

        self.graph = graph
        self.graph_metrics = graph_metrics
        self.recommendation = recommendation
        self.station_name_map = {
            station.name.casefold(): node_id for node_id, station in graph.stations.items()
        }
        self.station_names = sorted(station.name for station in graph.stations.values())
        self.start_station_entry.set_choices(self.station_names)
        self.end_station_entry.set_choices(self.station_names)
        self.path_summary_var.set("Enter two station names to inspect a shortest path.")
        self.path_detail_var.set("")
        self._reset_view_state()

        self._update_result_text()
        self._redraw_current_view()
        recommendation_scope = "all stations"
        if candidate_nodes is not None:
            recommendation_scope = f"{len(candidate_nodes)} important candidate stops"
        self.status_var.set(
            f"Loaded {graph.node_count()} subway stations. The recommendation search "
            f"was limited to {recommendation_scope} and ignored station pairs closer than "
            f"{DEFAULT_MIN_DISTANCE_KM:.1f} km or already connected in under "
            f"{DEFAULT_MIN_EXISTING_PATH_SECONDS / 60:.0f} minutes, and it skipped stations "
            f"already on the same subway route."
        )

    def display_shortest_path(self) -> None:
        """Resolve the typed station names and display the resulting shortest path."""
        if self.graph is None:
            return

        start_query = self.start_station_var.get().strip()
        end_query = self.end_station_var.get().strip()
        if not start_query or not end_query:
            messagebox.showerror("Missing Station Name", "Please enter both a start station and an end station.")
            return

        start_station_id = self._resolve_station_name(start_query)
        end_station_id = self._resolve_station_name(end_query)
        if start_station_id is None or end_station_id is None:
            return

        path, distance = shortest_path_between(self.graph, start_station_id, end_station_id)
        if not path or math.isinf(distance):
            self.path_summary_var.set(
                f"No path was found between {format_station_label(self.graph, start_station_id)} "
                f"and {format_station_label(self.graph, end_station_id)}."
            )
            self.path_detail_var.set("")
            self._redraw_current_view()
            return

        station_names = [format_station_label(self.graph, node_id) for node_id in path]
        self.path_summary_var.set(
            f"Shortest path from {station_names[0]} to {station_names[-1]} "
            f"contains {len(path)} stations and takes about {distance / 60:.1f} minutes."
        )
        self.path_detail_var.set(" -> ".join(station_names))
        self._redraw_current_view(path)

    def _select_candidate_nodes(
        self,
        graph: Graph,
        graph_metrics: NetworkMetrics,
    ) -> list[str] | None:
        """Bound the optimization search when the graph is large."""
        if graph.node_count() <= LARGE_GRAPH_NODE_THRESHOLD:
            return None

        ranked_nodes = top_k_central_stations(
            graph_metrics.betweenness_centrality,
            k=self.candidate_limit,
        )
        return [node_id for node_id, _score in ranked_nodes]

    def _update_result_text(self) -> None:
        """Populate the metrics and recommendation labels."""
        if self.graph is None or self.graph_metrics is None:
            return

        top_stations = top_k_central_stations(self.graph_metrics.betweenness_centrality, k=5)
        top_station_lines = [
            f"{index}. {format_station_label(self.graph, node_id)} ({score:.3f})"
            for index, (node_id, score) in enumerate(top_stations, start=1)
        ]
        self.metrics_var.set(
            "Network summary\n"
            f"Stations analyzed: {self.graph.node_count()}\n"
            f"Average shortest path: {self.graph_metrics.average_shortest_path:.3f} seconds\n"
            f"Diameter: {self.graph_metrics.diameter:.3f} seconds\n"
            f"Global efficiency: {self.graph_metrics.global_efficiency:.6f}\n\n"
            "Top 5 stations by centrality\n"
            + "\n".join(top_station_lines)
        )

        if self.recommendation is None:
            self.recommendation_var.set("No candidate edge recommendation was produced.")
            return

        self.recommendation_var.set(
            "Best new connection\n"
            f"Source: {format_station_label(self.graph, self.recommendation.source)}\n"
            f"Target: {format_station_label(self.graph, self.recommendation.target)}\n"
            f"Estimated travel time: {self.recommendation.weight:.1f} seconds\n"
            f"Efficiency improvement: {self.recommendation.improvement_percent:.2f}%"
        )

    def _reset_zoom(self) -> None:
        """Reset the canvas zoom level."""
        self.zoom_scale = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self._redraw_current_view()

    def _adjust_zoom(self, factor: float) -> None:
        """Multiply the current zoom level by ``factor`` and redraw."""
        self.zoom_scale = min(4.0, max(0.45, self.zoom_scale * factor))
        self._redraw_current_view()

    def _zoom_with_mousewheel(self, event: tk.Event) -> str:
        """Zoom the canvas with the mouse wheel."""
        if event.delta > 0:
            self._adjust_zoom(1.12)
        elif event.delta < 0:
            self._adjust_zoom(1 / 1.12)
        return "break"

    def _start_pan(self, event: tk.Event) -> None:
        """Store the initial pointer position for canvas panning."""
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _perform_pan(self, event: tk.Event) -> None:
        """Pan the current visualization while the mouse is dragged."""
        if self._drag_start_x is None or self._drag_start_y is None:
            return

        self.pan_x += event.x - self._drag_start_x
        self.pan_y += event.y - self._drag_start_y
        self._drag_start_x = event.x
        self._drag_start_y = event.y
        self._redraw_current_view()

    def _end_pan(self, _event: tk.Event) -> None:
        """Clear the drag state when the mouse button is released."""
        self._drag_start_x = None
        self._drag_start_y = None

    def _reset_view_state(self) -> None:
        """Reset pan and zoom when a new analysis is loaded."""
        self.zoom_scale = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0

    def _open_original_3d_map(self) -> None:
        """Generate and open the original HTML/MapLibre 3D map."""
        if self.graph is None or self.graph_metrics is None:
            messagebox.showerror("No Analysis Loaded", "Run the analysis first so the 3D map has data to display.")
            return

        output_path = save_3d_network_figure(
            self.graph,
            self.graph_metrics.betweenness_centrality,
            self.recommendation,
            self.data_dir.parent / "output" / "ttc_network_analysis_3d.html",
        )
        webbrowser.open(output_path.resolve().as_uri())
        self.status_var.set(
            "Opened the original interactive 3D MapLibre view in your browser. "
            "Tkinter is still using the in-app 2D/3D canvas view."
        )

    def _redraw_current_view(self, highlighted_path: list[str] | None = None) -> None:
        """Redraw the current graph on the 2D canvas view."""
        if self.graph is None:
            return

        if highlighted_path is not None:
            self._last_highlighted_path = highlighted_path[:]
        elif hasattr(self, "_last_highlighted_path"):
            highlighted_path = self._last_highlighted_path
        else:
            self._last_highlighted_path = []
            highlighted_path = []

        self._draw_network(highlighted_path)

    def _resolve_station_name(self, query: str) -> str | None:
        """Return the station ID for a user-entered station name."""
        if self.graph is None:
            return None

        normalized_query = query.casefold()
        direct_match = self.station_name_map.get(normalized_query)
        if direct_match is not None:
            return direct_match

        partial_matches = [
            node_id
            for node_id, station in self.graph.stations.items()
            if normalized_query in station.name.casefold()
        ]
        if len(partial_matches) == 1:
            return partial_matches[0]
        if len(partial_matches) > 1:
            suggestions = ", ".join(
                sorted(format_station_label(self.graph, node_id) for node_id in partial_matches[:6])
            )
            messagebox.showerror(
                "Ambiguous Station Name",
                f"'{query}' matches multiple stations. Please be more specific.\n\nExamples: {suggestions}",
            )
            return None

        station_names = [station.name for station in self.graph.stations.values()]
        close_matches = difflib.get_close_matches(query, station_names, n=5, cutoff=0.5)
        suggestion_text = ", ".join(close_matches) if close_matches else "No close match found."
        messagebox.showerror(
            "Station Not Found",
            f"Could not find a station named '{query}'.\n\nClosest matches: {suggestion_text}",
        )
        return None

    def _draw_network(self, highlighted_path: list[str] | None = None) -> None:
        """Draw the graph on the canvas and optionally highlight a shortest path."""
        if self.graph is None:
            return

        self.canvas.delete("all")
        self.canvas.configure(bg=BACKGROUND_COLOR)
        self.node_positions = self._compute_canvas_positions(self.graph)

        for source, target, _weight in self.graph.undirected_edges():
            self._draw_edge(source, target, fill=self._edge_color(source, target), width=1)

        if self.recommendation is not None:
            self._draw_edge(
                self.recommendation.source,
                self.recommendation.target,
                fill=RECOMMENDATION_COLOR,
                width=3,
                dash=(7, 4),
            )

        if highlighted_path is not None and len(highlighted_path) >= 2:
            for index in range(len(highlighted_path) - 1):
                self._draw_edge(
                    highlighted_path[index],
                    highlighted_path[index + 1],
                    fill=RECOMMENDATION_COLOR,
                    width=4,
                )

        top_nodes = set()
        if self.graph_metrics is not None:
            top_nodes = {
                node_id for node_id, _score in top_k_central_stations(self.graph_metrics.betweenness_centrality, k=5)
            }

        highlighted_nodes = set(highlighted_path or [])
        for node_id in self.graph.nodes():
            if not self._node_is_visible(node_id):
                continue
            x_value, y_value = self.node_positions[node_id]
            radius = 3
            fill = self._node_color(node_id)
            outline = ""

            if node_id in top_nodes:
                radius = 5
                fill = self._node_color(node_id)
            if node_id in highlighted_nodes:
                radius = 6
                fill = RECOMMENDATION_COLOR
                outline = "#7d1128"

            self.canvas.create_oval(
                x_value - radius,
                y_value - radius,
                x_value + radius,
                y_value + radius,
                fill=fill,
                outline=outline,
            )

        self._draw_node_labels(top_nodes | highlighted_nodes)
        self._draw_legend()

    def _compute_canvas_positions(self, graph: Graph) -> dict[str, tuple[float, float]]:
        """Return canvas coordinates for each station based on longitude/latitude."""
        stations = list(graph.stations.values())
        if not stations:
            return {}

        min_lon = min(station.longitude for station in stations)
        max_lon = max(station.longitude for station in stations)
        min_lat = min(station.latitude for station in stations)
        max_lat = max(station.latitude for station in stations)

        longitude_span = max(max_lon - min_lon, 1e-9)
        latitude_span = max(max_lat - min_lat, 1e-9)
        usable_width = (CANVAS_WIDTH - 2 * CANVAS_PADDING) * self.zoom_scale
        usable_height = (CANVAS_HEIGHT - 2 * CANVAS_PADDING) * self.zoom_scale
        center_x = CANVAS_WIDTH / 2 + self.pan_x
        center_y = CANVAS_HEIGHT / 2 + self.pan_y

        positions = {}
        for node_id, station in graph.stations.items():
            x_ratio = (station.longitude - min_lon) / longitude_span
            y_ratio = (station.latitude - min_lat) / latitude_span
            x_value = center_x - usable_width / 2 + x_ratio * usable_width
            y_value = center_y + usable_height / 2 - y_ratio * usable_height
            positions[node_id] = (x_value, y_value)

        return positions

    def _draw_edge(
        self,
        source: str,
        target: str,
        *,
        fill: str,
        width: int,
        dash: tuple[int, int] | None = None,
    ) -> None:
        """Draw one edge if both endpoint positions are known."""
        if source not in self.node_positions or target not in self.node_positions:
            return
        if not self._edge_is_visible(source, target):
            return

        source_x, source_y = self.node_positions[source]
        target_x, target_y = self.node_positions[target]
        self.canvas.create_line(source_x, source_y, target_x, target_y, fill=fill, width=width, dash=dash)

    def _node_color(self, node_id: str) -> str:
        """Return the fill color for a node."""
        _ = node_id
        return SUBWAY_COLOR

    def _edge_color(self, source: str, target: str) -> str:
        """Return the color for an edge."""
        _ = (source, target)
        return SUBWAY_COLOR

    def _node_is_visible(self, node_id: str) -> bool:
        """Return whether a node should be shown."""
        _ = node_id
        return True

    def _edge_is_visible(self, source: str, target: str) -> bool:
        """Return whether an edge should be shown with the current filters."""
        return self._node_is_visible(source) and self._node_is_visible(target)

    def _draw_node_labels(self, label_nodes: set[str]) -> None:
        """Label the most important or highlighted nodes on the 2D view."""
        if self.graph is None:
            return

        for node_id in list(label_nodes)[:MAX_NODE_LABELS]:
            if node_id not in self.node_positions or not self._node_is_visible(node_id):
                continue
            x_value, y_value = self.node_positions[node_id]
            self.canvas.create_text(
                x_value + 8,
                y_value - 8,
                text=format_station_label(self.graph, node_id),
                anchor="w",
                fill="#0f172a",
                font=("TkDefaultFont", 9, "bold"),
            )

    def _draw_legend(self, *, view_name: str = "2D") -> None:
        """Draw a small legend in the top-left of the canvas."""
        legend_x = 18
        legend_y = 18
        box_width = 250
        box_height = 118

        self.canvas.create_rectangle(
            legend_x,
            legend_y,
            legend_x + box_width,
            legend_y + box_height,
            fill="#ffffff",
            outline="#d2d9e3",
        )
        self.canvas.create_text(
            legend_x + 12,
            legend_y + 14,
            text=f"{view_name} canvas legend",
            anchor="w",
            font=("TkDefaultFont", 10, "bold"),
            fill="#243447",
        )

        legend_items = [
            (SUBWAY_COLOR, "Subway station / edge"),
            (RECOMMENDATION_COLOR, "Recommendation / shortest path"),
            ("#0f172a", f"Zoom: {self.zoom_scale:.2f}x"),
            ("#0f172a", "Drag to pan"),
        ]

        for index, (color, label) in enumerate(legend_items, start=1):
            current_y = legend_y + 18 + index * 20
            if label.startswith("Zoom:"):
                self.canvas.create_text(
                    legend_x + 14,
                    current_y,
                    text=label,
                    anchor="w",
                    fill="#243447",
                )
                continue
            self.canvas.create_line(
                legend_x + 14,
                current_y,
                legend_x + 48,
                current_y,
                fill=color,
                width=3,
            )
            self.canvas.create_text(
                legend_x + 58,
                current_y,
                text=label,
                anchor="w",
                fill="#243447",
            )


def launch_app(
    data_dir: Path,
    stops_file: str,
    stop_times_file: str,
    routes_file: str,
    trips_file: str,
) -> None:
    """Create and run the desktop application."""
    app = TransitAnalysisApp(
        data_dir=data_dir,
        stops_file=stops_file,
        stop_times_file=stop_times_file,
        routes_file=routes_file,
        trips_file=trips_file,
    )
    app.run()
