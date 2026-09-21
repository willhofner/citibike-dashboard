#!/usr/bin/env python3
"""Ingest activities exported from the Strava *website* (no API, no subscription).

Strava put API access behind a paid subscription in September 2026. The
website's own JSON endpoints still answer with a logged-in browser session:

    /athlete/training_activities?page=N&per_page=20   -> activity list
    /activities/<id>/streams?stream_types[]=latlng...   -> GPS / HR / time series

The browser-side collector (run from the site while logged in) writes a file
shaped like [{"list": {...}, "streams": {...}, "calories": "211", "device": ...}].
This script turns those into the same enriched records fetch_activities.py
produces, merges them into activities_enriched.json (deduped by id), and
leaves activities_raw.json alone.

Usage:
    python3 strava/ingest_web.py path/to/web_export.json
"""

import json
import math
import os
import sys
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
ENRICHED_FILE = os.path.join(DATA_DIR, "activities_enriched.json")

TYPE_MAP = {
    "Run": "Run", "TrailRun": "Run", "VirtualRun": "Run",
    "Ride": "Ride", "EBikeRide": "Ride", "VirtualRide": "Ride", "GravelRide": "Ride", "MountainBikeRide": "Ride",
    "Walk": "Walk", "Hike": "Hike", "WeightTraining": "WeightTraining", "Workout": "Workout",
    "Swim": "Swim", "Yoga": "Yoga",
}


def encode_polyline(points, precision=5):
    """Google encoded polyline for a list of [lat, lon]."""
    out = []
    prev_lat = prev_lon = 0
    factor = 10 ** precision
    for lat, lon in points:
        ilat, ilon = round(lat * factor), round(lon * factor)
        for cur, prev in ((ilat, prev_lat), (ilon, prev_lon)):
            v = cur - prev
            v = ~(v << 1) if v < 0 else (v << 1)
            while v >= 0x20:
                out.append(chr((0x20 | (v & 0x1F)) + 63))
                v >>= 5
            out.append(chr(v + 63))
        prev_lat, prev_lon = ilat, ilon
    return "".join(out)


def mile_splits(distance, time, heartrate, altitude):
    """Per-mile splits from the distance/time streams, matching the API's splits_standard shape."""
    if not distance or not time or len(distance) != len(time):
        return []
    mile = 1609.344
    splits, start_i, n = [], 0, 1
    for i in range(1, len(distance)):
        if distance[i] - distance[start_i] >= mile or i == len(distance) - 1:
            d = distance[i] - distance[start_i]
            t = time[i] - time[start_i]
            if d < 200 or t <= 0:
                break
            hr = None
            if heartrate and len(heartrate) == len(distance):
                seg = [x for x in heartrate[start_i:i + 1] if x]
                hr = sum(seg) / len(seg) if seg else None
            elev = None
            if altitude and len(altitude) == len(distance):
                elev = round(altitude[i] - altitude[start_i], 1)
            splits.append({
                "split": n,
                "distance": round(d, 1),
                "moving_time": int(t),
                "elevation_difference": elev,
                "average_speed": round(d / t, 3),
                "average_heartrate": hr,
                "pace_zone": None,
            })
            n += 1
            start_i = i
    return splits


def best_efforts(distance, time):
    """Fastest windows for the standard distances, from the distance/time streams."""
    if not distance or not time or len(distance) != len(time):
        return []
    targets = [("400m", 400), ("1/2 mile", 804.67), ("1k", 1000), ("1 mile", 1609.34), ("2 mile", 3218.69), ("5k", 5000), ("10k", 10000)]
    efforts = []
    for name, target in targets:
        if distance[-1] < target:
            continue
        best, j = None, 0
        for i in range(len(distance)):
            while j < len(distance) and distance[j] - distance[i] < target:
                j += 1
            if j >= len(distance):
                break
            t = time[j] - time[i]
            if best is None or t < best:
                best = t
        if best is not None:
            efforts.append({"name": name, "elapsed_time": int(best), "moving_time": int(best), "distance": int(target)})
    return efforts


