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

**One-liner**: A personal activity dashboard -- turning CitiBike rides, Strava runs, Uber rides, and Apple Watch data into beautiful, interactive visualizations.

### What We're Building

A personal activity dashboard for visualizing life data. Live with CitiBike (318 rides), Strava (85 runs, 391 miles), Uber (220 rides, $7.7K spent, 23 cities), Apple Watch heart rate (508K readings, 4.5 years), Books (Goodreads library), and Subway (5 trips detected from GPS). This is a personal site for showing friends — not public-facing. Strava data auto-syncs daily.

### Tech Stack

- **Frontend**: Vanilla HTML/CSS/JS (no build tools, no frameworks)
- **Maps**: Leaflet.js with CartoDB dark tiles
- **Charts**: Chart.js
- **Heatmaps**: Leaflet.heat
- **Routing**: OSRM (Open Source Routing Machine) for estimated bike/driving routes
- **Data**: Static JSON files, pre-processed with Python scripts
- **GPS Collection**: Overland iOS app → Railway-hosted receiver → daily JSON files

---

## Project Structure

```
citibike-bot/
├── index.html                  # Landing page (links to all dashboards)
├── CLAUDE.md                   # Project context (you are here)
├── ROADMAP.md                  # Product roadmap
├── .gitignore
├── package.json                # Minimal config (Railway deploy)
├── railway.json                # Railway deployment config
├── citibike/
│   ├── index.html              # HofBikes dashboard (stats, maps, charts, rankings)
│   ├── explore.html            # HofBikes ride explorer (animated bike routes)
│   ├── download_rides.js       # Browser console script to export rides from CitiBike account
│   ├── parse_rides.py          # Raw JSON → enriched JSON processor
│   ├── fetch_routes.py         # OSRM bike route fetcher for station pairs
│   └── data/
│       ├── citibike_rides_2026-02-27.json   # Raw ride data from GraphQL export (318 rides)
│       ├── rides_enriched.json              # Processed rides with coordinates + metadata
│       ├── routes.json                      # OSRM bike routes for 74 unique station pairs
│       └── station_coords.json              # Station name → lat/lon mapping from GBFS
├── strava/
│   ├── index.html              # HofRuns run explorer (animated routes, heatmap, timelapse)
│   ├── dashboard.html          # HofRuns dashboard (stats, charts, trends, rankings)
│   ├── fetch_activities.py     # OAuth + Strava API data fetcher (supports --incremental)
│   ├── build_dashboard.py      # Builds static HTML with baked-in data
│   ├── build_dashboard_stats.py # Builds dashboard stats
│   ├── update_strava.sh        # Full pipeline: fetch → build → commit + push
│   └── data/
│       ├── .strava_tokens.json          # OAuth tokens (gitignored)
│       ├── activities_raw.json          # Raw API response (gitignored)
│       └── activities_enriched.json     # Processed data for dashboard
├── uber/
│   ├── explore.html            # HofRides ride explorer (animated driving routes)
│   ├── dashboard.html          # HofRides spending dashboard (stats, charts, heatmaps, city breakdown)
│   ├── parse_rides.py          # CSV parser → enriched JSON
│   ├── fetch_routes.py         # OSRM driving route fetcher (220 routes, incremental)
│   └── data/
│       ├── Uber_Ride_History.csv        # Raw CSV from Uber privacy export (gitignored)
│       ├── rides_enriched.json          # Processed Uber rides (220 rides, 23 cities)
│       └── routes.json                  # OSRM driving routes keyed by ride ID (220 routes)
├── health/
│   ├── steps.html              # HofWalks — steps dashboard
│   ├── heartrate.html          # HofBeats — heart rate dashboard (RHR, HRV, VO2 Max, zones)
│   ├── parse_heartrate.py      # Apple Health XML → heart rate enriched JSON
│   ├── parse_health.py         # Apple Health XML → general health data overview
│   ├── build_steps.py          # Apple Health XML → steps enriched JSON
│   └── data/
│       ├── Apple_Health.xml             # Raw Apple Health export (gitignored, ~1.3GB)
│       ├── Apple_Health_CDA.xml         # Apple Health CDA export (gitignored, ~587MB)
│       ├── steps_enriched.json          # Daily step data (2,636 days)
│       └── heartrate_enriched.json      # Heart rate data (508K readings, 1,499 days)
├── books/
│   ├── index.html              # HofReads — bookshelf dashboard
│   ├── stack-of-books.jpg      # Dashboard hero image
│   └── data/
│       ├── Goodreads_Library.csv        # Raw Goodreads export (gitignored)
│       └── books.json                   # Processed book data
├── subway/
│   ├── explore.html            # HofSubways ride explorer (animated MTA routes)
│   ├── dashboard.html          # HofSubways dashboard (spending, heatgrid, line breakdown)
│   ├── receiver.py             # Overland GPS receiver (Railway-deployed, accepts POST from phone)
│   ├── pull_gps.py             # Downloads GPS data from Railway to local machine
│   ├── parse_rides.py          # GPS-to-subway-ride detection algorithm
│   ├── Dockerfile              # Railway deployment config
│   └── data/
│       ├── gps/                         # Daily GPS files: YYYY-MM-DD.json (gitignored)
│       ├── rides_enriched.json          # Detected subway rides with station data
│       └── *.csv                        # OMNY exports from omny.info (gitignored)
└── references/
    ├── index_redesign.html     # Landing page redesign draft
    ├── tweet_animation/
    └── new_dashboards_spec.md  # Specs for Uber/Lyft, Apple Watch, Subway dashboards
```

