# RavenEye — Build Spec (v0.1 + v0.2)

> **Handoff note.** This spec was produced in a planning session with Claude (claude.ai) and supersedes earlier drafts. Read Section 1 (Context) before touching code. The spec is big on purpose — Claude Code should see the whole system shape before building, so later work doesn't contradict earlier choices.

**Target repo:** `https://github.com/OneMeanToast/raveneye` (currently empty)
**License:** MIT
**Python:** 3.10+
**Ship in two tagged releases:**
- **v0.1 — Demand layer.** Events, bids, 2D choke-point viewer for the Hormuz scenario. The RPG table.
- **v0.2 — Supply + Mechanism + Globe viewer.** TLEs, access windows, allocation core, 3D CesiumJS globe. The game running on the table.

**Ship v0.1 first and tag it.** It stands alone as a demo. v0.2 extends cleanly on top of it and should not require breaking changes to v0.1 data shapes.

---

## 1. Context — read this first

### 1.1 What RavenEye is
RavenEye is a **multi-constellation EO tasking simulation** for evaluating satellite-tasking allocation mechanisms under realistic military collection demand. It is explicitly **not** a tasker, not an orchestration product, and not a competitor to Palantir MetaConstellation. The positioning is *evaluation environment*: the thing that tells you which tasking design survives contact with real operational tempo.

### 1.2 Three layers
The research thesis separates the system into four logical layers. This spec builds the first three:

| Layer | Role | v0.1 | v0.2 |
|---|---|---|---|
| Demand | Events → weighted bids | ✅ | (reused) |
| Supply | Real orbits + access windows | — | ✅ |
| Mechanism | Allocation algorithms | — | ✅ |
| Evaluation | Metrics, comparison | (manual) | (basic; v0.3) |

### 1.3 The central design distinction: event ≠ bid
**Don't collapse them.** Events are world-state changes. Bids are what stakeholders produce when they observe events through their own utility function. Same event, different stakeholders, different priority scores. This multi-utility structure is the point of the sim — it's what a single-stakeholder benchmark can't capture.

### 1.4 The second central distinction: demand ≠ supply ≠ mechanism
In v0.2, keep these three data flows clean:
- **Demand** produces `bids` (from events × stakeholders).
- **Supply** produces `access_windows` (from TLEs × targets).
- **Mechanism** consumes *both* and produces `allocations`.

If you find yourself computing allocations inside the event generator, or pulling TLE parsing into the bid module, stop. The layers exist so that swapping one (e.g. trying a different auction algorithm) doesn't require changing the others.

### 1.5 Scripted backbone + stochastic injects
The event stream is two-layered:
- **Scripted beats** (~20 events) are hand-curated narrative anchors. Same every run. IDs: `SCR-NNN`.
- **Stochastic injects** are seeded Poisson draws scaled by scenario phase. IDs: `STO-NNNN`.

**Seed determinism is a hard requirement.** Same seed must produce identical output across runs. There's a test for this.

### 1.6 Scope discipline
Don't build beyond this spec. Specifically:
- **v0.1:** no TLEs, no globe, no auctions. Just events, bids, and a flat choke-point map.
- **v0.2:** TLEs, access windows, globe, and one or two allocation mechanisms. No Foundry integration yet, no Cesium ion paid services, no classified data.

If you notice obvious follow-ups, add them to `TODO.md` or GitHub issues — don't implement them.

---

## 2. Target repo layout (final state after v0.2)

```
raveneye/
├── README.md
├── LICENSE                          # MIT
├── .gitignore
├── pyproject.toml                   # pip-installable; exposes CLI
├── raveneye/
│   ├── __init__.py
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── generate.py              # v0.1 CLI entry
│   │   └── build_scenario.py        # v0.2 CLI entry
│   ├── sim/                         # v0.1: demand layer
│   │   ├── __init__.py
│   │   ├── events.py                # Event, EventType, ObservableKind
│   │   ├── locations.py             # LOCATIONS, SENSOR_REQUIREMENTS
│   │   ├── phases.py                # Phase, PHASES, phase_at
│   │   ├── scripted.py              # SCRIPTED_BEATS
│   │   ├── stochastic.py            # BASE_RATES, sample_stochastic_event
│   │   ├── stakeholders.py          # Stakeholder, STAKEHOLDERS
│   │   ├── bids.py                  # Bid, derive_bids
│   │   └── build.py                 # build_events, build_sim, DEFAULT_T0
│   ├── orbital/                     # v0.2: supply layer
│   │   ├── __init__.py
│   │   ├── constellations.py        # Constellation metadata, CONSTELLATIONS list
│   │   ├── tle_ingest.py            # CelesTrak fetch + cache + OMM fallback
│   │   ├── propagate.py             # Skyfield wrapper; SGP4 propagation
│   │   ├── access.py                # find_access_windows()
│   │   ├── coverage.py              # instantaneous coverage cone math
│   │   └── build.py                 # build_supply()
│   ├── mechanism/                   # v0.2: allocation layer
│   │   ├── __init__.py
│   │   ├── base.py                  # Allocation; Mechanism protocol; match helper
│   │   ├── greedy.py                # GreedyPriorityMechanism (baseline)
│   │   ├── ssi.py                   # SequentialSingleItemMechanism
│   │   └── build.py                 # allocate(bids, access_windows, mechanism)
│   ├── scenario/                    # v0.2: unified scenario builder
│   │   ├── __init__.py
│   │   └── build.py                 # build_full_scenario()
│   └── viewer/
│       ├── __init__.py
│       ├── build_viewer.py          # stage_viewer()
│       ├── template.html            # v0.1 flat map viewer (kept for embeds)
│       └── globe/                   # v0.2 globe viewer (replaces as default)
│           ├── index.html
│           ├── main.js              # Cesium + satellite.js wiring
│           ├── orbits.js            # orbit rendering, ground tracks
│           ├── coverage.js          # sensor cone / swath rendering
│           ├── timeline.js          # playback + access-window display
│           ├── panels.js            # event feed, bid panel, allocation panel
│           └── style.css
├── tests/
│   ├── __init__.py
│   ├── fixtures/
│   │   └── tles.txt                 # committed 5-sat sample for tests (offline)
│   ├── test_events.py               # v0.1
│   ├── test_bids.py                 # v0.1
│   ├── test_determinism.py          # v0.1 + v0.2
│   ├── test_phases.py               # v0.1
│   ├── test_tle_ingest.py           # v0.2
│   ├── test_propagate.py            # v0.2
│   ├── test_access.py               # v0.2
│   ├── test_mechanism_greedy.py     # v0.2
│   └── test_mechanism_ssi.py        # v0.2
├── data/
│   ├── sample_sim.json              # v0.1 reference output (seed=42)
│   ├── sample_supply.json           # v0.2 reference access-window set
│   ├── sample_scenario.json         # v0.2 combined scenario
│   └── tle_cache/                   # v0.2; contents gitignored, dir kept via .gitkeep
└── docs/
    ├── architecture.md
    ├── event_taxonomy.md
    ├── bidding_interface.md
    ├── orbital_model.md             # v0.2: TLE, SGP4, access windows
    ├── mechanism_interface.md       # v0.2: how to plug in a new mechanism
    └── viewer_guide.md              # v0.2: what the globe view shows and why
```

