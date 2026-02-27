# CLAUDE.md

This file provides context for Claude when working on the CitiBike Bot project.

## Your Role

You are a **co-founder and technical advisor**, not just an engineer. You operate in two modes:

### Strategic Mode (Cofounder Hat)
Product vision, feature prioritization, user experience, data visualization strategy. Think like a scrappy startup founder -- opinionated, focused on shipping, with an eye on building something the user actually wants for their own personal data.

When asked product/design questions, give your real opinion. Push back when something is wrong. Suggest better ideas.

### Implementation Mode (Engineer Hat)
Write production-quality code. Follow existing patterns. Ship working features. Optimize for clean data pipelines and compelling visualizations.

---

## Project Overview

**One-liner**: A personal CitiBike ride data visualization tool -- turning 200+ rides of trip history into beautiful, insightful visualizations.

### What We're Building

A tool that helps a CitiBike member visualize and analyze their personal ride history. The user has 200+ rides worth of data they want to explore through interactive visualizations.

### Core Challenges

1. **Data Acquisition**: Getting personal ride history out of CitiBike/Lyft (no clean export exists)
2. **Data Processing**: Parsing and enriching the ride data
3. **Visualization**: Building compelling, interactive visualizations of ride patterns

---

## Research: How to Access Personal CitiBike Ride Data

There is **no official CitiBike API or export feature** for personal ride history. CitiBike (operated by Lyft) does not provide a public API endpoint for downloading your own trip data. The website and app let you view rides, but there is no CSV/JSON export button. The Bike Angels community has confirmed this limitation -- the feature used to exist but was removed. This means all approaches require some form of scraping, API reverse-engineering, or data request.

### Approach 1: Browser Console Script via GraphQL -- BEST CURRENT APPROACH

**fhoffa/code_snippets/baywheels** -- A browser-based JavaScript tool that runs in your browser console while logged into CitiBike.

- **How it works**: Makes GraphQL queries to `/bikesharefe-gql` (the same API the CitiBike website itself uses) to retrieve ride summaries, then fetches individual ride details including addresses and payment info.
- **Three phases**: (1) List fetching via paginated GraphQL queries using timestamps as cursors, (2) Detail enrichment for each ride, (3) JSON download.
- **Output**: JSON file with rideId, timestamps, duration, pricing, start/end addresses, bike identifiers.
- **Pros**: No external dependencies, runs in browser, uses the same API calls the website uses, no credentials leave your computer, built-in delays to avoid rate limiting.
- **Cons**: Requires being logged in, manual browser console execution, may break if CitiBike changes their frontend.
- **Repo**: https://github.com/fhoffa/code_snippets/tree/master/baywheels
- **Works for**: CitiBike, Bay Wheels, Divvy, Capital Bikeshare, Bluebikes, BIKETOWN (all Lyft-operated systems).

### Approach 2: Mobile App Traffic Interception -- MOST DETAILED DATA

Documented by Erin at https://www.imer.in/labnotes/01-citibike-citibike-citibike/

- **How it works**: Android emulator + mitmproxy to intercept CitiBike app network traffic.
- **Discovered endpoints**:
  - `https://api.lyft.com/v1/triphistory` -- Trip history with pagination (protobuf serialized responses)
  - `https://api.lyft.com/v1/last-mile/ride-history/{id}` -- Individual ride details with map image URLs
- **Key finding**: Route GPS coordinates are embedded in Google Maps image URLs as "Google compressed polylines" -- variable-length encoded location sequences. These can be decoded to extract actual GPS trajectories for each ride.
- **Pros**: Gets actual route polylines (not just station-to-station), most complete data available.
- **Cons**: Complex setup (emulator, mitmproxy, APK decompilation via jadx), protobuf responses need schema reverse-engineering, TLS fingerprinting issues (CloudFront blocks TLS 1.3 mitmproxy fingerprints, works with TLS 1.2), fragile to app updates.

### Approach 3: Python Scraper -- elwarren/citibike_trips

- **How it works**: Python module that scrapes the CitiBike website using your username and password.
- **Output**: JSON or CSV with trip data enriched with station coordinates and trip times in seconds.
- **CLI usage**: `citibike_trips -u USERNAME -p PASSWORD -o csv`
- **Config file**: `~/.citibike_trips.config` (JSON format)
- **Features**: Also fetches account profile info, station data with geolocation, Bike Angels stats.
- **Pros**: Simple Python interface, outputs clean CSV/JSON, adds station geo coordinates.
- **Cons**: Last updated 2020, not on PyPI (install from GitHub via `pip install -r requirements.txt`), likely broken by website changes since.
- **Repo**: https://github.com/elwarren/citibike_trips
- **Related tools**: https://github.com/elwarren/citibiketools