---

## Key Architecture Decisions

- **Static JSON, no server**: Explorers fetch enriched JSON at runtime via `fetch()`. Dashboards have data baked in at build time via Python. No backend needed.
- **Routes are pre-fetched**: OSRM routes are fetched once and stored in `routes.json` files. HTML files reference this cached data.
- **No build system**: Everything is static files. Python scripts are used for one-time data processing, not as a runtime dependency.
- **Incremental sync for Strava**: `fetch_activities.py` defaults to incremental mode — uses Strava's `after` param to only fetch new activities since last sync, then merges into existing data.
- **Automated daily updates**: macOS `launchd` agent runs `update_strava.sh` daily at 9 PM (fetch → build HTML → git commit + push). Runs on wake if laptop was asleep.
- **Pixel-based animation speed**: All ride explorers calculate animation rate from pixel distance after zoom completes, so every route animates at the same visual speed regardless of length or zoom level.

---

## CitiBike (HofBikes)

### What's Built

1. **Dashboard** (`citibike/index.html`)
   - Header stats: total rides, hours, spending
   - 6 stat cards: avg duration, avg cost, ebike %, unique stations, unique bikes, rides/week
   - Side-by-side route map + heatmap (Leaflet)
   - Day × Hour activity heatgrid
   - Ebike vs Classic doughnut chart
   - Monthly rides bar chart + monthly spending line chart
   - Day of week breakdown + duration distribution
   - Top start/end stations + top routes rankings

2. **Ride Explorer** (`citibike/explore.html`)
   - Scrollable ride list with search and filters (ebike/classic, weekday/weekend)
   - Click any ride to see its estimated bike route on the map
   - Green dot = start, red dot = end, animated route trace
   - Detail overlay: time, stations, duration, distance (mi + km), cost, bike ID
   - Keyboard navigation (arrow keys or j/k)

3. **Data Pipeline**
   - `download_rides.js`: Browser console script that hits CitiBike's GraphQL API to export all rides as JSON
   - `parse_rides.py`: Enriches rides with station coordinates (from GBFS), computes metadata
   - `fetch_routes.py`: Fetches OSRM bike routes for all unique station pairs
   - Data source: GraphQL endpoint `account.citibikenyc.com/bikesharefe-gql` (no official API exists)

### Key Stats

- 318 rides, Sep 2024 — Dec 2025
- $669.26 total spent, 35.1 hours on bikes
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

## Strava (HofRuns)

### What's Built

1. **Run Explorer** (`strava/index.html`)
   - Sidebar with all 85 runs: search, sort by date/distance/pace
   - Click any run to see actual GPS route on map (green start, red end)
   - **Route replay animation**: watch the run trace out in real-time with a moving dot
   - **Timelapse mode**: watch all runs accumulate on the map chronologically
   - Speed control (0.25x to 10x) for animations
   - Heatmap view showing run density
   - Per-mile split bars (color-coded: green=fast, orange=mid, red=slow)
   - Detail overlay: distance, pace, duration, elevation, avg HR, calories
   - Keyboard navigation (j/k, arrows, space to play/pause, Esc to deselect)

2. **Data Pipeline**
   - `fetch_activities.py`: OAuth2 flow + Strava API pull (supports `--incremental` and `--full`)
   - Tokens cached in `.strava_tokens.json` (auto-refresh, no browser needed after first auth)
   - `build_dashboard.py`: builds static HTML with data baked in
   - `update_strava.sh`: full pipeline script (fetch → build → commit + push)

