"""Skyfield/SGP4 wrapper that turns TLEs into satellite dicts.

This module owns the TLE → ``Satrec`` → ``EarthSatellite`` plumbing and
emits the Satellite schema documented in ``raveneyebuildspec.md`` §3.2.
Access-window computation lives in ``access.py``; coverage geometry in
``coverage.py``.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from sgp4.api import Satrec
from skyfield.api import EarthSatellite, load

from .constellations import Constellation
from .tle_ingest import TleTriple, load_cached_or_fetch, parse_tle_text

logger = logging.getLogger(__name__)


_TS = None


def _ts():
    """Lazy Skyfield timescale; safe to call repeatedly."""
    global _TS
    if _TS is None:
        _TS = load.timescale(builtin=True)
    return _TS


def _epoch_iso_from_satrec(satrec: Satrec) -> str:
    """Convert ``satrec.jdsatepoch + jdsatepochF`` to an ISO 8601 UTC string."""
    jd = satrec.jdsatepoch + satrec.jdsatepochF
    # Unix epoch in JD: 2440587.5 = 1970-01-01T00:00:00Z
    seconds_since_unix = (jd - 2440587.5) * 86400.0
    dt = datetime.fromtimestamp(seconds_since_unix, tz=timezone.utc)
    return dt.replace(microsecond=0).isoformat()


def _safe_sat_id(name: str, norad_id: int) -> str:
    """Stable, URL-safe satellite ID — used as the bid<->window join key."""
    base = name.strip().replace(" ", "_").replace("(", "").replace(")", "")
    base = "".join(c for c in base if c.isalnum() or c in "_-")
    return f"{base}-{norad_id}" if base else f"SAT-{norad_id}"


def _satellite_dict(
    triple: TleTriple,
    constellation: Constellation,
    t0: datetime,
) -> Optional[Dict]:
    name, l1, l2 = triple
    try:
        satrec = Satrec.twoline2rv(l1, l2)
    except Exception as exc:
        logger.warning("failed to parse TLE for %r: %s", name, exc)
        return None

    epoch_iso = _epoch_iso_from_satrec(satrec)
    epoch_dt = datetime.fromisoformat(epoch_iso)
    delta_days = abs((t0 - epoch_dt).total_seconds()) / 86400.0
    if delta_days > 7.0:
        logger.warning(
            "TLE for %r is %.1f days from scenario t0; SGP4 accuracy degrades beyond ~7d",
            name, delta_days,
        )

    return {
        "sat_id": _safe_sat_id(name, satrec.satnum),
        "name": name.strip(),
        "norad_id": int(satrec.satnum),
        "constellation_id": constellation.constellation_id,
        "vendor": constellation.vendor,
        "tle_line1": l1,
        "tle_line2": l2,
        "tle_epoch_iso": epoch_iso,
        "tle_age_days": round(delta_days, 2),
        "sensor_class": constellation.sensor_class,
        "nominal_gsd_m": constellation.nominal_gsd_m,
        "spectral_bands": list(constellation.spectral_bands),
        "max_off_nadir_deg": constellation.max_off_nadir_deg,
        "swath_width_km": constellation.swath_width_km,
        "slew_rate_deg_s": constellation.slew_rate_deg_s,
        "duty_cycle_pct": constellation.duty_cycle_pct,
    }


def build_satellites(
    constellations: List[Constellation],
    t0: datetime,
    cache_dir: Path,
    *,
    max_age_hours: float = 24.0,
) -> List[Dict]:
    """Fetch TLEs for each constellation and emit Satellite dicts.

    Order is deterministic: sorted by ``(constellation_id, norad_id)`` so
    repeat runs produce byte-identical scenario JSON.

    On per-constellation fetch failure we log and continue rather than
    abort the whole supply build — the missing constellation simply
    contributes zero satellites.
    """
    out: List[Dict] = []
    for constellation in constellations:
        try:
            triples = load_cached_or_fetch(
                constellation.celestrak_group,
                cache_dir,
                max_age_hours=max_age_hours,
            )
        except Exception as exc:  # network/IO at boundary; keep building
            logger.error(
                "TLE load failed for %s: %s — skipping constellation",
                constellation.constellation_id,
                exc,
            )
            continue
        for triple in triples:
            sat = _satellite_dict(triple, constellation, t0)
            if sat is not None:
                out.append(sat)
    out.sort(key=lambda s: (s["constellation_id"], s["norad_id"]))
    return out


def build_satellites_from_fixture(
    fixture_path: Path,
    constellation: Constellation,
    t0: datetime,
) -> List[Dict]:
    """Build satellites from a local TLE file (no network).

    Used by tests so the propagation+access stack can be exercised offline.
    """
    triples = parse_tle_text(Path(fixture_path).read_text(encoding="utf-8"))
    out = [
        s for s in (_satellite_dict(t, constellation, t0) for t in triples)
        if s is not None
    ]
    out.sort(key=lambda s: s["norad_id"])
    return out


def make_skyfield_satellite(sat_dict: Dict) -> EarthSatellite:
    """Construct a Skyfield ``EarthSatellite`` from a satellite dict."""
    return EarthSatellite(
        sat_dict["tle_line1"],
        sat_dict["tle_line2"],
        sat_dict.get("name", sat_dict["sat_id"]),
        _ts(),
    )


def propagate_subpoint(sat_dict: Dict, t: datetime) -> Dict[str, float]:
    """Sub-satellite point at UTC time ``t`` in WGS84.

    Returns ``{"lat", "lon", "alt_km"}``. Used by tests to spot-check
    that propagate.py and the JS satellite.js path agree (≤1 km, see
    ``scripts/verify_position_agreement.py`` in v0.2 phase L).
    """
    from skyfield.api import wgs84

    sat = make_skyfield_satellite(sat_dict)
    geo = sat.at(_ts().from_datetime(t))
    sub = wgs84.subpoint(geo)
    return {
        "lat": float(sub.latitude.degrees),
        "lon": float(sub.longitude.degrees),
        "alt_km": float(sub.elevation.km),
    }
