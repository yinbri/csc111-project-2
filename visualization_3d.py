"""CSC111 Winter 2026 Project 2: TTC 3D Network Visualization

Module Description
==================
This module provides a second visualization path for the TTC network project.
It exports the graph as a standalone HTML page that uses MapLibre GL JS and
OpenFreeMap to render a 3D city basemap with station nodes and network edges.

Copyright and Usage Information
===============================

This file is Copyright (c) 2026 Aarav Chhabra, Brian Yin, Sam Wang, and Kevin Liu
"""

from __future__ import annotations

import json
from pathlib import Path

from graph import Graph
from metrics import EdgeRecommendation


def _build_node_features(graph: Graph, centrality: dict[str, float]) -> list[dict]:
    """Return GeoJSON features for station nodes."""
    max_centrality = max(centrality.values(), default=0.0)
    features = []

    for node in graph.nodes():
        station = graph.stations.get(node)
        if station is None:
            continue

        score = centrality.get(node, 0.0)
        scaled_radius = 6.0 if max_centrality == 0 else 6.0 + 8.0 * (score / max_centrality)
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [station.longitude, station.latitude],
            },
            "properties": {
                "stop_id": station.stop_id,
                "name": station.name,
                "degree": graph.degree(node),
                "centrality": round(score, 6),
                "radius": round(scaled_radius, 2),
            },
        })

    return features


def _build_edge_features(graph: Graph) -> list[dict]:
    """Return GeoJSON features for existing network edges."""
    features = []

    for source, target, weight in graph.undirected_edges():
        source_station = graph.stations.get(source)
        target_station = graph.stations.get(target)
        if source_station is None or target_station is None:
            continue

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [source_station.longitude, source_station.latitude],
                    [target_station.longitude, target_station.latitude],
                ],
            },
            "properties": {
                "source": source_station.name,
                "target": target_station.name,
                "weight": round(weight, 3),
            },
        })

    return features


def _build_recommendation_features(graph: Graph, recommendation: EdgeRecommendation | None) -> list[dict]:
    """Return GeoJSON features for the recommended edge."""
    if recommendation is None:
        return []

    source_station = graph.stations.get(recommendation.source)
    target_station = graph.stations.get(recommendation.target)
    if source_station is None or target_station is None:
        return []

    return [{
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [source_station.longitude, source_station.latitude],
                [target_station.longitude, target_station.latitude],
            ],
        },
        "properties": {
            "source": source_station.name,
            "target": target_station.name,
            "weight": round(recommendation.weight, 3),
            "improvement_percent": round(recommendation.improvement_percent, 3),
        },
    }]


def _compute_map_center(graph: Graph) -> tuple[float, float]:
    """Return the average longitude/latitude center for the graph."""
    stations = list(graph.stations.values())
    if not stations:
        return (-79.3832, 43.6532)

    avg_longitude = sum(station.longitude for station in stations) / len(stations)
    avg_latitude = sum(station.latitude for station in stations) / len(stations)
    return (avg_longitude, avg_latitude)