---

## 3. Data-flow contract (the North Star for v0.2)

All layers exchange plain JSON objects. Schemas below are the v0.2 targets; v0.1 only populates `events`, `bids`, `locations`, `stakeholders`, `phases`, `meta`.

### 3.1 Scenario JSON (top-level output)
```json
{
  "meta": {
    "scenario": "Strait of Hormuz Blockade Arc (Apr 2026)",
    "t0_iso": "2026-04-13T12:00:00+00:00",
    "duration_hours": 168.0,
    "seed": 42,
    "n_events": 173,
    "n_bids": 692,
    "n_satellites": 112,
    "n_access_windows": 4821,
    "n_allocations": 428,
    "phases": [...]
  },
  "locations": {...},
  "stakeholders": [...],
  "constellations": [...],     // v0.2
  "satellites": [...],         // v0.2
  "events": [...],
  "bids": [...],
  "access_windows": [...],     // v0.2
  "allocations": [...]         // v0.2
}
```

### 3.2 Satellite object (v0.2)
```json
{
  "sat_id": "BLACKSKY-14",
  "norad_id": 56216,
  "constellation_id": "blacksky",
  "vendor": "BlackSky",
  "tle_line1": "1 56216U ...",
  "tle_line2": "2 56216 ...",
  "tle_epoch_iso": "2026-04-12T08:14:32+00:00",
  "sensor_class": "EO_HIGHRES",
  "nominal_gsd_m": 1.0,
  "spectral_bands": ["PAN", "MS"],
  "max_off_nadir_deg": 45.0,
  "swath_width_km": 5.5,
  "slew_rate_deg_s": 1.0,
  "duty_cycle_pct": 20.0
}
```

### 3.3 Access window object (v0.2)
A window is a time span during which a specific satellite can feasibly image a specific target.
```json
{
  "window_id": "AW-00000",
  "sat_id": "BLACKSKY-14",
  "target_lat": 25.900,
  "target_lon": 54.508,
  "target_id": "siri_island",       // optional; present when target is a named location
  "start_iso": "2026-04-13T18:42:12+00:00",
  "end_iso": "2026-04-13T18:49:03+00:00",
  "duration_s": 411.0,
  "max_elevation_deg": 62.4,
  "sun_elevation_deg": 23.1,
  "quality_score": 0.78             // 0..1 composite: elevation, sun angle, off-nadir
}
```

### 3.4 Allocation object (v0.2)
Output of the mechanism layer. One allocation = one bid matched to one access window.
```json
{
  "allocation_id": "ALLOC-00042",
  "bid_id": "BID-00123",
  "window_id": "AW-00857",
  "mechanism": "greedy_priority",
  "status": "COLLECTED",            // or SCHEDULED, DROPPED, DEADLINE_MISSED
  "priority_score": 8.32,
  "decision_t_iso": "2026-04-13T17:55:00+00:00",
  "notes": "Highest-priority bid within window; no conflicts."
}
```

