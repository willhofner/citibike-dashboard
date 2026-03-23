#!/usr/bin/env python3
"""Parse Uber ride history CSV into enriched JSON for dashboard."""
import csv
import json
from datetime import datetime, timedelta
from collections import defaultdict

INPUT = '../Uber_Ride_History.csv'
OUTPUT = 'data/rides_enriched.json'

def parse_timestamp(ts):
    """Parse Uber timestamp format."""
    if not ts:
        return None
    # Format: 2016-12-27T17:11:42.000Z
    try:
        return datetime.strptime(ts.replace('.000Z', ''), '%Y-%m-%dT%H:%M:%S')
    except:
        return None

def main():
    with open(INPUT, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    rides = []
    for r in rows:
        status = r.get('status', '')
        if status != 'completed':
            continue

        fare = float(r.get('fare_amount') or 0)
        if fare <= 0:
            continue

        begin = parse_timestamp(r.get('begintrip_timestamp_local'))
        end = parse_timestamp(r.get('dropoff_timestamp_local'))
        request = parse_timestamp(r.get('request_timestamp_local'))

        if not begin or not end:
            continue

        duration_sec = float(r.get('trip_duration_seconds') or 0)
        distance_mi = float(r.get('trip_distance_miles') or 0)

        ride = {
            'id': len(rides) + 1,
            'city': r.get('city_name', ''),
            'product': r.get('product_type_name', '') or r.get('global_product_name', ''),
            'requestTime': request.isoformat() if request else None,
            'startTime': begin.isoformat(),
            'endTime': end.isoformat(),
            'startLat': float(r['begintrip_lat']) if r.get('begintrip_lat') else None,
            'startLon': float(r['begintrip_lng']) if r.get('begintrip_lng') else None,
            'endLat': float(r['dropoff_lat']) if r.get('dropoff_lat') else None,
            'endLon': float(r['dropoff_lng']) if r.get('dropoff_lng') else None,
            'startAddress': r.get('begintrip_address', ''),
            'endAddress': r.get('dropoff_address', ''),
            'distanceMi': round(distance_mi, 2),
            'durationMin': round(duration_sec / 60, 1),
            'durationSec': int(duration_sec),
            'fare': round(fare, 2),
            'surgeMultiplier': float(r.get('surge_multiplier') or 1),
            'isSurged': r.get('is_surged', '').lower() == 'true',
            'isPool': r.get('is_pool_matched', '').lower() == 'true',
            'waitTimeSec': int(float(r.get('request_to_begin_duration_seconds') or 0)),
            'dayOfWeek': begin.strftime('%A'),
            'hour': begin.hour,
            'month': begin.strftime('%Y-%m'),
            'date': begin.strftime('%Y-%m-%d'),
            'year': begin.year,
        }
        rides.append(ride)

    # Sort by start time (newest first)
    rides.sort(key=lambda r: r['startTime'], reverse=True)

    # Compute summary
    total_fare = sum(r['fare'] for r in rides)
    total_dist = sum(r['distanceMi'] for r in rides)
    total_dur_min = sum(r['durationMin'] for r in rides)
    cities = list(set(r['city'] for r in rides))
    products = list(set(r['product'] for r in rides))
    dates = [r['date'] for r in rides]

    summary = {
        'totalRides': len(rides),
        'totalFare': round(total_fare, 2),
        'totalDistanceMi': round(total_dist, 1),
        'totalDurationMin': round(total_dur_min, 1),
        'totalDurationHr': round(total_dur_min / 60, 1),
        'avgFare': round(total_fare / len(rides), 2),
        'avgDistanceMi': round(total_dist / len(rides), 2),
        'avgDurationMin': round(total_dur_min / len(rides), 1),
        'avgWaitTimeSec': round(sum(r['waitTimeSec'] for r in rides) / len(rides), 0),
        'dateRange': [min(dates), max(dates)],
        'cities': sorted(cities),
        'cityCount': len(cities),
        'products': sorted(products),
        'longestRideMi': max(r['distanceMi'] for r in rides),
        'mostExpensiveRide': max(r['fare'] for r in rides),
        'surgedRides': sum(1 for r in rides if r['isSurged']),
        'poolRides': sum(1 for r in rides if r['isPool']),
    }

    output = {
        'generated': datetime.now().isoformat(),
        'summary': summary,
        'rides': rides,
    }

    with open(OUTPUT, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Wrote {len(rides)} rides to {OUTPUT}")
    print(f"Total fare: ${total_fare:.2f}")
    print(f"Total distance: {total_dist:.1f} mi")
    print(f"Date range: {min(dates)} to {max(dates)}")
    print(f"Cities: {len(cities)}")

if __name__ == '__main__':
    main()
