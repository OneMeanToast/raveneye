# Architecture

RavenEye is a four-layer system. **Three of four are shipped.** The fourth
(evaluation) is mostly manual until v0.3+.

```
┌──────────────────────────────────────────────────────────────────────┐
│  EVALUATION   Metrics, A/B comparison, welfare analysis      v0.3+   │
├──────────────────────────────────────────────────────────────────────┤
│  MECHANISM    bids + access_windows → allocations            ✅ v0.2 │
├──────────────────────────────────────────────────────────────────────┤
│  SUPPLY       TLEs + targets → access_windows                ✅ v0.2 │
├──────────────────────────────────────────────────────────────────────┤
│  DEMAND       events × stakeholders → bids                   ✅ v0.1 │
└──────────────────────────────────────────────────────────────────────┘
```

## Why demand was built first

The other layers don't have meaningful semantics until demand exists.

- An **access window** is only interesting in the context of a bid that wants
  it. Without bids, supply is just orbital geometry.
- A **mechanism** allocates supply to demand; without demand, there's nothing
  to allocate.
- An **evaluation** metric is a function of allocation outcomes vs. demand;
  without demand, there's no welfare to measure.

Demand is also the layer where the **hardest design choices** live (event
taxonomy, stakeholder utility, scenario tempo). Settling those first means
v0.2 inherits a stable target schema.

## The two non-negotiable distinctions

### Event ≠ Bid

An **event** is a world-state change. A **bid** is a stakeholder's reaction
to that event scored against their utility weights. Same event, different
stakeholders, different priority scores. Collapsing the two erases the
multi-stakeholder structure that makes the sim worth running.

### Demand ≠ Supply ≠ Mechanism

In v0.2, three data flows must remain separable:

- **Demand** produces `bids` (from events × stakeholders).
- **Supply** produces `access_windows` (from TLEs × targets).
- **Mechanism** consumes both and produces `allocations`.

If you find yourself computing allocations inside the event generator, or
pulling TLE parsing into the bid module, stop. Layers exist so swapping one
(e.g. trying a different auction algorithm) doesn't cascade through the rest.

## v0.1 demand-layer dataflow

```
phases.py ──┐
            │
locations.py ────► scripted.py ───┐
            │                     ├──► build.py: build_events ──► [Event…]
            └──► stochastic.py ───┘                                  │
                                                                     ▼
                                          stakeholders.py ──► bids.py: derive_bids
                                                                     │
                                                                     ▼
                                                                 [Bid…]
                                                                     │
                                                                     ▼
                                            build.py: build_sim ──► sim.json
                                                                     │
                                                                     ▼
                                          viewer/build_viewer.py ──► viewer_out/
```

Two functions are the public seams:

- `raveneye.sim.build_events(t0, duration_hours, tick_hours, seed)` →
  `List[Event]`
- `raveneye.sim.build_sim(seed, duration_hours, t0)` → JSON-shaped `dict`
  with `meta`, `locations`, `stakeholders`, `events`, `bids`,
  `sensor_requirements`.

Everything downstream — tests, the viewer, the eventual mechanism layer — is
expected to consume the JSON, not the Python dataclasses. JSON is the
boundary contract.

## v0.2 dataflow

```
TLE cache ──► orbital/build.build_supply ──► access_windows ─┐
                  │                                           │
                  └──► satellites                             │
                                                              ├──► mechanism/build.allocate
events × stakeholders ──► sim/build.build_sim ──► bids ──────┘                │
                                  │                                           ▼
                                  └──► events                          [Allocation…]
                                                                              │
                                                                              ▼
                            scenario/build.build_full_scenario ──► scenario.json
                                                                              │
                                                                              ▼
                                          viewer/build_viewer.py ──► globe_out/
```

The three layers join in `raveneye.scenario.build_full_scenario(seed,
duration_hours, mechanism, cache_dir)`. Each lower-level layer is also
independently usable — you can pull bids without computing supply, or
compute access windows without involving any mechanism.

The unified output is documented in `raveneyebuildspec.md` §3.1 and
`docs/viewer_guide.md`. Top-level keys:

```
{
  "meta": { ... seed, mechanism, n_*, total_welfare, drop_rate ... },
  "locations": { ... v0.1 ... },
  "stakeholders": [ ... v0.1 ... ],
  "sensor_requirements": { ... v0.1 ... },
  "constellations":  [ ... v0.2 ... ],
  "satellites":      [ ... v0.2 ... ],
  "events":          [ ... v0.1 ... ],
  "bids":            [ ... v0.1 ... ],
  "access_windows":  [ ... v0.2 ... ],
  "allocations":     [ ... v0.2, one per bid ... ]
}
```

## Determinism

A hard requirement throughout. Same seed → byte-identical JSON, enforced by
`tests/test_determinism.py`. The viewer is a pure function of the JSON, so
the same scenario always renders identically.

The seed flows through:

- `build_events` uses `random.Random(seed)` for all stochastic injects.
- Scripted beats are static — no RNG.
- `derive_bids` is a pure function of `(events, t0, stakeholders)` — no RNG.

When v0.2 adds supply, the seed will gate the Planet Dove subset selection
(picking ~30–50 representative sats from the full constellation). TLE epochs
themselves are pinned by the cached fixture in `tests/fixtures/tles.txt`.

## File-level notes

### `raveneye/sim/` — demand layer

- `events.py` — pure dataclasses + enums. Imports nothing from other sim
  modules. The data model is the contract.
- `locations.py` — 15 hand-picked Hormuz-region locations + the
  per-`ObservableKind` `SENSOR_REQUIREMENTS` table.
- `phases.py` — `phase_at(t_hours)` is the sole behavioral function.
- `scripted.py` — 20 narrative beats as plain Python literals.
- `stochastic.py` — Knuth Poisson + per-type sampling defaults. Capped at
  4 events per 0.5h tick so runaway phases don't explode the count.
- `stakeholders.py` — 4 stakeholders with utility weights on `[0, 2]`.
- `bids.py` — `derive_bids` and `urgency_factor` step function.
- `build.py` — orchestrator + `_to_jsonable()` helper.

### `raveneye/orbital/` — supply layer

- `constellations.py` — 6-entry constellation table with sensor specs and
  CelesTrak group names.
- `tle_ingest.py` — CelesTrak fetchers (TLE primary, OMM fallback) with
  on-disk caching keyed by group + UTC date. Tolerant TLE parser.
- `propagate.py` — Skyfield/SGP4 wrapper. Builds Satellite-schema dicts
  sorted by `(constellation_id, norad_id)` for determinism.
- `access.py` — `find_access_windows`. Skyfield `find_events()` driven;
  defensive against the well-known rise/cul/set edge cases. Closed-form
  NOAA solar position so tests don't need the JPL ephemeris.
- `coverage.py` — sensor cone radius, swath footprint polygons. Used by
  the globe viewer; not by access feasibility.
- `build.py` — `build_supply()` (network) + `build_supply_from_satellites()`
  (offline, for tests / alternative TLE sources).

### `raveneye/mechanism/` — allocation layer

- `base.py` — `Allocation` dataclass, `Mechanism` Protocol,
  `match_bid_to_window` (target / deadline / band), helper indexes.
- `greedy.py` — `GreedyPriorityMechanism`. Baseline.
- `ssi.py` — `SequentialSingleItemMechanism`. argmax welfare per bid.
- `build.py` — `allocate(...)` dispatcher + `total_welfare` and
  `drop_rate` metrics.

### `raveneye/scenario/` — unified builder

- `build.py` — `build_full_scenario(...)` joins demand × supply ×
  mechanism into a single Scenario JSON object (§3.1).

## Viewer

Static HTML. No build step. The viewer is intentionally not a framework
project — it has to survive being copied into a USB-stick demo or embedded
in a slide deck.

- **v0.1 flat map** — `template.html` is a single file with inline CSS
  and JS. `build_viewer.py` copies it next to a `sim.json` (or a
  scenario.json — superset shape).
- **v0.2 globe** — `globe/` is a flat directory of HTML / CSS / JS
  (no nesting). Cesium and satellite.js load from jsDelivr at runtime.
  Same `build_viewer.py` ships them with `kind="globe"` (default in
  `raveneye-build-scenario`).

Both kinds are static. Drop a staged directory on any HTTP host —
Render, GitHub Pages, S3 + CloudFront, `python3 -m http.server`. The
only outbound runtime calls are CDN fetches for fonts (Google), Cesium
+ satellite.js (jsDelivr), and OSM imagery. Mirror those if you need
to air-gap.
