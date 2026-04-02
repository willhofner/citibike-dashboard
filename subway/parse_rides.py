#!/usr/bin/env python3
"""Detect subway rides from Overland GPS data.

Reads GPS data files from subway/data/gps/, detects underground segments
via accuracy degradation, snaps entry/exit to MTA stations, groups legs
into trips (handling transfers), and outputs rides_enriched.json.
"""
import json
import os
import glob
from datetime import datetime, timezone, timedelta
from math import radians, cos, sin, sqrt, atan2
from collections import Counter

# --- Paths ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GPS_DIR = os.path.join(SCRIPT_DIR, 'data', 'gps')
OUTPUT = os.path.join(SCRIPT_DIR, 'data', 'rides_enriched.json')

# --- Timezone ---
EDT = timezone(timedelta(hours=-4))

# --- Detection thresholds ---
UNDERGROUND_ACC_THRESHOLD = 50    # accuracy (m) to flag as possibly underground
SURFACE_ACC_THRESHOLD = 30        # accuracy (m) at or below = definitely surface
MIN_UNDERGROUND_SEC = 20          # minimum underground duration to count as a ride
STATION_SNAP_RADIUS_M = 300       # max distance to snap to a station
TRANSFER_MAX_GAP_SEC = 900        # 15 min max gap between legs to count as transfer
ENTRY_EXIT_LOOKBACK = 60          # seconds to look back/forward for station snapping
MIN_DISPLACEMENT_M = 300          # minimum distance between entry and exit stations

# Home position — used to filter false positives from indoor accuracy blips
HOME_LAT = 40.7391
HOME_LON = -73.9901
HOME_RADIUS_M = 150               # points within this radius of home are "at home"

