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

A personal activity dashboard for visualizing life data. Live with CitiBike (318 rides), Strava (85 runs, 391 miles), Uber (220 rides, $7.7K spent, 23 cities), Apple Watch heart rate (508K readings, 4.5 years), Books (Goodreads library), and Subway (5 trips detected from GPS). HofSubways ride detection is working — detecting subway rides from GPS accuracy degradation via Overland iOS app. This is a personal site for showing friends — not public-facing. Strava data auto-syncs daily.

### Tech Stack

- **Frontend**: Vanilla HTML/CSS/JS (no build tools, no frameworks)
- **Maps**: Leaflet.js with CartoDB dark tiles
- **Charts**: Chart.js
- **Heatmaps**: Leaflet.heat
- **Routing**: OSRM (Open Source Routing Machine) for estimated bike routes
- **Data**: Static JSON files, pre-processed with Python scripts
- **GPS Collection**: Overland iOS app → Railway-hosted receiver → daily JSON files

---

## Project Structure

```
citibike-bot/
├── index.html                  # Landing page (links to all dashboards)
├── CLAUDE.md                   # Project context (you are here)
├── .gitignore
├── package.json                # Minimal config (Railway deploy)
├── railway.json                # Railway deployment config
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
│   ├── fetch_activities.py     # OAuth + Strava API data fetcher (supports --incremental)
│   ├── build_dashboard.py      # Builds static HTML with baked-in data
│   ├── update_strava.sh        # Full pipeline: fetch → build → commit + push
│   └── data/
│       ├── .strava_tokens.json          # OAuth tokens (gitignored)
│       ├── activities_raw.json          # Raw API response (gitignored)
│       └── activities_enriched.json     # Processed data for dashboard
├── uber/
│   ├── explore.html            # Ride explorer (animated driving routes, ghost layer)
│   ├── dashboard.html          # Spending dashboard (stats, charts, heatmaps, city breakdown)
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
│   ├── stack-of-books.jpg      # Dashboard image asset
│   └── data/
│       ├── Goodreads_Library.csv        # Raw Goodreads export (gitignored)
│       └── books.json                   # Processed book data
├── subway/
│   ├── receiver.py             # Overland GPS receiver (Railway-deployed, accepts POST from phone)
│   ├── pull_gps.py             # Downloads GPS data from Railway to local machine
│   ├── parse_rides.py          # GPS-to-subway-ride detection algorithm
│   ├── explore.html            # HofSubways ride explorer
│   ├── dashboard.html          # HofSubways dashboard (spending, heatgrid, line breakdown, station visits)
│   ├── Dockerfile              # Railway deployment config
│   └── data/
│       ├── gps/                        # Daily GPS files: YYYY-MM-DD.json (gitignored)
│       ├── rides_enriched.json         # Detected subway rides with station data
│       └── *.csv                       # OMNY exports from omny.info (gitignored)
└── references/
    ├── index_redesign.html     # Landing page redesign draft
    ├── tweet_animation/
    └── new_dashboards_spec.md  # Specs for Uber/Lyft, Apple Watch, Subway dashboards
```

### Key Architecture Decisions

- **Data is baked into HTML**: The enriched JSON data is injected directly into `index.html` and `explore.html` at build time via Python. No server needed -- just open the HTML files.
- **Routes are pre-fetched**: All 74 unique station-pair routes are fetched from OSRM once and stored in `routes.json`. The HTML files reference this cached data.
- **No build system**: Everything is static files. Python scripts are used for one-time data processing, not as a runtime dependency.
- **Incremental sync for Strava**: `fetch_activities.py` defaults to incremental mode — uses Strava's `after` param to only fetch new activities since last sync, then merges into existing data. ~2-4 API calls per new activity vs 338+ for a full re-fetch.
- **Automated daily updates**: macOS `launchd` agent runs `update_strava.sh` daily at 9 PM (fetch → build HTML → git commit + push). Runs on wake if laptop was asleep. Manual trigger: `./strava/update_strava.sh`

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
   - `strava/fetch_activities.py`: OAuth2 flow + Strava API pull (supports `--incremental` and `--full`)
   - Tokens cached in `strava/data/.strava_tokens.json` (auto-refresh, no browser needed after first auth)
   - `strava/build_dashboard.py`: builds static HTML with data baked in
   - `strava/update_strava.sh`: full pipeline script (fetch → build → commit + push)
   - Raw data: `strava/data/activities_raw.json` (175 activities, all types)
   - Enriched data: `strava/data/activities_enriched.json` (processed for dashboard)

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
- 4.6 mi average run
- 18.5 mi longest run (NYRR 18M)
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

