#!/usr/bin/env python3
"""Parse Apple Health XML for step count and heart rate data overview."""

import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
import json

HEALTH_FILE = "data/Apple_Health.xml"

# We'll collect data per day
steps_by_day = defaultdict(float)
steps_by_source = defaultdict(int)
steps_records = []

hr_by_day = defaultdict(list)
hr_records = []

resting_hr_by_day = {}
walking_hr_by_day = {}

print("Parsing Apple_Health.xml (streaming ~2.9M records)...")
print("This may take a minute...\n")

count = 0
for event, elem in ET.iterparse(HEALTH_FILE, events=("end",)):
    if elem.tag != "Record":
        continue

    rtype = elem.get("type")
    count += 1

    if count % 500000 == 0:
        print(f"  ...processed {count:,} records")

    if rtype == "HKQuantityTypeIdentifierStepCount":
        start = elem.get("startDate")
        end = elem.get("endDate")
        value = float(elem.get("value", 0))
        source = elem.get("sourceName")

        # Parse date
        dt = datetime.strptime(start[:19], "%Y-%m-%d %H:%M:%S")
        day = dt.strftime("%Y-%m-%d")
        hour = dt.hour

        steps_by_day[day] += value
        steps_by_source[source] += 1
        steps_records.append({
            "date": day,
            "hour": hour,
            "start": start[:19],
            "end": end[:19],
            "value": value,
            "source": source
        })

    elif rtype == "HKQuantityTypeIdentifierHeartRate":
        start = elem.get("startDate")
        value = float(elem.get("value", 0))
        source = elem.get("sourceName")

        dt = datetime.strptime(start[:19], "%Y-%m-%d %H:%M:%S")
        day = dt.strftime("%Y-%m-%d")
        hour = dt.hour

        hr_by_day[day].append(value)
        hr_records.append({
            "date": day,
            "hour": hour,
            "time": start[:19],
            "value": value,
        })

    elif rtype == "HKQuantityTypeIdentifierRestingHeartRate":
        start = elem.get("startDate")
        value = float(elem.get("value", 0))
        dt = datetime.strptime(start[:19], "%Y-%m-%d %H:%M:%S")
        day = dt.strftime("%Y-%m-%d")
        resting_hr_by_day[day] = value

    elif rtype == "HKQuantityTypeIdentifierWalkingHeartRateAverage":
        start = elem.get("startDate")
        value = float(elem.get("value", 0))
        dt = datetime.strptime(start[:19], "%Y-%m-%d %H:%M:%S")
        day = dt.strftime("%Y-%m-%d")
        walking_hr_by_day[day] = value

    # Free memory
    elem.clear()

print(f"\nDone! Processed {count:,} total records.\n")

# ===== STEPS OVERVIEW =====
print("=" * 60)
print("STEP COUNT DATA OVERVIEW")
print("=" * 60)

step_days = sorted(steps_by_day.keys())
print(f"\nTotal records: {len(steps_records):,}")
print(f"Date range: {step_days[0]} to {step_days[-1]}")
print(f"Days with data: {len(step_days)}")

# Calculate expected days
from datetime import timedelta
d1 = datetime.strptime(step_days[0], "%Y-%m-%d")
d2 = datetime.strptime(step_days[-1], "%Y-%m-%d")
expected_days = (d2 - d1).days + 1
print(f"Expected days in range: {expected_days}")
print(f"Coverage: {len(step_days)/expected_days*100:.1f}%")

daily_totals = [steps_by_day[d] for d in step_days]
print(f"\nDaily step totals:")
print(f"  Average: {sum(daily_totals)/len(daily_totals):,.0f} steps/day")
print(f"  Median:  {sorted(daily_totals)[len(daily_totals)//2]:,.0f} steps/day")
print(f"  Min:     {min(daily_totals):,.0f} steps")
print(f"  Max:     {max(daily_totals):,.0f} steps")
print(f"  Total:   {sum(daily_totals):,.0f} steps all-time")

# Find best and worst days
best_day = max(steps_by_day, key=steps_by_day.get)
worst_day = min(steps_by_day, key=steps_by_day.get)
print(f"\n  Best day:  {best_day} ({steps_by_day[best_day]:,.0f} steps)")
print(f"  Worst day: {worst_day} ({steps_by_day[worst_day]:,.0f} steps)")

