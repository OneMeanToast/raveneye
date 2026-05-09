# Viewer guide

RavenEye ships two viewers, both pure static HTML:

| Viewer | Default for | Loads | Path |
|---|---|---|---|
| Flat choke-point map | `raveneye-generate` (v0.1) | `sim.json` | `raveneye/viewer/template.html` |
| CesiumJS globe       | `raveneye-build-scenario` (v0.2) | `scenario.json` | `raveneye/viewer/globe/` |

Both stage cleanly with no build step, no bundler, no `npm install`.

## Quick start (v0.2 globe)

Single-constellation (5 satellites):

```bash
raveneye-build-scenario --seed 42 --duration 168 --mechanism ssi \
  --tle-fixture tests/fixtures/tles.txt \
  --out viewer_out/scenario.json --viewer viewer_out
cd viewer_out && python3 -m http.server
# open http://localhost:8000/
```

Multi-constellation (~36 satellites across 6 vendors — recommended for
demos that should show vendor diversity):

```bash
raveneye-build-scenario --seed 42 --duration 168 --mechanism ssi \
  --tle-fixture-dir tests/fixtures/multi_tles \
  --out viewer_out/scenario.json --viewer viewer_out
```

Override the data URL with `?scenario=path/to/scenario.json` or set
`window.RAVENEYE_SCENARIO_URL` in a wrapper page.

For network-fetched TLEs (production), drop the `--tle-fixture` flag and
let CelesTrak provide the elsets (with on-disk caching under
`data/tle_cache/`).

## Two views: GLOBE and BOARD

The header has a tab pair — **GLOBE** (default) and **BOARD** —
that flips between two coordinated views of the same scenario data.
Both views share the playback clock at the bottom of the page, so
scrubbing the timeline in one view advances the other.

| Tab | Shows |
|---|---|
| **GLOBE** | Earth + orbiting satellites + ground markers + coverage swaths during scheduled access windows |
| **BOARD** | Per-target Gantt of allocated windows (top half) + Kanban tasking flow (bottom half), both clock-driven |

There's also a **RTB** button next to the brand mark that opens an
architecture explainer drawer — a sales-pitch overlay walking through
the four layers of the system with live numbers from the loaded
scenario. Press `?` to toggle, `Esc` to close.

## Layout

```
┌────────────────────────────────────────────────────────────────────┐
│ HEADER (48px) — brand · scenario name · phase badge · clock        │
├──────────────────────────────────────────────────┬─────────────────┤
│                                                  │  ASIDE (420px)  │
│                                                  │  ── Stats       │
│                  CESIUM GLOBE                    │  ── Constells   │
│                                                  │  ── Selection   │
│                                                  │  ── Event feed  │
├──────────────────────────────────────────────────┴─────────────────┤
│ TIMELINE (180px) — phases · day ticks · event ticks · AW density  │
├────────────────────────────────────────────────────────────────────┤
│ FOOTER (40px) — play/pause · reset · speed · keyboard hints        │
└────────────────────────────────────────────────────────────────────┘
```

## Globe layer

Cesium 1.122 (Apache 2.0) loaded from jsDelivr. OSM imagery + the
ellipsoid terrain provider — no Cesium ion account required, no paid
tier. Camera flies to the Gulf (53°E, 26.5°N, 4500 km altitude) over 3 s
on load.

Built-in Cesium widgets (toolbar, animation, timeline, geocoder,
fullscreen, info-box, selection indicator) are all hidden. Playback is
driven by **our** clock, footer, and timeline.

## Satellites

Per scenario satellite, an entity with:

- **Position** — `SampledPositionProperty` populated by satellite.js
  SGP4 propagation at **30 s** sampling over the whole scenario span.
  Cesium interpolates smoothly between samples at any clock multiplier.
- **Point** — 6 px disc, color by vendor.
- **Path** — trailing **20-minute** orbit ribbon. Full ground tracks
  are *not* drawn — at 100+ sats they become visual noise.

| Vendor | Color |
|---|---|
| BlackSky | `#4cc4d8` cyan |
| Planet | `#5fb87a` green |
| Capella Space | `#f0a020` amber |
| ICEYE | `#e07b3c` orange |
| Vantor (Maxar) | `#9d7cd8` violet |

**Hover** any sat: name, NORAD ID, constellation, vendor, sensor class.
**Click** a sat: opens the satellite-selection panel; press `F` to
follow it with the camera.

## Locations & event pulses

The 15 Hormuz locations render as small ground markers with hover
labels. Hover or click for name + kind + country.