# --- MTA Station Data ---
# Focused on Lexington Ave (4/5/6) corridor and connecting stations.
# Coordinates verified against GPS data from confirmed rides.
STATIONS = [
    # Lexington Ave line (4/5/6) — south to north
    {"name": "Brooklyn Bridge-City Hall", "lat": 40.7131, "lon": -74.0028, "lines": ["4","5","6","J","Z"], "express": True},
    {"name": "Bleecker St", "lat": 40.7259, "lon": -73.9944, "lines": ["6"], "express": False},
    {"name": "Astor Place", "lat": 40.7301, "lon": -73.9909, "lines": ["6"], "express": False},
    {"name": "14th St-Union Sq", "lat": 40.7355, "lon": -73.9905, "lines": ["4","5","6","L","N","Q","R","W"], "express": True},
    {"name": "23rd St (6)", "lat": 40.7390, "lon": -73.9847, "lines": ["6"], "express": False},
    {"name": "28th St (6)", "lat": 40.7432, "lon": -73.9840, "lines": ["6"], "express": False},
    {"name": "33rd St (6)", "lat": 40.7460, "lon": -73.9827, "lines": ["6"], "express": False},
    {"name": "Grand Central-42nd St", "lat": 40.7527, "lon": -73.9772, "lines": ["4","5","6","7","S"], "express": True},
    {"name": "51st St", "lat": 40.7572, "lon": -73.9719, "lines": ["6"], "express": False},
    {"name": "59th St (4/5/6)", "lat": 40.7626, "lon": -73.9678, "lines": ["4","5","6"], "express": True},
    {"name": "68th St-Hunter College", "lat": 40.7687, "lon": -73.9638, "lines": ["6"], "express": False},
    {"name": "77th St", "lat": 40.7736, "lon": -73.9598, "lines": ["6"], "express": False},
    {"name": "86th St (4/5/6)", "lat": 40.7794, "lon": -73.9556, "lines": ["4","5","6"], "express": True},
    {"name": "96th St (6)", "lat": 40.7853, "lon": -73.9510, "lines": ["6"], "express": False},
    {"name": "103rd St (6)", "lat": 40.7907, "lon": -73.9475, "lines": ["6"], "express": False},
    {"name": "110th St (6)", "lat": 40.7954, "lon": -73.9435, "lines": ["6"], "express": False},
    {"name": "116th St (6)", "lat": 40.7987, "lon": -73.9415, "lines": ["6"], "express": False},
    {"name": "125th St (4/5/6)", "lat": 40.8042, "lon": -73.9376, "lines": ["4","5","6"], "express": True},

    # Broadway line (N/Q/R/W) — lower Manhattan
    {"name": "Canal St (N/Q/R/W)", "lat": 40.7201, "lon": -74.0014, "lines": ["N","Q","R","W"], "express": False},
    {"name": "8th St-NYU", "lat": 40.7302, "lon": -73.9924, "lines": ["R","W"], "express": False},
    {"name": "23rd St (R/W)", "lat": 40.7413, "lon": -73.9896, "lines": ["R","W"], "express": False},
    {"name": "28th St (R/W)", "lat": 40.7453, "lon": -73.9883, "lines": ["R","W"], "express": False},
    {"name": "34th St-Herald Sq", "lat": 40.7498, "lon": -73.9878, "lines": ["B","D","F","M","N","Q","R","W"], "express": False},
    {"name": "Times Sq-42nd St", "lat": 40.7553, "lon": -73.9870, "lines": ["1","2","3","7","N","Q","R","W","S"], "express": False},

    # 6th Ave line (B/D/F/M)
    {"name": "Broadway-Lafayette", "lat": 40.7253, "lon": -73.9959, "lines": ["B","D","F","M"], "express": False},
    {"name": "W 4th St", "lat": 40.7323, "lon": -74.0003, "lines": ["A","B","C","D","E","F","M"], "express": False},
    {"name": "14th St (F/M)", "lat": 40.7384, "lon": -73.9999, "lines": ["F","M","L"], "express": False},

    # L train
    {"name": "3rd Ave (L)", "lat": 40.7327, "lon": -73.9861, "lines": ["L"], "express": False},
    {"name": "1st Ave (L)", "lat": 40.7307, "lon": -73.9815, "lines": ["L"], "express": False},

    # Lower Manhattan
    {"name": "Canal St (6)", "lat": 40.7182, "lon": -73.9998, "lines": ["6","J","Z"], "express": False},
    {"name": "Spring St (6)", "lat": 40.7224, "lon": -73.9972, "lines": ["6"], "express": False},
    {"name": "Fulton St", "lat": 40.7102, "lon": -74.0069, "lines": ["2","3","4","5","A","C","J","Z"], "express": False},
    {"name": "Wall St (2/3)", "lat": 40.7069, "lon": -74.0091, "lines": ["2","3"], "express": False},
    {"name": "Chambers St (J/Z)", "lat": 40.7130, "lon": -74.0034, "lines": ["4","5","6","J","Z"], "express": True},  # same complex as Brooklyn Bridge-City Hall

    # 7th Ave / Broadway (1/2/3)
    {"name": "Christopher St", "lat": 40.7334, "lon": -74.0027, "lines": ["1"], "express": False},
    {"name": "14th St (1/2/3)", "lat": 40.7378, "lon": -74.0002, "lines": ["1","2","3"], "express": False},
    {"name": "34th St-Penn Station", "lat": 40.7507, "lon": -73.9910, "lines": ["1","2","3"], "express": False},
]


# Station complex aliases — different entrances of the same station
STATION_COMPLEX = {
    "Chambers St (J/Z)": "Brooklyn Bridge-City Hall",
}


def normalize_station_name(name):
    """Map station entrance names to canonical station complex names."""
    return STATION_COMPLEX.get(name, name)


def haversine(lat1, lon1, lat2, lon2):
    """Distance in meters between two lat/lon points."""
    R = 6371000
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))


