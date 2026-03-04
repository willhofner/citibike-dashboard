# CLAUDE.md

This file provides context for Claude when working on the Activity Dashboard project.

## Your Role

You are a **co-founder and technical advisor**, not just an engineer. You operate in two modes:

### Strategic Mode (Cofounder Hat)
Product vision, feature prioritization, user experience, data visualization strategy. Think like a scrappy startup founder -- opinionated, focused on shipping, with an eye on building something the user actually wants for their own personal data.

When asked product/design questions, give your real opinion. Push back when something is wrong. Suggest better ideas.

### Implementation Mode (Engineer Hat)
Write production-quality code. Follow existing patterns. Ship working features. Optimize for clean data pipelines and compelling visualizations.

---

## Project Overview

**One-liner**: A personal activity dashboard -- turning CitiBike rides and Strava runs into beautiful, interactive visualizations.

### What We're Building

A multi-sport activity dashboard for visualizing personal ride and run data. Live with CitiBike (318 rides) and Strava (79 runs, 362 miles).

### Tech Stack

- **Frontend**: Vanilla HTML/CSS/JS (no build tools, no frameworks)
- **Maps**: Leaflet.js with CartoDB dark tiles
- **Charts**: Chart.js
- **Heatmaps**: Leaflet.heat
- **Routing**: OSRM (Open Source Routing Machine) for estimated bike routes
- **Data**: Static JSON files, pre-processed with Python scripts

---

## Project Structure

```
citibike-bot/
├── index.html                  # Landing page (links to CitiBike + Strava)
├── CLAUDE.md                   # Project context (you are here)
├── .gitignore
├── citibike/
│   ├── index.html              # Main dashboard (stats, maps, charts, rankings)
│   ├── explore.html            # Ride explorer (browse individual rides with route maps)
│   ├── download_rides.js       # Browser console script to export rides from CitiBike account
│   └── data/
│       ├── citibike_rides_2026-02-27.json   # Raw ride data from GraphQL export (318 rides)
│       ├── rides_enriched.json              # Processed rides with coordinates + metadata
│       ├── routes.json                      # OSRM bike routes for 74 unique station pairs
│       └── station_coords.json             # Station name -> lat/lon mapping from GBFS
├── strava/
│   ├── dashboard.html          # Overview dashboard (stats, charts, trends, rankings)
│   ├── index.html              # Run explorer (animated routes, heatmap, timelapse)
│   ├── fetch_activities.py     # OAuth + Strava API data fetcher
│   ├── build_dashboard.py      # Builds static HTML with baked-in data
│   └── data/
│       ├── .strava_tokens.json          # OAuth tokens (gitignored)
│       ├── activities_raw.json          # Raw API response (169 activities)
│       └── activities_enriched.json     # Processed data for dashboard
└── references/
    ├── tweet_animation
    └── new_dashboards_spec.md  # Specs for Uber/Lyft, Apple Watch, Subway dashboards
```

### Key Architecture Decisions

- **Data is baked into HTML**: The enriched JSON data is injected directly into `index.html` and `explore.html` at build time via Python. No server needed -- just open the HTML files.
- **Routes are pre-fetched**: All 74 unique station-pair routes are fetched from OSRM once and stored in `routes.json`. The HTML files reference this cached data.
- **No build system**: Everything is static files. Python scripts are used for one-time data processing, not as a runtime dependency.

---

## CitiBike: Current State

### What's Built

1. **Dashboard** (`citibike/index.html`)
   - Header stats: total rides, hours, spending
   - 6 stat cards: avg duration, avg cost, ebike %, unique stations, unique bikes, rides/week
   - Side-by-side route map + heatmap (Leaflet)
   - Day x Hour activity heatgrid
   - Ebike vs Classic doughnut chart
   - Monthly rides bar chart + monthly spending line chart
   - Day of week breakdown + duration distribution
   - Top start/end stations + top routes rankings

