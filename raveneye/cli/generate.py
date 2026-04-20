"""``raveneye-generate`` CLI — build a scenario JSON and optionally stage the viewer."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import List, Optional

from ..sim import build_sim


def _print_stats(scenario: dict, stream=sys.stderr) -> None:
    meta = scenario["meta"]
    print(f"scenario: {meta['scenario']}", file=stream)
    print(f"seed={meta['seed']}  t0={meta['t0_iso']}  duration_h={meta['duration_hours']}", file=stream)
    print(f"n_events={meta['n_events']}  n_bids={meta['n_bids']}", file=stream)
    by_phase = Counter(e["phase"] for e in scenario["events"])
    by_type = Counter(e["event_type"] for e in scenario["events"])
    print("events by phase:", file=stream)
    for p in meta["phases"]:
        print(f"  {p['name']:22} {by_phase.get(p['name'], 0)}", file=stream)
    print("events by type:", file=stream)
    for t in sorted(by_type):
        print(f"  {t:28} {by_type[t]}", file=stream)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="raveneye-generate",
        description="Build a RavenEye v0.1 scenario (events + bids) as JSON.",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--duration", type=float, default=168.0, help="Scenario duration in hours.")
    parser.add_argument("--out", type=Path, default=Path("sim.json"))
    parser.add_argument(
        "--viewer",
        type=Path,
        default=None,
        help="Stage the v0.1 flat-map viewer into this directory (copies template + sim.json).",
    )
    parser.add_argument("--stats", action="store_true", help="Print summary stats to stderr.")
    args = parser.parse_args(argv)

    scenario = build_sim(seed=args.seed, duration_hours=args.duration)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(scenario, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.out} ({args.out.stat().st_size:,} bytes)")

    if args.viewer is not None:
        from ..viewer.build_viewer import stage_viewer

        viewer_path = stage_viewer(args.viewer, scenario)
        print(f"staged viewer at {viewer_path}")

    if args.stats:
        _print_stats(scenario)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