Events render as **pulsing ground rings** sized by severity. A ring
becomes visible at `t = event.t_hours − 0.5h`, expands and stays at
full intensity through `t = event.t_hours + min(6h, ltiov_hours)`,
then fades out over the next 4 hours.

Severity color palette:

| Sev | Color | Meaning |
|---|---|---|
| 1 | `#4cc4d8` cyan | background / nuisance |
| 2 | `#5fb87a` green | routine |
| 3 | `#f0a020` amber | notable |
| 4 | `#e07b3c` orange | high |
| 5 | `#e55a3c` red | critical |

## Coverage swaths and tethers

For every **scheduled** allocation, the viewer draws:

1. A **swath polygon** (ground ellipse) at the bid's target, sized by
   the satellite's `swath_width_km`. Visible only during the window's
   `[start_iso, end_iso]`. Trapezoidal fade at the edges so it reads
   as smooth on/off.
2. A **dashed polyline** from the satellite's live position to the
   target during the same interval — the "this sat is taking the
   shot" tether.

Color by allocation status:

| Status | Color | Visual |
|---|---|---|
| `SCHEDULED` | accent cyan `#4cc4d8` | low-alpha fill, dashed tether |
| `COLLECTED` | green `#5fb87a` | brighter fill |
| `DEADLINE_MISSED` | red `#e55a3c` | red outline |

Dropped allocations get no on-globe visual — they appear in the side
panel against the source bid (red `DROPPED` label with the mechanism's
notes).

## Side panel

Four blocks, top to bottom:

### Stats

A grid of scenario aggregates. All come from `scenario.meta`:

```
events       n_events
bids         n_bids
satellites   n_satellites
windows      n_access_windows
allocations  n_allocations
scheduled    n_scheduled
dropped      n_dropped
drop rate    drop_rate × 100%
welfare      total_welfare
mechanism    mechanism
```

### Constellations

Per-vendor checkbox filter. Default all on; uncheck a row to hide its
satellites and orbit ribbons. The count next to each row is the number
of sats in that constellation.

### Selection

Empty until you click something. Three flavors:

- **Event selection.** Full event metadata + the bid card for every
  derived bid. Each bid card shows stakeholder, priority, rationale,
  AND the allocation outcome — sat_id (clickable), window time,
  quality score, welfare contribution, mechanism. DROPPED bids show
  the mechanism's drop notes in red. Clicking the sat link in a bid
  card snaps the clock to the window's start, locks the camera onto
  the sat, and switches the panel to the satellite-selection view.

- **Satellite selection.** Sensor specs (vendor, class, GSD, swath,
  bands, max off-nadir) plus a scrollable list of every access window
  for the sat. Scheduled windows are starred (`★`); clicking a starred
  row jumps the clock to that window's start.

