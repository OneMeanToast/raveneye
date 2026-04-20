"""raveneye-generate CLI — produce a v0.1 sim.json (and optionally stage the viewer)."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import List, Optional

from ..sim import build_sim


def _parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="raveneye-generate",
        description="Generate a RavenEye v0.1 scenario (events + bids).",
    )
    p.add_argument("--seed", type=int, default=42, help="RNG seed (default 42).")
    p.add_argument(
        "--duration",
        type=float,
        default=168.0,
        help="Scenario duration in hours (default 168 = 7 days).",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=Path("sim.json"),
        help="Output JSON path (default sim.json).",
    )
    p.add_argument(
        "--viewer",
        type=Path,
        default=None,
        help="If set, stage the flat-map viewer at this directory.",
    )
    p.add_argument(
        "--stats",
        action="store_true",
        help="Print summary stats to stderr (events per phase and per type).",
    )
    return p.parse_args(argv)


def _print_stats(sim: dict) -> None:
    meta = sim["meta"]
    events = sim["events"]
    bids = sim["bids"]

    per_phase: Counter = Counter(e["phase"] for e in events)
    per_type: Counter = Counter(e["event_type"] for e in events)
    per_stakeholder: Counter = Counter(b["stakeholder_id"] for b in bids)

    print(f"scenario: {meta['scenario']}", file=sys.stderr)
    print(f"t0: {meta['t0_iso']}  duration: {meta['duration_hours']}h  seed: {meta['seed']}", file=sys.stderr)
    print(f"totals: events={meta['n_events']}  bids={meta['n_bids']}", file=sys.stderr)

    print("events per phase:", file=sys.stderr)
    for phase_info in meta["phases"]:
        name = phase_info["name"]
        print(f"  {name:24s} {per_phase.get(name, 0):4d}", file=sys.stderr)

    print("events per type:", file=sys.stderr)
    for t, c in sorted(per_type.items(), key=lambda kv: -kv[1]):
        print(f"  {t:28s} {c:4d}", file=sys.stderr)

    print("bids per stakeholder:", file=sys.stderr)
    for s, c in sorted(per_stakeholder.items(), key=lambda kv: -kv[1]):
        print(f"  {s:22s} {c:4d}", file=sys.stderr)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    sim = build_sim(seed=args.seed, duration_hours=args.duration)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        json.dump(sim, f, indent=2, sort_keys=True)
    print(f"wrote {args.out} ({sim['meta']['n_events']} events, {sim['meta']['n_bids']} bids)")

    if args.viewer is not None:
        from ..viewer.build_viewer import stage_viewer

        out_dir = stage_viewer(args.viewer, sim)
        print(f"staged viewer at {out_dir} (open index.html via `python3 -m http.server`)")

    if args.stats:
        _print_stats(sim)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
