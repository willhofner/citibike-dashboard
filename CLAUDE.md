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

**One-liner**: A personal activity dashboard -- turning CitiBike rides, Strava runs, Uber rides, and Apple Watch data into beautiful, interactive visualizations. And the birthplace of **Burrow** — a fog-of-war city explorer that shows you the shape of your life on a map.

### What We're Building

A personal activity dashboard for visualizing life data. Live with CitiBike (489 rides), Strava (85 runs, 391 miles), Uber (220 rides, $7.7K spent, 23 cities), Apple Watch heart rate (508K readings, 4.5 years), Books (Goodreads library), and Subway (9 trips detected from GPS). This is a personal site for showing friends — not public-facing. Strava data auto-syncs daily.

### The Bigger Vision: Burrow

The dashboards are individual lenses. **Burrow** is the unified view — every mode of transportation painted on one canvas, with fog everywhere you haven't been. It's the GTA fog-of-war mechanic applied to your real city.

The insight: a heatmap shows density ("you go to the East Village a lot"). Burrow shows *coverage* ("you've never set foot in Sunset Park"). One validates habits. The other provokes curiosity.

The name is a double entendre — Borough + burrow. *Breadth yields depth. By fanning out, you burrow down.* There are 6 million people in this city with 6 million different hyperlocal spheres, and every one of them is worth checking out.

**Why it resonates:**
- A dark patch on your map nags at you. You don't need an algorithm to tell you to go there. You just see it and think "huh, I've never been to Red Hook."
- A lack of fog cover is a badge of honor. People who've explored their city wear it in their heads already. Burrow gives it a visual.
- The cloudless island — you take the subway to Prospect Park, spend the day there, subway home. There's a cleared circle around the park, surrounded by fog. But if you *bike* there, there's a tunnel through the fog. The shape of how you got there matters.
- The frustration of a missed recording is real. An uncaptured subway ride means stolen exploration credit. That emotional pull — *I want proof that I left my burrow* — is the product.

**Long-term vision:** A native iOS app. Just allow location access and your fog lifts automatically, regardless of transportation mode. No Overland, no CSV exports, no data pipelines. Universal. Every city. But NYC is the perfect proving ground — the density makes coverage meaningful, and New Yorkers are obsessively proud of knowing their city.

**Current state:** Web prototype live at willhofner.com. Native iOS app in active development — building toward first TestFlight build. Goal: background location tracking + real-time fog-of-war, no data exports needed.

### Tech Stack