# Monthly averages
monthly_steps = defaultdict(list)
for d in step_days:
    month = d[:7]
    monthly_steps[month].append(steps_by_day[d])

print(f"\nMonthly averages:")
for month in sorted(monthly_steps.keys()):
    vals = monthly_steps[month]
    avg = sum(vals) / len(vals)
    print(f"  {month}: {avg:,.0f} steps/day ({len(vals)} days)")

# Records per day (granularity)
records_per_day = defaultdict(int)
for r in steps_records:
    records_per_day[r["date"]] += 1
rpd_vals = list(records_per_day.values())
print(f"\nGranularity (records per day):")
print(f"  Average: {sum(rpd_vals)/len(rpd_vals):.1f} records/day")
print(f"  Min: {min(rpd_vals)}, Max: {max(rpd_vals)}")

# Typical record duration
durations = []
for r in steps_records[:10000]:
    s = datetime.strptime(r["start"], "%Y-%m-%d %H:%M:%S")
    e = datetime.strptime(r["end"], "%Y-%m-%d %H:%M:%S")
    dur_min = (e - s).total_seconds() / 60
    durations.append(dur_min)
print(f"\nTypical record duration (sample of 10K):")
print(f"  Average: {sum(durations)/len(durations):.1f} min")
print(f"  Median:  {sorted(durations)[len(durations)//2]:.1f} min")

# Source breakdown
print(f"\nStep data sources:")
for src, cnt in sorted(steps_by_source.items(), key=lambda x: -x[1]):
    print(f"  {src}: {cnt:,} records")

# Hour of day distribution
hour_steps = defaultdict(float)
hour_counts = defaultdict(int)
for r in steps_records:
    hour_steps[r["hour"]] += r["value"]
    hour_counts[r["hour"]] += 1
print(f"\nSteps by hour of day (total across all days):")
for h in range(24):
    bar = "█" * int(hour_steps.get(h, 0) / max(hour_steps.values()) * 30)
    print(f"  {h:02d}:00  {hour_steps.get(h, 0):>10,.0f}  {bar}")

# Day of week
dow_steps = defaultdict(list)
for d in step_days:
    dt = datetime.strptime(d, "%Y-%m-%d")
    dow = dt.strftime("%A")
    dow_steps[dow].append(steps_by_day[d])
print(f"\nAverage steps by day of week:")
for dow in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
    vals = dow_steps[dow]
    avg = sum(vals) / len(vals) if vals else 0
    bar = "█" * int(avg / max(sum(v)/len(v) for v in dow_steps.values()) * 30)
    print(f"  {dow:9s}: {avg:,.0f}  {bar}")


# ===== HEART RATE OVERVIEW =====
print("\n" + "=" * 60)
print("HEART RATE DATA OVERVIEW")
print("=" * 60)

hr_days = sorted(hr_by_day.keys())
all_hr = [r["value"] for r in hr_records]

print(f"\nTotal records: {len(hr_records):,}")
print(f"Date range: {hr_days[0]} to {hr_days[-1]}")
print(f"Days with data: {len(hr_days)}")

d1 = datetime.strptime(hr_days[0], "%Y-%m-%d")
d2 = datetime.strptime(hr_days[-1], "%Y-%m-%d")
expected_days = (d2 - d1).days + 1
print(f"Expected days in range: {expected_days}")
print(f"Coverage: {len(hr_days)/expected_days*100:.1f}%")

print(f"\nAll-time HR stats:")
print(f"  Average: {sum(all_hr)/len(all_hr):.1f} bpm")
print(f"  Median:  {sorted(all_hr)[len(all_hr)//2]:.0f} bpm")
print(f"  Min:     {min(all_hr):.0f} bpm")
print(f"  Max:     {max(all_hr):.0f} bpm")