def _build_html(
    graph: Graph,
    centrality: dict[str, float],
    recommendation: EdgeRecommendation | None,
) -> str:
    """Return the standalone HTML page for the 3D map visualization."""
    node_geojson = {
        "type": "FeatureCollection",
        "features": _build_node_features(graph, centrality),
    }
    edge_geojson = {
        "type": "FeatureCollection",
        "features": _build_edge_features(graph),
    }
    recommendation_geojson = {
        "type": "FeatureCollection",
        "features": _build_recommendation_features(graph, recommendation),
    }
    center_longitude, center_latitude = _compute_map_center(graph)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TTC Transit Network Analysis 3D</title>
  <link rel="stylesheet" href="https://unpkg.com/maplibre-gl@5.20.0/dist/maplibre-gl.css">
  <script src="https://unpkg.com/maplibre-gl@5.20.0/dist/maplibre-gl.js"></script>
  <style>
    body {{
      margin: 0;
      font-family: "Helvetica Neue", Arial, sans-serif;
      background: #0b1220;
      color: #e5e7eb;
    }}

    #map {{
      width: 100vw;
      height: 100vh;
    }}

    .panel {{
      position: absolute;
      top: 16px;
      left: 16px;
      z-index: 1;
      max-width: 320px;
      padding: 14px 16px;
      border-radius: 14px;
      background: rgba(11, 18, 32, 0.86);
      box-shadow: 0 12px 30px rgba(0, 0, 0, 0.3);
      backdrop-filter: blur(6px);
    }}

    .panel h1 {{
      margin: 0 0 8px;
      font-size: 1.15rem;
    }}

    .panel p {{
      margin: 0;
      line-height: 1.45;
      font-size: 0.92rem;
      color: #cbd5e1;
    }}

    .legend {{
      margin-top: 12px;
      display: grid;
      gap: 6px;
      font-size: 0.84rem;
    }}

    .controls {{
      margin-top: 14px;
      padding-top: 12px;
      border-top: 1px solid rgba(148, 163, 184, 0.28);
      display: grid;
      gap: 10px;
    }}

    .toggle {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.88rem;
      color: #e2e8f0;
    }}

    .toggle input {{
      width: 16px;
      height: 16px;
      accent-color: #38bdf8;
    }}

    .legend-item {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .swatch {{
      width: 14px;
      height: 14px;
      border-radius: 999px;
      flex: 0 0 auto;
    }}

    .swatch-line {{
      width: 18px;
      height: 4px;
      border-radius: 999px;
    }}
  </style>
</head>
<body>
  <div class="panel">
    <h1>TTC Network 3D View</h1>
    <p>
      Explore the TTC graph on a 3D Toronto basemap. Drag to orbit, zoom in to
      see extruded buildings, and click stations for centrality details.
    </p>
    <div class="legend">
      <div class="legend-item"><span class="swatch" style="background:#38bdf8"></span>Stations</div>
      <div class="legend-item"><span class="swatch-line" style="background:#94a3b8"></span>Existing edges</div>
      <div class="legend-item"><span class="swatch-line" style="background:#ef4444"></span>Recommended edge</div>
    </div>
    <div class="controls">
      <label class="toggle">
        <input id="buildings-toggle" type="checkbox" checked>
        Show 3D buildings with real map height data
      </label>
    </div>
  </div>
  <div id="map"></div>
  <script>
    const stationData = {json.dumps(node_geojson)};
    const edgeData = {json.dumps(edge_geojson)};
    const recommendationData = {json.dumps(recommendation_geojson)};

    const map = new maplibregl.Map({{
      container: 'map',
      style: 'https://tiles.openfreemap.org/styles/bright',
      center: [{center_longitude:.6f}, {center_latitude:.6f}],
      zoom: 11.2,
      pitch: 58,
      bearing: -18,
      hash: false,
      canvasContextAttributes: {{ antialias: true }}
    }});

    map.addControl(new maplibregl.NavigationControl(), 'top-right');

    function firstLabelLayerId() {{
      const layers = map.getStyle().layers || [];
      for (const layer of layers) {{
        if (layer.type === 'symbol' && layer.layout && layer.layout['text-field']) {{
          return layer.id;
        }}
      }}
      return undefined;
    }}

    function showPopup(lngLat, html) {{
      new maplibregl.Popup({{ closeButton: true, closeOnClick: true }})
        .setLngLat(lngLat)
        .setHTML(html)
        .addTo(map);
    }}

    function setBuildingsVisibility(isVisible) {{
      if (!map.getLayer('3d-buildings')) {{
        return;
      }}

      map.setLayoutProperty(
        '3d-buildings',
        'visibility',
        isVisible ? 'visible' : 'none'
      );
    }}

    map.on('load', () => {{
      map.addSource('ttc-stations', {{
        type: 'geojson',
        data: stationData
      }});

      map.addSource('ttc-edges', {{
        type: 'geojson',
        data: edgeData
      }});

      map.addSource('ttc-recommendation', {{
        type: 'geojson',
        data: recommendationData
      }});

      map.addSource('openfreemap', {{
        type: 'vector',
        url: 'https://tiles.openfreemap.org/planet'
      }});

      const labelLayerId = firstLabelLayerId();

      map.addLayer({{
        id: 'ttc-edges-layer',
        type: 'line',
        source: 'ttc-edges',
        paint: {{
          'line-color': '#94a3b8',
          'line-opacity': 0.72,
          'line-width': 2
        }}
      }}, labelLayerId);

      map.addLayer({{
        id: 'ttc-recommendation-layer',
        type: 'line',
        source: 'ttc-recommendation',
        paint: {{
          'line-color': '#ef4444',
          'line-opacity': 0.95,
          'line-width': 4
        }}
      }}, labelLayerId);

      map.addLayer({{
        id: 'ttc-stations-layer',
        type: 'circle',
        source: 'ttc-stations',
        paint: {{
          'circle-color': '#38bdf8',
          'circle-stroke-color': '#f8fafc',
          'circle-stroke-width': 1.2,
          'circle-opacity': 0.95,
          'circle-radius': ['get', 'radius']
        }}
      }}, labelLayerId);

      map.addLayer({{
        id: 'ttc-station-labels',
        type: 'symbol',
        source: 'ttc-stations',
        minzoom: 11.5,
        layout: {{
          'text-field': ['get', 'name'],
          'text-size': 11,
          'text-offset': [0, 1.2]
        }},
        paint: {{
          'text-color': '#f8fafc',
          'text-halo-color': 'rgba(15, 23, 42, 0.95)',
          'text-halo-width': 1.2
        }}
      }});

      map.addLayer({{
        id: '3d-buildings',
        source: 'openfreemap',
        'source-layer': 'building',
        type: 'fill-extrusion',
        minzoom: 14,
        filter: ['!=', ['get', 'hide_3d'], true],
        paint: {{
          'fill-extrusion-color': [
            'interpolate',
            ['linear'],
            ['get', 'render_height'],
            0, '#cbd5e1',
            80, '#94a3b8',
            200, '#64748b'
          ],
          'fill-extrusion-height': [
            'interpolate',
            ['linear'],
            ['zoom'],
            14,
            0,
            15.5,
            ['get', 'render_height']
          ],
          'fill-extrusion-base': [
            'case',
            ['>=', ['zoom'], 15.5],
            ['get', 'render_min_height'],
            0
          ],
          'fill-extrusion-opacity': 0.72
        }}
      }}, labelLayerId);

      const buildingsToggle = document.getElementById('buildings-toggle');
      if (buildingsToggle instanceof HTMLInputElement) {{
        setBuildingsVisibility(buildingsToggle.checked);
        buildingsToggle.addEventListener('change', () => {{
          setBuildingsVisibility(buildingsToggle.checked);
        }});
      }}

      const bounds = new maplibregl.LngLatBounds();
      for (const feature of stationData.features) {{
        bounds.extend(feature.geometry.coordinates);
      }}
      if (!bounds.isEmpty()) {{
        map.fitBounds(bounds, {{
          padding: {{ top: 90, right: 60, bottom: 60, left: 360 }},
          duration: 0
        }});
      }}

      map.on('click', 'ttc-stations-layer', (event) => {{
        const feature = event.features && event.features[0];
        if (!feature) {{
          return;
        }}

        const props = feature.properties;
        showPopup(
          event.lngLat,
          `<strong>${{props.name}}</strong><br>` +
          `Degree: ${{props.degree}}<br>` +
          `Centrality: ${{Number(props.centrality).toFixed(3)}}`
        );
      }});

      map.on('click', 'ttc-recommendation-layer', (event) => {{
        const feature = event.features && event.features[0];
        if (!feature) {{
          return;
        }}

        const props = feature.properties;
        showPopup(
          event.lngLat,
          `<strong>Suggested connection</strong><br>` +
          `${{props.source}} ↔ ${{props.target}}<br>` +
          `Estimated travel time: ${{Number(props.weight).toFixed(1)}} seconds<br>` +
          `Efficiency improvement: ${{Number(props.improvement_percent).toFixed(2)}}%`
        );
      }});

      for (const layerId of ['ttc-stations-layer', 'ttc-recommendation-layer']) {{
        map.on('mouseenter', layerId, () => {{
          map.getCanvas().style.cursor = 'pointer';
        }});
        map.on('mouseleave', layerId, () => {{
          map.getCanvas().style.cursor = '';
        }});
      }}
    }});
  </script>
</body>
</html>
"""


def save_3d_network_figure(
    graph: Graph,
    centrality: dict[str, float],
    recommendation: EdgeRecommendation | None,
    output_path: str | Path,
) -> Path:
    """Write the 3D map visualization to an HTML file and return its path."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_build_html(graph, centrality, recommendation), encoding="utf-8")
    return output


if __name__ == "__main__":
    import doctest
    import python_ta

    doctest.testmod()
    python_ta.check_all(config={
        'extra-imports': ['json', 'pathlib', 'graph', 'metrics'],
        'allowed-io': ['save_3d_network_figure'],
        'max-line-length': 120
    })
