#!/usr/bin/env python3
"""
Overland GPS receiver endpoint.
Accepts location batches from the Overland iOS app and stores them.

Local usage:
    python3 subway/receiver.py

Railway deployment:
    Set env vars: AUTH_TOKEN (required), PORT (Railway sets this automatically)

Overland app config:
    URL: https://your-app.railway.app/location?token=YOUR_TOKEN
"""

import json
import os
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "data", "gps"))
PORT = int(os.environ.get("PORT", 8080))
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "")


class LocationHandler(BaseHTTPRequestHandler):
    def _check_auth(self):
        if not AUTH_TOKEN:
            return True
        query = parse_qs(urlparse(self.path).query)
        token = query.get("token", [None])[0]
        if token == AUTH_TOKEN:
            return True
        # Also check Authorization header
        auth_header = self.headers.get("Authorization", "")
        if auth_header == f"Bearer {AUTH_TOKEN}":
            return True
        self.send_response(401)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": "unauthorized"}).encode())
        return False

    def do_POST(self):
        if not self._check_auth():
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            return

        locations = data.get("locations", [])
        saved = 0

        for loc in locations:
            props = loc.get("properties", {})
            ts = props.get("timestamp", "")
            coords = loc.get("geometry", {}).get("coordinates", [])

            if not ts or len(coords) < 2:
                continue

            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                date_str = dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

            point = {
                "timestamp": ts,
                "lat": coords[1],
                "lon": coords[0],
                "altitude": coords[2] if len(coords) > 2 else None,
                "speed": props.get("speed", -1),
                "accuracy": props.get("horizontal_accuracy"),
                "battery": props.get("battery_level"),
                "wifi": props.get("wifi"),
                "motion": props.get("motion", []),
            }

            os.makedirs(DATA_DIR, exist_ok=True)
            filepath = os.path.join(DATA_DIR, f"{date_str}.json")

            existing = []
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    try:
                        existing = json.load(f)
                    except json.JSONDecodeError:
                        existing = []

            existing.append(point)

            with open(filepath, "w") as f:
                json.dump(existing, f, indent=2)

            saved += 1

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"result": "ok"}).encode())

        if saved:
            print(f"  Saved {saved} points")

    def do_GET(self):
        path = urlparse(self.path).path

        # Download endpoint: GET /data/YYYY-MM-DD.json
        if path.startswith("/data/"):
            if not self._check_auth():
                return
            filename = path.split("/data/")[-1]
            # Prevent path traversal
            if "/" in filename or ".." in filename:
                self.send_response(400)
                self.end_headers()
                return
            filepath = os.path.join(DATA_DIR, filename)
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(content.encode())
            else:
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "not found"}).encode())
            return

        # Status page
        os.makedirs(DATA_DIR, exist_ok=True)
        files = sorted(f for f in os.listdir(DATA_DIR) if f.endswith(".json"))

        total_points = 0
        days = []
        for f in files:
            with open(os.path.join(DATA_DIR, f), "r") as fh:
                try:
                    points = json.load(fh)
                    total_points += len(points)
                    days.append({"date": f.replace(".json", ""), "points": len(points)})
                except json.JSONDecodeError:
                    pass

        status = {
            "status": "running",
            "port": PORT,
            "total_points": total_points,
            "days_tracked": len(days),
            "days": days[-7:],
        }

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(status, indent=2).encode())

    def log_message(self, format, *args):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {args[0]}")


if __name__ == "__main__":
    if not AUTH_TOKEN:
        print("WARNING: No AUTH_TOKEN set. Endpoint is unauthenticated.")
        print("  Set AUTH_TOKEN env var for production use.\n")

    server = HTTPServer(("0.0.0.0", PORT), LocationHandler)
    print(f"Overland receiver running on port {PORT}")
    print(f"  Endpoint: http://0.0.0.0:{PORT}/location")
    print(f"  Data dir: {DATA_DIR}")
    print(f"  Status:   http://localhost:{PORT}/")
    print()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()