# HR distribution buckets
buckets = defaultdict(int)
for v in all_hr:
    bucket = int(v // 10) * 10
    buckets[bucket] += 1
print(f"\nHR distribution:")
for b in sorted(buckets.keys()):
    pct = buckets[b] / len(all_hr) * 100
    bar = "█" * int(pct * 2)
    print(f"  {b:3d}-{b+9:3d} bpm: {buckets[b]:>8,} ({pct:5.1f}%)  {bar}")

# Daily averages
daily_avg_hr = {d: sum(v)/len(v) for d, v in hr_by_day.items()}
daily_min_hr = {d: min(v) for d, v in hr_by_day.items()}
daily_max_hr = {d: max(v) for d, v in hr_by_day.items()}

avg_vals = list(daily_avg_hr.values())
print(f"\nDaily average HR:")
print(f"  Mean of daily averages: {sum(avg_vals)/len(avg_vals):.1f} bpm")
print(f"  Lowest daily avg:  {min(daily_avg_hr, key=daily_avg_hr.get)} ({min(avg_vals):.1f} bpm)")
print(f"  Highest daily avg: {max(daily_avg_hr, key=daily_avg_hr.get)} ({max(avg_vals):.1f} bpm)")

# Readings per day
rpd = {d: len(v) for d, v in hr_by_day.items()}
rpd_vals = list(rpd.values())
print(f"\nReadings per day:")
print(f"  Average: {sum(rpd_vals)/len(rpd_vals):.0f}")
print(f"  Min: {min(rpd_vals)}, Max: {max(rpd_vals)}")

# Typical interval between readings
from datetime import datetime as dt_class
hr_sorted = sorted(hr_records, key=lambda r: r["time"])
intervals = []
for i in range(1, min(50000, len(hr_sorted))):
    t1 = datetime.strptime(hr_sorted[i-1]["time"], "%Y-%m-%d %H:%M:%S")
    t2 = datetime.strptime(hr_sorted[i]["time"], "%Y-%m-%d %H:%M:%S")
    diff = (t2 - t1).total_seconds()
    if 0 < diff < 3600:  # within an hour (same session)
        intervals.append(diff)
if intervals:
    print(f"\nTypical interval between readings (within-session):")
    print(f"  Median: {sorted(intervals)[len(intervals)//2]:.0f} seconds ({sorted(intervals)[len(intervals)//2]/60:.1f} min)")
    print(f"  Average: {sum(intervals)/len(intervals):.0f} seconds")

# Hour of day HR
hour_hr = defaultdict(list)
for r in hr_records:
    hour_hr[r["hour"]].append(r["value"])
print(f"\nAverage HR by hour of day:")
for h in range(24):
    vals = hour_hr.get(h, [])
    if vals:
        avg = sum(vals) / len(vals)
        bar = "█" * int((avg - 50) / 3)
        print(f"  {h:02d}:00  {avg:5.1f} bpm ({len(vals):>6,} readings)  {bar}")

# Monthly averages
monthly_hr = defaultdict(list)
for d in hr_days:
    month = d[:7]
    monthly_hr[month].extend(hr_by_day[d])
print(f"\nMonthly HR averages:")
for month in sorted(monthly_hr.keys()):
    vals = monthly_hr[month]
    print(f"  {month}: {sum(vals)/len(vals):.1f} bpm ({len(vals):,} readings)")

# Resting HR
if resting_hr_by_day:
    rhr_vals = list(resting_hr_by_day.values())
    print(f"\nResting Heart Rate:")
    print(f"  Days with data: {len(resting_hr_by_day)}")
    print(f"  Average: {sum(rhr_vals)/len(rhr_vals):.1f} bpm")
    print(f"  Min: {min(rhr_vals):.0f} bpm")
    print(f"  Max: {max(rhr_vals):.0f} bpm")
    rhr_days = sorted(resting_hr_by_day.keys())
    print(f"  Date range: {rhr_days[0]} to {rhr_days[-1]}")

# Walking HR
if walking_hr_by_day:
    whr_vals = list(walking_hr_by_day.values())
    print(f"\nWalking Heart Rate Average:")
    print(f"  Days with data: {len(walking_hr_by_day)}")
    print(f"  Average: {sum(whr_vals)/len(whr_vals):.1f} bpm")
    print(f"  Min: {min(whr_vals):.0f} bpm")
    print(f"  Max: {max(whr_vals):.0f} bpm")

print("\n" + "=" * 60)
print("DONE!")
print("=" * 60)
