# Roadmap

Prioritized list of what's next. Order = suggested build order.

---

## 1. Dashboard Curation
Trim every dashboard down to fewer, bolder visuals that tell a story. Kill the noise.

**Guiding question**: What would you show a friend in 5 seconds?

- **HofBikes**: Route heatmap + monthly trend + home station dominance. Cut the doughnut charts.
- **HofRuns**: Pace trend over time + route heatmap + distance progression.
- **HofRides**: Spending trend + city map. Most other charts are noise.
- **HofBeats**: RHR trend + HRV trend + VO2 Max. Three lines, one story: "am I getting healthier?"
- **HofWalks**: Daily steps trend + streak/consistency view.

Decide the **one signature visual** per dashboard — that visual becomes the hero on the landing page and the thing that works best on mobile.

---

## 2. Mobile Explorers
Make the animated explorers work beautifully on phones. This is the "show friends at dinner" moment.

- Bottom-sheet pattern: ride list peeks from bottom, drag up to expand, tap to see route on fullscreen map
- Dismissable info overlays (explicit X buttons, tap-outside-to-close)
- Thumb-friendly animation controls (play/pause/speed)
- Apply to: HofBikes, HofRuns, HofRides explorers
- Build HofSubways mobile-first from the start

---

## 3. Landing Page Redesign
Kill the generic AI-generated card grid. Make it feel personal and crafted.

- Explore: bento grid with live preview visuals, editorial/magazine layout, or scrapbook/collage aesthetic
- Google Stitch inspiration: tactile textures, paper-like layers, slight imperfections, hand-drawn accents
- Each card should tease that dashboard's signature visual (from #1)
- Drop the "Scheduled Jobs" section (developer-facing, not visitor-facing)
- Add personality — display fonts, mixed type sizes, asymmetric layout
- Inspiration: Read.cv, Linear changelog, Stripe annual reports

**Do this after #1** — design the rooms before the hallway.

---

## 4. HofReads v2
Transform from data rectangles into something that looks and feels like real books.

- Pull cover images from Open Library Covers API (free, no auth, uses ISBN from Goodreads export)
- Shelf aesthetic: spines, shadows, physical feel
- Book-open animation: click a cover → CSS flip/open revealing details inside
- Consider: reading timeline, pages-per-month trend, genre breakdown

---

## 5. HofRides Animation Fix
The route animations are too slow/fast/inconsistent. Quick fix — probably just adjusting speed relative to route length.

---

## 6. HofSubways
GPS data collection started 2026-03-29. Target: eyeball data ~April 5, build if quality is sufficient.

Full build plan already documented in CLAUDE.md. Key steps:
1. Pull GPS data, eyeball for station-stop pings
2. Download MTA GTFS station data
3. Build station-snapping algorithm
4. Validate against OMNY CSV
5. Build explorer page (mobile-first)
6. Update landing page

---

## 7. PT Claude (Personal Trainer)
Turn Strava run data into a marathon training companion. NYC Marathon is November 2026.

- Load a training plan (Hal Higdon, Pfitz, or custom)
- Sync daily with Strava to track plan compliance
- Post-run notes to adapt the plan to how the body feels
- Tell me what my next run should be (day, distance, pace)
- Goal: 4:00 marathon (~9:09/mi pace)
- Training likely starts June/July (16-20 week plan) — scope and build in May
- Open question: static dashboard (HofMarathon?) vs conversational Claude project vs both

---

## 8. Unified Animation
One map, all transport modes, playing chronologically. The demo piece.

- Timeline scrubber: watch a day/week/month play out
- Bikes (blue), runs (orange), Ubers (purple), subways (yellow)
- Depends on HofSubways being done first
- This is the "tweet it / show at a dinner party" feature

---

## 9. Doctor Claude
Holistic health dashboard with biomarkers, test results, doctor visit notes, genetic tendencies, appointments.

- **Separate repo.** Different audience (just me), different sensitivity (lab results, genetics), different interaction model (conversational/AI-native).
- Import overlapping data from this repo (steps, HR, runs) rather than co-locating
- Not published to website
- Start when inspired — no deadline