def enrich(item):
    m, s = item["list"], item.get("streams") or {}
    activity_type = TYPE_MAP.get(m.get("sport_type"), m.get("sport_type") or "Unknown")
    epoch = m.get("start_date_local_raw")
    # start_time is UTC; the API path stored start_date_local with a Z suffix, so mirror that quirk
    # by using the local epoch rendered as if it were UTC.
    dt = datetime.fromtimestamp(epoch, tz=timezone.utc) if epoch else None
    start_time = dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else m.get("start_time")

    distance_m = float(m.get("distance_raw") or 0)
    distance_mi = round(distance_m * 0.000621371, 2)
    moving_time = int(m.get("moving_time_raw") or 0)
    elapsed_time = int(m.get("elapsed_time_raw") or 0)

    pace = None
    if distance_mi > 0 and activity_type == "Run":
        total = moving_time / distance_mi
        pace = f"{int(total // 60)}:{int(total % 60):02d}/mi"

    latlng = s.get("latlng") or None
    hr = s.get("heartrate") or None
    alt = s.get("altitude") or None
    vel = s.get("velocity_smooth") or None
    tme = s.get("time") or None
    dist = s.get("distance") or None

    cal = item.get("calories")
    try:
        cal = float(str(cal).replace(",", "")) if cal else None
    except ValueError:
        cal = None

    return {
        "id": int(m["id"]),
        "name": m.get("name"),
        "type": activity_type,
        "startTime": start_time,
        "date": dt.strftime("%Y-%m-%d") if dt else None,
        "dayOfWeek": dt.strftime("%A") if dt else None,
        "hour": dt.hour if dt else None,
        "month": dt.strftime("%Y-%m") if dt else None,
        "distance_m": round(distance_m, 1),
        "distance_mi": distance_mi,
        "distance_km": round(distance_m / 1000, 2),
        "moving_time": moving_time,
        "elapsed_time": elapsed_time,
        "pace": pace,
        "avg_speed": round(distance_m / moving_time, 3) if moving_time else None,
        "max_speed": round(max(vel), 3) if vel else None,
        "total_elevation_gain": float(m.get("elevation_gain_raw") or 0),
        "elev_high": round(max(alt), 1) if alt else None,
        "elev_low": round(min(alt), 1) if alt else None,
        "avg_heartrate": round(sum(hr) / len(hr), 1) if hr else None,
        "max_heartrate": float(max(hr)) if hr else None,
        "has_heartrate": bool(hr),
        "calories": cal,
        "startLat": latlng[0][0] if latlng else None,
        "startLon": latlng[0][1] if latlng else None,
        "endLat": latlng[-1][0] if latlng else None,
        "endLon": latlng[-1][1] if latlng else None,
        "polyline": encode_polyline(latlng) if latlng else None,
        "latlng": latlng,
        "heartrate": hr,
        "altitude": alt,
        "velocity": vel,
        "time": tme,
        "splits": mile_splits(dist, tme, hr, alt) if activity_type == "Run" else [],
        "bestEfforts": best_efforts(dist, tme) if activity_type == "Run" else [],
        "gear": None,
        "description": item.get("description") or m.get("description") or "",
        "workout_type": None,
        "suffer_score": m.get("suffer_score"),
        "source": "strava-web",
        "device": item.get("device"),
    }


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    with open(sys.argv[1]) as f:
        items = json.load(f)

    existing = []
    if os.path.exists(ENRICHED_FILE):
        with open(ENRICHED_FILE) as f:
            existing = json.load(f)
    by_id = {a["id"]: a for a in existing}

    added = 0
    for item in items:
        rec = enrich(item)
        # Records that came from the API are richer (gear, calories, official splits); keep them.
        if rec["id"] in by_id:
            continue
        by_id[rec["id"]] = rec
        added += 1

    merged = sorted(by_id.values(), key=lambda a: a.get("startTime", ""), reverse=True)
    with open(ENRICHED_FILE, "w") as f:
        json.dump(merged, f)

    runs = [a for a in merged if a["type"] == "Run"]
    print(f"Ingested {len(items)} web activities, {added} new -> {len(merged)} total ({len(runs)} runs)")
    print(f"  Newest: {merged[0]['date']} {merged[0]['name']}")


if __name__ == "__main__":
    main()
