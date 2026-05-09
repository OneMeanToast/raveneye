# RavenEye

**Multi-constellation EO tasking simulation** for evaluating satellite-tasking
allocation mechanisms under realistic military collection demand.

RavenEye is *not* a tasker, not an orchestration product, and not a competitor
to Palantir MetaConstellation. It is an **evaluation environment** — the thing
that tells you which tasking design survives contact with real operational
tempo.

**v0.2.1** is the current release. Layered on top of v0.2:

- **Multi-constellation offline TLE fixture** — 36 satellites across all
  six vendors (BlackSky, SkySat, Planet Dove, Capella, ICEYE, Maxar)
  for demos that don't have CelesTrak access. New CLI flag
  `--tle-fixture-dir`.
- **Image-delivery pipeline** — every allocation gets a `lifecycle`
  sub-dict with collection / processing / delivery timestamps and a
  terminal status: `DELIVERED`, `DEADLINE_MISSED`, `PROCESSING_FAILED`,
  or `DROPPED`. Per-vendor processing & delivery latencies; success
  rate modulated by access-window quality. See
  `docs/delivery_pipeline.md`.
- **RTB / architecture explainer drawer** — toggleable side panel
  (RTB button or `?` key) that walks a prospect through the four-layer
  architecture with live numbers from the loaded scenario.
- **BOARD tab** — second top-level page in the viewer with a per-target
  Gantt of allocated windows + a five-column Kanban tasking flow,
  both clock-driven.

**v0.2** added the supply layer (TLEs, SGP4 propagation, access windows),
the mechanism layer (greedy + sequential single-item auction), and the
CesiumJS globe viewer. **v0.1** shipped the demand layer (events,
stakeholder bids, phase tempo, flat choke-point map).

## Install

```
pip install -e ".[dev]"
```

Python 3.10+ (tested on 3.10–3.14). v0.2 runtime deps: `skyfield`, `sgp4`,
`requests`, `numpy`. `[dev]` adds `pytest` and `pytest-cov`.

## v0.1 — flat choke-point map (still useful for embeds)

```
raveneye-generate --seed 42 --out viewer_out/sim.json --viewer viewer_out
cd viewer_out && python3 -m http.server
```

Open <http://localhost:8000/>. The flat viewer shows events, stakeholder bids,
the 5-phase Hormuz arc, and a click-to-inspect side panel. No satellites — that
arrives in v0.2.

## v0.2 — full scenario + globe

Multi-constellation, fully offline (recommended starting point — 36 sats
across all 6 vendors, no CelesTrak access required):

```
raveneye-build-scenario --seed 42 --duration 168 --mechanism ssi \
  --tle-fixture-dir tests/fixtures/multi_tles \
  --out viewer_out/scenario.json --viewer viewer_out
cd viewer_out && python3 -m http.server
```

Single-constellation offline (5 sats, smaller demo):

```
raveneye-build-scenario --seed 42 --duration 168 --mechanism ssi \
  --tle-fixture tests/fixtures/tles.txt \
  --out viewer_out/scenario.json --viewer viewer_out
```

For network-fetched TLEs (production, requires CelesTrak access):

```
raveneye-build-scenario --seed 42 --duration 168 --mechanism ssi \
  --out data/sample_scenario.json --viewer viewer_out
```

Open <http://localhost:8000/>. The globe viewer shows the Earth, all
scenario satellites propagating live, orbit ribbons by vendor, ground markers
for the 15 Hormuz locations, **pulsing event rings** at occurrence, **swath
polygons drawn during scheduled access windows** with a dashed sat-to-target
tether, the per-event allocation panel showing every derived bid alongside
which sat / window serves it (including the full delivery lifecycle —
captured → processed → delivered with per-vendor latencies), and an
access-window density histogram on the timeline.

Two tabs in the header — **GLOBE** and **BOARD** — flip between the
3D view and a Gantt + Kanban tasking flow on the same data. Press the
**RTB** button (or `?`) to open the architecture explainer drawer.