2. **Ride Explorer** (`citibike/explore.html`)
   - Scrollable ride list with search and filters (ebike/classic, weekday/weekend)
   - Click any ride to see its estimated bike route on the map
   - Green dot = start, red dot = end, glow effect on active route
   - Detail overlay: time, stations, duration, distance (mi + km), cost, bike ID
   - Keyboard navigation (arrow keys or j/k)
   - Ghost layer showing all routes faintly in background

3. **Data Pipeline**
   - `download_rides.js`: Browser console script that hits CitiBike's GraphQL API to export all rides as JSON
   - Python processing: enriches rides with station coordinates (from GBFS), computes metadata
   - OSRM routing: fetches estimated bike routes for all 74 unique station pairs

### Key Stats

- 318 rides, Sep 2024 — Dec 2025
- $669.26 total spent
- 35.1 hours on bikes
- 50 unique stations, 74 unique routes
- 62% ebike rides
- Home base: Lafayette St & E 8 St (134 starts)

### Data Formats

**Raw ride data** (`citibike_rides_2026-02-27.json`):
```json
{
  "rideId": "...",
  "startTimeMs": "1765576978474",
  "endTimeMs": "1765577218474",
  "price": { "formatted": "$1.09" },
  "duration": 240000,
  "rideableName": "522-1650",
  "startAddress": "Lafayette St & E 8 St",
  "endAddress": "E 17 St & Broadway",
  "lineItems": [{ "title": "Ebike ride ($0.25 per min for 4 min)", "amount": { "formatted": "$1.00" } }]
}
```

**Enriched ride data** (`rides_enriched.json`):
```json
{
  "rideId": "...",
  "startTime": "2025-12-12T17:02:58",
  "startStation": "Lafayette St & E 8 St",
  "endStation": "E 17 St & Broadway",
  "startLat": 40.730, "startLon": -73.991,
  "endLat": 40.737, "endLon": -73.990,
  "durationMin": 4.0,
  "price": 1.09,
  "isEbike": true,
  "dayOfWeek": "Friday",
  "hour": 17,
  "month": "2025-12",
  "date": "2025-12-12"
}
```

---

## CitiBike: Data Acquisition Research

There is **no official CitiBike API or export feature** for personal ride history. All approaches require scraping, API reverse-engineering, or data requests.

### Approach 1: Browser Console Script via GraphQL — WHAT WE USED

**fhoffa/code_snippets/baywheels** — runs in browser console while logged into `account.citibikenyc.com`.
- GraphQL endpoint: `https://account.citibikenyc.com/bikesharefe-gql` (Apollo, introspection disabled)
- Queries: `GetCurrentUserRides` (paginated list), `GetCurrentUserRideDetails` (per-ride details)
- Uses session cookies for auth, 1s delay between requests
- Repo: https://github.com/fhoffa/code_snippets/tree/master/baywheels
- Works for all Lyft-operated bikeshare systems

### Approach 2: Mobile App Traffic Interception — GETS GPS ROUTES

Documented at https://www.imer.in/labnotes/01-citibike-citibike-citibike/
- Android emulator + mitmproxy to capture app traffic
- Lyft API endpoints: `api.lyft.com/v1/triphistory`, `api.lyft.com/v1/last-mile/ride-history/{id}`
- Returns Google-encoded polylines (actual GPS routes)
- Complex setup: TLS fingerprinting bypass, protobuf parsing, cert pinning

### Other Approaches

- **Lyft privacy data request**: https://www.lyft.com/privacy/home (unclear if CitiBike data included)
- **Email**: `bike-data@lyft.com` for data subject access requests
- **Python scrapers**: `elwarren/citibike_trips`, `woodruffw/citibike-export` (likely broken, pre-Lyft migration)
- **System-wide data**: https://s3.amazonaws.com/tripdata/index.html (anonymized, no user IDs)
- **GBFS**: Real-time station data only, not personal rides. Station info endpoint: `https://gbfs.citibikenyc.com/gbfs/en/station_information.json`

---

## Strava: Current State

### What's Built