- **Frontend**: Vanilla HTML/CSS/JS (no build tools, no frameworks)
- **Maps**: Leaflet.js with OpenStreetMap tiles inverted to dark via a CSS filter on `.leaflet-tile-pane` (switched from CartoDB dark tiles on 2026-09-20 when Carto began requiring an API key). Burrow 3D uses MapLibre + OpenFreeMap vector tiles.
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
├── package.json                # Node deps (serve-handler) + `npm start`
├── server.js                   # Static server with optional HTTP Basic Auth gate (SITE_USER / SITE_PASS env)
├── railway.json                # Railway deployment config (start: node server.js, healthcheck /healthz)
├── citibike/
│   ├── index.html              # HofBikes dashboard (stats, maps, charts, rankings)
│   ├── explore.html            # HofBikes ride explorer (animated bike routes)
│   ├── download_rides.js       # Browser console script to export rides from CitiBike account
│   ├── merge_rides.py          # Merge a new export into a fresh dated raw file (dedupes by rideId)
│   ├── build_pages.py          # Bake rides_enriched.json + routes.json into index.html / explore.html + landing card
│   ├── parse_rides.py          # Raw JSON → enriched JSON processor
│   ├── fetch_routes.py         # OSRM bike route fetcher for station pairs
│   └── data/
│       ├── citibike_rides_2026-09-20.json   # Raw ride data from GraphQL export (489 rides, newest file wins)
│       ├── rides_enriched.json              # Processed rides with coordinates + metadata
│       ├── routes.json                      # OSRM bike routes for 125 unique station pairs
│       └── station_coords.json              # Station name → lat/lon mapping from GBFS
├── strava/
│   ├── index.html              # HofRuns run explorer (animated routes, heatmap, timelapse)
│   ├── dashboard.html          # HofRuns dashboard (stats, charts, trends, rankings)
│   ├── fetch_activities.py     # OAuth + Strava API data fetcher (supports --incremental)
│   ├── build_dashboard.py      # Builds static HTML with baked-in data
│   ├── build_dashboard_stats.py # Builds dashboard stats
│   ├── update_strava.sh        # Full pipeline: fetch → build → commit + push (API path, dead while the app is inactive)
│   ├── ingest_web.py           # Merge a website-session export (no API) into activities_enriched.json
│   └── data/
│       ├── .strava_tokens.json          # OAuth tokens (gitignored)
│       ├── .strava_secrets.json         # Client ID + secret (gitignored, read by fetch_activities.py)
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
├── burrow/
│   ├── index.html              # Burrow — fog-of-war city explorer (unified map, all modes)
│   └── Burrow/                 # Native iOS app (SwiftUI + MapKit + Core Location)
│       ├── Burrow.xcodeproj/   # Xcode project
│       ├── Burrow/             # App source
│       │   ├── BurrowApp.swift         # App entry point
│       │   ├── LocationManager.swift   # Core Location manager (background tracking)
│       │   ├── LocationStore.swift     # SwiftData persistence for coordinates
│       │   ├── FogOverlay.swift        # Custom MKOverlay for fog rendering
│       │   ├── FogOverlayRenderer.swift # Core Graphics fog renderer (draws fog + clips holes)
│       │   ├── MapView.swift           # UIViewRepresentable wrapping MKMapView
│       │   ├── ContentView.swift       # Main SwiftUI view (map + coverage %)
│       │   └── Assets.xcassets/        # App icons and colors
│       └── Info.plist                  # Privacy descriptions + background modes
├── timelapse/
│   ├── index.html              # HofLapse — unified timelapse of every mode (play, scrub, step by day)
│   ├── build_events.py         # Builds the compact event feed from every mode's enriched data
│   └── data/events.json        # 731 trips with downsampled paths (~1.5 MB), sorted by start time
└── references/
    ├── index_redesign.html     # Landing page redesign draft
    ├── tweet_animation/
    └── new_dashboards_spec.md  # Specs for Uber/Lyft, Apple Watch, Subway dashboards
