#!/usr/bin/env python3
"""Merge newly exported CitiBike rides into a fresh dated raw file.

Usage:
    python3 citibike/merge_rides.py path/to/new_rides.json

Reads the most recent citibike_rides_*.json in citibike/data, merges the new
rides in (deduped by rideId, newest first), and writes
citibike_rides_<today>.json so parse_rides.py picks it up automatically.
"""

import json
import os
import sys
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")


def latest_raw_file():
    files = sorted(
        f for f in os.listdir(DATA_DIR)
        if f.startswith("citibike_rides_") and f.endswith(".json")
    )
    return os.path.join(DATA_DIR, files[-1]) if files else None


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        new_rides = json.load(f)

    existing = []
    src = latest_raw_file()
    if src:
        with open(src) as f:
            existing = json.load(f)
        print(f"Loaded {len(existing)} rides from {os.path.basename(src)}")

    by_id = {r["rideId"]: r for r in existing}
    added = 0
    for r in new_rides:
        if r["rideId"] not in by_id:
            added += 1
        by_id[r["rideId"]] = r

    merged = sorted(by_id.values(), key=lambda r: int(r["startTimeMs"]), reverse=True)

    out = os.path.join(DATA_DIR, f"citibike_rides_{date.today().isoformat()}.json")
    with open(out, "w") as f:
        json.dump(merged, f, indent=2)

    print(f"Added {added} new rides -> {len(merged)} total, wrote {os.path.basename(out)}")


if __name__ == "__main__":
    main()
