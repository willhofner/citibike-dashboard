#!/usr/bin/env python3
"""Parse Apple Health XML for heart rate data into enriched JSON."""
import xml.etree.ElementTree as ET
import json
from datetime import datetime
from collections import defaultdict

INPUT = 'data/Apple_Health.xml'
OUTPUT = 'data/heartrate_enriched.json'

TYPES = {
    'HKQuantityTypeIdentifierHeartRate': 'heartRate',
    'HKQuantityTypeIdentifierRestingHeartRate': 'restingHR',
    'HKQuantityTypeIdentifierHeartRateVariabilitySDNN': 'hrv',
    'HKQuantityTypeIdentifierVO2Max': 'vo2max',
    'HKQuantityTypeIdentifierWalkingHeartRateAverage': 'walkingHR',
}

def parse_date(s):
    """Parse Apple Health date format: 2024-11-21 18:40:02 -0400"""
    try:
        return datetime.strptime(s[:19], '%Y-%m-%d %H:%M:%S')
    except:
        return None

def main():
    print("Parsing Apple Health XML (this may take a moment)...")

    # Collect raw data
    hr_readings = []       # All heart rate readings
    resting_hr = []        # Daily resting HR
    hrv_readings = []      # HRV measurements
    vo2max_readings = []   # VO2 Max
    walking_hr = []        # Walking HR averages

    count = 0
    for event, elem in ET.iterparse(INPUT, events=('end',)):
        if elem.tag != 'Record':
            elem.clear()
            continue

        rec_type = elem.get('type', '')
        if rec_type not in TYPES:
            elem.clear()
            continue

        value = elem.get('value')
        start = elem.get('startDate')
        if not value or not start:
            elem.clear()
            continue

        dt = parse_date(start)
        if not dt:
            elem.clear()
            continue

        val = float(value)
        entry = {
            'value': round(val, 2),
            'datetime': dt.isoformat(),
            'date': dt.strftime('%Y-%m-%d'),
            'hour': dt.hour,
            'dayOfWeek': dt.strftime('%A'),
            'dayOfWeekNum': dt.weekday(),  # 0=Mon, 6=Sun
            'month': dt.strftime('%Y-%m'),
            'year': dt.year,
        }

        key = TYPES[rec_type]
        if key == 'heartRate':
            hr_readings.append(entry)
        elif key == 'restingHR':
            resting_hr.append(entry)
        elif key == 'hrv':
            hrv_readings.append(entry)
        elif key == 'vo2max':
            vo2max_readings.append(entry)
        elif key == 'walkingHR':
            walking_hr.append(entry)

        count += 1
        if count % 100000 == 0:
            print(f"  Processed {count:,} records...")

        elem.clear()

    print(f"  Total records parsed: {count:,}")

    # Sort all by datetime
    hr_readings.sort(key=lambda x: x['datetime'])
    resting_hr.sort(key=lambda x: x['datetime'])
    hrv_readings.sort(key=lambda x: x['datetime'])
    vo2max_readings.sort(key=lambda x: x['datetime'])
    walking_hr.sort(key=lambda x: x['datetime'])

    # Aggregate HR by day
    daily = defaultdict(lambda: {'values': [], 'hourly': defaultdict(list)})
    for r in hr_readings:
        d = r['date']
        daily[d]['values'].append(r['value'])
        daily[d]['hourly'][r['hour']].append(r['value'])

    daily_stats = []
    for date in sorted(daily.keys()):
        vals = daily[date]['values']
        hourly_avg = {}
        for h in range(24):
            hvals = daily[date]['hourly'].get(h, [])
            if hvals:
                hourly_avg[str(h)] = round(sum(hvals) / len(hvals), 1)

        dt = datetime.strptime(date, '%Y-%m-%d')
        daily_stats.append({
            'date': date,
            'dayOfWeek': dt.strftime('%A'),
            'dayOfWeekNum': dt.weekday(),
            'month': dt.strftime('%Y-%m'),
            'year': dt.year,
            'min': round(min(vals), 1),
            'max': round(max(vals), 1),
            'avg': round(sum(vals) / len(vals), 1),
            'count': len(vals),
            'hourly': hourly_avg,
        })

    # Aggregate HR by hour (all-time)
    hourly_all = defaultdict(list)
    for r in hr_readings:
        hourly_all[r['hour']].append(r['value'])
    hourly_avg_all = {}
    for h in range(24):
        vals = hourly_all.get(h, [])
        if vals:
            hourly_avg_all[str(h)] = round(sum(vals) / len(vals), 1)

    # Zone distribution
    zones = {'rest': 0, 'light': 0, 'moderate': 0, 'vigorous': 0, 'peak': 0}
    for r in hr_readings:
        v = r['value']
        if v < 60:
            zones['rest'] += 1
        elif v < 100:
            zones['light'] += 1
        elif v < 140:
            zones['moderate'] += 1
        elif v < 170:
            zones['vigorous'] += 1
        else:
            zones['peak'] += 1

    # BPM distribution (histogram buckets of 5)
    bpm_dist = defaultdict(int)
    for r in hr_readings:
        bucket = int(r['value'] // 5) * 5
        bpm_dist[bucket] += 1
    bpm_histogram = [{'bpm': k, 'count': v} for k, v in sorted(bpm_dist.items())]

    # Compute summary
    all_vals = [r['value'] for r in hr_readings]
    rhr_vals = [r['value'] for r in resting_hr]
    hrv_vals = [r['value'] for r in hrv_readings]

    summary = {
        'totalReadings': len(hr_readings),
        'dateRange': [hr_readings[0]['date'], hr_readings[-1]['date']] if hr_readings else [],
        'daysTracked': len(daily_stats),
        'overallAvg': round(sum(all_vals) / len(all_vals), 1) if all_vals else 0,
        'overallMin': round(min(all_vals), 1) if all_vals else 0,
        'overallMax': round(max(all_vals), 1) if all_vals else 0,
        'avgRestingHR': round(sum(rhr_vals) / len(rhr_vals), 1) if rhr_vals else 0,
        'minRestingHR': round(min(rhr_vals), 1) if rhr_vals else 0,
        'maxRestingHR': round(max(rhr_vals), 1) if rhr_vals else 0,
        'avgHRV': round(sum(hrv_vals) / len(hrv_vals), 1) if hrv_vals else 0,
        'restingHRCount': len(resting_hr),
        'hrvCount': len(hrv_readings),
        'vo2maxCount': len(vo2max_readings),
        'walkingHRCount': len(walking_hr),
        'latestVO2Max': vo2max_readings[-1]['value'] if vo2max_readings else None,
    }

    output = {
        'generated': datetime.now().isoformat(),
        'summary': summary,
        'dailyStats': daily_stats,
        'restingHR': resting_hr,
        'hrv': hrv_readings,
        'vo2max': vo2max_readings,
        'walkingHR': walking_hr,
        'hourlyAvg': hourly_avg_all,
        'zones': zones,
        'bpmHistogram': bpm_histogram,
    }

    with open(OUTPUT, 'w') as f:
        json.dump(output, f)

    print(f"\nWrote to {OUTPUT}")
    print(f"  HR readings: {len(hr_readings):,}")
    print(f"  Daily stats: {len(daily_stats)}")
    print(f"  Resting HR: {len(resting_hr)}")
    print(f"  HRV: {len(hrv_readings)}")
    print(f"  VO2 Max: {len(vo2max_readings)}")
    print(f"  Walking HR: {len(walking_hr)}")
    print(f"  Date range: {summary['dateRange']}")
    print(f"  Avg resting HR: {summary['avgRestingHR']} bpm")
    print(f"  Avg HRV: {summary['avgHRV']} ms")

if __name__ == '__main__':
    main()