Dropped bids (mechanism couldn't match them to any window) still get an allocation record with `status = "DROPPED"` and `window_id = null`. This makes metrics and the viewer's "here's what got dropped" panel trivial to compute.

---

## 4. v0.1 — Demand layer (ship this first)

### Phase A — Skeleton & tooling
- [ ] **A1.** Create directory tree from section 2 (v0.1 subset: `raveneye/cli`, `raveneye/sim`, `raveneye/viewer`, `tests`, `data`, `docs`). `.gitignore` covers `__pycache__/`, `*.egg-info/`, `.pytest_cache/`, `.venv/`, `build/`, `dist/`, `viewer_out/`, `globe_out/`, `data/tle_cache/*` (keep the dir via `.gitkeep`), `.DS_Store`, IDE files.
- [ ] **A2.** `LICENSE` — standard MIT, "RavenEye contributors", current year.
- [ ] **A3.** `pyproject.toml` — setuptools backend, name `raveneye`, version `0.1.0`, Python `>=3.10`. Runtime deps for v0.1: none (keep it pure-Python stdlib). Dev extras: `pytest`, `pytest-cov`. Console script: `raveneye-generate = raveneye.cli.generate:main`. Packages include `raveneye`, `raveneye.cli`, `raveneye.sim`, `raveneye.viewer`.
- [ ] **A4.** `raveneye/__init__.py` → `__version__ = "0.1.0"`.

### Phase B — Core data model

- [ ] **B1. `raveneye/sim/events.py`.**
  - `EventType` str-enum with 11 members, each with a doctrinal-analog docstring:
    `KINETIC_STRIKE`, `MINE_LAYING_REPORT`, `NAVAL_POSTURE_CHANGE`, `MOVEMENT_DETECTED`, `VESSEL_DARK`, `BLOCKADE_RUNNER`, `HUMINT_REPORT`, `SIGINT_CUE`, `WEATHER_DEGRADATION`, `DIPLOMATIC_STATUS_CHANGE`, `FACILITY_ANOMALY`.
  - `ObservableKind` str-enum: `VESSEL`, `PORT_FACILITY`, `REFINERY`, `MILITARY_BASE`, `ROUTE_SEGMENT`, `WIDE_AREA`, `AIRFIELD`.
  - `Event` dataclass: `event_id`, `t_iso`, `t_hours` (float), `event_type`, `location_id`, `lat`, `lon`, `observable_kind`, `severity` (int 1–5), `source_confidence` (float 0–1), `ltiov_hours`, `narrative`, `phase`, `scripted` (bool), `payload` (dict, default empty).

- [ ] **B2. `raveneye/sim/locations.py`.** `LOCATIONS` dict — 15 real Hormuz-region places. Each entry: `name`, `kind`, `lat`, `lon`, `country`. Full list (use coordinates verbatim):
  - `bandar_abbas_naval` (MILITARY_BASE, 27.129, 56.217, IR) "Bandar Abbas Naval Base"
  - `bandar_jask` (MILITARY_BASE, 25.644, 57.776, IR) "Bandar-e Jask Naval Base"
  - `qeshm_island` (MILITARY_BASE, 26.954, 56.270, IR) "Qeshm Island IRGC Facilities"
  - `larak_island` (WIDE_AREA, 26.867, 56.367, IR) "Larak Island"
  - `hormuz_island` (WIDE_AREA, 27.093, 56.462, IR) "Hormuz Island"
  - `kharg_terminal` (REFINERY, 29.232, 50.325, IR) "Kharg Island Oil Terminal"
  - `siri_island` (REFINERY, 25.900, 54.508, IR) "Siri Island Storage"
  - `bandar_mahshahr` (REFINERY, 30.558, 49.198, IR) "Bandar Mahshahr Petrochemical"
  - `fujairah_port` (PORT_FACILITY, 25.162, 56.358, AE) "Port of Fujairah"
  - `jebel_ali` (PORT_FACILITY, 25.013, 55.062, AE) "Jebel Ali Port"
  - `ras_laffan` (REFINERY, 25.919, 51.568, QA) "Ras Laffan LNG Terminal"
  - `ras_tanura` (REFINERY, 26.642, 50.154, SA) "Ras Tanura Refinery"
  - `mina_sulman` (MILITARY_BASE, 26.203, 50.613, BH) "Mina Sulman / NSA Bahrain"
  - `strait_chokepoint` (WIDE_AREA, 26.567, 56.250, INTL) "Strait of Hormuz Narrowest Point"
  - `gulf_of_oman_outbound` (WIDE_AREA, 25.200, 57.500, INTL) "Gulf of Oman Approach"

  `SENSOR_REQUIREMENTS` dict by ObservableKind: VESSEL {gsd_m:0.5, band:"EO_PAN", revisit_h:6}, PORT_FACILITY {0.5, "EO_MS", 12}, REFINERY {1.0, "EO_MS+TIR", 12}, MILITARY_BASE {0.3, "EO_PAN", 8}, ROUTE_SEGMENT {1.0, "EO_MS", 4}, WIDE_AREA {3.0, "SAR_X", 6}, AIRFIELD {0.5, "EO_PAN", 8}.

- [ ] **B3. `raveneye/sim/phases.py`.** `Phase` dataclass. `PHASES` list — 5 phases: `BLOCKADE_ACTIVE` @0h mult 1.0, `ESCALATION` @36h mult 2.2, `CEASEFIRE_ANNOUNCED` @72h mult 0.4, `CEASEFIRE_COLLAPSE` @96h mult 2.8, `BLOCKADE_REINFORCED` @132h mult 1.6. `phase_at(t_hours)` returns active phase; before-start returns first phase; half-open intervals.

- [ ] **B4. `raveneye/sim/scripted.py`.** `SCRIPTED_BEATS` — exactly 20 beats. The narrative text **is the demo** — write it well, grounded in the April 2026 Hormuz arc. Required beats in order:

  1. `t=2.0h` DIPLOMATIC_STATUS_CHANGE @ strait_chokepoint, sev 4, conf 0.99, ltiov 24h — CENTCOM reaffirms blockade.
  2. `t=5.5h` VESSEL_DARK @ strait_chokepoint, sev 3, conf 0.85, ltiov 8h — VLCC (payload `imo`, `last_flag:"PA"`, `last_speed_kn:11.3`) turned off AIS near Larak.
  3. `t=11.0h` KINETIC_STRIKE @ gulf_of_oman_outbound, sev 4, conf 0.90, ltiov 6h — container ship hit by projectile, BDA required (payload `vessel_type:"CONTAINER"`).
  4. `t=14.0h` NAVAL_POSTURE_CHANGE @ bandar_abbas_naval, sev 4, conf 0.75, ltiov 12h — IRGCN fast-boat surge.
  5. `t=38.0h` MINE_LAYING_REPORT @ strait_chokepoint, sev 5, conf 0.70, ltiov 4h — IRGC minelayer activity in TSS lane overnight.
  6. `t=41.5h` KINETIC_STRIKE @ siri_island, sev 5, conf 0.95, ltiov 8h — storage tank struck, ~1M bbl facility (payload `target_class:"OIL_STORAGE"`).
  7. `t=48.0h` HUMINT_REPORT @ bandar_mahshahr, sev 3, conf 0.55, ltiov 36h — tanker truck convoy, possible fuel diversion.
  8. `t=52.0h` MOVEMENT_DETECTED @ qeshm_island, sev 4, conf 0.80, ltiov 10h — 6+ vehicles off Qeshm garrison, possible CM launchers.
  9. `t=61.0h` WEATHER_DEGRADATION @ strait_chokepoint, sev 3, conf 0.92, ltiov 14h — dust/haze forecast window.
  10. `t=72.5h` DIPLOMATIC_STATUS_CHANGE @ strait_chokepoint, sev 3, conf 0.95, ltiov 72h — ceasefire; strait "fully open."
  11. `t=80.0h` FACILITY_ANOMALY @ kharg_terminal, sev 3, conf 0.88, ltiov 24h — thermal ramp; VLCC loading.
  12. `t=96.5h` KINETIC_STRIKE @ strait_chokepoint, sev 5, conf 0.98, ltiov 4h — IRGC gunboats fire on two Indian-flagged merchants.
  13. `t=98.0h` DIPLOMATIC_STATUS_CHANGE @ strait_chokepoint, sev 5, conf 0.99, ltiov 48h — Iran re-closes strait.
  14. `t=104.0h` BLOCKADE_RUNNER @ kharg_terminal, sev 4, conf 0.82, ltiov 6h — dark VLCC loading, imminent departure.
  15. `t=112.0h` KINETIC_STRIKE @ mina_sulman, sev 4, conf 0.85, ltiov 6h — drone impact near NSA Bahrain, force protection.
  16. `t=134.0h` SIGINT_CUE @ bandar_jask, sev 4, conf 0.78, ltiov 12h — C2 emitter pattern change.
  17. `t=140.0h` MOVEMENT_DETECTED @ kharg_terminal, sev 3, conf 0.90, ltiov 10h — VLCC RHN departing under fraudulent flag.
  18. `t=150.0h` HUMINT_REPORT @ hormuz_island, sev 3, conf 0.48, ltiov 48h — alleged new IRGC ASCM construction.
  19. `t=158.0h` WEATHER_DEGRADATION @ gulf_of_oman_outbound, sev 2, conf 0.95, ltiov 8h — marine fog reduces EO viability.
  20. (your choice — e.g. a late-stage SIGINT_CUE or FACILITY_ANOMALY that ties off the narrative).

- [ ] **B5. `raveneye/sim/stochastic.py`.**
  `BASE_RATES` (events/hour at mult 1.0) — tuned so 7-day run with `seed=42` produces 120–180 stochastic events:
  VESSEL_DARK 0.14, MOVEMENT_DETECTED 0.09, HUMINT_REPORT 0.06, SIGINT_CUE 0.07, KINETIC_STRIKE 0.02, MINE_LAYING_REPORT 0.008, NAVAL_POSTURE_CHANGE 0.03, BLOCKADE_RUNNER 0.035, FACILITY_ANOMALY 0.035, WEATHER_DEGRADATION 0.012, DIPLOMATIC_STATUS_CHANGE 0.002.

  `PLAUSIBLE_LOCATIONS` — which locations can host which event type. Principle: a mine doesn't fire at Ras Tanura. Use domain sense.

  `DEFAULTS` — per-type sampling ranges for severity, confidence, LTIOV (uniform within bounds; severity via `rng.randint`).

  `jitter_location(loc_id, rng, max_km=8.0)` — flat-earth jitter.
  `sample_stochastic_event(t_hours, rng, phase) → Event` with empty `event_id`/`t_iso` (builder owns IDs).
  `poisson_sample(lam, rng)` — Knuth's algorithm.

- [ ] **B6. `raveneye/sim/stakeholders.py`.** 4 stakeholders:

  **CENTCOM_J2** (force protection): KINETIC_STRIKE 2.0, MINE_LAYING_REPORT 2.0, NAVAL_POSTURE_CHANGE 1.8, MOVEMENT_DETECTED 1.5, BLOCKADE_RUNNER 1.6, SIGINT_CUE 1.3, DIPLOMATIC_STATUS_CHANGE 1.4, HUMINT_REPORT 0.9, FACILITY_ANOMALY 0.8, VESSEL_DARK 0.7, WEATHER_DEGRADATION 0.5.

  **NRO_CSPO** (EOCL utilization): KINETIC_STRIKE 1.6, MINE_LAYING_REPORT 1.5, FACILITY_ANOMALY 1.4, MOVEMENT_DETECTED 1.3, BLOCKADE_RUNNER 1.3, NAVAL_POSTURE_CHANGE 1.2, VESSEL_DARK 1.1, HUMINT_REPORT 1.0, SIGINT_CUE 1.0, DIPLOMATIC_STATUS_CHANGE 0.9, WEATHER_DEGRADATION 0.8.

  **ALLIED_PARTNER** (UK/FR maritime HQ — merchant protection, FON): MINE_LAYING_REPORT 1.9, KINETIC_STRIKE 1.8, VESSEL_DARK 1.5, DIPLOMATIC_STATUS_CHANGE 1.3, NAVAL_POSTURE_CHANGE 1.2, BLOCKADE_RUNNER 1.2, MOVEMENT_DETECTED 1.0, HUMINT_REPORT 0.7, WEATHER_DEGRADATION 0.6, SIGINT_CUE 0.6, FACILITY_ANOMALY 0.5.

  **COMMERCIAL_INSURER** (war-risk pricing): MINE_LAYING_REPORT 1.8, KINETIC_STRIKE 1.7, DIPLOMATIC_STATUS_CHANGE 1.6, BLOCKADE_RUNNER 1.5, VESSEL_DARK 1.4, FACILITY_ANOMALY 1.2, WEATHER_DEGRADATION 1.0, NAVAL_POSTURE_CHANGE 0.8, MOVEMENT_DETECTED 0.6, HUMINT_REPORT 0.4, SIGINT_CUE 0.2.

  Weights on [0, 2]: 0 = indifferent, 1 = standard, 2 = mission-critical.

- [ ] **B7. `raveneye/sim/bids.py`.** `Bid` dataclass (§3 schema minus v0.2 extras).
  `urgency_factor(ltiov_hours) → float` — step function: ≤4h → 1.6, ≤12h → 1.2, ≤24h → 1.0, ≤48h → 0.85, else 0.7.
  `derive_bids(events, t0, stakeholders=STAKEHOLDERS) → List[Bid]`. One bid per (event, interested stakeholder). Priority = `severity × confidence × weight × urgency_factor`, rounded 3dp. `ltiov_iso = t0 + (ev.t_hours + ev.ltiov_hours)` hours. Bid IDs `BID-NNNNN`.

- [ ] **B8. `raveneye/sim/build.py`.** `DEFAULT_T0 = datetime(2026, 4, 13, 12, 0, 0, tzinfo=timezone.utc)`.
  `build_events(t0, duration_hours=168.0, tick_hours=0.5, seed=42) → List[Event]`. Steps: (1) emit scripted beats, (2) walk time in 0.5h ticks drawing Poisson counts `min(4, poisson_sample(total_rate × mult × tick_hours, rng))`, jitter within tick, (3) sort by t_hours.
  `build_sim(seed=42, duration_hours=168.0, t0=None) → dict`. Include a `_to_jsonable()` helper converting enums (via `.value`) and dataclasses recursively.

- [ ] **B9. `raveneye/sim/__init__.py`.** Re-export public API with an explicit `__all__`.

- [ ] **B10.** Smoke test: `python -c "from raveneye.sim import build_sim; s = build_sim(); print(s['meta']['n_events'], s['meta']['n_bids'])"` should print ~170–180 events and ~680–720 bids. If off, tune `BASE_RATES`.

### Phase C — Tests (v0.1)
- [ ] **C1. `tests/test_events.py`** — schema invariants: every event has non-empty IDs/ISO/narrative; severity ∈ {1..5}; confidence ∈ [0,1]; ltiov > 0; event_type is valid; phase matches `phase_at(t_hours).name`; scripted IDs start `SCR-`, stochastic `STO-`; chronological order.
- [ ] **C2. `tests/test_bids.py`** — crafted fixture produces expected bid count; same-event bids share target/sensor; priority ordering reflects weight ordering when other factors equal; urgency boundaries at 4/12/24/48h are correct; LTIOV ISO math is correct.
- [ ] **C3. `tests/test_determinism.py`** — `build_sim(seed=42)` twice → identical (`json.dumps(sort_keys=True)`); different seeds differ; pinned invariants for seed=42 run (first scripted event is `SCR-000` of type `DIPLOMATIC_STATUS_CHANGE`; n_events and n_bids within ±2).
- [ ] **C4. `tests/test_phases.py`** — `phase_at(-5)`, `phase_at(0)`, `phase_at(35.999)` → BLOCKADE_ACTIVE; `phase_at(36)` → ESCALATION; `phase_at(1000)` → BLOCKADE_REINFORCED.
- [ ] **C5.** `pytest -q` passes clean.

### Phase D — CLI & reference data (v0.1)
- [ ] **D1. `raveneye/cli/generate.py`** — argparse CLI: `--seed`, `--duration`, `--out` (default `sim.json`), `--viewer` (stage dir), `--stats` (summary to stderr: events/phase, events/type, totals). `main(argv=None) → int`.
- [ ] **D2.** Run `raveneye-generate --seed 42 --out data/sample_sim.json`; commit the output. Note in README that this is canonical reference.

### Phase E — v0.1 viewer (flat choke-point map)
- [ ] **E1. `raveneye/viewer/template.html`** — single-page flat SVG map viewer. Ops-center aesthetic: dark UI, JetBrains Mono for data, IBM Plex Sans for narrative, no gradients, sharp status colors.
  Layout (CSS grid): 48px header (brand, scenario, phase badge, clock) / flexible main (SVG map) / 420px aside (selected event's derived bids on top, scrollable event feed below) / 180px timeline (phase bands, event ticks height-by-severity, playhead) / 40px footer (play/pause, reset, speed 1×/5×/15×/60×, keyboard hint).
  Data: `fetch("sim.json")` unless overridden by `?sim=path` or `window.RAVENEYE_SIM_URL`. Clear error box with `python3 -m http.server` hint if fetch fails.
  Map: equirectangular, bounds lat [24.5, 30.5] × lon [48.5, 59.0]. Stylized coastline polygons (not geodetic — it's a demo). Country labels, 1° grid, location markers with hover titles.
  Event dots: visible [t−0.5h, t+min(6h, ltiov_hours)] as "active", then "fading" 4h more. Outer ring sized by severity.
  Keyboard: Space, ←/→ (±2h), R.
- [ ] **E2. `raveneye/viewer/build_viewer.py`** — `stage_viewer(out_dir, sim) → Path`: copy template.html → index.html, write sim.json.
- [ ] **E3.** Wire `--viewer out/` flag on CLI.
- [ ] **E4.** Eyeball test: play 7-day arc at 60×; click a scripted event; four stakeholder bids appear sorted by priority. If it doesn't feel like a watch-floor replay, aesthetic is off.

### Phase F — v0.1 docs
- [ ] **F1. `README.md`** — What this is (evaluation testbed, not a tasker), Install/run, Layout, Concepts (event ≠ bid, scripted vs. stochastic), Reproducibility (seed + sample_sim.json), What's next (pointer to docs/ and TODO.md), License.
- [ ] **F2. `docs/architecture.md`** — the 4-layer model, ASCII or Mermaid diagram, why demand was built first.
- [ ] **F3. `docs/event_taxonomy.md`** — for each event type: definition, doctrinal analog (cite FM 34-2 / ATP 2-01 where relevant), typical severity/LTIOV ranges, example narrative.
- [ ] **F4. `docs/bidding_interface.md`** — I/O contract for a downstream mechanism. Input: list of Bid dicts. Output: list of Allocation dicts. State that v0.1 does not implement a mechanism.
- [ ] **F5. `TODO.md`** — forward parking lot.

### Phase G — v0.1 ship
- [ ] **G1.** `pytest -q` green; `raveneye-generate --stats` clean; viewer renders.
- [ ] **G2.** Clean initial commit.
  ```
  v0.1 — demand layer for EO tasking evaluation

  - Event taxonomy (11 types, doctrinally grounded)
  - Scripted backbone + seeded stochastic injects
  - 4 stakeholders with differentiated utility weights
  - Bid derivation (event × stakeholder → weighted request)
  - Playback viewer (ops-center aesthetic, fetches sim.json)
  - Hormuz blockade scenario (April 2026 arc, 7 days, 5 phases)
  - Tests, docs, MIT license
  ```
- [ ] **G3.** Push to `main`. Tag `v0.1.0`. **STOP here for PM review before starting v0.2.** v0.2 is bigger and the PM should validate the viewer story first.

---

## 5. v0.2 — Supply + Mechanism + Globe viewer

**Prerequisite:** v0.1 is tagged and merged. Don't start v0.2 until v0.1 is on `main` with a tag.

### 5.1 Key technical decisions (don't re-litigate these — they were made during spec design)

- **SGP4 propagation split:** Python (Skyfield) owns access-window computation (expensive, complex). JavaScript (satellite.js) owns live on-screen satellite positions in the viewer. The two code paths MUST agree to ≤1 km position error at any given time; there's a test for this.
- **Globe renderer:** CesiumJS, Apache 2.0. Industry standard. Used by AGI ComSpOC for tens of thousands of sats in real time. `satellite.js` for SGP4 in the browser.
- **Cesium ion:** free tier only. No commercial tokens. Use the default imagery and bundled Cesium World Terrain via the free tier token; if the token is unavailable, fall back to OSM imagery and `Cesium.createWorldTerrainAsync({ requestVertexNormals: false })` with defaults. Do NOT require a paid account.
- **TLE format:** TLE primary, OMM fallback. **CelesTrak is exhausting 5-digit NORAD catalog IDs around 2026-07-20;** post-overflow, new satellites will only be available as OMM (CCSDS). The `sgp4` Python package handles both; plan for OMM from day one even if TLEs work today.
- **Satellite count:** ~100–150. Specifically: BlackSky (~20 active), Planet SkySat (~20), Planet Dove/SuperDove (a representative subset of ~30–50 — NOT all 200+; pick by NORAD ID parity or random-seeded sample to keep the viewer performant), Capella Space SAR (~5–10), ICEYE SAR (~20–30), Maxar WorldView/GeoEye (6–8).
- **Viewer:** the globe view (`raveneye/viewer/globe/`) becomes the default. The flat choke-point map (v0.1 template.html) stays available for embeds and as a fallback. Globe view handles both zoom levels — a camera fly-to on scenario load gets you to the Gulf; zoom-out shows full orbital context.
- **Mechanism layer scope for v0.2:** two mechanisms. `GreedyPriorityMechanism` (baseline — matches what ops centers actually do) and `SequentialSingleItemMechanism` (SSI — first mechanism with real auction content). No CBBA, no ILP, no VCG in v0.2. Those come later.

### 5.2 Dependencies (added in v0.2)
Update `pyproject.toml`:
```toml
[project]
dependencies = [
    "skyfield>=1.49",
    "sgp4>=2.23",
    "requests>=2.31",
    "numpy>=1.26",
]
```
Pin lower bounds only.

### Phase H — Orbital (supply) layer

- [ ] **H1. `raveneye/orbital/constellations.py`.** `Constellation` dataclass (`constellation_id`, `vendor`, `sensor_class`, `nominal_gsd_m`, `spectral_bands`, `max_off_nadir_deg`, `swath_width_km`, `slew_rate_deg_s`, `duty_cycle_pct`, `celestrak_group`).
  `CONSTELLATIONS` entries for: BlackSky (`blacksky`, "BlackSky", EO_HIGHRES, 1.0m, ["PAN"], 45°, 5.5km, 1.0°/s, 20%), Planet SkySat (`skysat`, "Planet", EO_HIGHRES, 0.5m, ["PAN","MS"], 30°, 5.9km, 0.8°/s, 15%), Planet Dove (`planet_dove`, "Planet", EO_MEDRES, 3.0m, ["MS"], 5°, 25km, 0.1°/s, 80%), Capella (`capella`, "Capella Space", SAR, 0.5m, ["SAR_X"], 60°, 5km, 1.5°/s, 12%), ICEYE (`iceye`, "ICEYE", SAR, 1.0m, ["SAR_X"], 50°, 10km, 1.5°/s, 15%), Maxar (`maxar_wv`, "Vantor (Maxar)", EO_VHR, 0.3m, ["PAN","MS","SWIR"], 45°, 13km, 3.5°/s, 10%). These are public-spec approximations; cite the sources in `docs/orbital_model.md`.

- [ ] **H2. `raveneye/orbital/tle_ingest.py`.**
  `fetch_tle_group(group_name, cache_dir) → List[Tuple[str, str, str]]` — fetch from `https://celestrak.org/NORAD/elements/gp.php?GROUP={group}&FORMAT=tle`. Cache by group name + date. Respect CelesTrak's rate limit (they ask for ≤1 request per group per 2 hours). Return `(name, line1, line2)` tuples.
  `fetch_omm_group(group_name, cache_dir) → List[Dict]` — same endpoint with `FORMAT=json`. Fallback when TLE fails or NORAD ID > 99999.
  `load_cached_or_fetch(group_name, cache_dir, max_age_hours=24)`.
  On fetch failure: clear error message with URL tried, do NOT proceed with empty data — propagate step no-ops gracefully.

- [ ] **H3. `raveneye/orbital/propagate.py`.**
  `build_satellites(constellations, t0, cache_dir) → List[Dict]` — per constellation, fetch TLEs, create `Satrec` (via `sgp4.api`) and `EarthSatellite` (via Skyfield), attach constellation metadata. Returns dicts matching the Satellite schema (§3.2).
  If a satellite's TLE epoch is >7 days from scenario t0, log a warning but still include it.
  Deterministic ordering: sort by NORAD ID ascending within each constellation.

- [ ] **H4. `raveneye/orbital/access.py`.**
  `find_access_windows(satellites, targets, t0, duration_hours, min_elevation_deg=20.0) → List[Dict]` — for each (sat, target) pair, call `EarthSatellite.find_events(topos, t_start, t_end, altitude_degrees=min_elevation_deg)` and parse (rise, culminate, set) triples into windows. Skip pairs where geometry never works.
  Defensive handling for known find_events edge cases (use Skyfield ≥1.49; single-event near-boundary passes; rare short passes where culmination and rise collapse — see Skyfield issues #559, #1000, #1017).
  Per-window compute: `duration_s`, `max_elevation_deg` (at culminate), `sun_elevation_deg` at mid-window (from Skyfield sun ephemeris), `quality_score` = `0.4 × (max_elev/90) + 0.3 × max(0, sun_elev/30) + 0.3 × (1 − abs(off_nadir)/45)`. For SAR constellations, drop sun term (reweight: 0.55 elevation, 0.45 off-nadir).
  Return dicts matching §3.3 schema. Stable IDs `AW-NNNNN`.

- [ ] **H5. `raveneye/orbital/coverage.py`.** Helpers for the globe viewer:
  `sensor_cone_radius_m(altitude_m, max_off_nadir_deg) → float`.
  `swath_footprint_polygon(lat, lon, alt_m, off_nadir_deg, az_deg, swath_width_km) → List[Tuple[float, float]]`.
  Not used inside `find_access_windows` (windows already assume feasibility).

- [ ] **H6. `raveneye/orbital/build.py`.** `build_supply(constellations, targets, t0, duration_hours, cache_dir, seed=42) → Dict` → `{"satellites": [...], "access_windows": [...], "meta": {...}}`. Seed doesn't affect supply directly but is passed through for API consistency.

- [ ] **H7. `raveneye/orbital/__init__.py`.** Re-export `build_supply`, `CONSTELLATIONS`, `Constellation`.

- [ ] **H8.** Create `data/tle_cache/.gitkeep`.

### Phase I — Mechanism (allocation) layer

- [ ] **I1. `raveneye/mechanism/base.py`.**
  `Allocation` dataclass (§3.4).
  `Mechanism` typing.Protocol with one method: `allocate(self, bids, access_windows, t0, now=None) → List[Allocation]`. `now` lets future work restrict to bids/windows known as of a given sim time.
  `match_bid_to_window(bid, window) → bool`: True iff target within tolerance, window ends before bid's LTIOV, sensor band compatible.

- [ ] **I2. `raveneye/mechanism/greedy.py`.** `GreedyPriorityMechanism`:
  Sort bids by `priority_score` desc. For each bid, find earliest available window that matches; mark taken; emit `status="SCHEDULED"`. If none match: `status="DROPPED"`, `window_id=null`.
  This is the baseline. More sophisticated mechanisms MUST beat this on welfare metrics to justify their complexity.

- [ ] **I3. `raveneye/mechanism/ssi.py`.** `SequentialSingleItemMechanism`:
  Sort bids by priority desc. For each bid, auction among available feasible windows: allocate to the window maximizing `bid.priority_score × window.quality_score`.
  First mechanism with real auction content: a window matching a bid poorly (low elevation, bad sun, high off-nadir) loses to a better window even for a later bid.

- [ ] **I4. `raveneye/mechanism/build.py`.** `allocate(bids, access_windows, t0, mechanism="greedy") → List[Allocation]`. `mechanism` accepts string name or instance.

- [ ] **I5. `raveneye/mechanism/__init__.py`.** Re-export.

### Phase J — Unified scenario builder

- [ ] **J1. `raveneye/scenario/build.py`.** `build_full_scenario(seed=42, duration_hours=168.0, mechanism="greedy", use_cached_tles=True) → Dict` — calls `build_sim()` + `build_supply()` + `allocate()` and merges into §3.1 top-level Scenario JSON.

- [ ] **J2. `raveneye/cli/build_scenario.py`.** `raveneye-build-scenario` CLI: `--seed`, `--duration`, `--mechanism {greedy,ssi}`, `--out data/sample_scenario.json`, `--viewer globe_out/`, `--refresh-tles`.

### Phase K — Tests (v0.2)

- [ ] **K1. `tests/test_tle_ingest.py`** — cache freshness, OMM fallback wired up, rate-limit respect (mock `requests.get` — no live network in tests).
- [ ] **K2. `tests/test_propagate.py`** — build satellites from `tests/fixtures/tles.txt` (5 sats committed to repo); propagate ISS at a known time; assert position within 10 km of hard-coded reference from a clean Skyfield run.
- [ ] **K3. `tests/test_access.py`** — fixture with one sun-synchronous sat and one target at known lat/lon; `find_access_windows` over 24h; assert expected pass count (compute independently from orbital period + ground track). Pass durations > 1 minute.
- [ ] **K4. `tests/test_mechanism_greedy.py`** — 3 bids, 5 windows; assert deterministic allocation matching expected.
- [ ] **K5. `tests/test_mechanism_ssi.py`** — same fixture; SSI produces measurably different allocation than greedy, and welfare (sum of `priority × quality`) ≥ greedy's.
- [ ] **K6.** Update `tests/test_determinism.py` with scenario-level invariants (n_satellites, n_access_windows, n_allocations) for seed=42 + fixed TLE fixture.
- [ ] **K7.** All v0.2 tests pass without network access.

### Phase L — Globe viewer (`raveneye/viewer/globe/`)

**Important:** this is the new default viewer. Load CesiumJS and satellite.js from jsdelivr or unpkg — no build step, no bundler, no npm install in the viewer. Static HTML deployment. If Claude Code wants a build step, push back first.

- [ ] **L1. `globe/index.html`** — minimal page shell. Loads Cesium CSS, satellite.js, main.js, style.css. `#cesiumContainer` div. Header/side/timeline/footer from v0.1, re-skinned.

- [ ] **L2. `globe/style.css`** — ops-center aesthetic from v0.1. Dark Cesium viewer (`backgroundColor` via Cesium API). JetBrains Mono / IBM Plex Sans.

- [ ] **L3. `globe/main.js`** — boot logic.
  - Fetch `scenario.json` (override via `?scenario=path` or `window.RAVENEYE_SCENARIO_URL`).
  - Create Cesium Viewer: disable built-in timeline/animation widgets (we have our own), terrain enabled (free tier), starField + skyAtmosphere on.
  - Camera fly-to Gulf region over ~3s on load.
  - Wire playback clock to Cesium's clock: `viewer.clock.shouldAnimate = true` during play; `viewer.clock.currentTime = JulianDate.fromIso(sim_time_iso)` during scrub.

- [ ] **L4. `globe/orbits.js`** — satellite rendering.
  - Per satellite: Cesium `Entity` with `SampledPositionProperty` populated from satellite.js at 30-second sampling over scenario duration. Cesium interpolates smoothly.
  - Show a **trailing orbit ribbon** (polyline) behind each satellite, lasting 20 minutes of sim time. Don't draw full ground tracks — at 100 sats that's visual noise.
  - Color by constellation. Vendor legend in side panel.
  - Filtering: per-constellation checkboxes. Default all on.
  - Hover: sat name, NORAD ID, constellation, altitude, velocity.
  - Click: lock camera to satellite; show per-sat info pane.

- [ ] **L5. `globe/coverage.js`** — coverage rendering.
  - When a satellite is inside an access window allocated to a bid, draw its instantaneous imaging swath as a colored ground polygon. Fade in/out at window start/end.
  - Color by allocation status: bright = COLLECTED, dim = SCHEDULED, red outline = DEADLINE_MISSED.
  - When an event fires: pulse its location marker. If event has allocated windows, draw thin line from satellite to event during collection.

- [ ] **L6. `globe/timeline.js`** — playback timeline. Keep v0.1 shape (phase bands, event ticks, playhead); add a second lane underneath for access-window density (histogram per 15-minute bucket, colored by allocated vs dropped).

- [ ] **L7. `globe/panels.js`** — side panels.
  - Event feed (as v0.1).
  - Selected-event panel: derived bids AND allocation outcome per bid (which satellite, which window, status). New in v0.2.
  - Constellation filter.
  - Stats: events fired, bids produced, windows available, allocations made, drop rate.
  - Keyboard: Space / ←→ / R; plus `F` = toggle follow-selected-satellite camera.

- [ ] **L8.** Update `stage_viewer(out_dir, scenario)` to stage globe viewer by default (copy `globe/` dir); keep `--legacy-flat-map` flag for v0.1 viewer.

- [ ] **L9.** `scripts/verify_position_agreement.py` — spot-check 10 satellites at 10 random scenario times; Python WGS84 lat/lon/alt vs satellite.js must agree within 1 km.

- [ ] **L10.** Eyeball test: `raveneye-build-scenario --viewer globe_out/`, open it. You should see ~100 satellites orbiting, events pulsing at the Gulf, allocated satellites drawing brief swaths during access windows, and a side panel showing per-event stakeholder bids + allocation outcomes. If it doesn't feel like watching a real ISR replay, the globe design needs rework.

### Phase M — v0.2 docs
- [ ] **M1. `docs/orbital_model.md`** — TLE/OMM formats, SGP4 accuracy (1 km within 7 days of epoch), access window computation, quality scores. Cite Skyfield, sgp4, CelesTrak. Note the 2026-07-20 catalog overflow.
- [ ] **M2. `docs/mechanism_interface.md`** — updated. `Mechanism` protocol; Allocation schema; how to write a new mechanism. Worked greedy-vs-SSI example.
- [ ] **M3. `docs/viewer_guide.md`** — what the globe shows. Screenshots (commit them). Side panel / timeline layers. Keyboard reference.
- [ ] **M4.** Update `README.md` for v0.2.
- [ ] **M5.** Update `docs/architecture.md` — three of four layers exist.

### Phase N — v0.2 ship
- [ ] **N1.** All tests green; globe viewer renders 100+ sats smoothly at 60×.
- [ ] **N2.** `raveneye-build-scenario --seed 42 --out data/sample_scenario.json`; commit.
- [ ] **N3.** Commit message:
  ```
  v0.2 — supply layer + greedy/SSI mechanisms + CesiumJS globe viewer

  - Orbital supply: CelesTrak TLE ingestion with OMM fallback,
    Skyfield SGP4 propagation, access-window computation with
    sun geometry and quality scoring
  - ~100-150 satellites across 6 constellations
    (BlackSky, Planet SkySat, Planet Dove, Capella, ICEYE, Maxar)
  - Mechanism layer: GreedyPriorityMechanism baseline + SSI auction
  - CesiumJS globe viewer replaces flat map as default;
    orbit ribbons, instantaneous swath rendering, access-window
    density timeline, stakeholder allocation panel
  - Tests cover propagation, access windows, both mechanisms,
    Python↔JS position agreement within 1 km
  ```
- [ ] **N4.** Tag `v0.2.0`.

---

## 6. Red-flag checklist — things Claude Code should push back on

### v0.1
- If events and bids are collapsed → **stop.** Re-read §1.3.
- If orbital mechanics appear → **stop.** That's v0.2.
- If an allocation algorithm appears → **stop.** That's v0.2.
- If seed=42 produces <100 or >250 events → tune `BASE_RATES`.
- If the v0.1 viewer looks like a shadcn dashboard → aesthetic wrong; should feel like a watch-floor replay.

### v0.2
- If v0.1 needs breaking changes to enable v0.2 → stop and reconsider. Layers were designed to extend, not replace.
- If the globe viewer needs a build step (webpack, vite, npm install in CI) → push back. Static HTML + CDN-loaded Cesium is the intended shape.
- If a paid Cesium ion token is required → stop; switch to OSM tiles + default free terrain.
- If greedy beats SSI on welfare for the committed scenario → investigate. SSI should be measurably better in at least some conditions, or it isn't earning its complexity.
- If Python↔JS position agreement shows >1 km error anywhere → stop and diagnose. Likely a coordinate-frame bug (TEME vs ECI vs ECEF) that invalidates everything downstream.
- If Planet Dove TLE fetch pulls 200+ sats and the viewer grinds → cap to ~30–50 representative; document the subset.
- If CelesTrak returns HTTP errors during dev → use cache; don't hammer their servers. ≤1 request per group per 2 hours.

---

## 7. Quick reference — expected numbers

### v0.1 (seed=42, duration=168h)
- Events: ~170–180 (scripted 20, stochastic ~150–160)
- Bids: ~680–720 (~4× events)
- Events per phase (approx): BLOCKADE_ACTIVE 23, ESCALATION 49, CEASEFIRE_ANNOUNCED 4, CEASEFIRE_COLLAPSE 61, BLOCKADE_REINFORCED 36

### v0.2 (seed=42, duration=168h, representative TLE snapshot)
- Satellites: 100–150
- Access windows: ~4,000–8,000 (depends on target set and min_elevation)
- Allocations (greedy): one per bid; expect 30–50% DROPPED rate for high-urgency bids under normal density, higher during ESCALATION/CEASEFIRE_COLLAPSE phases
- Greedy vs SSI welfare delta: SSI should show 5–15% welfare improvement. If <2% or >25%, check the implementation.

---

## 8. Explicit non-goals (v0.1 and v0.2)

Capture as issues; don't build:
- CBBA, VCG, ILP combinatorial mechanisms (v0.3+)
- Foundry integration, ontology export
- Classified scenarios, ITAR-restricted TLEs, live operational feeds
- Satellite slew/duty-cycle constraint enforcement beyond published-spec defaults
- Cloud forecast ingestion (WEATHER_DEGRADATION events are the stub)
- SAR-specific tasking mechanics beyond spectral-band flag
- Multi-scenario comparisons, A/B testing UI
- Replay save/export, session bookmarking
