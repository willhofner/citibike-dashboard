#!/usr/bin/env python3
"""Build the compact event feed for the unified timelapse.

Reads every mode's enriched data and writes timelapse/data/events.json:
one record per trip, sorted by start time, with a downsampled path so the
whole history (hundreds of trips) stays a few MB and loads at runtime.

    python3 timelapse/build_events.py
"""

import json
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "timelapse", "data")
OUT = os.path.join(OUT_DIR, "events.json")

MAX_POINTS = 160  # per path; runs have ~1,300 GPS points, that is far more than a timelapse needs


def load(path):
    with open(os.path.join(ROOT, path)) as f:
        return json.load(f)


def downsample(coords, max_points=MAX_POINTS):
    if len(coords) <= max_points:
        return coords
    step = len(coords) / (max_points - 1)
    out = [coords[int(i * step)] for i in range(max_points - 1)]
    out.append(coords[-1])
    return out


def rnd(coords):
    return [[round(lat, 5), round(lon, 5)] for lat, lon in coords]


def epoch(iso):
    """ISO string -> unix seconds. Strava stores local time with a Z suffix; treat it as local."""
    s = iso.replace("Z", "")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        # interpret as America/New_York without a tz database dependency: store naive, page renders naive
        return int(dt.replace(tzinfo=timezone.utc).timestamp())
    return int(dt.astimezone(timezone.utc).timestamp())


def naive_epoch(iso):
    """Local wall-clock seconds (so everything sorts by the clock on the wall in NYC)."""
    s = iso.replace("Z", "")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return int(dt.replace(tzinfo=timezone.utc).timestamp())


def main():
    events = []

    # ── Strava (runs + other GPS activities) ──
    for a in load("strava/data/activities_enriched.json"):
        pts = a.get("latlng")
        if a["type"] != "Run" or not pts or len(pts) < 2:
            continue
        events.append({
            "mode": "run",
            "t": naive_epoch(a["startTime"]),
            "dur": int(a.get("moving_time") or 0),
            "mi": a.get("distance_mi", 0),
            "label": a.get("name") or a["type"],
            "sub": f"{a.get('distance_mi', 0)} mi · {a.get('pace') or a['type']}",
            "path": rnd(downsample(pts)),
        })

    # ── CitiBike ──
    routes = load("citibike/data/routes.json")
    for r in load("citibike/data/rides_enriched.json"):
        key = f"{r['startStation']}|{r['endStation']}"
        route = routes.get(key)
        if route and route.get("coordinates"):
            pts = [[c[1], c[0]] for c in route["coordinates"]]
        elif r.get("startLat") and r.get("endLat"):
            pts = [[r["startLat"], r["startLon"]], [r["endLat"], r["endLon"]]]
        else:
            continue
        events.append({
            "mode": "bike",
            "t": naive_epoch(r["startTime"]),
            "dur": int(r.get("durationMin", 0) * 60),
            "mi": round((route or {}).get("distance_m", 0) / 1609.34, 2),
            "label": f"{r['startStation']} → {r['endStation']}",
            "sub": f"{r.get('durationMin')} min · {'ebike' if r.get('isEbike') else 'classic'}",
            "path": rnd(downsample(pts)),
        })

    # ── Subway (entry → intermediate stations → exit, per leg) ──
    for trip in load("subway/data/rides_enriched.json").get("trips", []):
        pts = []
        for leg in trip.get("legs", []):
            seq = [[leg["entryLat"], leg["entryLon"]]]
            for s in leg.get("intermediateStations", []):
                seq.append([s["lat"], s["lon"]])
            seq.append([leg["exitLat"], leg["exitLon"]])
            for p in seq:
                if not pts or pts[-1] != p:
                    pts.append(p)
        if len(pts) < 2:
            continue
        lines = "/".join(dict.fromkeys(l["line"] for l in trip.get("legs", [])))
        events.append({
            "mode": "subway",
            "t": naive_epoch(trip["startTime"]),
            "dur": int(trip.get("durationMin", 0) * 60),
            "mi": 0,
            "label": f"{trip['entryStation']} → {trip['exitStation']}",
            "sub": f"{lines} train · {trip.get('durationMin')} min",
            "path": rnd(pts),
        })

    # ── Uber (NYC only) ──
    uroutes = load("uber/data/routes.json")
    for r in load("uber/data/rides_enriched.json")["rides"]:
        if r.get("city") != "New York City":
            continue
        route = uroutes.get(str(r["id"]))
        if route and route.get("coordinates"):
            pts = [[c[1], c[0]] for c in route["coordinates"]]
        elif r.get("startLat") and r.get("endLat"):
            pts = [[r["startLat"], r["startLon"]], [r["endLat"], r["endLon"]]]
        else:
            continue
        events.append({
            "mode": "uber",
            "t": naive_epoch(r["startTime"]),
            "dur": int(r.get("durationMin", 0) * 60),
            "mi": r.get("distanceMi", 0),
            "label": f"{r['startAddress'].split(',')[0]} → {r['endAddress'].split(',')[0]}",
            "sub": f"{r.get('product')} · ${r.get('fare')}",
            "path": rnd(downsample(pts)),
        })

    events.sort(key=lambda e: e["t"])
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT, "w") as f:
        json.dump({"generated": datetime.now(timezone.utc).isoformat(), "events": events}, f, separators=(",", ":"))

    counts = {}
    for e in events:
        counts[e["mode"]] = counts.get(e["mode"], 0) + 1
    size = os.path.getsize(OUT) / 1024 / 1024
    first = datetime.fromtimestamp(events[0]["t"], tz=timezone.utc).date()
    last = datetime.fromtimestamp(events[-1]["t"], tz=timezone.utc).date()
    print(f"Wrote {len(events)} events ({counts}) {first} → {last}, {size:.1f} MB")


if __name__ == "__main__":
    main()