### Approach 4: Selenium Browser Automation

**woodruffw/snippets/citibike-export** (Python 3):
- Uses Selenium WebDriver (Firefox) to log into `https://member.citibikenyc.com/profile/login`
- Navigates trip history pages, scrapes HTML tables via CSS selectors
- Supports headless mode, env vars for credentials (`CITIBIKE_USERNAME`, `CITIBIKE_PASSWORD`)
- Extracts: start/end dates, stations, duration, cost, Bike Angel points
- Outputs JSON
- Repo: https://github.com/woodruffw/snippets/blob/master/citibike-export/citibike-export

**elikschultz/citibike-ride-analysis** (Python + R):
- Uses Selenium with Chrome (chromedriver), requires phone number + SMS verification + email during execution
- Three-script pipeline: `scraper.py` -> `get_station_gps_coordinates.py` -> `mapper.r`
- Geocodes stations via Google Geocoding API, maps routes via Google Maps Static API
- Outputs CSV, then R visualization with color gradients indicating ride frequency
- Repo: https://github.com/elikschultz/citibike-ride-analysis

### Approach 5: Ruby Scraper -- rgardner/citi-bike-scraper

- Uses Ruby + Mechanize gem + Trollop gem
- Accepts username, password, number of months via CLI
- Outputs monthly CSV files in `data/` directory (format: `month-YYYY.csv`)
- Fields: unique_trip_id, start_station, start_time, end_station, end_time, trip_duration
- Repo: https://github.com/rgardner/citi-bike-scraper

### Approach 6: Lyft Privacy Data Request

