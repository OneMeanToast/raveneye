"""Supply-layer orchestrator.

``build_supply`` is the public entry point: hand it constellations,
targets, a t0, and a duration, and it returns a JSON-shaped dict with the
satellites and their access windows.

Two flavors:
- ``build_supply`` — production path. Pulls TLEs via ``tle_ingest`` (with
  on-disk caching). Requires network on cache miss.
- ``build_supply_from_satellites`` — pre-built satellite list. No network.
  Used by tests and by alternative ingest paths.

A small ``targets_from_locations`` helper adapts the v0.1
``raveneye.sim.locations.LOCATIONS`` dict shape to the {target_id, lat,
lon} list these functions expect.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .access import find_access_windows
from .constellations import Constellation
from .propagate import build_satellites


def targets_from_locations(locations: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Adapt the v0.1 LOCATIONS dict to the access-window target shape."""
    return [
        {"target_id": loc_id, "lat": L["lat"], "lon": L["lon"]}
        for loc_id, L in locations.items()
    ]


def _assemble(
    satellites: List[Dict],
    access_windows: List[Dict],
    constellations: Iterable[Constellation],
    t0: datetime,
    duration_hours: float,
    *,
    seed: int,
    min_elevation_deg: float,
) -> Dict[str, Any]:
    return {
        "satellites": satellites,
        "access_windows": access_windows,
        "constellations": [c.to_dict() for c in constellations],
        "meta": {
            "t0_iso": t0.replace(microsecond=0).isoformat(),
            "duration_hours": float(duration_hours),
            "n_satellites": len(satellites),
            "n_access_windows": len(access_windows),
            "n_constellations": sum(1 for _ in constellations),
            "seed": int(seed),
            "min_elevation_deg": float(min_elevation_deg),
        },
    }


def build_supply(
    constellations: List[Constellation],
    targets: List[Dict[str, Any]],
    t0: datetime,
    duration_hours: float,
    cache_dir: Path,
    *,
    seed: int = 42,
    min_elevation_deg: float = 20.0,
    max_age_hours: float = 24.0,
) -> Dict[str, Any]:
    """Production supply build: fetch TLEs, propagate, find windows.

    ``seed`` is currently unused inside this function but is part of the
    signature for API consistency and forward compatibility (Planet Dove
    sub-sampling will use it in a later chunk).
    """
    sats = build_satellites(
        constellations, t0, cache_dir, max_age_hours=max_age_hours
    )
    windows = find_access_windows(
        sats, targets, t0, duration_hours, min_elevation_deg=min_elevation_deg
    )
    return _assemble(
        sats, windows, constellations, t0, duration_hours,
        seed=seed, min_elevation_deg=min_elevation_deg,
    )


def build_supply_from_satellites(
    satellites: List[Dict],
    targets: List[Dict[str, Any]],
    t0: datetime,
    duration_hours: float,
    *,
    constellations: Iterable[Constellation] = (),
    seed: int = 42,
    min_elevation_deg: float = 20.0,
) -> Dict[str, Any]:
    """Same shape as ``build_supply`` but with pre-built satellites.

    Useful for tests, for offline dev, and for alternative TLE sources
    (e.g. Space-Track exports) that don't go through CelesTrak caching.
    """
    windows = find_access_windows(
        satellites, targets, t0, duration_hours, min_elevation_deg=min_elevation_deg
    )
    return _assemble(
        satellites, windows, list(constellations), t0, duration_hours,
        seed=seed, min_elevation_deg=min_elevation_deg,
    )