def nearest_station(lat, lon, max_dist_m=STATION_SNAP_RADIUS_M):
    """Find the nearest MTA station within max_dist_m. Returns (station, dist) or (None, None)."""
    best = None
    best_dist = max_dist_m + 1
    for s in STATIONS:
        d = haversine(lat, lon, s['lat'], s['lon'])
        if d < best_dist:
            best_dist = d
            best = s
    if best_dist <= max_dist_m:
        return best, best_dist
    return None, None


def parse_ts(ts_str):
    """Parse ISO timestamp string to datetime (UTC)."""
    # Handle both "Z" suffix and "+00:00" format
    ts_str = ts_str.replace('Z', '+00:00')
    return datetime.fromisoformat(ts_str)


def to_edt(dt):
    """Convert UTC datetime to EDT."""
    return dt.astimezone(EDT)


def load_all_gps_points():
    """Load all GPS files, merge, sort by timestamp, deduplicate."""
    all_points = []
    files = sorted(glob.glob(os.path.join(GPS_DIR, '*.json')))

    for filepath in files:
        with open(filepath) as f:
            points = json.load(f)
        for p in points:
            p['_dt'] = parse_ts(p['timestamp'])
        all_points.extend(points)

    # Sort by timestamp, deduplicate by (timestamp, lat, lon)
    all_points.sort(key=lambda p: p['_dt'])
    seen = set()
    deduped = []
    for p in all_points:
        key = (p['timestamp'], p['lat'], p['lon'])
        if key not in seen:
            seen.add(key)
            deduped.append(p)

    return deduped


def detect_underground_segments(points):
    """Find contiguous underground segments based on accuracy degradation.

    Returns list of segments, each containing:
      - start_idx, end_idx: indices into points array
      - start_time, end_time: datetime objects
      - max_accuracy: peak accuracy value during segment
      - points: list of point indices in this segment
    """
    segments = []
    n = len(points)
    i = 0

    while i < n:
        # Look for accuracy crossing above threshold
        if points[i]['accuracy'] > UNDERGROUND_ACC_THRESHOLD:
            seg_start = i

            # Scan forward to find the end of the underground segment.
            # Allow brief recoveries (accuracy drops below threshold for < 60 seconds)
            # as these are station pass-throughs, not actual emergence.
            j = i + 1
            last_underground = i
            max_acc = points[i]['accuracy']

            while j < n:
                acc = points[j]['accuracy']
                if acc > UNDERGROUND_ACC_THRESHOLD:
                    last_underground = j
                    max_acc = max(max_acc, acc)
                    j += 1
                else:
                    # Check if this is a brief recovery (station pass-through)
                    # Look ahead to see if we go back underground within 90 seconds
                    recovery_start = j
                    k = j
                    while k < n and points[k]['accuracy'] <= UNDERGROUND_ACC_THRESHOLD:
                        gap = (points[k]['_dt'] - points[recovery_start]['_dt']).total_seconds()
                        if gap > 90:
                            break
                        k += 1

                    if k < n and points[k]['accuracy'] > UNDERGROUND_ACC_THRESHOLD:
                        # Brief recovery — continue the segment
                        last_underground = k
                        max_acc = max(max_acc, points[k]['accuracy'])
                        j = k + 1
                    else:
                        # Real emergence — end the segment
                        break

            seg_end = last_underground
            duration = (points[seg_end]['_dt'] - points[seg_start]['_dt']).total_seconds()

            if duration >= MIN_UNDERGROUND_SEC and max_acc >= 80:
                segments.append({
                    'start_idx': seg_start,
                    'end_idx': seg_end,
                    'start_time': points[seg_start]['_dt'],
                    'end_time': points[seg_end]['_dt'],
                    'duration_sec': duration,
                    'max_accuracy': max_acc,
                })

            i = seg_end + 1
        else:
            i += 1

    return segments