## Uber (HofRides): Current State

### What's Built

1. **Ride Explorer** (`uber/explore.html`)
   - Two-panel layout: scrollable ride list + Leaflet map
   - Search locations, filter by product type (UberX/UberXL/Other), weekday/weekend
   - Sort: Recent, Farthest, Priciest
   - Click any ride to see animated driving route on map (OSRM street-level routing)
   - Route animation: purple dot traces actual driving path with glow trail
   - Green marker = pickup, red marker = dropoff
   - Ghost layer: all 220 pickup points as faded purple circles
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
   - `uber/parse_rides.py`: parses CSV export → enriched JSON
   - `uber/fetch_routes.py`: fetches OSRM driving routes for all rides (incremental, keyed by ride ID)
   - Source: Uber privacy data export (CSV)
   - Routes: OSRM public API (`router.project-osrm.org/route/v1/driving/`), 0.5s delay between requests

### Key Stats

- 220 completed rides, Dec 2016 — Mar 2026
- $7,685.80 total spent
- 1,359.5 total miles
- 61.7 hours of ride time
- 23 cities (NYC: 83, Columbus: 52, Chicago: 14, Mexico City: 14)
- 73 surge rides (33%)
- Top product: UberX (177 rides, 80%)

### Data Source: Uber Privacy Export

Downloaded from Uber's privacy portal. Export includes full ride history CSV with:
- Pickup/dropoff lat/lng and addresses
- Trip distance, duration, fare breakdown
- Product type, surge multiplier, wait time
- City, timezone, currency

### Data Formats

**Raw data** (`uber/data/Uber_Ride_History.csv`):
```csv
city_name,currency_code,timezone,flow,product_type_name,global_product_name,
request_timestamp_local,request_timestamp_utc,request_lat,request_lng,
begintrip_timestamp_local,begintrip_timestamp_utc,begintrip_lat,begintrip_lng,begintrip_address,
dropoff_timestamp_local,dropoff_timestamp_utc,dropoff_lat,dropoff_lng,dropoff_address,
trip_distance_miles,trip_duration_seconds,status,is_completed,fare_amount,
surge_multiplier,is_surged,is_pool_matched,...
```

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

## Heart Rate (HofBeats): Current State

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
   - `health/parse_heartrate.py`: parses Apple Health XML → enriched JSON
   - Source: Apple Health export (XML)
   - Extracts: HeartRate, RestingHeartRate, HRV (SDNN), VO2Max, WalkingHeartRateAverage

### Key Stats

- 508,148 heart rate readings, Oct 2021 — Mar 2026
- 1,499 days tracked
- Avg resting HR: 59.7 bpm
- Avg HRV: 40.0 ms
- 5,487 HRV measurements
- 528 VO2 Max measurements
- 1,355 walking HR averages

### Data Source: Apple Health Export

Exported from iPhone Health app (Settings → Health → Export All Health Data). Produces `Apple_Health.xml` (~5.8M lines). The parser uses `iterparse` for memory-efficient streaming.

### Data Formats