```

---

## Key Architecture Decisions

- **Static JSON, no server**: Explorers fetch enriched JSON at runtime via `fetch()`. Dashboards have data baked in at build time via Python. No backend needed.
- **Password gate (2026-09-20)**: `server.js` serves the static tree and, when `SITE_USER` and `SITE_PASS` are set on the Railway service, requires HTTP Basic Auth on every path except `/healthz`. With the variables unset the site is open, so a deploy can never lock anyone out. It also sends `X-Robots-Tag: noindex`. Rationale: the site publishes home-adjacent GPS traces and addresses; it is meant for friends, not the open web.
- **One Strava sync path**: the GitHub Action is the source of truth. The local launchd job committed the same files separately from April to June 2026 and its pushes stopped landing, which forced a manual merge on 2026-09-20. Unload the launchd agent (`launchctl unload ~/Library/LaunchAgents/com.hofner.strava-update.plist`) or expect the histories to diverge again.
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
   - `merge_rides.py`: Merges a fresh export into a new dated raw file, deduping by `rideId`
   - `build_pages.py`: Bakes enriched rides + routes into both HTML pages and refreshes the landing card stats. **Run after every data refresh** — the pages do not fetch JSON at runtime.
   - Data source: GraphQL endpoint `account.citibikenyc.com/bikesharefe-gql` (no official API exists)
   - Refresh flow (2026-09-20): log into account.citibikenyc.com/ride-history, run the export logic with a cutoff of the newest known `startTimeMs`, then `merge_rides.py new.json` → `parse_rides.py` → `fetch_routes.py` → `build_pages.py`
   - Known gotcha: the GraphQL list endpoint returns the cursor ride again on the next page, so exports contain duplicates. The original 2026-02-27 export had 31 duplicate rides (318 entries, 287 unique). Always dedupe by `rideId`.

### Key Stats

- 489 rides, Sep 2024 — Sep 2026 (refreshed 2026-09-20)
- $640.47 total spent, 57.1 hours on bikes
- 80 unique stations, 125 unique routes
- 39% ebike rides (2026 is almost all classic: 16 ebike of 202)
- Home bases: Cooper Square & Astor Pl (129 starts), Lafayette St & E 8 St (128), Broadway & E 19 St (120)

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
   - Client secret lives in `strava/data/.strava_secrets.json` (gitignored) or the `STRAVA_CLIENT_SECRET` env var. It was hardcoded in `fetch_activities.py` and committed to the public repo until 2026-09-20; that secret must be treated as burned and rotated when the Strava app is recreated.
   - `build_dashboard.py`: builds static HTML with data baked in
   - `update_strava.sh`: full pipeline script (fetch → build → commit + push)

3. **Automation**
   - macOS launchd agent: `~/Library/LaunchAgents/com.hofner.strava-update.plist`
   - Runs daily at 9 PM, catches up on wake if missed
   - Logs: `strava/data/.update.log`, `strava/data/.launchd_stderr.log`
   - Manual: `./strava/update_strava.sh` (or `--full` to re-fetch everything)

### Strava API Setup

- **Status (2026-09-20)**: Strava set app 206236 to **Inactive** and now gates API access behind a paid subscription ("API access is subscriber-only"). Every API call returns 403. The nightly launchd job and GitHub Action have failed since 2026-08-18. Will does not want the subscription for this, so **the API path is retired** in favor of the website-session path below. Last API sync: 2026-06-28.

### Website-session refresh (current path, no API, no subscription)

Strava's own site endpoints answer with a logged-in browser session:
- `GET /athlete/training_activities?page=N&per_page=20` — activity list (`start_date_local_raw`, `distance_raw`, `moving_time_raw`, `elevation_gain_raw`, `sport_type`)
- `GET /activities/<id>/streams?stream_types[]=latlng&stream_types[]=time&stream_types[]=heartrate&stream_types[]=distance&stream_types[]=altitude&stream_types[]=velocity_smooth` — full streams (HR only when the recording had it)
- `GET /activities/<id>` HTML — calories are scraped from the stats table

Flow: log into strava.com in a browser, run the collector (page through the list until `start_date_local_raw` reaches the newest known activity, then fetch streams per activity, ~0.5s apart), save the payload as `strava/data/web_export_<date>.json` (gitignored), then `python3 strava/ingest_web.py <file>` → `build_dashboard.py` → `build_dashboard_stats.py` → update the landing HofRuns card. `ingest_web.py` encodes the polyline itself, derives per-mile splits and best efforts from the distance/time streams, and never overwrites a record the API produced (those carry gear and official splits). Records from this path have `"source": "strava-web"`.

First web refresh 2026-09-20: 27 new runs since June 28 → 234 activities, 144 runs, 663 mi.
- **App ID**: 206236
- **OAuth callback**: `http://localhost:8888/callback`
- **Scopes**: `read,activity:read_all`
- **Rate limits**: 100 read requests/15min, 1,000/day
- **Token refresh**: automatic via saved refresh token

### Key Stats

- 234 total activities, 144 runs (refreshed 2026-09-20 via the website session)
- 663 miles total running distance, 109.4 hours
- 4.6 mi average run, 18.5 mi longest run (NYRR 18M), 9:53/mi average pace
- Date range: Apr 2021 — Sep 2026
- All runs have GPS routes (latlng streams) and polylines

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

