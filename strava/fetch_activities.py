#!/usr/bin/env python3
"""
Fetch all Strava activities via the Strava API v3.
Handles OAuth, pagination, and fetching detailed data + streams for each run.

Usage:
    python3 strava/fetch_activities.py

First run opens a browser for OAuth authorization.
Subsequent runs use the saved refresh token.
"""

import json
import os
import sys
import time
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import requests

# ── Config ──────────────────────────────────────────────────────────────────
CLIENT_ID = "206236"
CLIENT_SECRET = "0b1f866f9080597ae8f5edf97763ad8dc70b3fa0"
REDIRECT_URI = "http://localhost:8888/callback"
SCOPES = "read,activity:read_all"

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
TOKEN_FILE = os.path.join(DATA_DIR, ".strava_tokens.json")
RAW_FILE = os.path.join(DATA_DIR, "activities_raw.json")
ENRICHED_FILE = os.path.join(DATA_DIR, "activities_enriched.json")

# Rate limit safety: pause between API calls
DELAY_BETWEEN_CALLS = 0.5  # seconds

# ── OAuth ───────────────────────────────────────────────────────────────────

auth_code_result = {}

class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        if "code" in query:
            auth_code_result["code"] = query["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Authorization successful!</h1><p>You can close this tab.</p></body></html>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Authorization failed.")

    def log_message(self, format, *args):
        pass  # Suppress server logs


def get_auth_code():
    """Open browser for OAuth, catch the redirect on localhost."""
    auth_url = (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={REDIRECT_URI}"
        f"&approval_prompt=force"
        f"&scope={SCOPES}"
    )

    server = HTTPServer(("localhost", 8888), OAuthHandler)
    print("Opening browser for Strava authorization...")
    webbrowser.open(auth_url)
    print("Waiting for authorization callback...")

    while "code" not in auth_code_result:
        server.handle_request()

    server.server_close()
    return auth_code_result["code"]


def exchange_code_for_tokens(code):
    """Exchange authorization code for access + refresh tokens."""
    resp = requests.post("https://www.strava.com/oauth/token", data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
    })
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(refresh_token):
    """Use refresh token to get a new access token."""
    resp = requests.post("https://www.strava.com/oauth/token", data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    })
    resp.raise_for_status()
    return resp.json()


def get_access_token():
    """Get a valid access token, refreshing or re-authorizing as needed."""
    os.makedirs(DATA_DIR, exist_ok=True)

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            tokens = json.load(f)

        # Check if token is still valid (with 5 min buffer)
        if tokens.get("expires_at", 0) > time.time() + 300:
            print("Using cached access token.")
            return tokens["access_token"]

        # Try refresh
        print("Refreshing access token...")
        try:
            tokens = refresh_access_token(tokens["refresh_token"])
            with open(TOKEN_FILE, "w") as f:
                json.dump(tokens, f, indent=2)
            print("Token refreshed.")
            return tokens["access_token"]
        except Exception as e:
            print(f"Refresh failed ({e}), re-authorizing...")

    # Full OAuth flow
    code = get_auth_code()
    tokens = exchange_code_for_tokens(code)

    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f, indent=2)
    print("Authorization complete. Tokens saved.")
    return tokens["access_token"]


# ── API Calls ───────────────────────────────────────────────────────────────

def api_get(endpoint, token, params=None):
    """Make an authenticated GET request to the Strava API."""
    resp = requests.get(
        f"https://www.strava.com/api/v3{endpoint}",
        headers={"Authorization": f"Bearer {token}"},
        params=params or {},
    )
    if resp.status_code == 429:
        # Rate limited — wait and retry
        reset = int(resp.headers.get("X-RateLimit-Usage", "0,0").split(",")[0])
        print(f"  Rate limited (15-min usage: {reset}). Waiting 60s...")
        time.sleep(60)
        return api_get(endpoint, token, params)
    resp.raise_for_status()
    return resp.json()


def fetch_all_activities(token):
    """Fetch all activities (paginated, 200 per page)."""
    all_activities = []
    page = 1

    while True:
        print(f"  Fetching activities page {page}...")
        activities = api_get("/athlete/activities", token, {
            "per_page": 200,
            "page": page,
        })

        if not activities:
            break

        all_activities.extend(activities)
        print(f"  Got {len(activities)} activities (total: {len(all_activities)})")

        if len(activities) < 200:
            break

        page += 1
        time.sleep(DELAY_BETWEEN_CALLS)

    return all_activities


def fetch_activity_detail(activity_id, token):
    """Fetch detailed activity data (full polyline, splits, best efforts)."""
    return api_get(f"/activities/{activity_id}", token)


def fetch_activity_streams(activity_id, token):
    """Fetch raw time-series data (GPS, heart rate, speed, etc.)."""
    try:
        return api_get(f"/activities/{activity_id}/streams", token, {
            "keys": "time,latlng,distance,altitude,velocity_smooth,heartrate,cadence,moving,grade_smooth",
            "key_by_type": "true",
        })
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            return {}  # Some activities don't have streams
        raise


