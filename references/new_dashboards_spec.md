# New Dashboard Specs: Uber/Lyft, Apple Watch, NYC Subway

## Uber & Lyft Rides

### Data Acquisition

**Uber (Best approach: Privacy Data Download)**
- URL: https://privacy.uber.com/privacy/center
- Format: ZIP with CSV files
- Key fields: Begin Trip Lat/Lng, Dropoff Lat/Lng, addresses, timestamps, fare, distance, product type
- GPS coordinates included for pickup and dropoff
- No route polylines (use OSRM to estimate, same as CitiBike)
- Processing: hours to same day

**Uber (Richest approach: GraphQL scrape)**
- Endpoint: `riders.uber.com/graphql` with browser session cookies
- `Activities` query for paginated ride list, `GetTrip` for individual ride details with waypoints
- Returns route map data, fare/tip breakdown
- Same pattern as our CitiBike GraphQL approach

**Lyft (Best approach: Privacy Data Download)**
- URL: https://www.lyft.com/privacy/home
- Format: ZIP with CSVs + DataDictionary
- Includes ride details, fare breakdown with tips/taxes
- GPS coordinates likely included (privacy policy says they collect "precise location")
- Processing: up to 45 days

### Recommended Pipeline
1. Request Uber privacy download (immediate)
2. Request Lyft privacy download (takes days)
3. Python script to normalize both CSVs into `rides_enriched.json`
4. Geocode any address-only fields via Nominatim
5. Fetch OSRM driving routes for unique pickup/dropoff pairs
6. Bake into static HTML dashboard

### Dashboard Features
- Header stats: total rides, total spent, unique neighborhoods
- Side-by-side route map + heatmap (Leaflet)
- Day x Hour heatgrid
- Monthly rides + monthly spending charts
- Uber vs Lyft breakdown (doughnut)
- Product type breakdown (UberX vs Comfort vs XL)
- Top pickup/dropoff neighborhoods
- Spending trends over time

### Action Items
- [ ] Request Uber data download at privacy.uber.com
- [ ] Request Lyft data download at lyft.com/privacy/home
- [ ] Build `rideshare/parse_data.py` for CSV normalization
- [ ] Build `rideshare/index.html` dashboard

---

## Apple Watch / Apple Health

### Data Acquisition

**Best approach: Native Health Export + Python parsing**
- iPhone > Health app > Profile > Export All Health Data
- Produces ZIP: `export.xml` (main data, can be 500MB+) + `workout-routes/*.gpx` (GPS routes)

**Best for ongoing updates: Health Auto Export app ($5.99/yr)**
- Exports 150+ metrics in JSON/CSV
- Includes workout routes as lat/lon arrays
- Can push to REST API automatically
- Privacy-first, data stays on device

### Key Data Types

**Tier 1 (High-impact dashboard panels):**
- Resting heart rate over time (best single fitness indicator)
- VO2 Max trend (cardio fitness)
- Sleep architecture (Core/Deep/REM/Awake stages)
- Activity Rings (Move/Exercise/Stand daily summaries)

**Tier 2 (Deep dives):**
- Workout timeline with route replay (GPX files)
- Heart rate zones during workouts
- Steps heatmap (day x hour)
- Walking + running distance trends
- Weight trend

**Tier 3 (Interesting deep cuts):**
- Sleep duration vs resting HR correlation
- Training load vs HRV
- Environmental audio exposure
- Heart rate recovery trend

### Data Format Examples

**XML Record (Heart Rate):**
```xml
<Record type="HKQuantityTypeIdentifierHeartRate"
        sourceName="Will's Apple Watch"
        unit="count/min"
        startDate="2025-06-15 08:30:15 -0400"
        value="72"/>
```

**GPX Workout Route:**
```xml
<trkpt lat="40.730287" lon="-73.991432">
  <ele>15.2</ele>
  <time>2025-06-15T12:30:00Z</time>
  <extensions><speed>2.8</speed></extensions>
</trkpt>
```

**ActivitySummary (Daily Rings):**
```xml
<ActivitySummary dateComponents="2025-06-15"
                 activeEnergyBurned="485.2"
                 appleExerciseTime="35"
                 appleStandHours="10"/>
```

### Python Libraries
- `apple-health-parser` (pip3 install) -- full-featured
- `apple-health-extractor` -- converts to JSON/CSV
- DIY: ~50 lines with `xml.etree.ElementTree.iterparse`

### Recommended Pipeline
1. Export from iPhone Health app (one-time)
2. `health/parse_export.py`: XML -> enriched JSON for each metric
3. `health/parse_gpx.py`: GPX files -> route arrays
4. Bake into static HTML dashboards

