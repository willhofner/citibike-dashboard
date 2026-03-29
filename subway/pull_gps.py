#!/usr/bin/env python3
"""
Pull GPS data from the Railway-hosted receiver to local data directory.

Usage:
    python3 subway/pull_gps.py

Env vars (or edit below):
    RECEIVER_URL: e.g. https://your-app.railway.app
    RECEIVER_TOKEN: your auth token
"""

import json
import os
import sys
from urllib.request import Request, urlopen
from urllib.error import URLError

# Config — update these after Railway deployment
RECEIVER_URL = os.environ.get("RECEIVER_URL", "")
RECEIVER_TOKEN = os.environ.get("RECEIVER_TOKEN", "")
LOCAL_DIR = os.path.join(os.path.dirname(__file__), "data", "gps")


def pull():
    if not RECEIVER_URL:
        print("Set RECEIVER_URL env var (e.g. https://your-app.railway.app)")
        sys.exit(1)

    # Get status to find available days
    url = f"{RECEIVER_URL}/?token={RECEIVER_TOKEN}" if RECEIVER_TOKEN else RECEIVER_URL
    try:
        req = Request(url)
        resp = urlopen(req)
        status = json.loads(resp.read())
    except URLError as e:
        print(f"Failed to reach receiver: {e}")
        sys.exit(1)

    print(f"Remote: {status['total_points']} points across {status['days_tracked']} days")

    os.makedirs(LOCAL_DIR, exist_ok=True)

    # Download each day's file
    days = status.get("days", [])
    if not days:
        # Fetch full day list from status — the status only shows last 7
        # For now, just pull what's available
        print("No days available yet.")
        return

    for day in days:
        date = day["date"]
        remote_count = day["points"]
        local_path = os.path.join(LOCAL_DIR, f"{date}.json")

        # Check if we already have this file with same point count
        if os.path.exists(local_path):
            with open(local_path) as f:
                local_data = json.load(f)
            if len(local_data) >= remote_count:
                print(f"  {date}: {remote_count} points (already up to date)")
                continue

        # Download
        day_url = f"{RECEIVER_URL}/data/{date}.json?token={RECEIVER_TOKEN}"
        req = Request(day_url)
        resp = urlopen(req)
        data = resp.read()

        with open(local_path, "wb") as f:
            f.write(data)

        points = json.loads(data)
        print(f"  {date}: downloaded {len(points)} points")

    print("Done.")


if __name__ == "__main__":
    pull()