def find_entry_exit(points, segment):
    """Find entry and exit station for an underground segment.

    Entry: cluster of good-accuracy points near a station BEFORE going underground.
    Exit: cluster of good-accuracy points near a station AFTER emerging.
    """
    start_idx = segment['start_idx']
    end_idx = segment['end_idx']
    start_time = segment['start_time']
    end_time = segment['end_time']

    # --- Entry station ---
    # Look back from the start of the underground segment for good-accuracy points
    entry_points = []
    for i in range(start_idx - 1, -1, -1):
        p = points[i]
        gap = (start_time - p['_dt']).total_seconds()
        if gap > ENTRY_EXIT_LOOKBACK:
            break
        if p['accuracy'] <= SURFACE_ACC_THRESHOLD:
            entry_points.append(p)

    # If not enough points in 60s, expand to 120s
    if len(entry_points) < 3:
        for i in range(start_idx - 1, -1, -1):
            p = points[i]
            gap = (start_time - p['_dt']).total_seconds()
            if gap > 120:
                break
            if p['accuracy'] <= 40 and p not in entry_points:
                entry_points.append(p)

    entry_station = None
    entry_dist = None
    if entry_points:
        # Use centroid of entry points
        avg_lat = sum(p['lat'] for p in entry_points) / len(entry_points)
        avg_lon = sum(p['lon'] for p in entry_points) / len(entry_points)
        entry_station, entry_dist = nearest_station(avg_lat, avg_lon)

    # --- Exit station ---
    exit_points = []
    for i in range(end_idx + 1, len(points)):
        p = points[i]
        gap = (p['_dt'] - end_time).total_seconds()
        if gap > ENTRY_EXIT_LOOKBACK:
            break
        if p['accuracy'] <= SURFACE_ACC_THRESHOLD:
            exit_points.append(p)

    if len(exit_points) < 3:
        for i in range(end_idx + 1, len(points)):
            p = points[i]
            gap = (p['_dt'] - end_time).total_seconds()
            if gap > 120:
                break
            if p['accuracy'] <= 40 and p not in exit_points:
                exit_points.append(p)

    exit_station = None
    exit_dist = None
    if exit_points:
        avg_lat = sum(p['lat'] for p in exit_points) / len(exit_points)
        avg_lon = sum(p['lon'] for p in exit_points) / len(exit_points)
        exit_station, exit_dist = nearest_station(avg_lat, avg_lon)

    # --- Fallback: use the underground points closest to known stations ---
    if not entry_station:
        # Try first few underground points
        for i in range(start_idx, min(start_idx + 5, end_idx + 1)):
            p = points[i]
            s, d = nearest_station(p['lat'], p['lon'], max_dist_m=500)
            if s:
                entry_station = s
                entry_dist = d
                break

    if not exit_station:
        # Try last few underground points
        for i in range(end_idx, max(end_idx - 5, start_idx - 1), -1):
            p = points[i]
            s, d = nearest_station(p['lat'], p['lon'], max_dist_m=500)
            if s:
                exit_station = s
                exit_dist = d
                break

    return entry_station, entry_dist, exit_station, exit_dist