**Raw data** (`health/data/Apple_Health.xml`):
```xml
<Record type="HKQuantityTypeIdentifierHeartRate"
  sourceName="Will's Apple Watch" unit="count/min"
  startDate="2024-11-21 18:40:02 -0400" value="65"/>

<Record type="HKQuantityTypeIdentifierRestingHeartRate"
  sourceName="Will's Apple Watch" unit="count/min"
  startDate="2025-01-27 10:34:26 -0400" value="59"/>

<Record type="HKQuantityTypeIdentifierHeartRateVariabilitySDNN"
  sourceName="Will's Apple Watch" unit="ms"
  startDate="2021-10-10 22:52:18 -0400" value="22.8062"/>
```

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
  "dailyStats": [{
    "date": "2021-10-10",
    "min": 45.0, "max": 180.0, "avg": 72.5,
    "count": 340,
    "hourly": { "0": 62.3, "8": 78.1 }
  }],
  "restingHR": [{ "value": 59, "date": "2025-01-27" }],
  "hrv": [{ "value": 22.8, "date": "2021-10-10" }],
  "vo2max": [{ "value": 42.5, "date": "..." }],
  "hourlyAvg": { "0": 65.2, "1": 63.1, "23": 68.4 },
  "zones": { "rest": 50000, "light": 300000, "moderate": 100000, "vigorous": 40000, "peak": 18000 },
  "bpmHistogram": [{ "bpm": 40, "count": 500 }]
}
```

---

## Books (HofReads): Current State

### What's Built

1. **Bookshelf Dashboard** (`books/index.html`)
   - Visual bookshelf: books standing upright on a wooden shelf, spines facing out
   - Spine widths proportional to page count, heights varied per book
   - Weathered texture: grain overlay, sun-faded tops, scuff marks, edge darkening
   - Some books lean at angles with proper margin spacing
   - Barlow Condensed font for titles, authors at top of spine
   - Single horizontally scrollable shelf with fade edges and drag-to-scroll
   - Click any book for detail card with Open Library cover image (38/51 books have ISBN)
   - Filter by star rating (1-5 stars)
   - Keyboard dismiss with Escape
   - Stack-of-books hero image at top
   - Accent color: amber #eab308

2. **Data Pipeline**
   - Source: Goodreads Library export (CSV), gitignored at `books/data/Goodreads_Library.csv`
   - Processed data: `books/data/books.json`
   - Cover images: fetched from Open Library API via ISBN (`covers.openlibrary.org`)

---

## Subway (HofSubways): Current State

### Status: Live — Ride Detection Working (since 2026-04-02)

### What's Built

1. **Data Pipeline** (`subway/parse_rides.py`)
   - Detects subway rides from GPS accuracy degradation (>50m = underground)
   - Transfer detection: splits segments >8min at accuracy valleys (<50m) near known stations
   - Line detection: 6 local vs 4/5 express based on station patterns (entry/exit express flags)
   - False positive filtering: home accuracy blips, same-station segments, driving tunnels
   - Station complex mapping (e.g., Chambers St J/Z = Brooklyn Bridge-City Hall)
   - Station data hardcoded: focused Lex Ave corridor + connecting lines (~40 stations)
   - 5 confirmed rides detected across 2 days (March 30 — April 2)

2. **Ride Explorer** (`subway/explore.html`)
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

3. **Dashboard** (`subway/dashboard.html`)
   - Header stats: total trips, total spent ($3/entrance, transfers free), ride time
   - 4 stat cards: avg duration, lines ridden, stations visited, transfers
   - Rides by Line doughnut chart (MTA colors)
   - Most Visited Stations leaderboard (counts entry + exit + transfer stations only, not pass-throughs)
   - Day × Hour heatgrid (yellow intensity)
   - Accent color: yellow #eab308

4. **GPS Collection Pipeline** (live since 2026-03-29)
   - Overland iOS app → Railway receiver → daily JSON files
   - `pull_gps.py` downloads to local machine

### Key Stats

- 5 trips, 6 legs
- Lines: 6, 4/5, R/W
- Key stations: Astor Place, Union Sq, Brooklyn Bridge-City Hall, Grand Central, Canal St
- Date range: Mar 30 — Apr 2, 2026

### Key Architecture Decisions (Subway)

- **Detection uses accuracy degradation (>50m = underground)**, not GPS position — position is unreliable when underground
- **Transfer detection**: splits segments >8min at accuracy valleys (<50m) near known stations
- **Station data hardcoded**: focused Lex Ave corridor + connecting lines (~40 stations), not full GTFS import
- **Station complex mapping**: maps equivalent station names (e.g., Chambers St J/Z → Brooklyn Bridge-City Hall) so transfers are detected correctly
- **Home position filtering**: eliminates indoor accuracy blips near home that look like underground segments
- **Express vs local detection**: uses entry/exit station express flags to determine if ride was on 6 local or 4/5 express

### The Data Problem

NYC subway has **tap-in only, no tap-out**. OMNY (tap-to-pay) exports from `omny.info` include timestamps and fares but **no station names** — the MTA intentionally removed station names from exports after a 404 Media investigation revealed it as a stalking vector.

**Solution: GPS-based station detection.** When the phone goes underground, GPS accuracy degrades dramatically (from ~10-20m to 100-964m) as it falls back to cell tower triangulation. The phone regains partial signal at each station the train passes through. This allows us to:
1. Detect underground segments via GPS accuracy spikes (>100m = underground)
2. Identify entry/exit stations from the last/first good-accuracy points near known MTA stations
3. Detect intermediate stations from brief accuracy recoveries during the ride
4. Determine the exact subway line from the sequence of stations (using GTFS data)
5. Detect direction (uptown/downtown, eastbound/westbound) from station order
6. Detect transfers where the station sequence shifts to a different line
7. Distinguish subway from other underground scenarios (tunnels, basements) by requiring proximity to ≥2 MTA stations in sequence

### Architecture

```
Overland iOS app (passive GPS logging)
        ↓ HTTPS POST (batched, works offline)
