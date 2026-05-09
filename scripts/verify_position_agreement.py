"""Spot-check Skyfield (Python) ↔ satellite.js (browser) agreement.

The v0.2 supply layer computes access windows in Python via Skyfield/SGP4.
The viewer propagates the same TLEs in the browser via satellite.js for
live on-screen positions. Both implementations wrap the same SGP4 source
(Vallado), but coordinate-frame and time-handling differences can produce
silent drift. The buildspec demands ≤1 km horizontal disagreement at any
sample time within the scenario span.

This script writes a JSON reference table — N satellites × M times,
each row containing the Python WGS84 lat/lon/alt — to
``scripts/position_reference.json``. The viewer's
``window.RavenEyeAgreement`` helper (loaded via the dev-mode flag below)
loads the same TLEs, propagates them in satellite.js at the same times,
and compares; any pair > 1 km is logged to the browser console as an
error.

Usage:
    python3 scripts/verify_position_agreement.py \\
        --tles tests/fixtures/tles.txt --out scripts/position_reference.json

Then open the staged globe viewer with ``?agreement=1`` (the flag
makes main.js fetch position_reference.json and run the JS-side compare).
"""
from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

from raveneye.orbital import (
    Constellation,
    by_id,
    build_satellites_from_fixture,
    propagate_subpoint,
)


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="verify_position_agreement")
    p.add_argument("--tles", type=Path, default=Path("tests/fixtures/tles.txt"))
    p.add_argument("--constellation", default="blacksky",
                   help="Constellation to attach to fixture sats (any works)")
    p.add_argument("--t0", default="2026-04-13T12:00:00+00:00",
                   help="Scenario start time (UTC ISO 8601)")
    p.add_argument("--duration-hours", type=float, default=168.0)
    p.add_argument("--n-samples", type=int, default=10,
                   help="Random samples per satellite (default 10)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", type=Path, default=Path("scripts/position_reference.json"))
    args = p.parse_args(argv)

    rng = random.Random(args.seed)
    t0 = datetime.fromisoformat(args.t0)
    duration_s = args.duration_hours * 3600.0

    constellation = by_id(args.constellation)
    sats = build_satellites_from_fixture(args.tles, constellation, t0)

    rows = []
    for sat in sats:
        for _ in range(args.n_samples):
            offset_s = rng.uniform(0.0, duration_s)
            t = t0 + timedelta(seconds=offset_s)
            sub = propagate_subpoint(sat, t)
            rows.append({
                "sat_id": sat["sat_id"],
                "norad_id": sat["norad_id"],
                "tle_line1": sat["tle_line1"],
                "tle_line2": sat["tle_line2"],
                "t_iso": t.replace(microsecond=0).isoformat(),
                "lat_deg": sub["lat"],
                "lon_deg": sub["lon"],
                "alt_km": sub["alt_km"],
            })

    out_payload = {
        "meta": {
            "tles_file": str(args.tles),
            "constellation": args.constellation,
            "t0_iso": args.t0,
            "duration_hours": args.duration_hours,
            "n_satellites": len(sats),
            "n_samples_per_sat": args.n_samples,
            "tolerance_km": 1.0,
            "generated_by": "scripts/verify_position_agreement.py",
        },
        "rows": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        json.dump(out_payload, f, indent=2, sort_keys=True)
    print(f"wrote {args.out} ({len(rows)} rows across {len(sats)} satellites)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
