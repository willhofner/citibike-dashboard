#!/usr/bin/env python3
"""
Build the Strava Stats Dashboard HTML.
Reads activities_enriched.json, computes stats, and generates a static HTML file
with all data baked in. Follows the same pattern as the CitiBike dashboard.
"""

import json
import os
from datetime import datetime
from collections import Counter

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
ENRICHED_FILE = os.path.join(DATA_DIR, "activities_enriched.json")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard.html")


def pace_seconds_per_mile(moving_time_sec, distance_mi):
    """Compute pace in seconds per mile."""
    if not distance_mi or distance_mi == 0:
        return 9999
    return moving_time_sec / distance_mi


def fmt_pace(seconds_per_mile):
    """Format pace as M:SS/mi string."""
    if seconds_per_mile >= 9999:
        return "--"
    m = int(seconds_per_mile // 60)
    s = int(seconds_per_mile % 60)
    return f"{m}:{s:02d}/mi"


def fmt_duration(total_seconds):
    """Format duration as Xh Ym string."""
    h = int(total_seconds // 3600)
    m = int((total_seconds % 3600) // 60)
    if h > 0:
        return f"{h}h {m}m"
    return f"{m}m"


def main():
    with open(ENRICHED_FILE) as f:
        activities = json.load(f)

    # Filter to runs only
    runs = [a for a in activities if a["type"] == "Run"]
    runs.sort(key=lambda r: r.get("startTime", ""), reverse=True)

    if not runs:
        print("No runs found in data!")
        return

    # ── Compute stats ──

    total_runs = len(runs)
    total_distance_mi = sum(r["distance_mi"] for r in runs)
    total_time_sec = sum(r["moving_time"] for r in runs)
    total_time_hrs = total_time_sec / 3600
    total_elevation_m = sum(r.get("total_elevation_gain", 0) for r in runs)
    total_elevation_ft = total_elevation_m * 3.28084
    total_calories = sum(r.get("calories", 0) or 0 for r in runs)

    avg_pace_sec = pace_seconds_per_mile(total_time_sec, total_distance_mi)
    avg_distance = total_distance_mi / total_runs
    longest_run = max(runs, key=lambda r: r["distance_mi"])

    dates = sorted(r["date"] for r in runs if r.get("date"))
    earliest_date = datetime.strptime(dates[0], "%Y-%m-%d")
    latest_date = datetime.strptime(dates[-1], "%Y-%m-%d")
    weeks_span = max(1, (latest_date - earliest_date).days / 7)
    runs_per_week = total_runs / weeks_span

    avg_calories = total_calories / total_runs if total_runs else 0

    # ── For maps: strip heavy data, keep polylines ──
    runs_for_html = []
    for r in runs:
        run = {
            "id": r["id"],
            "name": r.get("name", "Run"),
            "startTime": r["startTime"],
            "date": r["date"],
            "dayOfWeek": r["dayOfWeek"],
            "hour": r["hour"],
            "month": r["month"],
            "distance_mi": r["distance_mi"],
            "distance_km": r.get("distance_km", 0),
            "moving_time": r["moving_time"],
            "pace": r.get("pace", ""),
            "avg_speed": r.get("avg_speed", 0),
            "total_elevation_gain": r.get("total_elevation_gain", 0),
            "calories": r.get("calories", 0),
            "startLat": r.get("startLat"),
            "startLon": r.get("startLon"),
            "endLat": r.get("endLat"),
            "endLon": r.get("endLon"),
            "polyline": r.get("polyline", ""),
            "bestEfforts": r.get("bestEfforts", []),
        }
        runs_for_html.append(run)

    # ── Build stats dict for HTML ──
    stats = {
        "totalRuns": total_runs,
        "totalMiles": round(total_distance_mi, 1),
        "totalHours": round(total_time_hrs, 1),
        "avgPace": fmt_pace(avg_pace_sec),
        "avgDistance": round(avg_distance, 1),
        "longestRun": round(longest_run["distance_mi"], 1),
        "longestRunName": longest_run.get("name", ""),
        "totalElevationFt": round(total_elevation_ft),
        "runsPerWeek": round(runs_per_week, 1),
        "avgCalories": round(avg_calories),
        "dateRange": f"{dates[0]} to {dates[-1]}" if dates else "",
    }

    # ── Serialize ──
    data_json = json.dumps(runs_for_html, separators=(",", ":"))
    stats_json = json.dumps(stats)

    html = build_html(data_json, stats_json)

    with open(OUTPUT_FILE, "w") as f:
        f.write(html)

    print(f"Built {OUTPUT_FILE}")
    print(f"  {total_runs} runs, {stats['totalMiles']} mi total")
    size_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    print(f"  File size: {size_mb:.1f} MB")


def build_html(data_json, stats_json):
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Strava Runs Dashboard</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
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
    --amber: #fbbf24;
    --red: #ef4444;
    --purple: #a855f7;
  }}

  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif;
    background: var(--bg);
    color: var(--text);
    overflow-x: hidden;
  }}

  a {{ color: var(--accent); text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}

  /* Header */
  .header {{
    padding: 32px 40px 24px;
    border-bottom: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
  }}
  .header h1 {{
    font-size: 28px;
    font-weight: 700;
    letter-spacing: -0.5px;
  }}
  .header h1 span {{ color: var(--accent); }}
  .header .subtitle {{
    color: var(--text-dim);
    font-size: 14px;
    margin-top: 4px;
  }}
  .header-stats {{
    display: flex;
    gap: 32px;
    align-items: flex-end;
  }}
  .header-stat {{
    text-align: right;
  }}
  .header-stat .value {{
    font-size: 24px;
    font-weight: 700;
    color: var(--accent);
  }}
  .header-stat .label {{
    font-size: 11px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 1px;
  }}
  .nav-links {{
    font-size: 13px;
    margin-top: 8px;
    display: flex;
    gap: 16px;
  }}

  /* Stat cards */
  .stats-row {{
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 12px;
    padding: 20px 40px;
  }}
  .stat-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
  }}
  .stat-card .label {{
    font-size: 11px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 6px;
  }}
  .stat-card .value {{
    font-size: 22px;
    font-weight: 700;
  }}
  .stat-card .detail {{
    font-size: 12px;
    color: var(--text-dim);
    margin-top: 4px;
  }}

  /* Map section */
  .map-section {{
    padding: 20px 40px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }}
  .map-container {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
    position: relative;
  }}
  .map-container .map-label {{
    position: absolute;
    top: 12px;
    left: 12px;
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
  #routeMap, #heatMap {{ height: 500px; width: 100%; }}

  /* Charts section */
  .charts-section {{
    padding: 20px 40px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }}
  .chart-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 20px;
  }}
  .chart-card h3 {{
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--text-dim);
    margin-bottom: 16px;
  }}
  .chart-card canvas {{ width: 100% !important; }}

  /* Rankings section */
  .rankings-section {{
    padding: 20px 40px;
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 12px;
  }}
  .ranking-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 20px;
  }}
  .ranking-card h3 {{
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--text-dim);
    margin-bottom: 16px;
  }}
  .ranking-item {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid var(--border);
  }}
  .ranking-item:last-child {{ border-bottom: none; }}
  .ranking-item .rank {{
    font-size: 12px;
    color: var(--text-dim);
    width: 24px;
    flex-shrink: 0;
  }}
  .ranking-item .name {{
    flex: 1;
    font-size: 13px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .ranking-item .stat {{
    font-weight: 700;
    font-size: 14px;
    color: var(--accent);
    margin-left: 12px;
    white-space: nowrap;
    flex-shrink: 0;
  }}
  .bar-bg {{
    position: relative;
    flex: 1;
    margin: 0 12px;
    overflow: hidden;
  }}
  .bar-bg .bar-fill {{
    height: 4px;
    border-radius: 2px;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
  }}

  /* Heatmap grid */
  .heatmap-section {{
    padding: 20px 40px;
  }}
  .heatgrid-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 20px;
  }}
  .heatgrid-card h3 {{
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--text-dim);
    margin-bottom: 16px;
  }}
  .heatgrid {{
    display: grid;
    grid-template-columns: auto repeat(24, 1fr);
    gap: 2px;
    font-size: 10px;
  }}
  .heatgrid .day-label {{
    color: var(--text-dim);
    display: flex;
    align-items: center;
    padding-right: 8px;
    font-size: 11px;
  }}
  .heatgrid .hour-label {{
    color: var(--text-dim);
    text-align: center;
    padding-bottom: 4px;
    font-size: 10px;
  }}
  .heatgrid .cell {{
    aspect-ratio: 1;
    border-radius: 3px;
    min-width: 14px;
    cursor: pointer;
    transition: transform 0.1s;
  }}
  .heatgrid .cell:hover {{
    transform: scale(1.3);
    outline: 1px solid var(--text);
  }}

  /* Footer */
  .footer {{
    padding: 24px 40px;
    border-top: 1px solid var(--border);
    text-align: center;
    color: var(--text-dim);
    font-size: 12px;
  }}

  /* Leaflet overrides */
  .leaflet-container {{ background: #0a0a0f; }}
  .leaflet-tile-pane {{ filter: saturate(0.5) brightness(1.5) contrast(1.05); }}
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>Strava <span>Runs</span></h1>
    <div class="subtitle" id="dateRange"></div>
    <div class="nav-links">
      <a href="../index.html">&larr; Home</a>
      <a href="index.html">Run Explorer &rarr;</a>
    </div>
  </div>
  <div class="header-stats" id="headerStats"></div>
</div>

<div class="stats-row" id="statsRow"></div>

<div class="map-section">
  <div class="map-container">
    <div class="map-label">All Routes</div>
    <div id="routeMap"></div>
  </div>
  <div class="map-container">
    <div class="map-label">Heat Map</div>
    <div id="heatMap"></div>
  </div>
</div>

<div class="heatmap-section">
  <div class="heatgrid-card">
    <h3>Run Activity &mdash; Day &amp; Hour</h3>
    <div class="heatgrid" id="dayHourGrid"></div>
  </div>
</div>

<div class="charts-section">
  <div class="chart-card">
    <h3>Monthly Runs</h3>
    <canvas id="monthlyChart"></canvas>
  </div>
  <div class="chart-card">
    <h3>Monthly Miles</h3>
    <canvas id="monthlyMilesChart"></canvas>
  </div>
</div>

<div class="charts-section">
  <div class="chart-card">
    <h3>Runs by Day of Week</h3>
    <canvas id="dowChart"></canvas>
  </div>
  <div class="chart-card">
    <h3>Duration Distribution</h3>
    <canvas id="durationChart"></canvas>
  </div>
</div>

<div class="charts-section">
  <div class="chart-card">
    <h3>Distance Distribution</h3>
    <canvas id="distanceChart"></canvas>
  </div>
  <div class="chart-card">
    <h3>Pace Distribution</h3>
    <canvas id="paceChart"></canvas>
  </div>
</div>

<div class="rankings-section">
  <div class="ranking-card">
    <h3>Top 10 Fastest Runs</h3>
    <div id="topFastest"></div>
  </div>
  <div class="ranking-card">
    <h3>Top 10 Longest Runs</h3>
    <div id="topLongest"></div>
  </div>
  <div class="ranking-card">
    <h3>Best Efforts</h3>
    <div id="topEfforts"></div>
  </div>
</div>

<div class="footer">
  Built with <span id="footerCount"></span> runs of Strava data &nbsp;|&nbsp;
  <a href="index.html">Explore Individual Runs &rarr;</a>
</div>

<script>
// ── Inline data ──
const RUNS = {data_json};
const STATS = {stats_json};

// ============================================================
// UTILITY
// ============================================================
function countBy(arr, fn) {{
  const map = {{}};
  arr.forEach(item => {{
    const key = fn(item);
    map[key] = (map[key] || 0) + 1;
  }});
  return map;
}}

function sumBy(arr, fn) {{
  return arr.reduce((s, item) => s + fn(item), 0);
}}

function topN(obj, n) {{
  return Object.entries(obj)
    .sort((a, b) => b[1] - a[1])
    .slice(0, n);
}}

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

function getRunCoords(run) {{
  if (run.polyline) return decodePoly(run.polyline);
  return null;
}}

function fmtPaceFromSpeed(speed) {{
  if (!speed || speed === 0) return "--";
  const paceSecPerMi = 1609.34 / speed;
  const m = Math.floor(paceSecPerMi / 60);
  const s = Math.floor(paceSecPerMi % 60);
  return m + ":" + String(s).padStart(2, "0") + "/mi";
}}

function fmtDuration(sec) {{
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  if (h > 0) return h + "h " + m + "m";
  return m + ":" + String(s).padStart(2, "0");
}}

function fmtEffortTime(sec) {{
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return m + ":" + String(s).padStart(2, "0");
}}

// ============================================================
// HEADER & STATS
// ============================================================
function renderHeader() {{
  const dateRange = STATS.dateRange || "";
  if (dateRange) {{
    const parts = dateRange.split(" to ");
    const fmtD = (str) => {{
      const d = new Date(str + "T00:00:00");
      return d.toLocaleDateString("en-US", {{ month: "short", year: "numeric" }});
    }};
    if (parts.length === 2) {{
      document.getElementById("dateRange").textContent = fmtD(parts[0]) + " — " + fmtD(parts[1]);
    }}
  }}

  document.getElementById("headerStats").innerHTML = `
    <div class="header-stat"><div class="value">${{STATS.totalRuns}}</div><div class="label">Total Runs</div></div>
    <div class="header-stat"><div class="value">${{STATS.totalMiles}} mi</div><div class="label">Total Miles</div></div>
    <div class="header-stat"><div class="value">${{STATS.totalHours}}h</div><div class="label">Total Hours</div></div>
  `;

  document.getElementById("statsRow").innerHTML = `
    <div class="stat-card"><div class="label">Avg Pace</div><div class="value">${{STATS.avgPace}}</div></div>
    <div class="stat-card"><div class="label">Avg Distance</div><div class="value">${{STATS.avgDistance}} mi</div></div>
    <div class="stat-card"><div class="label">Longest Run</div><div class="value">${{STATS.longestRun}} mi</div><div class="detail">${{STATS.longestRunName}}</div></div>
    <div class="stat-card"><div class="label">Total Elevation</div><div class="value">${{STATS.totalElevationFt.toLocaleString()}} ft</div></div>
    <div class="stat-card"><div class="label">Runs / Week</div><div class="value">${{STATS.runsPerWeek}}</div></div>
    <div class="stat-card"><div class="label">Avg Calories</div><div class="value">${{STATS.avgCalories}}</div><div class="detail">${{(STATS.avgCalories * STATS.totalRuns).toLocaleString()}} total</div></div>
  `;

  document.getElementById("footerCount").textContent = STATS.totalRuns;
}}

// ============================================================
// ROUTE MAP
// ============================================================
function renderRouteMap() {{
  const map = L.map("routeMap", {{
    zoomControl: false,
    attributionControl: false
  }}).setView([40.73, -73.99], 13);

  L.control.zoom({{ position: "topright" }}).addTo(map);

  L.tileLayer("https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png", {{
    maxZoom: 19
  }}).addTo(map);

  const allCoords = [];
  RUNS.forEach(run => {{
    const coords = getRunCoords(run);
    if (!coords || coords.length < 2) return;

    coords.forEach(c => allCoords.push(c));

    L.polyline(coords, {{
      color: "#f97316",
      weight: 1.5,
      opacity: 0.25,
    }}).addTo(map);
  }});

  if (allCoords.length > 0) {{
    map.fitBounds(L.latLngBounds(allCoords).pad(0.05));
  }}
}}

// ============================================================
// HEAT MAP
// ============================================================
function renderHeatMap() {{
  const map = L.map("heatMap", {{
    zoomControl: false,
    attributionControl: false
  }}).setView([40.73, -73.99], 13);

  L.control.zoom({{ position: "topright" }}).addTo(map);

  L.tileLayer("https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png", {{
    maxZoom: 19
  }}).addTo(map);

  const heatPoints = [];
  const allCoords = [];
  RUNS.forEach(run => {{
    const coords = getRunCoords(run);
    if (!coords) return;
    const step = Math.max(1, Math.floor(coords.length / 200));
    for (let i = 0; i < coords.length; i += step) {{
      heatPoints.push([coords[i][0], coords[i][1], 0.5]);
      allCoords.push(coords[i]);
    }}
  }});

  L.heatLayer(heatPoints, {{
    radius: 12,
    blur: 15,
    maxZoom: 17,
    gradient: {{ 0.2: "#1a1a2e", 0.4: "#f97316", 0.6: "#fb923c", 0.8: "#fbbf24", 1.0: "#fff" }},
  }}).addTo(map);

  if (allCoords.length > 0) {{
    map.fitBounds(L.latLngBounds(allCoords).pad(0.05));
  }}
}}

// ============================================================
// DAY x HOUR HEATGRID
// ============================================================
function renderDayHourGrid() {{
  const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
  const dayAbbr = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const grid = {{}};
  let maxVal = 0;

  days.forEach(d => {{ grid[d] = {{}}; for (let h = 0; h < 24; h++) grid[d][h] = 0; }});
  RUNS.forEach(r => {{ grid[r.dayOfWeek][r.hour]++; }});
  days.forEach(d => {{ for (let h = 0; h < 24; h++) maxVal = Math.max(maxVal, grid[d][h]); }});

  const container = document.getElementById("dayHourGrid");

  // Hour labels row
  container.innerHTML = "<div></div>";
  for (let h = 0; h < 24; h++) {{
    container.innerHTML += '<div class="hour-label">' + h + "</div>";
  }}

  days.forEach((d, di) => {{
    container.innerHTML += '<div class="day-label">' + dayAbbr[di] + "</div>";
    for (let h = 0; h < 24; h++) {{
      const val = grid[d][h];
      const intensity = maxVal > 0 ? val / maxVal : 0;
      // Orange gradient: from dark to bright orange
      const r = Math.round(30 + intensity * 219);   // 30 -> 249
      const g = Math.round(30 + intensity * 85);    // 30 -> 115
      const b = Math.round(46 + intensity * (22 - 46)); // 46 -> 22
      const bg = val === 0 ? "rgba(30,30,46,0.5)" : "rgba(" + r + "," + g + "," + b + "," + (0.3 + intensity * 0.7) + ")";
      container.innerHTML += '<div class="cell" style="background:' + bg + '" title="' + d + " " + h + ':00 — ' + val + ' runs"></div>';
    }}
  }});
}}

// ============================================================
// CHARTS
// ============================================================
const chartDefaults = {{
  responsive: true,
  maintainAspectRatio: true,
  plugins: {{
    legend: {{ display: false }},
    tooltip: {{
      backgroundColor: "rgba(10,10,15,0.95)",
      borderColor: "#1e1e2e",
      borderWidth: 1,
      titleColor: "#e0e0e8",
      bodyColor: "#e0e0e8",
      cornerRadius: 6,
      padding: 10,
    }}
  }},
  scales: {{
    x: {{
      ticks: {{ color: "#8888a0", font: {{ size: 11 }} }},
      grid: {{ display: false }},
      border: {{ color: "transparent" }}
    }},
    y: {{
      ticks: {{ color: "#8888a0", font: {{ size: 11 }} }},
      grid: {{ color: "rgba(30,30,46,0.8)" }},
      border: {{ color: "transparent" }}
    }}
  }}
}};

function renderMonthlyChart() {{
  const monthly = countBy(RUNS, r => r.month);
  const months = Object.keys(monthly).sort();

  new Chart(document.getElementById("monthlyChart"), {{
    type: "bar",
    data: {{
      labels: months.map(m => {{ const [y,mo] = m.split("-"); return new Date(y, mo-1).toLocaleDateString("en-US",{{month:"short",year:"2-digit"}}); }}),
      datasets: [{{
        data: months.map(m => monthly[m]),
        backgroundColor: "#f97316",
        borderRadius: 4,
        borderSkipped: false,
      }}]
    }},
    options: {{ ...chartDefaults, aspectRatio: 2.2 }}
  }});
}}

function renderMonthlyMilesChart() {{
  const monthlyMiles = {{}};
  RUNS.forEach(r => {{
    monthlyMiles[r.month] = (monthlyMiles[r.month] || 0) + r.distance_mi;
  }});
  const months = Object.keys(monthlyMiles).sort();

  new Chart(document.getElementById("monthlyMilesChart"), {{
    type: "line",
    data: {{
      labels: months.map(m => {{ const [y,mo] = m.split("-"); return new Date(y, mo-1).toLocaleDateString("en-US",{{month:"short",year:"2-digit"}}); }}),
      datasets: [{{
        data: months.map(m => +monthlyMiles[m].toFixed(1)),
        borderColor: "#fb923c",
        backgroundColor: "rgba(251,146,60,0.1)",
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: "#fb923c",
      }}]
    }},
    options: {{
      ...chartDefaults,
      aspectRatio: 2.2,
      scales: {{
        ...chartDefaults.scales,
        y: {{ ...chartDefaults.scales.y, ticks: {{ ...chartDefaults.scales.y.ticks, callback: v => v + " mi" }} }}
      }}
    }}
  }});
}}

function renderDowChart() {{
  const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
  const dayAbbr = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const dow = countBy(RUNS, r => r.dayOfWeek);
  const colors = days.map((d, i) => i >= 5 ? "#fbbf24" : "#f97316");

  new Chart(document.getElementById("dowChart"), {{
    type: "bar",
    data: {{
      labels: dayAbbr,
      datasets: [{{
        data: days.map(d => dow[d] || 0),
        backgroundColor: colors,
        borderRadius: 4,
        borderSkipped: false,
      }}]
    }},
    options: {{ ...chartDefaults, aspectRatio: 2.2 }}
  }});
}}

function renderDurationChart() {{
  const buckets = {{ "<20min": 0, "20-30": 0, "30-45": 0, "45-60": 0, "60+": 0 }};
  RUNS.forEach(r => {{
    const mins = r.moving_time / 60;
    if (mins < 20) buckets["<20min"]++;
    else if (mins < 30) buckets["20-30"]++;
    else if (mins < 45) buckets["30-45"]++;
    else if (mins < 60) buckets["45-60"]++;
    else buckets["60+"]++;
  }});

  new Chart(document.getElementById("durationChart"), {{
    type: "bar",
    data: {{
      labels: Object.keys(buckets).map(k => k.includes("min") ? k : k + " min"),
      datasets: [{{
        data: Object.values(buckets),
        backgroundColor: "#fb923c",
        borderRadius: 4,
        borderSkipped: false,
      }}]
    }},
    options: {{ ...chartDefaults, aspectRatio: 2.2 }}
  }});
}}

function renderDistanceChart() {{
  const buckets = {{ "<2mi": 0, "2-3": 0, "3-4": 0, "4-5": 0, "5-8": 0, "8+": 0 }};
  RUNS.forEach(r => {{
    const d = r.distance_mi;
    if (d < 2) buckets["<2mi"]++;
    else if (d < 3) buckets["2-3"]++;
    else if (d < 4) buckets["3-4"]++;
    else if (d < 5) buckets["4-5"]++;
    else if (d < 8) buckets["5-8"]++;
    else buckets["8+"]++;
  }});

  new Chart(document.getElementById("distanceChart"), {{
    type: "bar",
    data: {{
      labels: Object.keys(buckets).map(k => k.includes("mi") ? k : k + " mi"),
      datasets: [{{
        data: Object.values(buckets),
        backgroundColor: "#f97316",
        borderRadius: 4,
        borderSkipped: false,
      }}]
    }},
    options: {{ ...chartDefaults, aspectRatio: 2.2 }}
  }});
}}

function renderPaceChart() {{
  const buckets = {{ "<7:00": 0, "7-8": 0, "8-9": 0, "9-10": 0, "10-11": 0, "11-12": 0, "12+": 0 }};
  RUNS.forEach(r => {{
    if (!r.avg_speed || r.avg_speed === 0) return;
    const paceSec = 1609.34 / r.avg_speed;
    const paceMin = paceSec / 60;
    if (paceMin < 7) buckets["<7:00"]++;
    else if (paceMin < 8) buckets["7-8"]++;
    else if (paceMin < 9) buckets["8-9"]++;
    else if (paceMin < 10) buckets["9-10"]++;
    else if (paceMin < 11) buckets["10-11"]++;
    else if (paceMin < 12) buckets["11-12"]++;
    else buckets["12+"]++;
  }});

  new Chart(document.getElementById("paceChart"), {{
    type: "bar",
    data: {{
      labels: Object.keys(buckets).map(k => k + " /mi"),
      datasets: [{{
        data: Object.values(buckets),
        backgroundColor: "#a855f7",
        borderRadius: 4,
        borderSkipped: false,
      }}]
    }},
    options: {{ ...chartDefaults, aspectRatio: 2.2 }}
  }});
}}

// ============================================================
// RANKINGS
// ============================================================
function renderRankings() {{
  // Top 10 Fastest (by avg_speed, higher = faster)
  const bySpeed = [...RUNS].filter(r => r.avg_speed > 0 && r.distance_mi >= 1)
    .sort((a, b) => b.avg_speed - a.avg_speed)
    .slice(0, 10);

  const fastestMax = bySpeed[0]?.avg_speed || 1;
  document.getElementById("topFastest").innerHTML = bySpeed.map((r, i) => `
    <div class="ranking-item">
      <span class="rank">${{i + 1}}</span>
      <div class="bar-bg">
        <div class="name">${{r.name || r.date}} (${{r.distance_mi}} mi)</div>
        <div class="bar-fill" style="width:${{(r.avg_speed / fastestMax * 100).toFixed(0)}}%"></div>
      </div>
      <span class="stat">${{r.pace}}</span>
    </div>
  `).join("");

  // Top 10 Longest (by distance)
  const byDist = [...RUNS].sort((a, b) => b.distance_mi - a.distance_mi).slice(0, 10);
  const distMax = byDist[0]?.distance_mi || 1;
  document.getElementById("topLongest").innerHTML = byDist.map((r, i) => `
    <div class="ranking-item">
      <span class="rank">${{i + 1}}</span>
      <div class="bar-bg">
        <div class="name">${{r.name || r.date}}</div>
        <div class="bar-fill" style="width:${{(r.distance_mi / distMax * 100).toFixed(0)}}%"></div>
      </div>
      <span class="stat">${{r.distance_mi}} mi</span>
    </div>
  `).join("");

  // Best Efforts (collect all bestEfforts, group by name, take fastest)
  const effortsByName = {{}};
  RUNS.forEach(run => {{
    if (!run.bestEfforts) return;
    run.bestEfforts.forEach(e => {{
      const key = e.name;
      if (!effortsByName[key] || e.elapsed_time < effortsByName[key].time) {{
        effortsByName[key] = {{
          name: e.name,
          time: e.elapsed_time,
          distance: e.distance,
          runName: run.name || run.date,
          runDate: run.date,
        }};
      }}
    }});
  }});

  // Sort by distance (shorter efforts first)
  const efforts = Object.values(effortsByName).sort((a, b) => a.distance - b.distance);

  document.getElementById("topEfforts").innerHTML = efforts.map((e, i) => `
    <div class="ranking-item">
      <span class="rank">${{i + 1}}</span>
      <div class="bar-bg">
        <div class="name">${{e.name}}</div>
      </div>
      <span class="stat">${{fmtEffortTime(e.time)}}</span>
    </div>
  `).join("");
}}

// ============================================================
// INIT
// ============================================================
renderHeader();
renderRouteMap();
renderHeatMap();
renderDayHourGrid();
renderMonthlyChart();
renderMonthlyMilesChart();
renderDowChart();
renderDurationChart();
renderDistanceChart();
renderPaceChart();
renderRankings();
</script>
</body>
</html>'''


if __name__ == "__main__":
    main()