Railway receiver (subway/receiver.py)
        ↓ stores as daily JSON files on Railway volume
pull_gps.py (downloads to local subway/data/gps/)
        ↓
parse_rides.py (GPS accuracy → ride detection) ✅
        ↓ cross-reference with OMNY CSV for validation
rides_enriched.json ✅
        ↓
HofSubways explorer page (TODO — next)
```

### Data Collection Pipeline

- **Overland iOS app**: Free, open-source GPS logger. Runs passively in background, batches points, sends via HTTPS POST. Queues data when offline, sends when connectivity returns.
- **Railway receiver** (`subway/receiver.py`): Python HTTP server accepting Overland's GeoJSON payloads. Stores points in daily JSON files (`/data/gps/YYYY-MM-DD.json`) on a Railway persistent volume. Auth via `?token=` query param.
- **Railway deployment**: Service `subway-data` in the citibot Railway project. Root directory: `subway`, Dockerfile builder. Domain: `subway-data-production.up.railway.app`. Volume mounted at `/data`.
- **Pull script** (`subway/pull_gps.py`): Downloads GPS data from Railway to local `subway/data/gps/`. Usage: `RECEIVER_URL=https://subway-data-production.up.railway.app RECEIVER_TOKEN=yourtoken python3 subway/pull_gps.py`

### Data Sources

1. **Overland GPS data** (primary): Continuous GPS coordinates with timestamps, speed, accuracy, motion state. Stored as daily JSON files on Railway.
2. **OMNY CSV export** (`subway/data/2026-03-27-trailing-12-months-mta-data.csv`, gitignored): 448 trips, Mar 2025 — Mar 2026. Has exact tap timestamps and fares but NO station names. Downloaded from `omny.info`. Used for validation — cross-reference OMNY tap times with GPS data to confirm station detection accuracy.
3. **MTA station data**: ~40 stations hardcoded in `parse_rides.py` (focused on Lex Ave corridor + connecting lines). Covers the user's common routes. Can expand as needed — full GTFS import not required.

### Data Formats

