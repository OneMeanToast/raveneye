# TODO — forward parking lot

Things noticed during v0.1 development that are intentionally **out of
scope** for v0.1 and v0.2. Logged here so they aren't forgotten and so
future work doesn't have to re-derive the same observations.

When you pick one of these up, file it as a GitHub issue and remove the
corresponding line from this file.

## v0.2 candidates (already in `raveneyebuildspec.md` §5)

- [ ] Supply layer (`raveneye/orbital/`) — TLE/OMM ingest, SGP4, access
      windows, quality scoring.
- [ ] Mechanism layer (`raveneye/mechanism/`) — `GreedyPriorityMechanism`
      and `SequentialSingleItemMechanism`.
- [ ] CesiumJS globe viewer (`raveneye/viewer/globe/`).
- [ ] Python ↔ JavaScript SGP4 position-agreement check (≤ 1 km).

These are tracked in the buildspec and don't need separate issues.

## v0.3+ — evaluation layer

- [ ] Welfare metrics: per-stakeholder satisfaction, drop rate by event
      type / phase, time-to-collect distribution, equity (Jain's index)
      across stakeholders.
- [ ] A/B comparison harness: run the same scenario through N mechanisms,
      diff allocations, surface where they disagreed.
- [ ] Multi-seed sweep: characterize mechanism variance across e.g.
      20 seeds at fixed scenario length.

## Demand-layer ideas (post-v0.2)

- [ ] **Bid revision.** Allow a stakeholder to update or withdraw a bid as
      new information arrives (e.g. a HUMINT_REPORT that gets corroborated
      becomes higher-confidence; a VESSEL_DARK that comes back on AIS
      should drop).
- [ ] **Cross-event correlation.** A KINETIC_STRIKE following a
      MINE_LAYING_REPORT in the same area should boost the latter's
      retroactive priority.
- [ ] **Stakeholder budgets.** Each stakeholder gets a finite "bid budget"
      per scenario; forces them to triage rather than blanket-bid.
- [ ] **Doctrine-specific stakeholders.** Add CJTF-OIR, EUNAVFOR ATALANTA,
      JMSDF as additional stakeholder personas with distinct weight
      profiles. Each one expands the multi-utility surface.
- [ ] **Per-stakeholder confidence floors.** A stakeholder may refuse to
      bid on events below their confidence threshold.

## Supply-layer ideas (post-v0.2)

- [ ] **Per-satellite duty-cycle accounting.** Track minutes-per-day of
      tasking already committed; reject windows that would push past
      `duty_cycle_pct`.
- [ ] **Slew constraints between consecutive collects.** Enforce
      `slew_rate_deg_s` between back-to-back tasks on the same sat.
- [ ] **Cloud forecast ingestion.** Replace the WEATHER_DEGRADATION stub
      with real cloud-cover predictions (e.g. ECMWF, GFS) as a per-window
      attenuation on quality_score.
- [ ] **Tasking latency model.** Some constellations cannot retask within
      X minutes of acquisition. Model that.

## Mechanism-layer ideas (post-v0.2)

- [ ] **CBBA** (Consensus-Based Bundle Algorithm) — distributed multi-
      agent allocation.
- [ ] **VCG** (Vickrey-Clarke-Groves) — strategy-proof but socially
      complicated. Worth it as a theoretical baseline.
- [ ] **Mixed-integer programming** baseline (PuLP / OR-Tools) so we have
      an offline optimum to benchmark heuristics against.
- [ ] **Two-sided matching** treating bids and windows symmetrically.

## Viewer / UX

- [ ] **Per-stakeholder filter** on the event feed and bid panel.
- [ ] **Bid-priority histogram** in a side panel — show how scores cluster
      by phase and stakeholder.
- [ ] **Hover preview on the timeline** — without committing the playhead,
      preview the map state at hover time.
- [ ] **URL state sync** — bookmarkable `?t=42.5&event=SCR-005` links so
      demos can jump straight to a moment.
- [ ] **Export PNG** of the current map state for slide decks.
- [ ] **WebGL atlas of location markers** for v0.2 globe view; SVG is fine
      for v0.1 but won't scale to 100+ access-window swaths.

## Tooling

- [ ] **CI** — GitHub Actions: pytest, ruff, basic JS lint of
      `template.html` (eslint with `--no-eslintrc` and a minimal config).
- [ ] **Coverage gate** — keep test coverage above 80% (`pytest --cov`
      already wired via `[dev]`).
- [ ] **Pre-commit** hooks — black, ruff, end-of-file-fixer.
- [ ] **Static type check** — mypy on `raveneye/`.
- [ ] **Versioned docs** — when v0.2 ships, version-tag `docs/` so
      `docs/v0.1/` and `docs/v0.2/` coexist.

## Explicit non-goals (don't build, even if asked)

These are listed in `raveneyebuildspec.md` §8 and repeated here for
visibility.

- Foundry / ontology export.
- Classified scenarios, ITAR-restricted TLEs, live operational feeds.
- Live web-streaming of TLEs; CelesTrak's free tier is the boundary.
- Multi-scenario A/B testing UI in the v0.2 viewer (that's evaluation
  layer = v0.3+).
- Replay save / export, session bookmarking (low priority for an
  evaluation testbed).