### Action Items
- [ ] Export Apple Health data from iPhone
- [ ] Build `health/parse_export.py`
- [ ] Build `health/index.html` dashboard (resting HR, VO2, sleep, rings)
- [ ] Consider Health Auto Export app for ongoing updates

---

## NYC Subway

### The Core Problem

**OMNY stripped station names from trip history** after a 2023 privacy scandal (anyone could look up a stranger's station history by credit card number). The data exists internally but is not exposed to users.

Credit card statements only show `MTA*NYCT PAYGO` with no station info.

### Data Acquisition Approaches (Ranked)

**1. Google Maps Timeline (BEST if you have history)**
- Google classifies `IN_SUBWAY` trips with start/end coordinates and transit line info
- Export from phone: Google Maps > Settings > Export Timeline Data
- Critical: Check auto-delete setting NOW (default is 3 months)
- Data includes: entry station, exit station, transit line, timestamps

```json
{
  "activityType": "IN_SUBWAY",
  "transitPath": {
    "transitStops": [
      {"name": "Astor Pl"},
      {"name": "Grand Central-42 St"}
    ],
    "name": "6",
    "hexRgbColor": "#00933C"
  }
}
```

**2. OMNY Timestamps + Google Timeline Hybrid**
- OMNY gives authoritative entry timestamps + fare/cap data
- Google Timeline gives station names
- Cross-reference by timestamp for best accuracy

**3. Manual/Automated Logging (going forward)**
- iOS Shortcut triggered by subway use
- Simple station picker webapp
- Combine with OMNY data for cost tracking

### MTA Open Data (Excellent)
- Station list with coordinates: `data.ny.gov/Transportation/MTA-Subway-Stations/39hk-dx4f`
- GTFS static feed: `rrgtfsfeeds.s3.amazonaws.com/gtfs_subway.zip` (stops, routes, shapes, schedules)
- Subway entrance/exit coordinates: `data.ny.gov/Transportation/MTA-Subway-Entrances-and-Exits-2024/i9wp-a4ja`
- GeoJSON for Leaflet: `github.com/kevin-brown/nyc-open-geojson`
- No API key required

### Exit Station Inference
NYC subway charges on entry only. Best approach:
1. **Next entry = previous exit** (MTA's own method, ~80% accuracy)
2. For last trip of day, assume destination = first entry of day

### Action Items
- [ ] Check Google Maps Timeline on phone — do you have history?
- [ ] Export Google Timeline data immediately
- [ ] Set auto-delete to maximum or off
- [ ] Download MTA station data (CSV + GTFS)
- [ ] Build `subway/parse_timeline.py` to extract IN_SUBWAY segments
- [ ] Build `subway/index.html` dashboard

---

## Phone Location Data

### What's Available

**Google Maps Timeline (if enabled)**
- Now on-device only (since late 2024)
- Auto-deletes after 3 months by default
- Export from phone only, not Google Takeout
- Gives classified activity segments (walking, subway, driving, etc.)

**Apple Significant Locations**
- Settings > Privacy > Location Services > System Services > Significant Locations
- Tracks places you visit frequently
- No native export; third-party app "Significant Locations" ($, iOS 18+) can export CSV/JSON
- Visit-level data (arrivals/departures), not continuous GPS breadcrumbs

**For continuous tracking going forward:**
- **Arc App** (iOS) -- best all-in-one passive tracker, exports JSON/GPX, classifies activities
- **OwnTracks** (open source) -- sends data to your own server
- **Overland** (open source) -- POSTs GeoJSON to your endpoint

### Recommendation
1. Export Google Maps Timeline NOW (before auto-delete)
2. Install Arc App for continuous tracking going forward
3. These feed into subway dashboard and future movement visualizations

---

## Other Ideas (Brainstorm)

### Goodreads Bookshelf
- Export: goodreads.com/review/import (CSV export)
- Fields: title, author, rating, date read, shelves
- Dashboard: reading timeline, genre breakdown, pages/month, author network

### Letterboxd / Netflix Watch History
- Letterboxd: letterboxd.com/settings/data (ZIP export with diary.csv, ratings.csv)
- Netflix: netflix.com/account > Download your data (viewing history CSV)
- Dashboard: watch timeline, genre trends, rating distribution, binge patterns

### Photos / Scrapbooking
- Apple Photos export: Photos app or `osxphotos` CLI tool for metadata
- EXIF data: timestamps, GPS coordinates, camera settings
- Dashboard: photo map (where you've taken photos), timeline, most-photographed locations