- 15 trips, 17 legs (re-parsed 2026-09-20 from 14 GPS days)
- Lines: 6, 4/5, R/W
- Key stations: Astor Place, Union Sq, 8th St-NYU, Canal St, Grand Central
- Date range: Mar 30 — May 30, 2026
- GPS collection: Overland stopped posting after 2026-05-31 (52,648 points across 14 days on Railway). The app needs to be re-enabled on the phone for new data.

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

## Burrow (Fog-of-War City Explorer)

### The Idea

Every run you've taken, every bike ride, every subway exit, every Uber drop-off — they all paint on the same canvas. Everywhere you've been lifts the fog. Everywhere you haven't is dark. You open Burrow and you see *your* New York. The shape of your life on a map.

This isn't a heatmap. A heatmap shows where you go a lot. Burrow shows where you've *never been*. The dark patches are the product. They nag at you. They make you want to go.

### What's Built

1. **Fog Map** (`burrow/index.html`)
   - Full interactive Leaflet map of NYC covered in fog overlay
   - Zoom constrained to NYC bounds (can't zoom out to other cities)
   - All transportation data unified on one canvas
   - Fog cleared along routes and around stations with configurable radii
   - Coverage % stat for Manhattan
   - Accent color: emerald #10b981

### Defogging Rules (by transportation mode)

Each mode of transportation clears fog differently based on how much of the city you actually *experience* while traveling:

| Mode | Defogging Style | Default Radius | Rationale |
|------|----------------|----------------|-----------|
| **Running** (Strava) | Trail — fog cleared along full GPS trace | 80m (one block each side) | You're above ground, taking in the city at human speed |
| **Biking** (CitiBike) | Trail — fog cleared along OSRM route | 80m (one block each side) | Above ground, eyes open, experiencing the streets. Note: routes are OSRM shortest-path estimates, not actual GPS — a known limitation |
| **Subway** (MTA) | Dumbbell — circles at entry + exit stations only | 500m (~2 long blocks) | You didn't see anything underground. But you emerged somewhere and explored. Wide radius acknowledges the walking you did after exiting |
| **Uber** | Dumbbell — circles at pickup + dropoff only | 500m (~2 long blocks) | "Counting above-ground Uber travel would be stolen valor." You arrived somewhere, that's what counts |

All radii are system configs — adjustable on the fly to experiment with what feels "vibe-accurate" without redeploying.

**Future consideration:** Ubers and above-ground subway segments could get a very slim trail radius to show you passed through, but for MVP they're dumbbells only.

### Data Sources (for web prototype)

- **Strava**: `activities_enriched.json` → `latlng` arrays (actual GPS traces, highest fidelity)
- **CitiBike**: `rides_enriched.json` → start/end stations, `routes.json` → OSRM route coordinates keyed by `startStation|endStation`
- **Uber**: `rides_enriched.json` → start/end lat/lon (NYC rides only, 83 of 220), `routes.json` → OSRM route coordinates keyed by ride ID
- **Subway**: `rides_enriched.json` → entry/exit station lat/lon per leg (9 trips, 11 legs)

### Coverage Metrics

- **Coverage %**: Grid cells visited / total grid cells within borough boundary
- **Grid granularity**: ~50m cells — fine enough to reward exploring a new block, coarse enough to not be creepy
- Potential future scores: per-borough breakdown, depth score (how concentrated is your daily radius), exploration streaks

### The North Star: Native iOS App

The web prototype proves the visual. The real product is a native app where you just allow location access and your fog lifts automatically. No data exports, no CSV parsing, no Overland crashes. The frustration of a missed subway ride — riding home from 96th St on the 1/2/3, transferring at 42nd to the NRQW, finishing at 8th Ave, and none of it recorded — that frustration disappears. Every step counts. Every exploration gets credit.

---

## Burrow iOS App

### Status: Active Development (April 2026)

Building the native iOS app — the "North Star" described above. Web prototype proved the visual works. Now shipping a TestFlight MVP so the founder can dog-food real-time fog-of-war exploration on his phone.

### MVP Scope (TestFlight v0.1)

The app does exactly three things:
1. **Collects location in the background** — even when the app is closed or phone is locked
2. **Stores every coordinate locally on-device** — no server, no accounts, no syncing
3. **Renders the fog map with defogged trails** — when you open the app, you see where you've been

That's it. No historical data import, no transportation mode detection, no social features. Just your phone, your GPS, your map.

### Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **UI** | SwiftUI | Fastest path for a one-person team |
| **Maps** | MapKit (`MKMapView` via `UIViewRepresentable`) | Native performance, dark map style built-in, proper overlay system for fog rendering |
| **Location** | Core Location (`CLLocationManager`) | `allowsBackgroundLocationUpdates` + "Always" authorization = GPS points even when app is killed |
| **Persistence** | SwiftData | On-device storage for location coordinates. Simple model, no server needed |
| **Fog rendering** | Core Graphics in custom `MKOverlayRenderer` | Draw filled fog rect, then `CGContext.clear()` circles/trails along the path. Same concept as web canvas clipping, different API |

**Why not MapboxGL or Leaflet in a WebView?** Native MapKit gets smoother performance, proper background location permission UX, and App Store reviewers won't flag it. WebView-based maps in a native shell creates friction with background location justification.

### Architecture

```
┌─────────────────────────────────────────────┐
│  ContentView (SwiftUI)                      │
│  ┌─────────────────────────────────────┐    │
│  │  MapView (UIViewRepresentable)      │    │
│  │  ┌───────────────────────────────┐  │    │
│  │  │  MKMapView                    │  │    │
│  │  │  + FogOverlay (MKOverlay)     │  │    │
│  │  │  + FogOverlayRenderer         │  │    │
│  │  └───────────────────────────────┘  │    │
│  └─────────────────────────────────────┘    │
│  Coverage: 2.3% of Manhattan                │
└─────────────────────────────────────────────┘
        │                       │
        ▼                       ▼
┌──────────────┐    ┌──────────────────────┐
│ LocationManager │  │ LocationStore        │
│ (Core Location) │  │ (SwiftData)          │
│ - Always auth   │  │ - LocationPoint model│
│ - Background    │  │ - lat, lon, timestamp│
│   updates       │  │ - accuracy           │
│ - Significant   │  │                      │
│   change monitor│  │ Coverage calculator  │
└──────────────┘    │ - 50m grid cells     │
                    │ - Manhattan boundary  │
                    └──────────────────────┘
```

### Key Files

| File | Purpose |
|------|---------|
| `BurrowApp.swift` | App entry point, SwiftData container setup |
| `LocationManager.swift` | `CLLocationManager` wrapper — requests "Always" permission, receives background updates, feeds locations to store |
| `LocationStore.swift` | SwiftData `@Model` for `LocationPoint` (lat, lon, timestamp, accuracy). Query interface for fog rendering |
| `FogOverlay.swift` | `MKOverlay` subclass — defines the overlay's bounding rect (all of NYC) |
| `FogOverlayRenderer.swift` | `MKOverlayRenderer` subclass — Core Graphics rendering: fill fog, clip circles along stored paths |
| `MapView.swift` | `UIViewRepresentable` wrapping `MKMapView` — needed because SwiftUI's `Map` doesn't support custom overlay renderers |
| `ContentView.swift` | Main view — full-screen map + coverage % label overlay |
| `Info.plist` | `NSLocationAlwaysAndWhenInUseUsageDescription`, `NSLocationWhenInUseUsageDescription`, `UIBackgroundModes: [location]` |

### Location Permission Flow

Apple's "Always" location permission is a two-step process:

1. **First ask** → user sees "Allow While Using App" / "Allow Once" / "Don't Allow" (no "Always" option)
2. **After granting "While Using"** → system prompts again later to upgrade to "Always"
3. Can trigger the upgrade prompt programmatically after initial grant

For TestFlight, testers will grant it. For App Store eventually, need to demonstrate value first — show the fog, let them walk with "While Using", then pitch the upgrade.

### Privacy Strings

```
NSLocationAlwaysAndWhenInUseUsageDescription:
"Burrow tracks your location to reveal the parts of the city you've explored, even when the app is closed."

NSLocationWhenInUseUsageDescription:
"Burrow uses your location to show where you are on the map and lift the fog as you explore."
```

### Defogging Rules (MVP)

For the native app, every GPS point defogs the same way — no transportation mode detection needed:

| What | How | Radius |
|------|-----|--------|
| **Every GPS point** | Circle cleared around coordinate | 80m (one block each side) |
| **Connected points** | Trail cleared between consecutive points within 5 min | 80m wide trail |
| **Stale gaps** | Points >5 min apart = separate circles, no connecting trail | Prevents false trails across subway rides or drives |

This is simpler than the web version's per-mode rules. The native app doesn't know *how* you traveled — it just knows *where you were*. And that's fine for MVP. The shape of your path emerges naturally from GPS density.

### Coverage Calculation

- **Grid**: ~50m cells overlaid on Manhattan (same as web prototype)
- **Manhattan boundary**: Polygon defining the borough outline
- **Coverage %**: cells with ≥1 GPS point / total cells within boundary
- **Future**: Brooklyn toggle (re-center map, different boundary polygon), global view

### TestFlight Deployment

1. **Prerequisites**: Apple Developer account ($99/year), Xcode, valid provisioning profile with Background Modes (Location) entitlement
2. **Build**: Archive in Xcode (Product → Archive)
3. **Upload**: Send to App Store Connect via Xcode organizer
4. **Review**: Apple reviews TestFlight builds (usually <24 hours)
5. **Install**: Add testers in App Store Connect → install via TestFlight app

### Future iOS Features (Post-MVP)

- **Historical data import**: Pull in web prototype data (Strava GPS traces, CitiBike routes, etc.) to seed the map
- **Borough toggle**: Brooklyn, Queens, Bronx, Staten Island — each with its own coverage %
- **Global mode**: Full globe covered in fog, defog as you travel anywhere
- **Transportation mode detection**: Use `CMMotionActivityManager` to detect walking/running/cycling/driving
- **Exploration streaks**: Consecutive days with new coverage
- **Share card**: Screenshot-ready view of your fog map for sharing

---

## HofLapse (Unified Timelapse)

### What's Built (2026-09-20)

1. **Timelapse page** (`timelapse/index.html`)
   - One Leaflet map, a virtual clock, and every trip drawn in the order it happened: runs (orange), CitiBike (blue), subway (yellow, dashed), Uber NYC (purple)
   - Play/pause, speed from 0.25 to 30 days per second, a scrubber across the whole timeline, ← → to step a day, space to play
   - Each trip animates as a bright trace with a moving dot, then settles into a faint persistent line, so the map accumulates like the HofRuns timelapse
   - HUD: current date, per-mode counters (click to hide a mode), miles on the map; "now playing" card with the trip's label
   - Runs outside NYC still play but the map stays framed on the city

2. **Data feed** (`timelapse/build_events.py` → `timelapse/data/events.json`)
   - Runs: Strava `latlng` downsampled to ≤160 points. Bikes: OSRM route for the station pair. Subway: entry → intermediate stations → exit. Uber: OSRM driving route, NYC rides only
   - Times are local wall-clock seconds so all modes sort together (Strava's local-time-with-Z quirk is handled here)
   - **Run after any data refresh**, then the page picks it up at load (fetched at runtime, not baked in)

## Landing Page

The landing page (`index.html`) has two sections:

1. **Activity cards**: 2-column grid with Burrow, HofLapse (full width), HofBikes, HofRuns, HofRides, HofSubways, HofWalks, HofBeats, and HofReads. Each card has icon, badge (Live/New), brand, description, key stats, and links to explorer + dashboard. Stats are currently hardcoded — not auto-updated by the sync pipeline. Burrow is the first card — it's the unified view that ties everything together.

2. **Scheduled Jobs**: A footer section listing all recurring automated jobs (currently just Strava Sync — daily at 9 PM). Green dot = active. Update this section when new scheduled jobs are added.

---

## Design Principles

1. **Ship fast** -- Iterate quickly, get feedback early
2. **Keep it simple** -- No build tools, no frameworks, static HTML files
3. **Own your data** -- Everything runs locally, no third-party services required
4. **Data tells the story** -- Let the numbers speak
5. **Personal first** -- This is for one user's data, not a platform
6. **Dark theme** -- All UI uses the dark color scheme (--bg: #0a0a0f). Accent colors: Burrow=emerald #10b981, HofBikes=blue #3b82f6, HofRuns=orange #f97316, HofRides=purple #a855f7, HofWalks=green #22c55e, HofBeats=red #ef4444, HofSubways=yellow #eab308
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
| Landing page stats stale | Stats in `index.html` are hardcoded | HofBikes card is updated by `citibike/build_pages.py`; the others still need manual edits |
| Site asks for a password | `SITE_USER` / `SITE_PASS` are set on Railway | Intended. Remove the variables to open the site |
| `git push` rejected (non-fast-forward) | launchd and the GitHub Action both committed Strava data | Merge and take the union of activities; keep only the Action running |
| Overland not sending data | Token mismatch or endpoint URL wrong | Check Overland app endpoint URL includes `?token=...`; verify Railway service is running |
| Railway GPS data lost on redeploy | Volume not mounted | Ensure Railway volume is mounted at `/data` in service settings |
| GPS data not pulling locally | Env vars not set | Run with `RECEIVER_URL=... RECEIVER_TOKEN=... python3 subway/pull_gps.py` |
| Map tiles look wrong / light | Tile pane CSS filter missing or provider changed | All Leaflet pages use `tile.openstreetmap.org` with `invert(1) hue-rotate(180deg)` filter for dark; Burrow flat uses the same tiles unfiltered (light) |
| Strava sync 403 on every call | Strava app Inactive; API is now subscriber-only | Use the website-session refresh (Strava section). Do not pay for the API |
| CitiBike ride count too high | GraphQL pagination repeats the cursor ride on each page | `merge_rides.py` dedupes by `rideId`; never trust raw export counts |

---

## Personal Preferences

- **NEVER edit `thoughts.md`** -- This is the user's personal journal. Read-only inspiration, not instruction. Some entries are the most valuable creative direction he's ever discovered; others are contradictory, unrelated, or exploratory. Treat contents as context and motivation, never as specs. Do not write to, append to, or modify this file under any circumstances.
- **Always use `python3`** -- Never `python`
- **Always use `pip3`** -- Never `pip`
- **NEVER use port 5000 on macOS** -- Conflicts with AirPlay Receiver. Use 8000+.
- **Git workflow**: "merge", "ship", "push", "commit" all mean the same thing — commit all changes + push to GitHub. Don't ask which one they meant.
- **Web searches require NO approval** -- Search freely, report findings.
- **Always validate HTML pages with headless browser before presenting to user** -- Use Playwright (`python3 -m playwright`) to load the page, check for JS errors, verify elements render. Start a local server (`python3 -m http.server 8080`), load the page with `wait_until='networkidle'`, check console errors, verify key elements exist. Playwright is installed (`pip3 install --break-system-packages playwright && python3 -m playwright install chromium`).
- **Screenshot every Burrow UI change** -- After any visual edit to `burrow/index.html`, take a Playwright screenshot and save to `burrow/screenshots/NNN-description.png` with incrementing number. Check existing files for next number. This tracks the visual evolution over time. The screenshots folder is gitignored.

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