def detect_intermediate_stations(points, segment, entry_station=None, exit_station=None):
    """Find intermediate station pings within an underground segment.

    These are brief accuracy recoveries near known stations mid-ride.
    Only includes stations that share a line with the entry/exit stations
    to avoid showing nearby stations on different lines (e.g., Canal St N/Q/R/W
    when riding the 6).
    """
    # Determine which lines this leg is on
    leg_lines = set()
    if entry_station:
        leg_lines.update(entry_station.get('lines', []))
    if exit_station:
        leg_lines.update(exit_station.get('lines', []))

    intermediates = []
    start_idx = segment['start_idx']
    end_idx = segment['end_idx']

    # Look for accuracy dips below 80m within the segment
    i = start_idx
    while i <= end_idx:
        p = points[i]
        if p['accuracy'] <= 80:
            # Found a recovery — collect consecutive good points
            cluster = [p]
            j = i + 1
            while j <= end_idx and points[j]['accuracy'] <= 80:
                cluster.append(points[j])
                j += 1

            # Check if this cluster is near a known station
            avg_lat = sum(c['lat'] for c in cluster) / len(cluster)
            avg_lon = sum(c['lon'] for c in cluster) / len(cluster)
            station, dist = nearest_station(avg_lat, avg_lon, max_dist_m=400)

            if station and dist is not None:
                # Only include if station shares a line with entry/exit
                station_lines = set(station.get('lines', []))
                if not leg_lines or (station_lines & leg_lines):
                    intermediates.append({
                        'station': normalize_station_name(station['name']),
                        'lat': station['lat'],
                        'lon': station['lon'],
                        'dist_m': round(dist),
                        'time': to_edt(cluster[0]['_dt']).isoformat(),
                        'num_points': len(cluster),
                    })

            i = j
        else:
            i += 1

    # Deduplicate — same station shouldn't appear twice in a row
    deduped = []
    for s in intermediates:
        if not deduped or deduped[-1]['station'] != s['station']:
            deduped.append(s)

    return deduped


def split_transfer_segments(points, segments):
    """Split long underground segments at transfer points.

    A transfer looks like: underground → accuracy recovery near a station
    (position clusters for 20+ seconds with accuracy < 50m) → underground again.

    Key insight: cell tower pings at pass-through stations have accuracy 50-80m,
    while actual platform transfers have accuracy 25-45m (better signal from
    being stationary on platform). We use a tight threshold (< 50m) to
    distinguish real transfers from pass-throughs.
    """
    result = []

    for seg in segments:
        # Only try to split segments longer than 8 minutes.
        # Shorter segments are single rides — local trains get 20-45s of good
        # signal at each station stop, which can look like a transfer.
        if seg['duration_sec'] < 480:
            result.append(seg)
            continue

        start_idx = seg['start_idx']
        end_idx = seg['end_idx']

        # Find accuracy valleys with tight threshold (< 50m = real platform signal)
        TRANSFER_ACC_THRESHOLD = 50
        valleys = []
        i = start_idx
        while i <= end_idx:
            p = points[i]
            if p['accuracy'] < TRANSFER_ACC_THRESHOLD:
                valley_start = i
                j = i
                while j <= end_idx and points[j]['accuracy'] < TRANSFER_ACC_THRESHOLD:
                    j += 1
                valley_end = j - 1
                valley_dur = (points[valley_end]['_dt'] - points[valley_start]['_dt']).total_seconds()

                # Needs 20+ seconds to be a real transfer (not just a blip)
                if valley_dur >= 20:
                    valley_pts = [points[k] for k in range(valley_start, valley_end + 1)]
                    avg_lat = sum(p['lat'] for p in valley_pts) / len(valley_pts)
                    avg_lon = sum(p['lon'] for p in valley_pts) / len(valley_pts)
                    station, dist = nearest_station(avg_lat, avg_lon, max_dist_m=300)

                    if station:
                        # Check this isn't at the very start or end of the segment
                        # (that would be the entry/exit, not a transfer)
                        time_from_start = (points[valley_start]['_dt'] - points[start_idx]['_dt']).total_seconds()
                        time_to_end = (points[end_idx]['_dt'] - points[valley_end]['_dt']).total_seconds()

                        if time_from_start >= MIN_UNDERGROUND_SEC and time_to_end >= MIN_UNDERGROUND_SEC:
                            valleys.append({
                                'start_idx': valley_start,
                                'end_idx': valley_end,
                                'duration_sec': valley_dur,
                                'station': station,
                                'dist': dist,
                            })
                i = j
            else:
                i += 1

        if not valleys:
            result.append(seg)
            continue

        # Pick the best transfer point: the valley farthest from both entry and exit
        # (i.e., the one at the "turning point" of the trip)
        entry_lat = points[start_idx]['lat']
        entry_lon = points[start_idx]['lon']
        exit_lat = points[end_idx]['lat']
        exit_lon = points[end_idx]['lon']

        def score_valley(v):
            """Higher score = better transfer candidate. Prefer valleys far from entry/exit."""
            d_entry = haversine(v['station']['lat'], v['station']['lon'], entry_lat, entry_lon)
            d_exit = haversine(v['station']['lat'], v['station']['lon'], exit_lat, exit_lon)
            return min(d_entry, d_exit)  # maximize the minimum distance

        best = max(valleys, key=score_valley)

        seg1_dur = (points[best['start_idx']]['_dt'] - points[start_idx]['_dt']).total_seconds()
        seg2_dur = (points[end_idx]['_dt'] - points[best['end_idx']]['_dt']).total_seconds()

        seg1 = {
            'start_idx': start_idx,
            'end_idx': best['start_idx'],
            'start_time': points[start_idx]['_dt'],
            'end_time': points[best['start_idx']]['_dt'],
            'duration_sec': seg1_dur,
            'max_accuracy': max(points[k]['accuracy'] for k in range(start_idx, best['start_idx'] + 1)),
        }
        seg2 = {
            'start_idx': best['end_idx'],
            'end_idx': end_idx,
            'start_time': points[best['end_idx']]['_dt'],
            'end_time': points[end_idx]['_dt'],
            'duration_sec': seg2_dur,
            'max_accuracy': max(points[k]['accuracy'] for k in range(best['end_idx'], end_idx + 1)),
        }

        print(f"  SPLIT: {to_edt(seg['start_time']).strftime('%I:%M%p')} segment split at "
              f"{best['station']['name']} (transfer {best['duration_sec']:.0f}s, "
              f"{best['dist']:.0f}m from station)")
        result.extend([seg1, seg2])
        continue

    return result