`--legacy-flat-map` stages the v0.1 flat map with the v0.2 scenario JSON
(handy for embeds that don't want a 3D globe).

## Flags reference

`raveneye-generate`:

| Flag | Default | Notes |
|---|---|---|
| `--seed` | `42` | RNG seed. |
| `--duration` | `168.0` | Hours. |
| `--out` | `sim.json` | Output JSON path. |
| `--viewer` | *(off)* | Stage flat-map viewer at this directory. |
| `--stats` | *(off)* | Print summary stats to stderr. |

`raveneye-build-scenario`:

| Flag | Default | Notes |
|---|---|---|
| `--seed` | `42` | RNG seed. |
| `--duration` | `168.0` | Hours. |
| `--mechanism` | `greedy` | `greedy` or `ssi`. |
| `--out` | `scenario.json` | Output JSON path. |
| `--viewer` | *(off)* | Stage globe viewer at this directory. |
| `--legacy-flat-map` | *(off)* | Stage flat map instead of globe. |
| `--cache-dir` | `data/tle_cache` | TLE cache directory. |
| `--refresh-tles` | *(off)* | Bypass TLE cache. |
| `--tle-fixture` | *(off)* | Use this offline TLE file instead of CelesTrak (single constellation). |
| `--fixture-constellation` | `blacksky` | Tag fixture sats with this constellation (single-constellation mode only). |
| `--tle-fixture-dir` | *(off)* | Scan this directory for `<constellation_id>.txt` files; multi-constellation offline mode. Mutually exclusive with `--tle-fixture`. |
| `--min-elevation` | `20.0` | Minimum access-window elevation (deg). |
| `--stats` | *(off)* | Print summary stats. |

## Repo layout (v0.2)

```
raveneye/
├── raveneye/
│   ├── cli/
│   │   ├── generate.py             # raveneye-generate (v0.1)
│   │   └── build_scenario.py       # raveneye-build-scenario (v0.2)
│   ├── sim/                        # demand layer (v0.1)
│   │   ├── events.py
│   │   ├── locations.py
│   │   ├── phases.py
│   │   ├── scripted.py
│   │   ├── stochastic.py
│   │   ├── stakeholders.py
│   │   ├── bids.py
│   │   └── build.py
│   ├── orbital/                    # supply layer (v0.2)
│   │   ├── constellations.py
│   │   ├── tle_ingest.py
│   │   ├── propagate.py
│   │   ├── access.py
│   │   ├── coverage.py
│   │   └── build.py
│   ├── mechanism/                  # allocation layer (v0.2)
│   │   ├── base.py                 # Allocation, Mechanism Protocol, match
│   │   ├── greedy.py               # GreedyPriorityMechanism
│   │   ├── ssi.py                  # SequentialSingleItemMechanism
│   │   └── build.py                # allocate(...) entry point + welfare
│   ├── scenario/                   # unified builder (v0.2)
│   │   └── build.py                # build_full_scenario, _offline
│   └── viewer/
│       ├── template.html           # v0.1 flat map (kept for embeds)
│       ├── build_viewer.py         # stage_viewer(kind="flat"|"globe")
│       └── globe/                  # v0.2 CesiumJS viewer
│           ├── index.html
│           ├── style.css
│           ├── main.js             # boot, clock, camera, control wiring
│           ├── orbits.js           # satellite.js + orbit ribbons
│           ├── ground.js           # location markers + event pulses
│           ├── coverage.js         # swath polygons + sat-target tethers
│           ├── panels.js           # stats / filter / selection / feed
│           └── timeline.js         # phases, ticks, AW density, playhead
├── data/
│   ├── sample_sim.json             # canonical v0.1 reference (seed=42)
│   ├── sample_scenario.json        # canonical v0.2 reference (seed=42)
│   └── tle_cache/.gitkeep
├── tests/
│   ├── fixtures/tles.txt           # 5-sat offline fixture
│   ├── test_events.py / test_bids.py / test_phases.py / test_determinism.py
│   ├── test_constellations.py / test_tle_ingest.py
│   ├── test_propagate.py / test_access.py / test_coverage.py
│   ├── test_supply_build.py / test_scenario_build.py
│   ├── test_mechanism_greedy.py / test_mechanism_ssi.py
│   └── test_viewer_staging.py
├── scripts/
│   └── verify_position_agreement.py  # Python↔JS ≤1km agreement table
└── docs/
    ├── architecture.md
    ├── event_taxonomy.md
    ├── bidding_interface.md
    ├── mechanism_interface.md
    ├── orbital_model.md
    └── viewer_guide.md
```

## Concepts

### The four-layer model

| Layer | Role | Status |
|---|---|---|
| Demand | Events × stakeholders → bids | ✅ v0.1 |
| Supply | TLEs × targets → access windows | ✅ v0.2 |
| Mechanism | Bids + access windows → allocations | ✅ v0.2 (greedy + SSI) |
| Evaluation | Welfare metrics, A/B comparison | v0.3+ |

### The two non-negotiable distinctions

- **Event ≠ Bid.** Events are world-state changes; bids are stakeholders'
  reactions to events through their utility weights. Same event, different
  stakeholders, different priority scores. Multi-utility structure is the
  point of the sim.
- **Demand ≠ Supply ≠ Mechanism.** Three separable data flows. A bid module
  doesn't parse TLEs; an event generator doesn't allocate; a mechanism
  consumes both bids and windows. Swapping one layer doesn't cascade.

### Scripted backbone + stochastic injects

20 hand-curated narrative anchors (`SCR-NNN`) plus seeded Poisson injects
(`STO-NNNN`). Both kinds derive bids the same way.

### Phases

The 7-day Hormuz arc walks through 5 phases, each with a rate multiplier:

| Phase | Start (h) | Rate × |
|---|---|---|
| BLOCKADE_ACTIVE | 0 | 1.0 |
| ESCALATION | 36 | 2.2 |
| CEASEFIRE_ANNOUNCED | 72 | 0.4 |
| CEASEFIRE_COLLAPSE | 96 | 2.8 |
| BLOCKADE_REINFORCED | 132 | 1.6 |

## Reproducibility

Both reference outputs are committed:

- `data/sample_sim.json` — v0.1 demand-only output (seed=42, 168h)
- `data/sample_scenario.json` — v0.2 unified output (seed=42, 168h,
  mechanism=greedy). Built from `tests/fixtures/tles.txt` — the offline
  5-sat fixture — so the byte-equality determinism test is independent
  of CelesTrak TLE drift. For a production-quality scenario, regenerate
  with live TLEs:
  ```
  raveneye-build-scenario --seed 42 --out data/sample_scenario.json --refresh-tles
  ```

Tests pin invariants against `seed=42`. If you change demand, supply, or
mechanism logic, regenerate the affected reference file and review the diff.

## Deploying the viewer

The staged directory is fully self-contained: HTML + JS + CSS + JSON. Drop it
on any static host. Render Static Site build command:

```
pip install -e . && raveneye-build-scenario --seed 42 \
  --tle-fixture tests/fixtures/tles.txt \
  --out site/scenario.json --viewer site
```

Publish directory: `site`. Add a `runtime.txt` with `python-3.12.x` if your
host's auto-detect picks the wrong Python.

## Docs

- `docs/architecture.md` — four-layer model, dataflow, why-demand-first.
- `docs/event_taxonomy.md` — per-EventType definition + doctrinal analog.
- `docs/bidding_interface.md` — bid I/O contract for downstream mechanisms.
- `docs/mechanism_interface.md` — Mechanism Protocol, Allocation schema,
  worked greedy-vs-SSI example, how to add a new mechanism.
- `docs/orbital_model.md` — TLE/OMM, SGP4 accuracy, access windows, quality
  scoring, vendor-spec citations, OMM transition note.
- `docs/delivery_pipeline.md` — image-delivery state machine, per-vendor
  latencies, quality-modulated success rate, lifecycle aggregates,
  determinism guarantees.
- `docs/viewer_guide.md` — globe layout, side panels, timeline lanes,
  coverage tether, BOARD tab (Gantt + Kanban), RTB drawer, keyboard,
  URL flags, deploy notes.

## What's next

- **v0.3** — evaluation layer: welfare metrics, A/B comparison harness,
  multi-seed sweeps. CBBA / VCG / ILP combinatorial mechanisms. See
  `TODO.md` for the parking lot.

## License

MIT. See `LICENSE`.