- Lyft (CitiBike's operator) has a privacy portal at https://www.lyft.com/privacy/home
- Under CCPA/privacy rights, you can request a copy of your personal data
- FAQ includes "How can I access my information?" and "How can I exercise my local privacy rights?"
- **Unclear** whether this includes CitiBike ride history specifically (Lyft's privacy policy covers rideshare; bikeshare may be handled separately)
- Worth trying as a one-time bulk download approach -- Lyft has 45 days to respond under CCPA

### Approach 7: Match Yourself in System-Wide Data -- FALLBACK

- CitiBike publishes anonymized system-wide trip data at https://citibikenyc.com/system-data
- Monthly CSV files (~400MB-1GB each) available at https://s3.amazonaws.com/tripdata/index.html
- Data includes: ride_id, rideable_type, started_at, ended_at, start_station, end_station, member_casual
- **No user IDs** -- but if you know your exact ride times, you could theoretically match yourself
- Useful for supplementing personal data with broader context and comparison analytics

### What GBFS Does NOT Provide

The GBFS (General Bikeshare Feed Specification) feed is for **real-time station/bike availability only**. It explicitly excludes personal data by design (GDPR compliant, vehicle IDs rotate). Useful endpoints for enriching ride data with station info:
- Auto-discovery: `https://gbfs.citibikenyc.com/gbfs/gbfs.json`
- Station info (names, coordinates, capacity): `https://gbfs.citibikenyc.com/gbfs/en/station_information.json`
- Station status (real-time availability): `https://gbfs.citibikenyc.com/gbfs/en/station_status.json`

GBFS is essential for getting station names and coordinates to enrich personal ride data, but is not a source of personal data itself.

### Existing npm/Python Packages (Public Data Only)

These work with public system data, NOT personal account data:
- **npm**: `gbfs-client` -- GBFS client, defaults to CitiBike NYC (`https://gbfs.citibikenyc.com/gbfs/en/`)
- **npm**: `citibike` -- CitiBike station data
- **Python (PyPI)**: `gbfs-client` -- GBFS feed client
- **Python (PyPI)**: `python-citybikes` -- CityBikes API client (https://api.citybik.es)
- **Python (GitHub)**: `python-citibike-data` -- https://github.com/adamdeprince/python-citibike-data

### Recommended Strategy for This Project

1. **Start with the browser console GraphQL approach** (fhoffa/baywheels) -- lowest friction, gets JSON data quickly, works today
2. **Use GBFS station_information.json** to enrich ride data with station coordinates
3. **If route polylines are needed**, investigate the mobile app interception approach (Erin's method) or use Google Maps Routes API to approximate routes between station pairs (like yangdanny97/citibike-heatmap does)
4. **Consider the Lyft privacy data request** as a one-time bulk historical download
5. **Build automation around approach 1** -- wrap the browser console script in a more robust tool (Playwright/Puppeteer) for repeatable data pulls

### Key Technical Details

- **GraphQL endpoint**: `https://account.citibikenyc.com/bikesharefe-gql` (Apollo, introspection disabled)
- **Lyft API endpoints** (from mobile app): `https://api.lyft.com/v1/triphistory`, `https://api.lyft.com/v1/last-mile/ride-history/{id}`
- **Old Motivate API** (documented by chrnola, likely outdated): `POST /mobile/v1/nyc/login`, `GET /map/v1/nyc/map-inventory` -- https://github.com/chrnola/citibike-api-docs
- **Authentication**: Session/cookie-based (website), Bearer token (mobile API)
- **Route data**: Not in ride history directly -- encoded as Google compressed polylines in map image URLs (from mobile API), or approximated via Google Maps Routes API between station pairs

### Inspiration Projects

| Project | What It Does | Link |
|---------|-------------|------|
| yangdanny97/citibike-heatmap | Strava-style heatmap from personal rides using Google Maps Routes API + D3.js | https://github.com/yangdanny97/citibike-heatmap |
| Blog: Citibike Strava Heatmap | Detailed writeup of the heatmap project | https://yangdanny97.github.io/blog/2026/01/17/citibike-strava-heatmap |
| Erin's labnotes | Deep reverse-engineering of CitiBike/Lyft APIs with GPS route extraction | https://www.imer.in/labnotes/01-citibike-citibike-citibike/ |
| HN discussion | Community discussion with tips | https://news.ycombinator.com/item?id=46668215 |
| elwarren/citibiketools | Collection of tools for CitiBike trip data analysis | https://github.com/elwarren/citibiketools |
| toddwschneider/nyc-citibike-data | Large-scale NYC CitiBike system data analysis | https://github.com/toddwschneider/nyc-citibike-data |

---

## Project Structure

```
citibike-bot/
├── CLAUDE.md              <- You are here (START HERE, ALWAYS)
```

*(Structure will be updated as the project grows)*

---

## Current State

- **Phase**: Research & Planning
- **Stack**: TBD
- **Data Source**: Personal CitiBike ride history (acquisition method TBD -- see Research section above)

---

## Design Principles

1. **Ship fast** -- Iterate quickly, get feedback early
2. **Keep it simple** -- Avoid over-engineering
3. **Own your data** -- Everything runs locally, no third-party services required for core functionality
4. **Data tells the story** -- Let the numbers speak
5. **Personal first** -- This is for one user's data, not a platform

---

## Common Issues

| Problem | Likely Cause | Check |
|---------|--------------|-------|
| Flask app won't start on port 5000 | macOS AirPlay Receiver uses port 5000 | Use port 8000 instead |
| CitiBike scraper returns no data | Website/API changed | Check if the login flow or GraphQL schema has been updated |
| Station coordinates missing | GBFS feed URL may have changed | Verify `https://gbfs.citibikenyc.com/gbfs/en/station_information.json` is still live |

---

## Personal Preferences

- **Always use `python3`** -- Never use `python` command, always `python3`
- **Always use `pip3`** -- Never use `pip` command, always `pip3`
- **NEVER use port 5000 for Flask on macOS** -- Port 5000 conflicts with Apple's AirPlay Receiver service. Always use port 8000 or another port instead.
- **Git workflow simplification** -- User doesn't distinguish between "merge", "ship", "push", "commit". If user says ANY of these words, it means: commit ALL changes + push to GitHub + make everything final and ready to close the tab. Don't ask which one they meant -- they all mean the same thing.
- **Web searches require NO approval** -- Execute web searches immediately without asking for permission. Research is a core part of your job. Search freely and report findings.

---

## Documentation Workflow

### While Shipping (CONTINUOUS)

CLAUDE.md is the single source of truth for every Claude instance that touches this project. Update it as you go:

- **New file created?** -- Add it to the Project Structure tree immediately
- **New endpoint?** -- Add to relevant section
- **Changed data structures?** -- Update relevant sections
- **New common issue discovered?** -- Add to Common Issues table
- **Architecture change?** -- Update relevant sections

Don't batch these. A 30-second edit now saves 10 minutes of confusion for the next instance.

---

CLAUDE.md = project context and research. Update it as the project evolves.