def snap_segments_to_legs(points, segments):
    """Convert underground segments into ride legs with station info."""
    legs = []

    for seg in segments:
        entry_station, entry_dist, exit_station, exit_dist = find_entry_exit(points, seg)

        if not entry_station or not exit_station:
            print(f"  SKIP: Could not snap segment at {to_edt(seg['start_time']).strftime('%Y-%m-%d %I:%M%p')} "
                  f"(entry={'?' if not entry_station else entry_station['name']}, "
                  f"exit={'?' if not exit_station else exit_station['name']})")
            continue

        # Check minimum displacement — same station = always false positive
        dist = haversine(entry_station['lat'], entry_station['lon'],
                         exit_station['lat'], exit_station['lon'])
        if dist < MIN_DISPLACEMENT_M:
            print(f"  SKIP: Same area ({entry_station['name']} → {exit_station['name']}) — "
                  f"displacement {dist:.0f}m < {MIN_DISPLACEMENT_M}m")
            continue

        # Filter out segments where entry OR exit is at home (indoor accuracy blips)
        entry_home_dist = haversine(entry_station['lat'], entry_station['lon'], HOME_LAT, HOME_LON)
        exit_home_dist = haversine(exit_station['lat'], exit_station['lon'], HOME_LAT, HOME_LON)
        if entry_home_dist < HOME_RADIUS_M and exit_home_dist < HOME_RADIUS_M:
            print(f"  SKIP: Both stations near home ({entry_station['name']} → {exit_station['name']})")
            continue

        intermediates = detect_intermediate_stations(points, seg, entry_station, exit_station)

        # Normalize station names (collapse complex entrances)
        entry_name = normalize_station_name(entry_station['name'])
        exit_name = normalize_station_name(exit_station['name'])

        # Determine direction
        if exit_station['lat'] > entry_station['lat']:
            direction = "Northbound"
        else:
            direction = "Southbound"

        # Determine line (basic heuristic)
        line = guess_line(entry_station, exit_station, intermediates)

        edt_start = to_edt(seg['start_time'])
        edt_end = to_edt(seg['end_time'])

        leg = {
            'entryStation': entry_name,
            'exitStation': exit_name,
            'entryLat': entry_station['lat'],
            'entryLon': entry_station['lon'],
            'exitLat': exit_station['lat'],
            'exitLon': exit_station['lon'],
            'direction': direction,
            'line': line,
            'startTime': edt_start.isoformat(),
            'endTime': edt_end.isoformat(),
            'durationMin': round(seg['duration_sec'] / 60, 1),
            'maxAccuracy': seg['max_accuracy'],
            'entryDist': round(entry_dist) if entry_dist else None,
            'exitDist': round(exit_dist) if exit_dist else None,
            'intermediateStations': intermediates,
        }
        legs.append(leg)

    return legs


