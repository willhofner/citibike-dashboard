#!/usr/bin/env python3
"""Parse CitiBike raw ride export into enriched JSON for dashboard."""

import json
import os
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
STATION_COORDS_FILE = os.path.join(DATA_DIR, "station_coords.json")
OUTPUT_FILE = os.path.join(DATA_DIR, "rides_enriched.json")

GBFS_URL = "https://gbfs.citibikenyc.com/gbfs/en/station_information.json"


def find_raw_file():
    """Find the most recent raw ride export file."""
    files = [f for f in os.listdir(DATA_DIR) if f.startswith("citibike_rides_") and f.endswith(".json")]
    if not files:
        print("No raw ride file found (citibike_rides_*.json)")
        return None
    files.sort(reverse=True)
    return os.path.join(DATA_DIR, files[0])


def load_station_coords():
    """Load existing station coordinates."""
    if os.path.exists(STATION_COORDS_FILE):
        with open(STATION_COORDS_FILE) as f:
            return json.load(f)
    return {}


def fetch_gbfs_stations():
    """Fetch station coordinates from CitiBike GBFS feed."""
    print("Fetching station coordinates from GBFS...")
    req = urllib.request.Request(GBFS_URL, headers={"User-Agent": "HofBikes/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    stations = {}
    for s in data["data"]["stations"]:
        stations[s["name"]] = {"lat": s["lat"], "lon": s["lon"]}
    print(f"  Got {len(stations)} stations from GBFS")
    return stations


def parse_price(formatted):
    """Parse '$1.09' into 1.09."""
    if not formatted:
        return 0.0
    return float(formatted.replace("$", "").replace(",", ""))


def is_ebike(line_items):
    """Check if ride was an ebike based on line items."""
    for item in (line_items or []):
        title = item.get("title", "").lower()
        if "ebike" in title or "e-bike" in title:
            return True
    return False


NYC_TZ = ZoneInfo("America/New_York")


def ms_to_datetime(ms_str):
    """Convert millisecond timestamp string to NYC local datetime."""
    ms = int(ms_str)
    dt_utc = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    return dt_utc.astimezone(NYC_TZ)


def main():
    raw_file = find_raw_file()
    if not raw_file:
        return
    print(f"Reading {os.path.basename(raw_file)}...")

    with open(raw_file) as f:
        raw_rides = json.load(f)
    print(f"  {len(raw_rides)} rides in raw file")

    # Load station coords, fetch missing from GBFS
    coords = load_station_coords()
    all_stations = set()
    for r in raw_rides:
        all_stations.add(r.get("startAddress", ""))
        all_stations.add(r.get("endAddress", ""))
    all_stations.discard("")

    missing = all_stations - set(coords.keys())
    if missing:
        gbfs = fetch_gbfs_stations()
        found = 0
        for name in missing:
            if name in gbfs:
                coords[name] = gbfs[name]
                found += 1
        if found:
            with open(STATION_COORDS_FILE, "w") as f:
                json.dump(coords, f, indent=2, sort_keys=True)
            print(f"  Added {found} new station coords ({len(missing) - found} still missing)")
        still_missing = missing - set(coords.keys())
        if still_missing:
            print(f"  Warning: no coords for: {', '.join(sorted(still_missing))}")

    # Parse and enrich rides
    rides = []
    for r in raw_rides:
        start_ms = r.get("startTimeMs")
        end_ms = r.get("endTimeMs")
        if not start_ms or not end_ms:
            continue

        start_dt = ms_to_datetime(start_ms)
        end_dt = ms_to_datetime(end_ms)

        start_station = r.get("startAddress", "")
        end_station = r.get("endAddress", "")

        start_coords = coords.get(start_station, {})
        end_coords = coords.get(end_station, {})

        duration_ms = r.get("duration", int(end_ms) - int(start_ms))

        ride = {
            "rideId": r["rideId"],
            "startTime": start_dt.isoformat(),
            "endTime": end_dt.isoformat(),
            "startStation": start_station,
            "endStation": end_station,
            "startLat": start_coords.get("lat"),
            "startLon": start_coords.get("lon"),
            "endLat": end_coords.get("lat"),
            "endLon": end_coords.get("lon"),
            "durationMin": round(duration_ms / 60000, 1),
            "price": parse_price(r.get("price", {}).get("formatted")),
            "bikeName": r.get("rideableName", ""),
            "isEbike": is_ebike(r.get("lineItems")),
            "dayOfWeek": start_dt.strftime("%A"),
            "hour": start_dt.hour,
            "month": start_dt.strftime("%Y-%m"),
            "date": start_dt.strftime("%Y-%m-%d"),
        }
        rides.append(ride)

    # Sort newest first
    rides.sort(key=lambda r: r["startTime"], reverse=True)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(rides, f, indent=2)

    # Stats
    total_price = sum(r["price"] for r in rides)
    ebike_count = sum(1 for r in rides if r["isEbike"])
    stations = set()
    for r in rides:
        stations.add(r["startStation"])
        stations.add(r["endStation"])

    print(f"\nWrote {len(rides)} rides to {os.path.basename(OUTPUT_FILE)}")
    print(f"  Total spent: ${total_price:.2f}")
    print(f"  Ebike rides: {ebike_count} ({100*ebike_count//len(rides)}%)")
    print(f"  Unique stations: {len(stations)}")
    print(f"  Date range: {rides[-1]['date']} to {rides[0]['date']}")


if __name__ == "__main__":
    main()