# ── Main Pipeline ───────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Strava Activity Fetcher")
    print("=" * 60)

    # Step 1: Auth
    token = get_access_token()

    # Step 2: Fetch all activities
    print("\nFetching all activities...")
    all_activities = fetch_all_activities(token)
    print(f"\nFound {len(all_activities)} total activities.")

    # Count by type
    type_counts = {}
    for a in all_activities:
        t = a.get("type", "Unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
    for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")

    # Step 3: Fetch detailed data for each activity
    print(f"\nFetching detailed data for all {len(all_activities)} activities...")
    detailed_activities = []

    for i, activity in enumerate(all_activities):
        aid = activity["id"]
        atype = activity.get("type", "Unknown")
        aname = activity.get("name", "Untitled")

        print(f"  [{i+1}/{len(all_activities)}] {atype}: {aname}")

        # Fetch detail (full polyline, splits, best efforts)
        detail = fetch_activity_detail(aid, token)
        time.sleep(DELAY_BETWEEN_CALLS)

        # Fetch streams (raw GPS, heart rate, etc.)
        streams = fetch_activity_streams(aid, token)
        time.sleep(DELAY_BETWEEN_CALLS)

        detail["_streams"] = streams
        detailed_activities.append(detail)

    # Step 4: Save raw data
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(RAW_FILE, "w") as f:
        json.dump(detailed_activities, f, indent=2)
    print(f"\nSaved {len(detailed_activities)} activities to {RAW_FILE}")

    # Step 5: Enrich
    print("\nEnriching activities...")
    enriched = enrich_activities(detailed_activities)
    with open(ENRICHED_FILE, "w") as f:
        json.dump(enriched, f, indent=2)
    print(f"Saved {len(enriched)} enriched activities to {ENRICHED_FILE}")

    print("\nDone!")


def enrich_activities(activities):
    """Process raw API data into a clean, dashboard-ready format."""
    enriched = []

    for a in activities:
        activity_type = a.get("type", "Unknown")

        # Parse start time
        start_time = a.get("start_date_local", a.get("start_date", ""))

        # Distance
        distance_m = a.get("distance", 0)
        distance_mi = round(distance_m * 0.000621371, 2)
        distance_km = round(distance_m / 1000, 2)

        # Duration
        moving_time = a.get("moving_time", 0)
        elapsed_time = a.get("elapsed_time", 0)

        # Pace (min/mile) for runs
        pace_str = None
        if distance_mi > 0 and activity_type == "Run":
            pace_total_sec = moving_time / distance_mi
            pace_min = int(pace_total_sec // 60)
            pace_sec = int(pace_total_sec % 60)
            pace_str = f"{pace_min}:{pace_sec:02d}/mi"

        # Polyline
        map_data = a.get("map", {})
        polyline = map_data.get("polyline") or map_data.get("summary_polyline")

        # Start/end coordinates
        start_latlng = a.get("start_latlng", [None, None])
        end_latlng = a.get("end_latlng", [None, None])

        # Splits
        splits = []
        for s in a.get("splits_standard", []):
            splits.append({
                "split": s.get("split"),
                "distance": round(s.get("distance", 0), 1),
                "moving_time": s.get("moving_time"),
                "elevation_difference": s.get("elevation_difference"),
                "average_speed": s.get("average_speed"),
                "average_heartrate": s.get("average_heartrate"),
                "pace_zone": s.get("pace_zone"),
            })

        # Best efforts
        best_efforts = []
        for be in a.get("best_efforts", []):
            best_efforts.append({
                "name": be.get("name"),
                "elapsed_time": be.get("elapsed_time"),
                "moving_time": be.get("moving_time"),
                "distance": be.get("distance"),
            })

        # Streams (raw GPS + heart rate time series)
        streams = a.get("_streams", {})
        latlng_stream = None
        heartrate_stream = None
        altitude_stream = None
        velocity_stream = None
        time_stream = None

        if isinstance(streams, dict):
            latlng_stream = streams.get("latlng", {}).get("data")
            heartrate_stream = streams.get("heartrate", {}).get("data")
            altitude_stream = streams.get("altitude", {}).get("data")
            velocity_stream = streams.get("velocity_smooth", {}).get("data")
            time_stream = streams.get("time", {}).get("data")

        # Date parts
        from datetime import datetime
        try:
            dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            day_of_week = dt.strftime("%A")
            hour = dt.hour
            month = dt.strftime("%Y-%m")
            date = dt.strftime("%Y-%m-%d")
        except Exception:
            day_of_week = None
            hour = None
            month = None
            date = None

        enriched.append({
            "id": a.get("id"),
            "name": a.get("name"),
            "type": activity_type,
            "startTime": start_time,
            "date": date,
            "dayOfWeek": day_of_week,
            "hour": hour,
            "month": month,
            "distance_m": round(distance_m, 1),
            "distance_mi": distance_mi,
            "distance_km": distance_km,
            "moving_time": moving_time,
            "elapsed_time": elapsed_time,
            "pace": pace_str,
            "avg_speed": a.get("average_speed"),
            "max_speed": a.get("max_speed"),
            "total_elevation_gain": a.get("total_elevation_gain"),
            "elev_high": a.get("elev_high"),
            "elev_low": a.get("elev_low"),
            "avg_heartrate": a.get("average_heartrate"),
            "max_heartrate": a.get("max_heartrate"),
            "has_heartrate": a.get("has_heartrate", False),
            "calories": a.get("calories"),
            "startLat": start_latlng[0] if start_latlng else None,
            "startLon": start_latlng[1] if start_latlng else None,
            "endLat": end_latlng[0] if end_latlng else None,
            "endLon": end_latlng[1] if end_latlng else None,
            "polyline": polyline,
            "latlng": latlng_stream,
            "heartrate": heartrate_stream,
            "altitude": altitude_stream,
            "velocity": velocity_stream,
            "time": time_stream,
            "splits": splits,
            "bestEfforts": best_efforts,
            "gear": a.get("gear", {}).get("name") if a.get("gear") else None,
            "description": a.get("description"),
            "workout_type": a.get("workout_type"),
            "suffer_score": a.get("suffer_score"),
        })

    return enriched


if __name__ == "__main__":
    main()