**GPS point** (from Overland, stored in `subway/data/gps/YYYY-MM-DD.json`):
```json
{
  "timestamp": "2026-03-29T14:23:05-04:00",
  "lat": 40.7308,
  "lon": -73.9909,
  "altitude": 10,
  "speed": 0.5,
  "accuracy": 5,
  "battery": 0.85,
  "wifi": null,
  "motion": ["walking"]
}
```

**OMNY CSV** (from `omny.info`):
```csv
Reference,Transit Account #,Trip Time,Mode,Product Type,Fare Amount ($)
4165910775,441062336017,2026-03-26 19:48:55,Subway,PAYGO,$3.00
```

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
  }],
  "summary": {
    "total_trips": 5,
    "total_legs": 6,
    "lines": ["6", "4/5", "R/W"],
    "date_range": ["2026-03-30", "2026-04-02"]
  }
}
```

### GPS Detection Methodology

**Primary signal: GPS accuracy degradation.** When the phone goes underground, GPS accuracy degrades from ~10-20m to 100-964m as the phone falls back to cell tower triangulation. This is the most reliable indicator of being underground. Validated against a known 1-stop ride on the 6 train (Astor Place → Union Square, 2026-03-30 ~9:07-9:08 AM).

**Anatomy of a subway ride (observed from real data):**

| Phase | Duration | Accuracy | Motion | Position |
|-------|----------|----------|--------|----------|
| Walk to station | 2-5 min | 10-25m (normal) | `walking` | Gradual movement toward station entrance |
| Wait on platform | 1-10 min | 14-20m (slightly degraded) | `stationary` | Clusters near station coordinates |
| Train in tunnel | 1-3 min/stop | 44m → 224m → 964m | `[]` (empty) | Coordinate jumps (fake positions from cell towers) |
| Brief station stop | 10-30 sec | 30-80m (partial recovery) | `[]` or `stationary` | Briefly near station coordinates |
| Exit station | — | Recovers to <30m | `walking` | Moves away from station at walking speed |
| Walk from station | 2-10 min | 10-20m (normal) | `walking` | Gradual movement to destination |

**Detection rules:**
1. **Underground = accuracy > 100m.** Surface GPS in Manhattan is reliably 5-25m. Anything above ~100m means the phone lost sky-view GPS.
2. **Entry station** = last cluster of good-accuracy points (~<30m) near a known MTA station before accuracy degrades.
3. **Exit station** = first cluster of good-accuracy points near a known MTA station after accuracy recovers, followed by sustained good accuracy + walking motion away from the station.
4. **Pass-through station** (not exiting) = brief accuracy recovery (10-30 sec) near a station, followed by accuracy degrading again. The phone does NOT start walking away.
5. **Discard low-accuracy positions.** Points with accuracy >100m are cell tower guesses, not real locations. Don't use them for station matching.

### Edge Cases & Gotchas

**1. Multi-stop rides**
The phone regains some signal at every station the train passes through, whether it stops or not. Expected pattern: repeated cycles of accuracy spike (tunnel) → brief recovery (station) → spike again. The key distinction between "passing through" and "exiting" is what happens after the accuracy recovery:
- **Pass-through**: Brief good-accuracy window (10-30 sec), position stays near station, then accuracy degrades again as train enters next tunnel segment.
- **Actual exit**: Sustained good-accuracy window (>1-2 min), position starts moving away from station at walking speed, motion field switches to `walking`.

Detection approach: after each accuracy recovery near a station, wait to see if accuracy degrades again within ~60 seconds. If it does → pass-through. If it stays good → exit.

**2. Long underground walks in stations**
Some stations (14th St-Union Square, Times Square-42nd St, Atlantic Ave-Barclays, Fulton St) have extensive underground concourses. The user may be underground with degraded accuracy for minutes before reaching the platform or after leaving the train. This means:
- The accuracy degradation may start well before the train departs (walking through station).
- The accuracy may not recover immediately after exiting the train (still underground walking to exit).
- The "entry station" and "exit station" should be determined by proximity to known station coordinates, not by the exact moment accuracy degrades/recovers.

Detection approach: within a degraded-accuracy window, look for the points nearest to known stations at the boundaries. The station-snapping algorithm should be tolerant of the phone being underground but walking (not riding) near the start and end.

**3A. Transfers (general)**
A transfer connects two train rides into a single trip. Transfers can happen:
- **Underground**: Walk through connecting tunnels/passageways between platforms. Accuracy stays degraded throughout. Looks like: train ride ends at station → extended period of degraded accuracy with walking-speed position changes → new train ride starts.
- **Above ground**: Exit station, walk on surface to a different station, re-enter. Accuracy fully recovers during the surface walk. Looks like: two separate rides with a walking segment in between.

Data model: A **trip** is the full door-to-door journey. A **leg** is one continuous train ride. A trip can have multiple legs connected by transfers. This matches how people think about subway travel ("I took the subway to work" = 1 trip, even if 2 trains).

Detection approach: if two detected legs are separated by <15 minutes and the exit station of leg 1 is a known transfer point to the entry station of leg 2, group them into one trip.

**3B. Same-platform transfers (express ↔ local)**
The user exits an express train and waits on the same platform for a local (or vice versa). GPS signature: accuracy recovers at a station → extended stationary period (longer than a normal 10-30 sec station stop, likely 2-5 min) → accuracy degrades again as new train departs. The user never changes platforms or walks anywhere.

Detection approach: if a station stop lasts significantly longer than normal (>90 sec?) and the subsequent station sequence shifts from express stops to local stops (or vice versa), flag it as a same-platform transfer. Requires knowing which stations are express vs. local for each line (from GTFS data).

**3C. Direction changes (overshoots)**
The user rides past their intended stop, realizes the mistake, gets off, crosses to the opposite platform, and rides back. GPS signature: station sequence goes in one direction (e.g., uptown: 14th → 23rd → 28th), then a transfer-like pause, then the same stations in reverse order (28th → 23rd → 14th). The line is the same, but direction flips.

Detection approach: if a transfer happens at a station that's on the same line as the previous leg, and the direction reverses, flag it as an overshoot/direction change. Model as two legs within one trip. Requires knowing station ordering per line per direction from GTFS.

**4. Distinguishing subway from other underground scenarios**
False positives to watch for:
- **Basement/underground venues**: Accuracy degrades but no station-to-station movement pattern. Filter by requiring proximity to ≥2 different MTA stations in sequence.
- **Driving through tunnels** (Holland, Lincoln, Brooklyn-Battery): Single accuracy degradation event, no intermediate station pings, positions at tunnel endpoints don't match subway stations.
- **Walking near station entrances**: Brief accuracy blips from passing near subway grates/entrances. Filter by requiring sustained degradation (>30 sec) and movement between stations.

**5. Data quality unknowns (to validate with more data)**
- How reliably does the phone get signal at underground stations? Some deep stations (e.g., 190th St on the A, Roosevelt Island on the F) may not produce usable pings.
- Does Overland continue logging when the phone has no GPS fix at all, or does it only log when it gets some position (even if inaccurate)?
- How does battery saver mode / low battery affect logging frequency? (Note: the 3/29 data showed battery at 5% — logging may be sparser at low battery.)
- Express trains that skip stations: the phone may not get signal recovery at skipped stations. The station sequence will have gaps matching the express pattern — this is actually useful for identifying which line the user is on.

### Build Workflow

1. ~~**Pull GPS data from Railway**~~ ✅ DONE
2. ~~**User downloads fresh OMNY CSV**~~ ✅ DONE
3. ~~**Eyeball the raw GPS data**~~ ✅ DONE — validated against known 6 train ride (Astor Place → Union Sq)
4. ~~**Download MTA GTFS station data**~~ ✅ DONE (hardcoded ~40 stations instead of full GTFS import)
5. ~~**Build station-snapping algorithm** (`subway/parse_rides.py`)~~ ✅ DONE — accuracy-based detection with transfer splitting, line detection, false positive filtering
6. ~~**Validate against OMNY CSV**~~ ✅ DONE — detected ride times match OMNY tap timestamps
7. ~~**Generate `subway/data/rides_enriched.json`**~~ ✅ DONE — 5 trips, 6 legs

8. ~~**Build HofSubways explorer page** (`subway/explore.html`)~~ ✅ DONE — MTA bullet filters, animated routes, per-leg detail cards
9. ~~**Update landing page** (`index.html`)~~ ✅ DONE — HofSubways card with stats and links
10. ~~**Accent color**~~ ✅ DONE — yellow #eab308 (matching MTA branding)

### Key Research Findings

- **Apple privacy.apple.com export**: Does NOT include location history. Significant Locations are on-device only, end-to-end encrypted.
- **Tile tracker**: Bluetooth-only, no GPS. Free tier = zero history, Premium = 30 days. Not useful.
- **Google Timeline**: Unreliable for NYC subway on iPhone. Post-2024 on-device migration made exports inconsistent. iPhone is second-class citizen.
- **Carrier cell tower data**: US carriers won't provide cell tower logs via CCPA requests. Even if available, precision (~200m) can't distinguish nearby stations.
- **Arc App**: Best commercial option ($45/yr) but still can't detect specific subway lines or transfers. 10-20% daily battery drain.
- **Overland + Railway**: Chosen approach. Open source, privacy-first (data goes only to our server), ~2-5% battery/day, GeoJSON output fits our Python pipeline.

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
| Data not showing in HTML | Data injection step was skipped | Re-run Python script to inject JSON into HTML |
| Strava token refresh fails | App deauthorized or tokens corrupted | Delete `.strava_tokens.json`, re-run `fetch_activities.py` (will open browser for re-auth) |
| Strava daily sync not running | launchd agent unloaded or laptop off | `launchctl list \| grep hofner` to check; `launchctl load ~/Library/LaunchAgents/com.hofner.strava-update.plist` to reload |
| Landing page stats stale | Stats in `index.html` are hardcoded | Manually update the card stat values after a sync (not yet automated) |
| Overland not sending data | Token mismatch or endpoint URL wrong | Check Overland app endpoint URL includes `?token=...`; verify Railway service is running at status endpoint |
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

**CLAUDE.md is a living document.** It must stay in sync with reality at all times. Treat it like a co-founder's shared notebook — if something happened, write it down *now*, not later.

### Always Update CLAUDE.md When:

- **New file or directory created** — Add to Project Structure tree
- **File moved, renamed, or deleted** — Update Project Structure + any path references
- **New bug discovered** — Add to Common Issues table with cause + fix
- **Bug fixed** — Update or remove the Common Issues entry
- **Architecture decision made** — Add to Key Architecture Decisions with rationale
- **New data source added** — Add full section (What's Built, Key Stats, Data Formats)
- **New dashboard or feature shipped** — Update the relevant "What's Built" section
- **Script path or behavior changed** — Update Data Pipeline references
- **New API or external dependency** — Document it in the relevant section
- **Mistake made and lesson learned** — Add to Common Issues or a new "Lessons Learned" entry
- **Design pattern established** — Note it so future work follows the same pattern
- **Stats changed** (new rides, new runs, etc.) — Update Key Stats
- **New scheduled job added** — Update Automation section + Landing Page section
- **Project direction shifted** — Update Project Overview
- **New personal preference discovered** — Add to Personal Preferences

### How to Update:

- **Do it inline, immediately** — Don't batch documentation updates. A 30-second edit now saves 10 minutes of confusion for the next Claude instance.
- **Be specific** — Include file paths, numbers, dates, and rationale. Vague notes are useless.
- **Include the "why"** — Future context depends on understanding *why* a decision was made, not just *what* was done.
- **Delete stale info** — Wrong documentation is worse than no documentation. If something is no longer true, remove it or mark it as deprecated.
