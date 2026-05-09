# Architecture

RavenEye is a four-layer system. v0.1 implements the first layer; v0.2 adds
the next two. The fourth (evaluation) is mostly manual until v0.3+.

```
┌──────────────────────────────────────────────────────────────────────┐
│  EVALUATION             Metrics, A/B comparison, welfare analysis    │  v0.3+
├──────────────────────────────────────────────────────────────────────┤
│  MECHANISM              bids + access_windows → allocations          │  v0.2
├──────────────────────────────────────────────────────────────────────┤
│  SUPPLY                 TLEs + targets → access_windows              │  v0.2
├──────────────────────────────────────────────────────────────────────┤
│  DEMAND                 events × stakeholders → bids                 │  v0.1
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

## v0.2 preview

```
                   ┌───────────────► access_windows ─┐
                   │                                  │
TLE cache ──► supply (Skyfield)                       ├──► mechanism ──► allocations
                                                      │
events × stakeholders ──► bids (already v0.1) ───────┘
```

`scenario.build_full_scenario(seed, duration_hours, mechanism)` will glue the
three together and emit the unified Scenario JSON described in
`raveneyebuildspec.md` §3.1.

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

- `events.py` — pure dataclasses + enums. Imports nothing from other sim
  modules. The data model is the contract.
- `locations.py` — pure data. 15 hand-picked Hormuz-region locations, plus
  the per-`ObservableKind` `SENSOR_REQUIREMENTS` table.
- `phases.py` — `phase_at(t_hours)` is the sole behavioral function. Used by
  both event builders and the viewer.
- `scripted.py` — 20 narrative beats as plain Python literals. Easy to
  diff, easy to review for tone.
- `stochastic.py` — Knuth Poisson + per-type sampling defaults. Capped at
  4 events per 0.5h tick so runaway phases don't explode the count.
- `stakeholders.py` — 4 stakeholders, each with a `weights: dict[EventType,
  float]` on `[0, 2]`.
- `bids.py` — `derive_bids` and `urgency_factor`. Step function for
  urgency (≤4h → 1.6, ≤12h → 1.2, ≤24h → 1.0, ≤48h → 0.85, else 0.7).
- `build.py` — orchestrator + `_to_jsonable()` recursive helper that
  flattens enums to `.value` and dataclasses to dicts.

## Viewer

Static HTML. No build step. The viewer is intentionally not a framework
project — it has to survive being copied into a USB-stick demo or embedded
in a slide deck. `template.html` is a single file with inline CSS and JS;
`build_viewer.py` copies it next to a `sim.json` and that's the deployment.

The v0.2 globe viewer (CesiumJS) follows the same shape: static files
loaded from CDN, no bundler, `?scenario=path` override for swapping data.
