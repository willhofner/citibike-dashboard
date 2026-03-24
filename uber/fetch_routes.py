#!/usr/bin/env python3
"""Fetch OSRM driving routes for all Uber rides and cache them."""

import json
import time
import urllib.request
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
RIDES_FILE = os.path.join(DATA_DIR, "rides_enriched.json")
ROUTES_FILE = os.path.join(DATA_DIR, "routes.json")

OSRM_URL = "https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"


def fetch_route(start_lat, start_lon, end_lat, end_lon):
    """Fetch a driving route from OSRM."""
    url = OSRM_URL.format(
        lat1=start_lat, lon1=start_lon,
        lat2=end_lat, lon2=end_lon
    )
    req = urllib.request.Request(url, headers={"User-Agent": "HofRides/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())

    if data.get("code") != "Ok" or not data.get("routes"):
        return None

    route = data["routes"][0]
    return {
        "coordinates": route["geometry"]["coordinates"],  # [lon, lat] pairs
        "distance": route["distance"],  # meters
        "duration": route["duration"],  # seconds
    }


def main():
    with open(RIDES_FILE) as f:
        data = json.load(f)
    rides = data["rides"]

    # Load existing routes to support incremental fetching
    existing = {}
    if os.path.exists(ROUTES_FILE):
        with open(ROUTES_FILE) as f:
            existing = json.load(f)

    routes = dict(existing)
    fetched = 0
    skipped = 0
    failed = 0

    for ride in rides:
        ride_id = str(ride["id"])
        if ride_id in routes:
            skipped += 1
            continue

        slat, slon = ride.get("startLat"), ride.get("startLon")
        elat, elon = ride.get("endLat"), ride.get("endLon")
        if not all([slat, slon, elat, elon]):
            failed += 1
            continue

        try:
            route = fetch_route(slat, slon, elat, elon)
            if route:
                routes[ride_id] = route
                fetched += 1
                print(f"  [{fetched}] Ride {ride_id}: {ride.get('startAddress', '?')[:30]} → {ride.get('endAddress', '?')[:30]} ({len(route['coordinates'])} pts)")
            else:
                failed += 1
                print(f"  [!] Ride {ride_id}: no route found")
        except Exception as e:
            failed += 1
            print(f"  [!] Ride {ride_id}: error - {e}")

        time.sleep(0.5)  # Be nice to OSRM

    with open(ROUTES_FILE, "w") as f:
        json.dump(routes, f)

    print(f"\nDone: {fetched} fetched, {skipped} cached, {failed} failed")
    print(f"Total routes: {len(routes)}")


if __name__ == "__main__":
    main()