def guess_line(entry, exit_station, intermediates):
    """Best-guess subway line based on entry/exit stations.

    Note: intermediate station pings are NOT reliable for express vs local
    detection. The phone picks up cell tower signals when passing through
    local stations even on express trains. Line detection is based primarily
    on entry/exit stations.
    """
    # Check if entry and exit are on the Lex Ave line (4/5/6)
    lex_lines = {'4', '5', '6'}
    entry_on_lex = bool(lex_lines & set(entry['lines']))
    exit_on_lex = bool(lex_lines & set(exit_station['lines']))

    if entry_on_lex and exit_on_lex:
        # Both on Lex Ave — express or local?
        # If both are express stations, likely 4/5
        if entry['express'] and exit_station['express']:
            # Check if there are any local-only stations that the train
            # would have to pass through. If the distance between stations
            # implies skipping stops, it's express.
            return "4/5"

        # If either is local-only (Astor, Bleecker, etc), it's the 6
        if not entry['express'] or not exit_station['express']:
            return "6"

        return "4/5/6"

    # Check for other lines
    entry_lines = set(entry['lines'])
    exit_lines = set(exit_station['lines'])
    shared = entry_lines & exit_lines

    if shared:
        return '/'.join(sorted(shared))

    return "unknown"


def group_into_trips(legs):
    """Group consecutive legs into trips, detecting transfers."""
    if not legs:
        return []

    trips = []
    current_trip_legs = [legs[0]]

    for i in range(1, len(legs)):
        prev = legs[i-1]
        curr = legs[i]

        prev_end = datetime.fromisoformat(prev['endTime'])
        curr_start = datetime.fromisoformat(curr['startTime'])
        gap = (curr_start - prev_end).total_seconds()

        # Check if this is a transfer
        if gap <= TRANSFER_MAX_GAP_SEC:
            # Check if exit of previous leg is near entry of current leg
            dist = haversine(prev['exitLat'], prev['exitLon'],
                             curr['entryLat'], curr['entryLon'])
            if dist < 500:  # same station complex
                current_trip_legs.append(curr)
                continue

        # Not a transfer — save current trip and start a new one
        trips.append(current_trip_legs)
        current_trip_legs = [curr]

    trips.append(current_trip_legs)
    return trips