- **Location selection.** Name, country, lat/lon. (Lightweight — the
  v0.1 LOCATIONS table doesn't carry much else.)

### Event feed

Scrollable list of all events sorted by `t_hours`. Each row: time,
severity (color-coded), event ID + type, narrative, location + phase.
Scripted events are marked in cyan. Click any row to fly the camera,
snap the clock, and fill the selection panel.

## Timeline

Four lanes inside a 1000×180 viewBox:

```
y =   0..30  ▓▓▓ Phase bands (color by phase) — labels + rate ×
y =  32..50  Day ticks  D0 D1 D2 …
y =  52..120 ━ Event ticks (severity-colored, height ~ severity × 12)
y = 122..168 ▮▮▮ Access-window density histogram
                  scheduled (cyan) stacked on dropped (muted) — 15-min buckets
```

Click anywhere outside an event tick to **scrub** the playhead. Click
an event tick to fly the camera to that event. The cyan playhead line
moves with the Cesium clock.

## Footer

| Control | Action |
|---|---|
| ▶ PLAY / ▮▮ PAUSE | toggle Cesium clock animation |
| ▮ RESET | clock → start of scenario, paused |
| 60× / 300× / 1800× / 3600× | clock speed multiplier |

A 168 h scenario at 1800× plays through in ~5.6 minutes. At 3600× in
~2.8 minutes.

## Keyboard

| Key | Action |
|---|---|
| `Space` | play / pause |
| `←` / `→` | scrub by ±1 h |
| `R` | reset to t=0 |
| `F` | follow currently-selected sat with the camera |

## URL flags

| Flag | Effect |
|---|---|
| `?scenario=<url>` | load a different scenario JSON |

`window.RAVENEYE_SCENARIO_URL` accomplishes the same thing from a
wrapper page (useful for embedding).

## Deploying

The staged directory is fully self-contained:

- `index.html` (and the v0.1 fallback when staged with `--legacy-flat-map`)
- `scenario.json`
- `style.css`, `main.js`, `orbits.js`, `ground.js`, `coverage.js`,
  `panels.js`, `timeline.js`

Drop it on any static host. Tested deployments:

- `python3 -m http.server` (local)
- Render Static Site (build command + publish dir; see README)
- GitHub Pages
- S3 + CloudFront

The only outbound network requests at runtime are:

- **Google Fonts** (JetBrains Mono, IBM Plex Sans) — graceful fallback
  to system mono / sans if blocked.
- **jsDelivr** (Cesium + satellite.js JS bundles).
- **OpenStreetMap tile servers** — Cesium's imagery layer.

If your environment air-gaps these, mirror the three CDN bundles +
swap in a local imagery provider in `main.js`.

## Performance notes

- Per-satellite SampledPositionProperty buffers ~20,000 samples for a
  168 h scenario at 30 s sampling. With 100 sats that's ~2M samples in
  memory — Cesium handles this comfortably on a modern laptop GPU.
- Coverage swaths and tethers are CallbackProperty-driven, so they
  don't allocate per-frame; only the visibility result changes.
- Constellation visibility filter toggles `entity.show` on the orbit
  ribbons, which is essentially free (no scene-graph rebuild).

If you push beyond ~250 sats and feel the framerate dip, the cheapest
wins are: lower the SGP4 sample step from 30 s to 60 s in `orbits.js`
(`SAMPLE_S`), and shorten the orbit ribbon trail from 20 min to 10 min
(`RIBBON_MIN`).

## BOARD tab — Gantt + Kanban

A second top-level page in the viewer, accessed via the **BOARD** tab
in the header. Two coordinated views on the same allocation set, both
driven by the playback clock that drives the GLOBE view.

### Gantt (top half)

One row per target location, sorted by allocation count desc — the
busiest target sits at the top. Each scheduled allocation renders as
a horizontal bar that spans collection → processing → in-transit →
delivered. The four lifecycle stages are nested colored segments:

| Segment | Color | Stage |
|---|---|---|
| Outer fill | cyan `#4cc4d8` | COLLECTING (the access window itself) |
| Inner stripe at center | amber `#f0a020` | PROCESSING (window end → processing complete) |
| Inner stripe at center, narrower | orange `#e07b3c` | IN_TRANSIT (processing → delivered) |
| Terminal circle at right edge | per status | final outcome |

Bar height encodes bid priority — taller bars are higher-priority
work. A vertical cyan playhead tracks the Cesium clock; scrub the
bottom timeline to see exactly where in each delivery cycle you are.

Hover any bar to see bid_id, sat_id, priority, terminal status, and
delivery timestamp.

### Kanban (bottom half)

Five flow columns showing where each scheduled allocation sits *right
now* given the playback clock:

```
BIDDED → COLLECTING → PROCESSING → IN_TRANSIT → DELIVERED
```

Cards advance left-to-right as the clock moves forward. Within each
column, cards are sorted by priority desc — so the top card in the
**BIDDED** column is always the highest-priority bid that hasn't
collected yet, i.e. the next-up tasking.

Each card shows:

- `bid_id` (linkable color)
- priority score (amber)
- target location ID
- assigned satellite + window start time

Below the five-column flow there's a **TERMINAL FAILURES** lane that
shows the three terminal failure modes from the delivery pipeline:

- `DEADLINE_MISSED` — image delivered after LTIOV
- `PROCESSING_FAILED` — collection happened, processing pipeline rejected
- `DROPPED` — mechanism couldn't match the bid to any window

Cards never re-enter the flow once they're in a terminal column.

Columns cap at 60 cards each (with a "… and N more" footer) so the
700+ allocation full-week scenario doesn't lock up the DOM. The
Kanban re-buckets every 500 ms of real time during playback.

## RTB drawer

Press the **RTB** button next to the brand mark (or press `?`) to
open the architecture explainer drawer. A 560-px-wide panel slides in
from the left and walks through:

1. **Why RTB.** The case for treating multi-constellation EO tasking
   as a real-time auction.
2. **The four-layer architecture** with live counts at each layer
   (DEMAND → SUPPLY → MECHANISM → DELIVERY) pulled from
   `scenario.meta`.
3. **One section per layer** with definition-list aggregates.
4. **What this unblocks** — the closing argument for v0.3+ research
   work.

Press `Esc` or click outside the drawer to dismiss. The drawer is
**not** modal — playback continues behind it, and the ESC/click-out
behavior leaves the clock and globe state untouched.
