#!/usr/bin/env python3
"""Fetch OSRM bike routes for all unique CitiBike station pairs and cache them."""

import json
import os
import time
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
RIDES_FILE = os.path.join(DATA_DIR, "rides_enriched.json")
ROUTES_FILE = os.path.join(DATA_DIR, "routes.json")

# Use bike profile for cycling routes
OSRM_URL = "https://router.project-osrm.org/route/v1/bike/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"


def fetch_route(start_lat, start_lon, end_lat, end_lon):
    """Fetch a bike route from OSRM."""
    url = OSRM_URL.format(
        lat1=start_lat, lon1=start_lon,
        lat2=end_lat, lon2=end_lon,
    )
    req = urllib.request.Request(url, headers={"User-Agent": "HofBikes/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())

    if data.get("code") != "Ok" or not data.get("routes"):
        return None

    route = data["routes"][0]
    return {
        "coordinates": route["geometry"]["coordinates"],  # [lon, lat] pairs
        "distance_m": route["distance"],  # meters
        "duration_s": route["duration"],  # seconds
    }


def main():
    with open(RIDES_FILE) as f:
        rides = json.load(f)

    # Load existing routes for incremental fetching
    existing = {}
    if os.path.exists(ROUTES_FILE):
        with open(ROUTES_FILE) as f:
            existing = json.load(f)

    # Find unique station pairs that need routes
    pairs = {}
    for ride in rides:
        key = f"{ride['startStation']}|{ride['endStation']}"
        if key not in pairs and key not in existing:
            slat, slon = ride.get("startLat"), ride.get("startLon")
            elat, elon = ride.get("endLat"), ride.get("endLon")
            if all([slat, slon, elat, elon]):
                pairs[key] = (slat, slon, elat, elon)

    if not pairs:
        print(f"All routes cached ({len(existing)} routes)")
        return

    print(f"Fetching {len(pairs)} new routes ({len(existing)} already cached)...")

    routes = dict(existing)
    fetched = 0
    failed = 0

    for key, (slat, slon, elat, elon) in pairs.items():
        start, end = key.split("|")
        try:
            route = fetch_route(slat, slon, elat, elon)
            if route:
                routes[key] = route
                fetched += 1
                print(f"  [{fetched}] {start} → {end} ({len(route['coordinates'])} pts)")
            else:
                failed += 1
                print(f"  [!] {start} → {end}: no route found")
        except Exception as e:
            failed += 1
            print(f"  [!] {start} → {end}: error - {e}")

        time.sleep(0.5)

    with open(ROUTES_FILE, "w") as f:
        json.dump(routes, f)

    print(f"\nDone: {fetched} fetched, {len(existing)} cached, {failed} failed")
    print(f"Total routes: {len(routes)}")


if __name__ == "__main__":
    main()
