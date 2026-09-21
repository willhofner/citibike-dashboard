#!/usr/bin/env python3
"""Bake the enriched CitiBike data into the HofBikes pages.

Replaces the `const RIDES = ...;` and `const ROUTES = ...;` lines in
citibike/index.html and citibike/explore.html with the current contents of
data/rides_enriched.json and data/routes.json, and refreshes the hardcoded
headline numbers on the dashboard and the landing page.

Usage:
    python3 citibike/build_pages.py
"""

import json
import os
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(SCRIPT_DIR, "data")

RIDES_FILE = os.path.join(DATA_DIR, "rides_enriched.json")
ROUTES_FILE = os.path.join(DATA_DIR, "routes.json")

PAGES = [os.path.join(SCRIPT_DIR, "index.html"), os.path.join(SCRIPT_DIR, "explore.html")]
LANDING = os.path.join(ROOT_DIR, "index.html")

RIDES_RE = re.compile(r"^(\s*)const RIDES = .*;$", re.M)
ROUTES_RE = re.compile(r"^(\s*)const ROUTES = .*;$", re.M)


def inject(html, rides_json, routes_json):
    html, n1 = RIDES_RE.subn(lambda m: f"{m.group(1)}const RIDES = {rides_json};", html, count=1)
    html, n2 = ROUTES_RE.subn(lambda m: f"{m.group(1)}const ROUTES = {routes_json};", html, count=1)
    if n1 != 1 or n2 != 1:
        raise SystemExit(f"Expected one RIDES and one ROUTES line, found {n1} and {n2}")
    return html


def main():
    with open(RIDES_FILE) as f:
        rides = json.load(f)
    with open(ROUTES_FILE) as f:
        routes = json.load(f)

    rides_json = json.dumps(rides, separators=(",", ":"))
    routes_json = json.dumps(routes, separators=(",", ":"))

    total = len(rides)
    hours = sum(r["durationMin"] for r in rides) / 60
    stations = {r["startStation"] for r in rides} | {r["endStation"] for r in rides}
    stations.discard("")

    for page in PAGES:
        with open(page) as f:
            html = f.read()
        html = inject(html, rides_json, routes_json)
        # Dashboard copy that quotes the ride count
        html = re.sub(r"Browse all \d+ rides", f"Browse all {total} rides", html)
        html = re.sub(r"Built with \d+ rides", f"Built with {total} rides", html)
        with open(page, "w") as f:
            f.write(html)
        print(f"Built {os.path.relpath(page, ROOT_DIR)} ({os.path.getsize(page) / 1024 / 1024:.1f} MB)")

    # Landing page HofBikes card: Rides / Stations / On Bikes
    with open(LANDING) as f:
        landing = f.read()
    card = re.search(r'class="card bikes".*?<div class="card-links">', landing, re.S)
    if card:
        block = card.group(0)
        new_block = re.sub(r'(<div class="val">)[^<]*(</div><div class="lbl">Rides</div>)', rf"\g<1>{total}\g<2>", block)
        new_block = re.sub(r'(<div class="val">)[^<]*(</div><div class="lbl">Stations</div>)', rf"\g<1>{len(stations)}\g<2>", new_block)
        new_block = re.sub(r'(<div class="val">)[^<]*(</div><div class="lbl">On Bikes</div>)', rf"\g<1>{hours:.1f}h\g<2>", new_block)
        landing = landing.replace(block, new_block)
        with open(LANDING, "w") as f:
            f.write(landing)
        print("Updated landing page card")
    else:
        print("Warning: HofBikes card not found on landing page")

    print(f"  {total} rides, {len(stations)} stations, {hours:.1f} hours, {len(routes)} routes")
    print(f"  Date range: {rides[-1]['date']} to {rides[0]['date']}")


if __name__ == "__main__":
    main()
