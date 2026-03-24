#!/bin/bash
# Daily Strava data update pipeline
# Fetches new activities, rebuilds dashboard HTML, commits + pushes to GitHub
#
# Usage:
#   ./strava/update_strava.sh           # incremental update (default)
#   ./strava/update_strava.sh --full    # re-fetch everything

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

LOG_FILE="$PROJECT_DIR/strava/data/.update.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

log() { echo "[$TIMESTAMP] $*" | tee -a "$LOG_FILE"; }

log "Starting Strava update..."

# Step 1: Fetch new activities (incremental by default)
log "Fetching activities..."
python3 strava/fetch_activities.py "$@" 2>&1 | tee -a "$LOG_FILE"
FETCH_EXIT=${PIPESTATUS[0]}

if [ $FETCH_EXIT -ne 0 ]; then
    log "ERROR: fetch_activities.py failed (exit $FETCH_EXIT)"
    exit 1
fi

# Step 2: Rebuild dashboard HTML
log "Rebuilding dashboard HTML..."
python3 strava/build_dashboard.py 2>&1 | tee -a "$LOG_FILE"

# Step 3: Commit and push if there are changes
if git diff --quiet strava/data/ strava/index.html strava/dashboard.html 2>/dev/null; then
    log "No changes to commit. Already up to date."
else
    log "Committing changes..."
    git add strava/data/activities_raw.json strava/data/activities_enriched.json
    git add strava/index.html strava/dashboard.html 2>/dev/null || true

    # Count new activities from the fetch output
    NEW_COUNT=$(grep -oP 'Added \K\d+' "$LOG_FILE" 2>/dev/null | tail -1 || echo "")
    if [ -n "$NEW_COUNT" ]; then
        COMMIT_MSG="Update Strava data: $NEW_COUNT new activities"
    else
        COMMIT_MSG="Update Strava data ($(date '+%Y-%m-%d'))"
    fi

    git commit -m "$COMMIT_MSG"
    git push
    log "Pushed to GitHub."
fi

log "Done."