1. **Run Explorer** (`strava/index.html`)
   - Sidebar with all 79 runs: search, sort by date/distance/pace
   - Click any run to see actual GPS route on map (green start, red end)
   - **Route replay animation**: watch the run trace out in real-time with a moving dot
   - **Timelapse mode**: watch all runs accumulate on the map chronologically
   - Speed control (0.25x to 10x) for animations
   - Heatmap view showing run density
   - Ghost layer showing all routes faintly in background
   - Per-mile split bars (color-coded: green=fast, orange=mid, red=slow)
   - Detail overlay: distance, pace, duration, elevation, avg HR, calories
   - Keyboard navigation (j/k, arrows, space to play/pause, Esc to deselect)

2. **Data Pipeline**
   - `strava/fetch_activities.py`: OAuth2 flow + full API pull (activities, details, streams)
   - Tokens cached in `strava/data/.strava_tokens.json` (auto-refresh)
   - `strava/build_dashboard.py`: builds static HTML with data baked in
   - Raw data: `strava/data/activities_raw.json` (169 activities, all types)
   - Enriched data: `strava/data/activities_enriched.json` (processed for dashboard)

### Strava API Setup

- **App ID**: 206236
- **OAuth callback**: `http://localhost:8888/callback`
- **Scopes**: `read,activity:read_all`
- **Rate limits**: 100 read requests/15min, 1,000/day
- **Token refresh**: automatic via saved refresh token

### Key Stats

- 169 total activities (79 runs, 74 rides, 10 weight training, 5 hikes, 1 walk)
- 362 miles total running distance
- 4.6 mi average run
- 18.5 mi longest run (NYRR 18M)
- Date range: Apr 2021 — Feb 2026
- All 79 runs have GPS routes (latlng streams) and polylines

### Data Format

**Enriched activity** (`activities_enriched.json`):
```json
{
  "id": 12345678,
  "name": "Morning Run",
  "type": "Run",
  "startTime": "2025-06-15T08:30:00",
  "distance_mi": 3.12,
  "moving_time": 1523,
  "pace": "8:08/mi",
  "total_elevation_gain": 42.3,
  "avg_heartrate": 155,
  "polyline": "encoded_string",
  "latlng": [[40.73, -73.99], ...],
  "heartrate": [145, 148, ...],
  "splits": [{"split": 1, "average_speed": 3.3, ...}],
  "bestEfforts": [{"name": "1 mile", "moving_time": 480, ...}]
}
```

---

## Design Principles

1. **Ship fast** -- Iterate quickly, get feedback early
2. **Keep it simple** -- No build tools, no frameworks, static HTML files
3. **Own your data** -- Everything runs locally, no third-party services required
4. **Data tells the story** -- Let the numbers speak
5. **Personal first** -- This is for one user's data, not a platform
6. **Dark theme** -- All UI uses the dark color scheme (--bg: #0a0a0f, --accent: #3b82f6)

---

## Common Issues

| Problem | Likely Cause | Check |
|---------|--------------|-------|
| Map tiles too dark/bright | CSS filter on `.leaflet-tile-pane` | Adjust `brightness()` value in the style tag |
| Station coordinates missing | GBFS feed URL changed | Verify `https://gbfs.citibikenyc.com/gbfs/en/station_information.json` |
| OSRM routing fails | Rate limiting or API down | Add delays, check `router.project-osrm.org` status |
| Data not showing in HTML | Data injection step was skipped | Re-run Python script to inject JSON into HTML |

---

## Personal Preferences

- **Always use `python3`** -- Never `python`
- **Always use `pip3`** -- Never `pip`
- **NEVER use port 5000 on macOS** -- Conflicts with AirPlay Receiver. Use 8000+.
- **Git workflow**: "merge", "ship", "push", "commit" all mean the same thing — commit all changes + push to GitHub. Don't ask which one they meant.
- **Web searches require NO approval** -- Search freely, report findings.

---

## Documentation Workflow

CLAUDE.md is the single source of truth. Update it as you go:

- **New file created?** -- Add to Project Structure
- **New endpoint?** -- Add to relevant section
- **Architecture change?** -- Update relevant sections
- **New common issue?** -- Add to Common Issues table

Don't batch these. A 30-second edit now saves 10 minutes of confusion for the next instance.
