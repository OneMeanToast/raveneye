"""raveneye-build-scenario CLI — produce a unified v0.2 scenario.json.

The v0.2 counterpart to ``raveneye-generate``. Joins demand + supply +
mechanism into one JSON.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import List, Optional

from ..orbital import build_satellites_from_fixture, by_id
from ..scenario import build_full_scenario, build_full_scenario_offline
from ..sim import DEFAULT_T0


def _parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="raveneye-build-scenario",
        description="Generate a RavenEye v0.2 scenario (events + bids + supply + allocations).",
    )
    p.add_argument("--seed", type=int, default=42, help="RNG seed (default 42).")
    p.add_argument(
        "--duration", type=float, default=168.0,
        help="Scenario duration in hours (default 168 = 7 days).",
    )
    p.add_argument(
        "--mechanism", choices=["greedy", "ssi"], default="greedy",
        help="Allocation mechanism (default greedy).",
    )
    p.add_argument(
        "--out", type=Path, default=Path("scenario.json"),
        help="Output scenario JSON path (default scenario.json).",
    )
    p.add_argument(
        "--viewer", type=Path, default=None,
        help="If set, stage the globe viewer at this directory.",
    )
    p.add_argument(
        "--cache-dir", type=Path, default=Path("data/tle_cache"),
        help="Directory for CelesTrak TLE cache (default data/tle_cache).",
    )
    p.add_argument(
        "--refresh-tles", action="store_true",
        help="Bypass cache and re-fetch TLEs.",
    )
    p.add_argument(
        "--tle-fixture", type=Path, default=None,
        help="If set, use this offline TLE file instead of fetching from "
             "CelesTrak. Useful for offline dev and air-gapped demos.",
    )
    p.add_argument(
        "--fixture-constellation", default="blacksky",
        help="Constellation ID to attach to satellites loaded from --tle-fixture.",
    )
    p.add_argument(
        "--min-elevation", type=float, default=20.0,
        help="Minimum elevation (deg) for an access window (default 20).",
    )
    p.add_argument(
        "--stats", action="store_true",
        help="Print summary stats to stderr.",
    )
    return p.parse_args(argv)


def _print_stats(scenario: dict) -> None:
    meta = scenario["meta"]
    events = scenario.get("events", [])
    bids = scenario.get("bids", [])
    allocs = scenario.get("allocations", [])

    per_phase = Counter(e["phase"] for e in events)
    per_type = Counter(e["event_type"] for e in events)
    per_status = Counter(a["status"] for a in allocs)

    print(f"scenario: {meta.get('scenario')}", file=sys.stderr)
    print(
        f"t0: {meta.get('t0_iso')}  duration: {meta.get('duration_hours')}h  "
        f"seed: {meta.get('seed')}  mechanism: {meta.get('mechanism')}",
        file=sys.stderr,
    )
    print(
        f"demand:  events={meta.get('n_events')}  bids={meta.get('n_bids')}",
        file=sys.stderr,
    )
    print(
        f"supply:  satellites={meta.get('n_satellites')}  "
        f"constellations={meta.get('n_constellations')}  "
        f"access_windows={meta.get('n_access_windows')}",
        file=sys.stderr,
    )
    print(
        f"alloc:   total={meta.get('n_allocations')}  "
        f"scheduled={meta.get('n_scheduled')}  "
        f"dropped={meta.get('n_dropped')}  "
        f"drop_rate={meta.get('drop_rate')}  "
        f"welfare={meta.get('total_welfare')}",
        file=sys.stderr,
    )

    print("events per phase:", file=sys.stderr)
    for ph in meta.get("phases", []):
        print(f"  {ph['name']:24s} {per_phase.get(ph['name'], 0):4d}", file=sys.stderr)

    print("events per type:", file=sys.stderr)
    for t, c in sorted(per_type.items(), key=lambda kv: -kv[1]):
        print(f"  {t:28s} {c:4d}", file=sys.stderr)

    print("allocation status:", file=sys.stderr)
    for s, c in sorted(per_status.items(), key=lambda kv: -kv[1]):
        print(f"  {s:18s} {c:4d}", file=sys.stderr)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)

    if args.tle_fixture is not None:
        try:
            constellation = by_id(args.fixture_constellation)
        except KeyError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        satellites = build_satellites_from_fixture(args.tle_fixture, constellation, DEFAULT_T0)
        scenario = build_full_scenario_offline(
            satellites,
            seed=args.seed,
            duration_hours=args.duration,
            mechanism=args.mechanism,
            constellations=[constellation],
            min_elevation_deg=args.min_elevation,
        )
    else:
        scenario = build_full_scenario(
            seed=args.seed,
            duration_hours=args.duration,
            mechanism=args.mechanism,
            cache_dir=args.cache_dir,
            min_elevation_deg=args.min_elevation,
            max_age_hours=0.0 if args.refresh_tles else 24.0,
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        json.dump(scenario, f, indent=2, sort_keys=True)
    print(
        f"wrote {args.out} "
        f"(events={scenario['meta']['n_events']} "
        f"bids={scenario['meta']['n_bids']} "
        f"satellites={scenario['meta']['n_satellites']} "
        f"windows={scenario['meta']['n_access_windows']} "
        f"allocations={scenario['meta']['n_allocations']})"
    )

    if args.viewer is not None:
        # The globe viewer arrives in the next v0.2 chunk; for now we stage
        # the v0.1 flat-map viewer with the scenario JSON. scenario.json is
        # a superset of sim.json (events + bids carry through unchanged), so
        # the flat viewer renders it correctly — it just doesn't yet show the
        # supply / allocation overlays.
        from ..viewer.build_viewer import stage_viewer

        # stage_viewer writes scenario.json under the legacy "sim.json" name
        # so the unmodified v0.1 template fetches it.
        out_dir = stage_viewer(args.viewer, scenario)
        print(f"staged viewer at {out_dir} (open index.html via `python3 -m http.server`)")

    if args.stats:
        _print_stats(scenario)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
