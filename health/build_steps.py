#!/usr/bin/env python3
"""Parse Apple Health XML and build enriched steps JSON for the HofWalks dashboard."""

import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
import json
import os

HEALTH_FILE = os.path.join(os.path.dirname(__file__), "data", "Apple_Health.xml")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "data", "steps_enriched.json")

print("Parsing Apple_Health.xml for step data...")

# Collect raw step records
steps_by_day = defaultdict(float)
steps_by_day_hour = defaultdict(lambda: defaultdict(float))
records_count = 0
total_records = 0

for event, elem in ET.iterparse(HEALTH_FILE, events=("end",)):
    if elem.tag != "Record":
        continue
    total_records += 1
    if total_records % 500000 == 0:
        print(f"  ...scanned {total_records:,} records")

    if elem.get("type") != "HKQuantityTypeIdentifierStepCount":
        elem.clear()
        continue

    start = elem.get("startDate")
    value = float(elem.get("value", 0))

    dt = datetime.strptime(start[:19], "%Y-%m-%d %H:%M:%S")
    day = dt.strftime("%Y-%m-%d")
    hour = dt.hour

    steps_by_day[day] += value
    steps_by_day_hour[day][hour] += value
    records_count += 1
    elem.clear()

print(f"Done! Found {records_count:,} step records across {len(steps_by_day)} days.\n")

# Build daily records
days_sorted = sorted(steps_by_day.keys())
daily_records = []

for day in days_sorted:
    dt = datetime.strptime(day, "%Y-%m-%d")
    total = round(steps_by_day[day])
    hourly = {str(h): round(steps_by_day_hour[day].get(h, 0)) for h in range(24)}

    daily_records.append({
        "date": day,
        "steps": total,
        "dayOfWeek": dt.strftime("%A"),
        "dayOfWeekNum": dt.isoweekday(),  # 1=Mon, 7=Sun
        "month": day[:7],
        "year": int(day[:4]),
        "hourly": hourly,
    })

# Compute summary stats
all_steps = [r["steps"] for r in daily_records]
total_steps = sum(all_steps)
avg_steps = total_steps / len(all_steps)

output = {
    "generated": datetime.now().isoformat(),
    "summary": {
        "totalSteps": total_steps,
        "totalDays": len(daily_records),
        "dateRange": [days_sorted[0], days_sorted[-1]],
        "avgStepsPerDay": round(avg_steps),
        "medianStepsPerDay": round(sorted(all_steps)[len(all_steps) // 2]),
        "maxSteps": max(all_steps),
        "minSteps": min(all_steps),
        "bestDay": max(daily_records, key=lambda r: r["steps"])["date"],
        "worstDay": min(daily_records, key=lambda r: r["steps"])["date"],
    },
    "days": daily_records,
}

with open(OUTPUT_FILE, "w") as f:
    json.dump(output, f)

file_size = os.path.getsize(OUTPUT_FILE)
print(f"Wrote {OUTPUT_FILE}")
print(f"  {len(daily_records)} daily records")
print(f"  File size: {file_size / 1024:.0f} KB")
print(f"  Total steps: {total_steps:,}")
print(f"  Avg: {avg_steps:,.0f}/day")