def build_output(trip_groups):
    """Build the final enriched JSON output."""
    trips = []

    for trip_id, legs in enumerate(trip_groups, 1):
        first_leg = legs[0]
        last_leg = legs[-1]

        start_dt = datetime.fromisoformat(first_leg['startTime'])
        end_dt = datetime.fromisoformat(last_leg['endTime'])
        total_min = (end_dt - start_dt).total_seconds() / 60

        transfer_stations = []
        for i in range(len(legs) - 1):
            transfer_stations.append(legs[i]['exitStation'])

        # Number legs
        numbered_legs = []
        for i, leg in enumerate(legs, 1):
            leg_copy = dict(leg)
            leg_copy['legNumber'] = i
            numbered_legs.append(leg_copy)

        trip = {
            'id': trip_id,
            'date': start_dt.strftime('%Y-%m-%d'),
            'startTime': first_leg['startTime'],
            'endTime': last_leg['endTime'],
            'entryStation': first_leg['entryStation'],
            'exitStation': last_leg['exitStation'],
            'direction': first_leg['direction'] if len(legs) == 1 else 'Mixed',
            'line': first_leg['line'] if len(legs) == 1 else '/'.join(dict.fromkeys(l['line'] for l in legs)),
            'isExpress': any('4' in l['line'] or '5' in l['line'] for l in legs),
            'durationMin': round(total_min, 1),
            'numLegs': len(legs),
            'dayOfWeek': start_dt.strftime('%A'),
            'hour': start_dt.hour,
            'month': start_dt.strftime('%Y-%m'),
            'legs': numbered_legs,
            'transferStations': transfer_stations,
        }
        trips.append(trip)

    # Sort newest first
    trips.sort(key=lambda t: t['startTime'], reverse=True)

    # Reassign IDs after sorting
    for i, t in enumerate(trips, 1):
        t['id'] = i

    # Summary
    dates = [t['date'] for t in trips]
    station_counts = Counter()
    for t in trips:
        station_counts[t['entryStation']] += 1
        station_counts[t['exitStation']] += 1

    # Unique stations used
    all_station_names = set()
    for t in trips:
        all_station_names.add(t['entryStation'])
        all_station_names.add(t['exitStation'])
        for leg in t['legs']:
            for s in leg.get('intermediateStations', []):
                all_station_names.add(s['station'])

    # Station reference data
    station_ref = {}
    for name in all_station_names:
        for s in STATIONS:
            if s['name'] == name:
                station_ref[name] = {
                    'lat': s['lat'],
                    'lon': s['lon'],
                    'lines': s['lines'],
                    'tripCount': station_counts.get(name, 0),
                }
                break

    summary = {
        'totalTrips': len(trips),
        'totalLegs': sum(t['numLegs'] for t in trips),
        'uniqueStations': len(all_station_names),
        'dateRange': [min(dates), max(dates)] if dates else [],
        'daysWithRides': len(set(dates)),
        'mostCommonStation': station_counts.most_common(1)[0][0] if station_counts else None,
        'expressTrips': sum(1 for t in trips if t['isExpress']),
        'transferTrips': sum(1 for t in trips if t['numLegs'] > 1),
    }

    return {
        'generated': datetime.now().isoformat(),
        'summary': summary,
        'trips': trips,
        'stations': station_ref,
    }


def main():
    print("Loading GPS data...")
    points = load_all_gps_points()
    file_count = len(glob.glob(os.path.join(GPS_DIR, '*.json')))
    print(f"  {len(points)} points from {file_count} days")

    print("Detecting underground segments...")
    segments = detect_underground_segments(points)
    print(f"  {len(segments)} underground segments found")

    for seg in segments:
        edt = to_edt(seg['start_time'])
        print(f"    {edt.strftime('%m/%d %I:%M%p')} — {seg['duration_sec']:.0f}s, max acc {seg['max_accuracy']}m")

    print("Checking for transfers within segments...")
    segments = split_transfer_segments(points, segments)
    print(f"  {len(segments)} segments after splitting")

    print("Snapping to stations...")
    legs = snap_segments_to_legs(points, segments)
    print(f"  {len(legs)} legs matched to stations")

    print("Grouping into trips...")
    trip_groups = group_into_trips(legs)
    print(f"  {len(trip_groups)} trips detected")

    output = build_output(trip_groups)

    with open(OUTPUT, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nWrote {len(trip_groups)} trips to {OUTPUT}")
    print()
    for t in output['trips']:
        legs_str = " → ".join(l['entryStation'] for l in t['legs']) + f" → {t['legs'][-1]['exitStation']}"
        line_str = f"[{t['line']}]"
        print(f"  {t['date']} {t['hour']:02d}:{datetime.fromisoformat(t['startTime']).minute:02d}  "
              f"{line_str:>8}  {legs_str}")


if __name__ == '__main__':
    main()
