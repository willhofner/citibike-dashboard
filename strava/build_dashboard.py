#!/usr/bin/env python3
"""
Build the Strava dashboard HTML files.
Injects enriched activity data directly into the HTML.
"""

import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
ENRICHED_FILE = os.path.join(DATA_DIR, "activities_enriched.json")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")


def main():
    with open(ENRICHED_FILE) as f:
        activities = json.load(f)

    # Filter to runs only for now (we can expand later)
    runs = [a for a in activities if a["type"] == "Run"]

    # For the HTML, strip the heavy streams data and use polylines instead
    # Keep latlng for animation but drop altitude/velocity/heartrate/time arrays
    # to keep file size manageable. We'll keep them for runs only.
    runs_for_html = []
    for r in runs:
        run = {k: v for k, v in r.items() if k not in ("altitude", "velocity")}
        runs_for_html.append(run)

    # Compute summary stats
    total_distance = sum(r["distance_mi"] for r in runs)
    total_time_sec = sum(r["moving_time"] for r in runs)
    total_time_hrs = total_time_sec / 3600
    avg_pace_sec = total_time_sec / total_distance if total_distance else 0
    avg_pace_min = int(avg_pace_sec // 60)
    avg_pace_s = int(avg_pace_sec % 60)
    longest_run = max(runs, key=lambda r: r["distance_mi"])
    dates = sorted(r["date"] for r in runs if r.get("date"))

    stats = {
        "totalRuns": len(runs),
        "totalDistance": round(total_distance, 1),
        "totalHours": round(total_time_hrs, 1),
        "avgPace": f"{avg_pace_min}:{avg_pace_s:02d}/mi",
        "avgDistance": round(total_distance / len(runs), 1),
        "longestRun": round(longest_run["distance_mi"], 1),
        "longestRunName": longest_run.get("name", ""),
        "dateRange": f"{dates[0]} to {dates[-1]}" if dates else "",
    }

    # Build HTML
    data_json = json.dumps(runs_for_html, separators=(",", ":"))
    stats_json = json.dumps(stats)

    html = build_html(data_json, stats_json)

    with open(OUTPUT_FILE, "w") as f:
        f.write(html)

    print(f"Built {OUTPUT_FILE}")
    print(f"  {len(runs)} runs, {stats['totalDistance']} mi total")
    size_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    print(f"  File size: {size_mb:.1f} MB")


def build_html(data_json, stats_json):
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Strava Run Explorer</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  :root {{
    --bg: #0a0a0f;
    --card: #12121a;
    --border: #1e1e2e;
    --text: #e0e0e8;
    --text-dim: #8888a0;
    --accent: #f97316;
    --accent2: #fb923c;
    --green: #22c55e;
    --red: #ef4444;
    --blue: #3b82f6;
  }}

  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif;
    background: var(--bg);
    color: var(--text);
    display: grid;
    grid-template-columns: 380px 1fr;
    height: 100vh;
    overflow: hidden;
  }}

  /* Sidebar */
  .sidebar {{
    display: flex;
    flex-direction: column;
    border-right: 1px solid var(--border);
    height: 100vh;
    overflow: hidden;
  }}

  .sidebar-header {{
    padding: 20px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }}
  .sidebar-header h1 {{
    font-size: 20px;
    font-weight: 700;
    margin-bottom: 4px;
  }}
  .sidebar-header h1 span {{ color: var(--accent); }}
  .sidebar-header .back-link {{
    font-size: 12px;
    color: var(--accent);
    text-decoration: none;
  }}
  .sidebar-header .back-link:hover {{ text-decoration: underline; }}

  /* Stats bar */
  .stats-bar {{
    padding: 14px 20px;
    border-bottom: 1px solid var(--border);
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    flex-shrink: 0;
  }}
  .mini-stat {{
    text-align: center;
  }}
  .mini-stat .val {{
    font-size: 18px;
    font-weight: 700;
    color: var(--accent);
  }}
  .mini-stat .lbl {{
    font-size: 10px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}

  /* Controls */
  .controls {{
    padding: 12px 20px;
    border-bottom: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    gap: 8px;
    flex-shrink: 0;
  }}
  .search-input {{
    width: 100%;
    padding: 8px 12px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--text);
    font-size: 13px;
    outline: none;
  }}
  .search-input:focus {{ border-color: var(--accent); }}
  .search-input::placeholder {{ color: var(--text-dim); }}

  .btn-row {{
    display: flex;
    gap: 6px;
  }}
  .filter-btn {{
    padding: 5px 10px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text-dim);
    font-size: 11px;
    cursor: pointer;
    transition: all 0.15s;
    flex: 1;
    text-align: center;
  }}
  .filter-btn:hover {{ border-color: var(--accent); color: var(--text); }}
  .filter-btn.active {{ background: var(--accent); color: #fff; border-color: var(--accent); }}

  .run-count {{
    font-size: 11px;
    color: var(--text-dim);
    padding: 0 2px;
  }}

  /* Run list */
  .run-list {{
    flex: 1;
    overflow-y: auto;
    scrollbar-width: thin;
    scrollbar-color: var(--border) transparent;
  }}

  .run-item {{
    padding: 14px 20px;
    border-bottom: 1px solid var(--border);
    cursor: pointer;
    transition: background 0.15s;
  }}
  .run-item:hover {{ background: rgba(249,115,22,0.05); }}
  .run-item.active {{ background: rgba(249,115,22,0.1); border-left: 3px solid var(--accent); }}

  .run-item .run-date {{
    font-size: 11px;
    color: var(--text-dim);
    margin-bottom: 4px;
    display: flex;
    justify-content: space-between;
  }}
  .run-item .run-name {{
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 4px;
  }}
  .run-item .run-meta {{
    display: flex;
    gap: 12px;
    font-size: 11px;
    color: var(--text-dim);
  }}
  .run-item .run-meta .highlight {{
    color: var(--accent);
    font-weight: 600;
  }}

  /* Map panel */
  .map-panel {{
    position: relative;
    height: 100vh;
  }}
  #runMap {{
    width: 100%;
    height: 100%;
  }}

  .leaflet-container {{ background: #0a0a0f; }}
  .leaflet-tile-pane {{ filter: saturate(0.5) brightness(1.5) contrast(1.05); }}

  /* Runner glow pulse */
  .runner-glow {{
    animation: pulse 1s ease-in-out infinite;
  }}
  @keyframes pulse {{
    0%, 100% {{ opacity: 0.3; transform: scale(1); }}
    50% {{ opacity: 0.6; transform: scale(1.3); }}
  }}

  /* Run detail overlay */
  .run-detail-overlay {{
    position: absolute;
    bottom: 24px;
    left: 24px;
    right: 24px;
    z-index: 1000;
    background: rgba(10,10,15,0.92);
    backdrop-filter: blur(12px);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px 24px;
    display: none;
  }}
  .run-detail-overlay.visible {{ display: block; }}
  .detail-title {{
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 12px;
  }}
  .detail-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
    gap: 16px;
  }}
  .detail-stat .d-val {{
    font-size: 20px;
    font-weight: 700;
    color: var(--accent);
  }}
  .detail-stat .d-lbl {{
    font-size: 10px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}

  /* Splits */
  .splits-row {{
    margin-top: 14px;
    padding-top: 14px;
    border-top: 1px solid var(--border);
  }}
  .splits-label {{
    font-size: 11px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
  }}
  .splits-bars {{
    display: flex;
    gap: 3px;
    align-items: flex-end;
    height: 40px;
  }}
  .split-bar {{
    flex: 1;
    border-radius: 2px 2px 0 0;
    position: relative;
    cursor: default;
    min-width: 8px;
    transition: opacity 0.15s;
  }}
  .split-bar:hover {{ opacity: 0.8; }}
  .split-tooltip {{
    display: none;
    position: absolute;
    bottom: calc(100% + 4px);
    left: 50%;
    transform: translateX(-50%);
    background: rgba(10,10,15,0.95);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 10px;
    white-space: nowrap;
    z-index: 10;
  }}
  .split-bar:hover .split-tooltip {{ display: block; }}

  /* Animation controls */
  .anim-controls {{
    position: absolute;
    top: 16px;
    right: 16px;
    z-index: 1000;
    display: flex;
    gap: 8px;
  }}
  .anim-btn {{
    padding: 8px 14px;
    background: rgba(10,10,15,0.9);
    backdrop-filter: blur(8px);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--text);
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
    display: flex;
    align-items: center;
    gap: 6px;
  }}
  .anim-btn:hover {{ border-color: var(--accent); color: var(--accent); }}
  .anim-btn.active {{ background: var(--accent); color: #fff; border-color: var(--accent); }}
  .anim-btn.playing {{ background: var(--accent); color: #fff; border-color: var(--accent); }}

  /* Speed control */
  .speed-control {{
    position: absolute;
    top: 16px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 1000;
    display: none;
    align-items: center;
    gap: 8px;
    background: rgba(10,10,15,0.9);
    backdrop-filter: blur(8px);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 8px 14px;
    font-size: 12px;
  }}
  .speed-control.visible {{ display: flex; }}
  .speed-label {{ color: var(--text-dim); }}
  .speed-val {{ color: var(--accent); font-weight: 700; min-width: 30px; text-align: center; }}
  .speed-btn {{
    width: 24px;
    height: 24px;
    border-radius: 4px;
    border: 1px solid var(--border);
    background: var(--bg);
    color: var(--text);
    cursor: pointer;
    font-size: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
  }}
  .speed-btn:hover {{ border-color: var(--accent); }}

  /* Progress bar */
  .anim-progress {{
    position: absolute;
    top: 56px;
    right: 16px;
    z-index: 1000;
    display: none;
    flex-direction: column;
    gap: 4px;
    background: rgba(10,10,15,0.9);
    backdrop-filter: blur(8px);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 10px 14px;
    min-width: 180px;
  }}
  .anim-progress.visible {{ display: flex; }}
  .progress-bar {{
    height: 4px;
    background: var(--border);
    border-radius: 2px;
    overflow: hidden;
  }}
  .progress-fill {{
    height: 100%;
    background: var(--accent);
    border-radius: 2px;
    transition: width 0.1s linear;
    width: 0%;
  }}
  .progress-text {{
    font-size: 10px;
    color: var(--text-dim);
    display: flex;
    justify-content: space-between;
  }}

  /* Map overlay labels */
  .map-label {{
    position: absolute;
    top: 16px;
    left: 16px;
    z-index: 1000;
    background: rgba(10,10,15,0.85);
    backdrop-filter: blur(8px);
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    border: 1px solid var(--border);
  }}

  /* View toggle */
  .view-toggle {{
    position: absolute;
    top: 16px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 1000;
    display: flex;
    background: rgba(10,10,15,0.9);
    backdrop-filter: blur(8px);
    border: 1px solid var(--border);
    border-radius: 6px;
    overflow: hidden;
  }}
  .view-btn {{
    padding: 8px 16px;
    border: none;
    background: none;
    color: var(--text-dim);
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
    border-right: 1px solid var(--border);
  }}
  .view-btn:last-child {{ border-right: none; }}
  .view-btn:hover {{ color: var(--text); }}
  .view-btn.active {{ background: var(--accent); color: #fff; }}
</style>
</head>
<body>

<div class="sidebar">
  <div class="sidebar-header">
    <h1>Run <span>Explorer</span></h1>
    <a href="../index.html" class="back-link">Back to Dashboard</a>
  </div>

  <div class="stats-bar">
    <div class="mini-stat">
      <div class="val" id="statRuns">--</div>
      <div class="lbl">Runs</div>
    </div>
    <div class="mini-stat">
      <div class="val" id="statMiles">--</div>
      <div class="lbl">Miles</div>
    </div>
    <div class="mini-stat">
      <div class="val" id="statPace">--</div>
      <div class="lbl">Avg Pace</div>
    </div>
  </div>

  <div class="controls">
    <input type="text" class="search-input" id="searchInput" placeholder="Search runs...">
    <div class="btn-row">
      <button class="filter-btn active" data-sort="date">Recent</button>
      <button class="filter-btn" data-sort="distance">Longest</button>
      <button class="filter-btn" data-sort="pace">Fastest</button>
    </div>
    <div class="run-count" id="runCount"></div>
  </div>

  <div class="run-list" id="runList"></div>
</div>

<div class="map-panel">
  <div id="runMap"></div>

  <div class="view-toggle" id="viewToggle">
    <button class="view-btn active" data-view="routes">Routes</button>
    <button class="view-btn" data-view="heatmap">Heatmap</button>
  </div>

  <div class="anim-controls" id="animControls">
    <button class="anim-btn" id="btnAnimate" title="Replay this run">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5,3 19,12 5,21"/></svg>
      Replay
    </button>
    <button class="anim-btn" id="btnTimelapse" title="Watch all runs accumulate">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12,6 12,12 16,14"/></svg>
      Timelapse
    </button>
  </div>

  <div class="speed-control" id="speedControl">
    <span class="speed-label">Speed</span>
    <button class="speed-btn" id="speedDown">-</button>
    <span class="speed-val" id="speedVal">1x</span>
    <button class="speed-btn" id="speedUp">+</button>
  </div>

  <div class="anim-progress" id="animProgress">
    <div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>
    <div class="progress-text">
      <span id="progressLabel">0%</span>
      <span id="progressTime"></span>
    </div>
  </div>

  <div class="run-detail-overlay" id="runDetail"></div>
</div>

<script>
// ── Data ──
const RUNS = {data_json};
const STATS = {stats_json};

// ── State ──
let map, heatLayer, ghostLayers = [], activeRoute = null, activeMarkers = [];
let animFrame = null, animSpeed = 1;
let currentView = "routes";
let activeRunId = null;
let filteredRuns = [...RUNS];
let sortMode = "date";

// ── Decode Google polyline ──
function decodePoly(str) {{
  const coords = [];
  let i = 0, lat = 0, lng = 0;
  while (i < str.length) {{
    let b, shift = 0, result = 0;
    do {{ b = str.charCodeAt(i++) - 63; result |= (b & 0x1f) << shift; shift += 5; }} while (b >= 0x20);
    lat += (result & 1) ? ~(result >> 1) : (result >> 1);
    shift = 0; result = 0;
    do {{ b = str.charCodeAt(i++) - 63; result |= (b & 0x1f) << shift; shift += 5; }} while (b >= 0x20);
    lng += (result & 1) ? ~(result >> 1) : (result >> 1);
    coords.push([lat / 1e5, lng / 1e5]);
  }}
  return coords;
}}

// ── Format helpers ──
function fmtDuration(sec) {{
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  if (h > 0) return h + "h " + m + "m";
  return m + ":" + String(s).padStart(2, "0");
}}

function fmtDate(str) {{
  const d = new Date(str);
  return d.toLocaleDateString("en-US", {{ weekday: "short", month: "short", day: "numeric", year: "numeric" }});
}}

function fmtTime(str) {{
  const d = new Date(str);
  return d.toLocaleTimeString("en-US", {{ hour: "numeric", minute: "2-digit" }});
}}

function paceFromSpeed(speed) {{
  if (!speed || speed === 0) return "--";
  const paceSecPerMi = 1609.34 / speed;
  const m = Math.floor(paceSecPerMi / 60);
  const s = Math.floor(paceSecPerMi % 60);
  return m + ":" + String(s).padStart(2, "0") + "/mi";
}}

// ── Init Map ──
function initMap() {{
  map = L.map("runMap", {{
    center: [40.73, -73.99],
    zoom: 13,
    zoomControl: false,
  }});

  L.control.zoom({{ position: "bottomright" }}).addTo(map);

  L.tileLayer("https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png", {{
    attribution: "&copy; OSM &amp; CARTO",
    subdomains: "abcd",
    maxZoom: 19,
  }}).addTo(map);

  // Auto-center on runs
  const allCoords = [];
  RUNS.forEach(r => {{
    if (r.startLat && r.startLon) allCoords.push([r.startLat, r.startLon]);
    if (r.endLat && r.endLon) allCoords.push([r.endLat, r.endLon]);
  }});
  if (allCoords.length > 0) {{
    map.fitBounds(L.latLngBounds(allCoords).pad(0.1));
  }}

  showGhostRoutes();
}}

// ── Ghost routes (all routes faintly visible) ──
function showGhostRoutes() {{
  clearGhostRoutes();
  RUNS.forEach(run => {{
    const coords = getRunCoords(run);
    if (!coords || coords.length < 2) return;
    const line = L.polyline(coords, {{
      color: "#f97316",
      weight: 1.5,
      opacity: 0.12,
    }}).addTo(map);
    ghostLayers.push(line);
  }});
}}

function clearGhostRoutes() {{
  ghostLayers.forEach(l => map.removeLayer(l));
  ghostLayers = [];
}}

function getRunCoords(run) {{
  // Prefer raw latlng stream (higher resolution)
  if (run.latlng && run.latlng.length > 0) return run.latlng;
  // Fallback to decoded polyline
  if (run.polyline) return decodePoly(run.polyline);
  return null;
}}

// ── Heatmap ──
function showHeatmap() {{
  if (heatLayer) map.removeLayer(heatLayer);
  const points = [];
  RUNS.forEach(run => {{
    const coords = getRunCoords(run);
    if (!coords) return;
    // Sample every Nth point to keep performance good
    const step = Math.max(1, Math.floor(coords.length / 200));
    for (let i = 0; i < coords.length; i += step) {{
      points.push([coords[i][0], coords[i][1], 0.5]);
    }}
  }});
  heatLayer = L.heatLayer(points, {{
    radius: 12,
    blur: 15,
    maxZoom: 17,
    gradient: {{ 0.2: "#1a1a2e", 0.4: "#f97316", 0.6: "#fb923c", 0.8: "#fbbf24", 1.0: "#fff" }},
  }}).addTo(map);
}}

function hideHeatmap() {{
  if (heatLayer) {{ map.removeLayer(heatLayer); heatLayer = null; }}
}}

// ── Select a run (auto-animates the route) ──
function selectRun(runId) {{
  stopAnimation();
  activeRunId = runId;

  document.querySelectorAll(".run-item").forEach(el => {{
    el.classList.toggle("active", el.dataset.id == runId);
  }});

  const run = RUNS.find(r => r.id == runId);
  if (!run) return;

  clearActiveRoute();

  const coords = getRunCoords(run);
  if (!coords || coords.length < 2) return;

  // Fit map first
  map.fitBounds(L.latLngBounds(coords).pad(0.15));

  // Show detail overlay immediately
  showRunDetail(run);

  // Start marker (green)
  const startMarker = L.circleMarker(coords[0], {{
    radius: 7, color: "#22c55e", fillColor: "#22c55e", fillOpacity: 1, weight: 2,
  }}).addTo(map);
  activeMarkers = [startMarker];

  // Glow layer behind the runner
  const glow = L.circleMarker(coords[0], {{
    radius: 14, color: "#f97316", fillColor: "#f97316", fillOpacity: 0.3, weight: 0, className: "runner-glow",
  }}).addTo(map);
  activeMarkers.push(glow);

  // Runner dot
  const runner = L.circleMarker(coords[0], {{
    radius: 6, color: "#fff", fillColor: "#f97316", fillOpacity: 1, weight: 2,
  }}).addTo(map);
  activeMarkers.push(runner);

  // Animated trail
  const trail = L.polyline([], {{
    color: "#f97316", weight: 4, opacity: 0.9,
  }}).addTo(map);

  // Glow trail
  const glowTrail = L.polyline([], {{
    color: "#f97316", weight: 10, opacity: 0.15,
  }}).addTo(map);
  activeRoute = trail;
  activeMarkers.push(glowTrail);

  let idx = 0;
  const totalPoints = coords.length;
  const targetFrames = 180; // ~3 seconds at 60fps
  const baseRate = Math.max(1, Math.ceil(totalPoints / targetFrames));

  function step() {{
    const pointsPerFrame = Math.max(1, Math.floor(baseRate * animSpeed));
    const end = Math.min(idx + pointsPerFrame, totalPoints);

    for (let i = idx; i < end; i++) {{
      trail.addLatLng(coords[i]);
      glowTrail.addLatLng(coords[i]);
    }}
    idx = end;
    const pos = coords[idx - 1];
    runner.setLatLng(pos);
    glow.setLatLng(pos);

    if (idx < totalPoints) {{
      animFrame = requestAnimationFrame(step);
    }} else {{
      // Done — add end marker, remove glow
      map.removeLayer(glow);
      const endMarker = L.circleMarker(coords[coords.length - 1], {{
        radius: 7, color: "#ef4444", fillColor: "#ef4444", fillOpacity: 1, weight: 2,
      }}).addTo(map);
      activeMarkers.push(endMarker);
      // Remove runner dot, keep the trail
      map.removeLayer(runner);
    }}
  }}

  animFrame = requestAnimationFrame(step);
}}

function clearActiveRoute() {{
  if (activeRoute) {{ map.removeLayer(activeRoute); activeRoute = null; }}
  activeMarkers.forEach(m => map.removeLayer(m));
  activeMarkers = [];
}}

// ── Run Detail Overlay ──
function showRunDetail(run) {{
  const el = document.getElementById("runDetail");

  let splitsHtml = "";
  if (run.splits && run.splits.length > 0) {{
    const paces = run.splits.map(s => {{
      if (!s.average_speed || s.average_speed === 0) return 999;
      return 1609.34 / s.average_speed;
    }});
    const minPace = Math.min(...paces.filter(p => p < 900));
    const maxPace = Math.max(...paces.filter(p => p < 900));
    const range = maxPace - minPace || 1;

    const bars = run.splits.map((s, i) => {{
      const pace = paces[i];
      if (pace >= 900) return "";
      const pct = 30 + ((maxPace - pace) / range) * 70;
      const pm = Math.floor(pace / 60);
      const ps = Math.floor(pace % 60);
      const color = pace <= minPace + range * 0.33 ? "var(--green)" :
                    pace <= minPace + range * 0.66 ? "var(--accent)" : "var(--red)";
      return '<div class="split-bar" style="height:' + pct + '%;background:' + color + '">' +
        '<div class="split-tooltip">Mi ' + (i + 1) + ": " + pm + ":" + String(ps).padStart(2, "0") + "/mi</div></div>";
    }}).join("");

    splitsHtml = '<div class="splits-row"><div class="splits-label">Splits (per mile)</div><div class="splits-bars">' + bars + '</div></div>';
  }}

  el.innerHTML = '<div class="detail-title">' + (run.name || "Run") + '</div>' +
    '<div class="detail-grid">' +
      '<div class="detail-stat"><div class="d-val">' + run.distance_mi + '</div><div class="d-lbl">Miles</div></div>' +
      '<div class="detail-stat"><div class="d-val">' + (run.pace || "--") + '</div><div class="d-lbl">Pace</div></div>' +
      '<div class="detail-stat"><div class="d-val">' + fmtDuration(run.moving_time) + '</div><div class="d-lbl">Duration</div></div>' +
      '<div class="detail-stat"><div class="d-val">' + (run.total_elevation_gain ? Math.round(run.total_elevation_gain * 3.281) + " ft" : "--") + '</div><div class="d-lbl">Elevation</div></div>' +
      '<div class="detail-stat"><div class="d-val">' + (run.avg_heartrate ? Math.round(run.avg_heartrate) + " bpm" : "--") + '</div><div class="d-lbl">Avg HR</div></div>' +
      '<div class="detail-stat"><div class="d-val">' + (run.calories ? Math.round(run.calories) : "--") + '</div><div class="d-lbl">Calories</div></div>' +
    '</div>' + splitsHtml;

  el.classList.add("visible");
}}

function hideRunDetail() {{
  document.getElementById("runDetail").classList.remove("visible");
}}

// ── Route Animation (replay button — re-triggers the same animation) ──
function animateRun(runId) {{
  // Just re-select to replay the animation
  selectRun(runId);
}}

// ── Timelapse (all runs accumulate over time) ──
function timelapse() {{
  stopAnimation();
  clearActiveRoute();
  clearGhostRoutes();
  hideRunDetail();

  // Sort runs by date
  const sorted = [...RUNS].filter(r => getRunCoords(r)).sort((a, b) => new Date(a.startTime) - new Date(b.startTime));
  if (sorted.length === 0) return;

  document.getElementById("speedControl").classList.add("visible");
  document.getElementById("animProgress").classList.add("visible");
  document.getElementById("btnTimelapse").classList.add("playing");

  let runIdx = 0;

  function addNextRun() {{
    if (runIdx >= sorted.length) {{
      document.getElementById("btnTimelapse").classList.remove("playing");
      return;
    }}

    const run = sorted[runIdx];
    const coords = getRunCoords(run);
    runIdx++;

    if (coords && coords.length > 1) {{
      const line = L.polyline(coords, {{
        color: "#f97316",
        weight: 2.5,
        opacity: 0.6,
      }}).addTo(map);
      ghostLayers.push(line);
    }}

    // Update progress
    const pct = Math.round((runIdx / sorted.length) * 100);
    document.getElementById("progressFill").style.width = pct + "%";
    document.getElementById("progressLabel").textContent = run.date || "";
    document.getElementById("progressTime").textContent = runIdx + "/" + sorted.length;

    // Highlight in sidebar
    document.querySelectorAll(".run-item").forEach(el => {{
      el.classList.toggle("active", el.dataset.id == run.id);
    }});
    const activeEl = document.querySelector('.run-item[data-id="' + run.id + '"]');
    if (activeEl) activeEl.scrollIntoView({{ block: "nearest" }});

    const delay = Math.max(50, 500 / animSpeed);
    animFrame = setTimeout(addNextRun, delay);
  }}

  addNextRun();
}}

function stopAnimation() {{
  if (animFrame) {{
    cancelAnimationFrame(animFrame);
    clearTimeout(animFrame);
    animFrame = null;
  }}
  document.getElementById("speedControl").classList.remove("visible");
  document.getElementById("animProgress").classList.remove("visible");
  document.getElementById("progressFill").style.width = "0%";
  document.getElementById("btnAnimate").classList.remove("playing");
  document.getElementById("btnTimelapse").classList.remove("playing");
}}

// ── Render run list ──
function renderRunList() {{
  const query = document.getElementById("searchInput").value.toLowerCase();

  filteredRuns = RUNS.filter(r => {{
    if (query && !(r.name || "").toLowerCase().includes(query) && !(r.date || "").includes(query)) return false;
    return true;
  }});

  // Sort
  if (sortMode === "distance") {{
    filteredRuns.sort((a, b) => b.distance_mi - a.distance_mi);
  }} else if (sortMode === "pace") {{
    filteredRuns.sort((a, b) => {{
      const pa = a.avg_speed || 0;
      const pb = b.avg_speed || 0;
      return pb - pa;  // Faster = higher speed
    }});
  }} else {{
    filteredRuns.sort((a, b) => new Date(b.startTime) - new Date(a.startTime));
  }}

  const list = document.getElementById("runList");
  list.innerHTML = filteredRuns.map(r => {{
    const isActive = r.id == activeRunId;
    return '<div class="run-item' + (isActive ? " active" : "") + '" data-id="' + r.id + '">' +
      '<div class="run-date"><span>' + fmtDate(r.startTime) + '</span><span>' + fmtTime(r.startTime) + '</span></div>' +
      '<div class="run-name">' + (r.name || "Run") + '</div>' +
      '<div class="run-meta">' +
        '<span class="highlight">' + r.distance_mi + ' mi</span>' +
        '<span>' + (r.pace || "--") + '</span>' +
        '<span>' + fmtDuration(r.moving_time) + '</span>' +
        (r.total_elevation_gain ? '<span>' + Math.round(r.total_elevation_gain * 3.281) + ' ft</span>' : '') +
      '</div>' +
    '</div>';
  }}).join("");

  document.getElementById("runCount").textContent = filteredRuns.length + " runs";

  // Click handlers
  list.querySelectorAll(".run-item").forEach(el => {{
    el.addEventListener("click", () => selectRun(el.dataset.id));
  }});
}}

// ── Init ──
function init() {{
  initMap();
  renderRunList();

  // Stats
  document.getElementById("statRuns").textContent = STATS.totalRuns;
  document.getElementById("statMiles").textContent = STATS.totalDistance;
  document.getElementById("statPace").textContent = STATS.avgPace;

  // Search
  document.getElementById("searchInput").addEventListener("input", renderRunList);

  // Sort buttons
  document.querySelectorAll("[data-sort]").forEach(btn => {{
    btn.addEventListener("click", () => {{
      document.querySelectorAll("[data-sort]").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      sortMode = btn.dataset.sort;
      renderRunList();
    }});
  }});

  // View toggle
  document.querySelectorAll("[data-view]").forEach(btn => {{
    btn.addEventListener("click", () => {{
      document.querySelectorAll("[data-view]").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentView = btn.dataset.view;
      if (currentView === "heatmap") {{
        clearGhostRoutes();
        clearActiveRoute();
        hideRunDetail();
        showHeatmap();
      }} else {{
        hideHeatmap();
        showGhostRoutes();
      }}
    }});
  }});

  // Animate button
  document.getElementById("btnAnimate").addEventListener("click", () => {{
    if (document.getElementById("btnAnimate").classList.contains("playing")) {{
      stopAnimation();
      if (activeRunId) selectRun(activeRunId);
    }} else if (activeRunId) {{
      animateRun(activeRunId);
    }}
  }});

  // Timelapse button
  document.getElementById("btnTimelapse").addEventListener("click", () => {{
    if (document.getElementById("btnTimelapse").classList.contains("playing")) {{
      stopAnimation();
      showGhostRoutes();
    }} else {{
      timelapse();
    }}
  }});

  // Speed controls
  document.getElementById("speedUp").addEventListener("click", () => {{
    animSpeed = Math.min(10, animSpeed * 2);
    document.getElementById("speedVal").textContent = animSpeed + "x";
  }});
  document.getElementById("speedDown").addEventListener("click", () => {{
    animSpeed = Math.max(0.25, animSpeed / 2);
    document.getElementById("speedVal").textContent = animSpeed + "x";
  }});

  // Keyboard navigation
  document.addEventListener("keydown", (e) => {{
    if (e.target.tagName === "INPUT") return;
    const items = filteredRuns;
    const idx = items.findIndex(r => r.id == activeRunId);

    if (e.key === "ArrowDown" || e.key === "j") {{
      e.preventDefault();
      const next = Math.min(idx + 1, items.length - 1);
      selectRun(items[next].id);
      document.querySelector('.run-item[data-id="' + items[next].id + '"]')?.scrollIntoView({{ block: "nearest" }});
    }} else if (e.key === "ArrowUp" || e.key === "k") {{
      e.preventDefault();
      const prev = Math.max(idx - 1, 0);
      selectRun(items[prev].id);
      document.querySelector('.run-item[data-id="' + items[prev].id + '"]')?.scrollIntoView({{ block: "nearest" }});
    }} else if (e.key === " ") {{
      e.preventDefault();
      if (activeRunId) {{
        if (document.getElementById("btnAnimate").classList.contains("playing")) {{
          stopAnimation();
          selectRun(activeRunId);
        }} else {{
          animateRun(activeRunId);
        }}
      }}
    }} else if (e.key === "Escape") {{
      stopAnimation();
      clearActiveRoute();
      hideRunDetail();
      activeRunId = null;
      document.querySelectorAll(".run-item").forEach(el => el.classList.remove("active"));
      showGhostRoutes();
    }}
  }});

  // Select first run
  if (RUNS.length > 0) {{
    selectRun(filteredRuns[0].id);
  }}
}}

init();
</script>
</body>
</html>'''


if __name__ == "__main__":
    main()
