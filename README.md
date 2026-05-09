# RavenEye

**Multi-constellation EO tasking simulation** for evaluating satellite-tasking
allocation mechanisms under realistic military collection demand.

RavenEye is *not* a tasker, not an orchestration product, and not a competitor
to Palantir MetaConstellation. It is an **evaluation environment** — the thing
that tells you which tasking design survives contact with real operational
tempo.

This repo currently ships **v0.1: the demand layer.** Events, stakeholder
bids, phase-driven scenario tempo, and a flat choke-point map viewer for the
Strait of Hormuz blockade arc (April 2026). Supply (orbits / access windows)
and mechanism (allocation) layers land in v0.2.

## Install

```
pip install -e ".[dev]"
```

Python 3.10+. v0.1 has no runtime dependencies beyond the standard library;
`[dev]` adds `pytest` and `pytest-cov`.

## Generate a scenario

```
raveneye-generate --seed 42 --out data/sample_sim.json --stats
```

Flags:

| Flag | Default | Notes |
|---|---|---|
| `--seed` | `42` | RNG seed. Same seed → identical output. |
| `--duration` | `168.0` | Scenario duration in hours (default = 7 days). |
| `--out` | `sim.json` | Output JSON path. |
| `--viewer` | *(off)* | If set, stage the flat-map viewer at this directory. |
| `--stats` | *(off)* | Print summary stats to stderr. |

## Open the viewer

```
raveneye-generate --seed 42 --out viewer_out/sim.json --viewer viewer_out
cd viewer_out && python3 -m http.server
```

Then open <http://localhost:8000/> in a browser.

The viewer is a single static HTML page — no build step, no bundler, no npm.
It loads `sim.json` via `fetch()` (which is why it needs an HTTP server, not
`file://`). Use `?sim=path/to/sim.json` or set `window.RAVENEYE_SIM_URL` to
point at a different scenario file.

Controls:

- **Space** — play / pause
- **← / →** — jump ±2 hours
- **R** — reset to t=0
- **Speed** — 1× / 5× / 15× / 60× (60× = full 7-day arc in ~2.8 hours)
- **Click** an event on the map or in the feed to inspect its derived bids
- **Click** the timeline to scrub

## Repo layout (v0.1)

```
raveneye/
├── raveneye/
│   ├── cli/generate.py            # raveneye-generate CLI
│   ├── sim/                       # demand layer
│   │   ├── events.py              # Event, EventType, ObservableKind
│   │   ├── locations.py           # 15 Hormuz-region locations + sensor reqs
│   │   ├── phases.py              # 5 scenario phases with rate multipliers
│   │   ├── scripted.py            # 20 narrative anchor beats
│   │   ├── stochastic.py          # Poisson-sampled inject events
│   │   ├── stakeholders.py        # 4 stakeholders with utility weights
│   │   ├── bids.py                # event × stakeholder → weighted bid
│   │   └── build.py               # build_events, build_sim
│   └── viewer/
│       ├── template.html          # flat SVG choke-point viewer
│       └── build_viewer.py        # stage_viewer()
├── data/
│   └── sample_sim.json            # canonical seed=42, 168h reference output
├── tests/                         # pytest, no network
└── docs/
    ├── architecture.md
    ├── event_taxonomy.md
    └── bidding_interface.md
```

## Concepts

### Event ≠ Bid

This is the central design distinction. **Don't collapse them.**

- An **Event** is a world-state change. It happens once, at a place, with a
  severity and a confidence. It exists independent of any observer.
- A **Bid** is what a stakeholder produces when they observe an event through
  their own utility function. Same event, different stakeholders, different
  priority scores.

The same `KINETIC_STRIKE` at Siri Island produces a bid from CENTCOM J2 (high
priority — force protection), from NRO CSPO (high — utilization-worthy
target), from the Allied Maritime HQ (high — merchant-traffic risk), and from
a commercial war-risk insurer (high — premium repricing). The priority
*scores* differ because the *weights* differ. This multi-utility structure is
the point of the sim — it's what a single-stakeholder benchmark can't capture.

### Scripted backbone + stochastic injects

The event stream has two layers:

- **Scripted beats** (~20) are hand-curated narrative anchors. Same every
  run. Event IDs `SCR-NNN`. They give the scenario a story arc.
- **Stochastic injects** are seeded Poisson draws scaled by scenario phase.
  Event IDs `STO-NNNN`. They provide texture and density.

Both kinds derive bids the same way.

### Phases

The 7-day Hormuz arc walks through 5 phases, each with a rate multiplier on
the stochastic event stream:

| Phase | Start (h) | Rate × |
|---|---|---|
| BLOCKADE_ACTIVE | 0 | 1.0 |
| ESCALATION | 36 | 2.2 |
| CEASEFIRE_ANNOUNCED | 72 | 0.4 |
| CEASEFIRE_COLLAPSE | 96 | 2.8 |
| BLOCKADE_REINFORCED | 132 | 1.6 |

## Reproducibility

`data/sample_sim.json` is the canonical `seed=42`, `duration=168h` reference
output, committed to the repo. Tests pin invariants against this seed; if you
change `BASE_RATES`, sampling logic, or any data shape, regenerate it with:

```
raveneye-generate --seed 42 --out data/sample_sim.json
```

and review the diff. `tests/test_determinism.py` enforces that two runs with
the same seed produce byte-identical JSON.

## What's next

- **v0.2** — supply layer (TLEs, SGP4, access windows), mechanism layer
  (greedy + sequential single-item auction), and a CesiumJS globe viewer.
  See `raveneyebuildspec.md` Section 5 for the full spec.
- See `TODO.md` for a parking lot of ideas explicitly out of scope for v0.1
  and v0.2.
- See `docs/architecture.md`, `docs/event_taxonomy.md`, and
  `docs/bidding_interface.md` for design background.

## License

MIT. See `LICENSE`.