3. **Automation**
   - macOS launchd agent: `~/Library/LaunchAgents/com.hofner.strava-update.plist`
   - Runs daily at 9 PM, catches up on wake if missed
   - Logs: `strava/data/.update.log`, `strava/data/.launchd_stderr.log`
   - Manual: `./strava/update_strava.sh` (or `--full` to re-fetch everything)

### Strava API Setup

- **App ID**: 206236
- **OAuth callback**: `http://localhost:8888/callback`
- **Scopes**: `read,activity:read_all`
- **Rate limits**: 100 read requests/15min, 1,000/day
- **Token refresh**: automatic via saved refresh token

### Key Stats

- 175 total activities (85 runs, 74 rides, 10 weight training, 5 hikes, 1 walk)
- 391 miles total running distance
- 4.6 mi average run, 18.5 mi longest run (NYRR 18M)
- Date range: Apr 2021 — Mar 2026
- All 85 runs have GPS routes (latlng streams) and polylines

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

## Uber (HofRides)

### What's Built

1. **Ride Explorer** (`uber/explore.html`)
   - Two-panel layout: scrollable ride list + Leaflet map
   - Search locations, filter by product type (UberX/UberXL/Other), weekday/weekend
   - Sort: Recent, Farthest, Priciest
   - Click any ride to see animated driving route on map (OSRM street-level routing)
   - Route animation: purple dot traces actual driving path with glow trail
   - Green marker = pickup, red marker = dropoff
   - Detail overlay: date, time, addresses, product, distance, duration, fare, city, wait time, surge
   - Keyboard navigation (j/k, arrows, Escape)
   - Accent color: purple (#a855f7)

2. **Dashboard** (`uber/dashboard.html`)
   - Header stats: total rides, total spent, ride time
   - 6 stat cards: avg fare, avg distance, avg duration, cities, avg wait, surge rides
   - Monthly spending line chart + monthly ride count bar chart
   - Day × Hour heatgrid (purple intensity)
   - Distribution histograms: distance, duration, cost (3 side-by-side)
   - Hour of day + day of week bar charts
   - Top 10 cities leaderboard
   - Product type doughnut chart

3. **Data Pipeline**
   - `parse_rides.py`: parses CSV export → enriched JSON
   - `fetch_routes.py`: fetches OSRM driving routes for all rides (incremental, keyed by ride ID)
   - Source: Uber privacy data export (CSV from privacy portal)
   - Routes: OSRM public API (`router.project-osrm.org/route/v1/driving/`), 0.5s delay between requests

### Key Stats

- 220 completed rides, Dec 2016 — Mar 2026
- $7,685.80 total spent, 1,359.5 total miles, 61.7 hours of ride time
- 23 cities (NYC: 83, Columbus: 52, Chicago: 14, Mexico City: 14)
- 73 surge rides (33%), Top product: UberX (177 rides, 80%)

### Data Formats

**Enriched ride data** (`uber/data/rides_enriched.json`):
```json
{
  "summary": {
    "totalRides": 220,
    "totalFare": 7685.80,
    "totalDistanceMi": 1359.5,
    "totalDurationHr": 61.7,
    "avgFare": 34.94,
    "avgDistanceMi": 6.18,
    "avgDurationMin": 16.8,
    "cityCount": 23,
    "surgedRides": 73
  },
  "rides": [{
    "id": 220,
    "city": "New York City",
    "product": "uberX",
    "startTime": "2026-03-17T20:02:09",
    "startLat": 40.72876, "startLon": -73.98759,
    "endLat": 40.72139, "endLon": -73.98769,
    "startAddress": "132 2nd Ave, New York City, NY 10002, US",
    "endAddress": "132 2nd Ave, New York City, NY 10002, US",
    "distanceMi": 0.7,
    "durationMin": 5.6,
    "fare": 13.53,
    "isSurged": false,
    "dayOfWeek": "Tuesday",
    "hour": 20,
    "month": "2026-03",
    "date": "2026-03-17"
  }]
}
```

---

## Heart Rate (HofBeats)

### What's Built

1. **Dashboard** (`health/heartrate.html`)
   - Header stats: total readings, days tracked, resting BPM
   - 6 stat cards: overall avg/min/max, avg HRV, latest VO2 Max, HRV readings
   - Resting Heart Rate trend (line chart with Daily/Weekly/Monthly toggles + rolling average)
   - HRV trend (line chart with toggles)
   - VO2 Max trend (line chart)
   - Daily HR range (floating bar chart: min-to-max with avg overlay, 30d/90d/1yr/all toggles)
   - Heart Rate zones (doughnut + bar chart side-by-side)
   - Hour of day pattern + Day × Hour heatgrid
   - BPM distribution histogram
   - Accent color: red (#ef4444)

2. **Data Pipeline**
   - `parse_heartrate.py`: parses Apple Health XML → enriched JSON (uses `iterparse` for ~1.3GB file)
   - `parse_health.py`: general Apple Health data overview
   - Source: Apple Health export (Settings → Health → Export All Health Data)
   - Extracts: HeartRate, RestingHeartRate, HRV (SDNN), VO2Max, WalkingHeartRateAverage

### Key Stats

- 508,148 heart rate readings, Oct 2021 — Mar 2026
- 1,499 days tracked
- Avg resting HR: 59.7 bpm, Avg HRV: 40.0 ms
- 5,487 HRV measurements, 528 VO2 Max measurements

### Data Format

**Enriched data** (`health/data/heartrate_enriched.json`):
```json
{
  "summary": {
    "totalReadings": 508148,
    "dateRange": ["2021-10-10", "2026-03-15"],
    "daysTracked": 1499,
    "overallAvg": 78.3,
    "avgRestingHR": 59.7,
    "avgHRV": 40.0,
    "latestVO2Max": 42.5
  },
  "dailyStats": [{ "date": "2021-10-10", "min": 45.0, "max": 180.0, "avg": 72.5, "count": 340, "hourly": {} }],
  "restingHR": [{ "value": 59, "date": "2025-01-27" }],
  "hrv": [{ "value": 22.8, "date": "2021-10-10" }],
  "vo2max": [{ "value": 42.5, "date": "..." }],
  "hourlyAvg": { "0": 65.2, "1": 63.1, "23": 68.4 },
  "zones": { "rest": 50000, "light": 300000, "moderate": 100000, "vigorous": 40000, "peak": 18000 },
  "bpmHistogram": [{ "bpm": 40, "count": 500 }]
}
```

---

## Steps (HofWalks)

### What's Built

1. **Dashboard** (`health/steps.html`)
   - Accent color: green (#22c55e)

2. **Data Pipeline**
   - `build_steps.py`: Apple Health XML → steps enriched JSON
   - Data: `health/data/steps_enriched.json` (2,636 days)

---

## Books (HofReads)

### What's Built

1. **Bookshelf Dashboard** (`books/index.html`)
   - Visual bookshelf: books standing upright on a wooden shelf, spines facing out
   - Spine widths proportional to page count, heights varied per book
   - Weathered texture: grain overlay, sun-faded tops, scuff marks, edge darkening
   - Single horizontally scrollable shelf with fade edges and drag-to-scroll
   - Click any book for detail card with Open Library cover image (38/51 books have ISBN)
   - Filter by star rating (1-5 stars)
   - Stack-of-books hero image at top
   - Accent color: amber #eab308

2. **Data Pipeline**
   - Source: Goodreads Library export (CSV), gitignored
   - Processed data: `books/data/books.json`
   - Cover images: fetched from Open Library API via ISBN (`covers.openlibrary.org`)

---

## Subway (HofSubways)

### What's Built

1. **Ride Explorer** (`subway/explore.html`)
   - Two-panel layout: scrollable ride list + Leaflet map
   - MTA-style colored circle bullet filters (6, 4, 5, R/W) with active/dimmed states
   - Ride list: line bullets, date, entry→exit stations, duration
   - Click any ride to see animated route on map with colored MTA line segments
   - Animated rider dot traces route between stations
   - Per-leg detail cards with line bullets, direction, station info
   - Transfer rides show as stacked leg cards
   - Green marker = entry, red marker = exit
   - Keyboard navigation (j/k, arrows, Escape)
   - Accent color: yellow #eab308

2. **Dashboard** (`subway/dashboard.html`)
   - Header stats: total trips, total spent ($3/entrance, transfers free), ride time
   - 4 stat cards: avg duration, lines ridden, stations visited, transfers
   - Rides by Line doughnut chart (MTA colors)
   - Most Visited Stations leaderboard
   - Day × Hour heatgrid (yellow intensity)

3. **Data Pipeline** (`subway/parse_rides.py`)
   - Detects subway rides from GPS accuracy degradation (>50m = underground)
   - Transfer detection: splits segments >8min at accuracy valleys near known stations
   - Line detection: 6 local vs 4/5 express based on station patterns
   - False positive filtering: home accuracy blips, same-station segments, driving tunnels
   - Station complex mapping (e.g., Chambers St J/Z = Brooklyn Bridge-City Hall)
   - Station data hardcoded: focused Lex Ave corridor + connecting lines (~40 stations)

4. **GPS Collection Pipeline** (live since 2026-03-29)
   - **Overland iOS app**: Free, open-source GPS logger. Runs passively, batches points, sends via HTTPS POST.
   - **Railway receiver** (`subway/receiver.py`): Accepts Overland's GeoJSON payloads, stores as daily JSON files on persistent volume. Auth via `?token=` query param.
   - **Railway deployment**: Service `subway-data`, domain `subway-data-production.up.railway.app`, volume at `/data`.
   - **Pull script** (`subway/pull_gps.py`): Downloads GPS data to local `subway/data/gps/`.
     ```
     RECEIVER_URL=https://subway-data-production.up.railway.app RECEIVER_TOKEN=yourtoken python3 subway/pull_gps.py
     ```

### Key Stats

- 5 trips, 6 legs
- Lines: 6, 4/5, R/W
- Key stations: Astor Place, Union Sq, Brooklyn Bridge-City Hall, Grand Central, Canal St
- Date range: Mar 30 — Apr 2, 2026

### GPS Detection Methodology

**Primary signal: GPS accuracy degradation.** When the phone goes underground, GPS accuracy degrades from ~10-20m to 100-964m as it falls back to cell tower triangulation.

| Phase | Accuracy | Key Signal |
|-------|----------|------------|
| Surface / walking | 10-25m | Normal GPS |
| Underground / tunnel | 100-964m | Cell tower fallback |
| Station stop | 30-80m | Brief partial recovery |
| Exit / surface | Recovers to <30m | Sustained + walking motion |

**Detection rules:**
1. Underground = accuracy > 100m (surface Manhattan is reliably 5-25m)
2. Entry station = last good-accuracy cluster near a known MTA station before degradation
3. Exit station = first good-accuracy cluster near a known MTA station after recovery, followed by walking motion away
4. Pass-through vs exit: if accuracy recovers briefly (<60s) then degrades again → pass-through; if sustained → exit

**Edge cases handled:**
- Multi-stop rides (repeated accuracy spike/recovery cycles)
- Long underground walks in stations (station-snap by proximity, not by accuracy boundary)
- Underground transfers (extended degraded accuracy with walking-speed changes between legs)
- Same-platform express↔local transfers (>90s station stop + station sequence shift)
- False positives: basements (require ≥2 stations in sequence), tunnels (no station pings), home blips (geo-filtered)

### The Data Problem

NYC subway has **tap-in only, no tap-out**. OMNY exports from `omny.info` have timestamps and fares but **no station names** (removed by MTA after stalking concerns). Solution: GPS-based station detection via Overland iOS app.

**Data sources:**
1. **Overland GPS** (primary): Continuous coordinates with accuracy, stored as daily JSON on Railway
2. **OMNY CSV** (validation only): 448 trips, gitignored. Cross-reference tap times with GPS to confirm detection
3. **MTA stations**: ~40 stations hardcoded in `parse_rides.py` (Lex Ave corridor + connecting lines)

### Data Format

**Enriched trip data** (`rides_enriched.json`):
```json
{
  "trips": [{
    "id": "trip_2026-03-30_1",
    "date": "2026-03-30",
    "legs": [{
      "entry_station": "Astor Place",
      "exit_station": "Union Sq - 14th St",
      "entry_time": "2026-03-30T09:06:43-04:00",
      "exit_time": "2026-03-30T09:09:01-04:00",
      "duration_min": 2.3,
      "line": "6",
      "direction": "Uptown",
      "num_stops": 1,
      "entry_lat": 40.7291, "entry_lon": -73.9910,
      "exit_lat": 40.7348, "exit_lon": -73.9899
    }],
    "total_duration_min": 2.3,
    "num_legs": 1,
    "has_transfer": false
  }]
}
```

---

## Landing Page

The landing page (`index.html`) has two sections:

1. **Activity cards**: 2-column grid with HofBikes, HofRuns, HofRides, HofSubways, HofWalks, HofBeats, and HofReads. Each card has icon, badge (Live/New), brand, description, key stats, and links to explorer + dashboard. Stats are currently hardcoded — not auto-updated by the sync pipeline.

2. **Scheduled Jobs**: A footer section listing all recurring automated jobs (currently just Strava Sync — daily at 9 PM). Green dot = active. Update this section when new scheduled jobs are added.

---

## Design Principles

1. **Ship fast** -- Iterate quickly, get feedback early
2. **Keep it simple** -- No build tools, no frameworks, static HTML files
3. **Own your data** -- Everything runs locally, no third-party services required
4. **Data tells the story** -- Let the numbers speak
5. **Personal first** -- This is for one user's data, not a platform
6. **Dark theme** -- All UI uses the dark color scheme (--bg: #0a0a0f). Accent colors: HofBikes=blue #3b82f6, HofRuns=orange #f97316, HofRides=purple #a855f7, HofWalks=green #22c55e, HofBeats=red #ef4444, HofSubways=yellow #eab308
7. **Consistent naming** -- All pages use the `Hof<span>Brand</span>` h1 pattern. Titles: `HofBrand — Dashboard` or `HofBrand — Ride Explorer`. Nav links: plain `Home` + sibling page name (no arrows). Explorers use `.back-link` in sidebar, dashboards use `.nav-links` in header.

---

## Common Issues

| Problem | Likely Cause | Check |
|---------|--------------|-------|
| Map tiles too dark/bright | CSS filter on `.leaflet-tile-pane` | Adjust `brightness()` value in the style tag |
| Station coordinates missing | GBFS feed URL changed | Verify `https://gbfs.citibikenyc.com/gbfs/en/station_information.json` |
| OSRM routing fails | Rate limiting or API down | Add delays, check `router.project-osrm.org` status |
| Strava token refresh fails | App deauthorized or tokens corrupted | Delete `.strava_tokens.json`, re-run `fetch_activities.py` (will open browser for re-auth) |
| Strava daily sync not running | launchd agent unloaded or laptop off | `launchctl list \| grep hofner` to check; `launchctl load ~/Library/LaunchAgents/com.hofner.strava-update.plist` to reload |
| Landing page stats stale | Stats in `index.html` are hardcoded | Manually update the card stat values after a sync (not yet automated) |
| Overland not sending data | Token mismatch or endpoint URL wrong | Check Overland app endpoint URL includes `?token=...`; verify Railway service is running |
| Railway GPS data lost on redeploy | Volume not mounted | Ensure Railway volume is mounted at `/data` in service settings |
| GPS data not pulling locally | Env vars not set | Run with `RECEIVER_URL=... RECEIVER_TOKEN=... python3 subway/pull_gps.py` |

---

## Personal Preferences

- **Always use `python3`** -- Never `python`
- **Always use `pip3`** -- Never `pip`
- **NEVER use port 5000 on macOS** -- Conflicts with AirPlay Receiver. Use 8000+.
- **Git workflow**: "merge", "ship", "push", "commit" all mean the same thing — commit all changes + push to GitHub. Don't ask which one they meant.
- **Web searches require NO approval** -- Search freely, report findings.
- **Always validate HTML pages with headless browser before presenting to user** -- Use Playwright (`python3 -m playwright`) to load the page, check for JS errors, verify elements render. Start a local server (`python3 -m http.server 8080`), load the page with `wait_until='networkidle'`, check console errors, verify key elements exist. Playwright is installed (`pip3 install --break-system-packages playwright && python3 -m playwright install chromium`).

---

## Documentation Workflow

**CLAUDE.md is a living document.** Keep it in sync with reality. When something changes, update it immediately.

### Always Update CLAUDE.md When:

- **New file or directory created/moved/deleted** — Update Project Structure tree
- **New dashboard or feature shipped** — Update the relevant "What's Built" section
- **Architecture decision made** — Add to Key Architecture Decisions with rationale
- **New data source added** — Add full section (What's Built, Key Stats, Data Formats)
- **Stats changed** (new rides, new runs, etc.) — Update Key Stats
- **New scheduled job added** — Update Automation section + Landing Page section
- **New bug discovered/fixed** — Update Common Issues table
- **New personal preference discovered** — Add to Personal Preferences
- **Design pattern established** — Note it so future work follows the same pattern

### How to Update:

- **Do it inline, immediately** — Don't batch documentation updates.
- **Be specific** — Include file paths, numbers, dates, and rationale.
- **Include the "why"** — Future context depends on understanding *why* a decision was made.
- **Delete stale info** — Wrong documentation is worse than no documentation.
