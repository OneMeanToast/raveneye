"""Access-window computation for the v0.2 supply layer.

A window is a time span during which a specific satellite can feasibly
image a specific target. We use Skyfield's ``EarthSatellite.find_events``
to compute rise / culminate / set triples per (sat, target) pair.

Sun elevation at mid-window comes from a closed-form NOAA-style solar
position approximation (~1° accurate) rather than a JPL ephemeris, so the
v0.2 test suite stays fully offline.

Quality score (after spec):
    EO:  0.4 × (max_elev/90) + 0.3 × max(0, sun_elev/30)
       + 0.3 × max(0, 1 − |off_nadir|/45)
    SAR: 0.55 × (max_elev/90) + 0.45 × max(0, 1 − |off_nadir|/45)
    (sun term dropped — SAR is illumination-independent)
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from skyfield.api import load, wgs84

from .propagate import make_skyfield_satellite

logger = logging.getLogger(__name__)


EARTH_RADIUS_KM = 6371.0
_TS = None


def _ts():
    global _TS
    if _TS is None:
        _TS = load.timescale(builtin=True)
    return _TS


# ----------------------------------------------------------------------
# Solar position (analytical, ephemeris-free)
# ----------------------------------------------------------------------

def solar_elevation_deg(lat: float, lon: float, dt: datetime) -> float:
    """Approximate solar elevation in degrees.

    Implements the NOAA Solar Calculator's spencer-fourier expansion. Good
    to roughly 0.5–1.0° everywhere on Earth — more than enough fidelity for
    a tasking-quality discount factor. Avoids the JPL ephemeris dependency.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt_utc = dt.astimezone(timezone.utc)
    n = dt_utc.timetuple().tm_yday
    hour_frac = dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
    gamma = 2.0 * math.pi / 365.0 * (n - 1 + (hour_frac - 12) / 24.0)

    eqtime = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )
    decl = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.001480 * math.sin(3 * gamma)
    )

    tst = hour_frac * 60.0 + eqtime + 4.0 * lon  # true solar time, minutes
    ha = math.radians(tst / 4.0 - 180.0)         # hour angle, radians
    lat_r = math.radians(lat)
    cos_zen = (
        math.sin(lat_r) * math.sin(decl)
        + math.cos(lat_r) * math.cos(decl) * math.cos(ha)
    )
    cos_zen = max(-1.0, min(1.0, cos_zen))
    return 90.0 - math.degrees(math.acos(cos_zen))


# ----------------------------------------------------------------------
# Geometry
# ----------------------------------------------------------------------

def off_nadir_at_satellite(elev_deg: float, alt_km: float) -> float:
    """Off-nadir angle (deg) at the satellite for a target seen at ground
    elevation ``elev_deg``.

    Spherical-Earth law-of-sines: sin(off_nadir) = R/(R+h) · cos(elev).
    """
    e = math.radians(max(0.0, min(90.0, elev_deg)))
    arg = (EARTH_RADIUS_KM / (EARTH_RADIUS_KM + max(0.1, alt_km))) * math.cos(e)
    arg = max(-1.0, min(1.0, arg))
    return math.degrees(math.asin(arg))


def quality_score(
    max_elev_deg: float,
    sun_elev_deg: float,
    off_nadir_deg: float,
    *,
    is_sar: bool,
) -> float:
    e_term = max(0.0, min(1.0, max_elev_deg / 90.0))
    on_term = max(0.0, 1.0 - abs(off_nadir_deg) / 45.0)
    if is_sar:
        return round(0.55 * e_term + 0.45 * on_term, 3)
    s_term = max(0.0, min(1.0, sun_elev_deg / 30.0))
    return round(0.4 * e_term + 0.3 * s_term + 0.3 * on_term, 3)


# ----------------------------------------------------------------------
# Window builder
# ----------------------------------------------------------------------

def _altitude_at(es, topos, t) -> float:
    """Sat altitude angle (deg) above the local horizon at the target."""
    diff = es - topos
    alt, _, _ = diff.at(t).altaz()
    return float(alt.degrees)


def _sat_alt_km(es, t) -> float:
    sub = wgs84.subpoint(es.at(t))
    return float(sub.elevation.km)


def _window_dict(
    sat: Dict,
    target: Dict,
    rise_dt: datetime,
    cul_dt: datetime,
    set_dt: datetime,
    max_elev_deg: float,
    sat_alt_km: float,
) -> Dict[str, Any]:
    is_sar = sat.get("sensor_class", "").startswith("SAR")
    off_nadir = off_nadir_at_satellite(max_elev_deg, sat_alt_km)
    mid_dt = rise_dt + (set_dt - rise_dt) / 2
    sun_elev = solar_elevation_deg(target["lat"], target["lon"], mid_dt)
    aw = {
        "window_id": "AW-PENDING",   # reassigned after global sort
        "sat_id": sat["sat_id"],
        "target_lat": float(target["lat"]),
        "target_lon": float(target["lon"]),
        "start_iso": rise_dt.replace(microsecond=0).isoformat(),
        "end_iso": set_dt.replace(microsecond=0).isoformat(),
        "culminate_iso": cul_dt.replace(microsecond=0).isoformat(),
        "duration_s": round((set_dt - rise_dt).total_seconds(), 1),
        "max_elevation_deg": round(max_elev_deg, 2),
        "off_nadir_at_culminate_deg": round(off_nadir, 2),
        "sun_elevation_deg": round(sun_elev, 2),
        "quality_score": quality_score(
            max_elev_deg, sun_elev, off_nadir, is_sar=is_sar
        ),
    }
    if "target_id" in target:
        aw["target_id"] = target["target_id"]
    return aw


def find_access_windows(
    satellites: List[Dict],
    targets: List[Dict],
    t0: datetime,
    duration_hours: float,
    *,
    min_elevation_deg: float = 20.0,
    min_duration_s: float = 30.0,
) -> List[Dict]:
    """Find all (sat, target) access windows in ``[t0, t0+duration_hours]``.

    Each target dict must have ``lat`` and ``lon`` (decimal degrees) and may
    have ``target_id`` (carried through to the output for joins).

    Drops windows shorter than ``min_duration_s`` (default 30 s — too short
    for any realistic acquisition) or whose required off-nadir exceeds the
    satellite's ``max_off_nadir_deg``.
    """
    if not satellites or not targets:
        return []

    ts = _ts()
    t_start = ts.from_datetime(_aware(t0))
    t_end = ts.from_datetime(_aware(t0) + timedelta(hours=duration_hours))

    out: List[Dict] = []
    for sat_dict in satellites:
        es = make_skyfield_satellite(sat_dict)
        max_off_nadir_allowed = float(sat_dict.get("max_off_nadir_deg", 45.0))
        for target in targets:
            topos = wgs84.latlon(float(target["lat"]), float(target["lon"]))
            try:
                times, events = es.find_events(
                    topos,
                    t_start,
                    t_end,
                    altitude_degrees=min_elevation_deg,
                )
            except Exception as exc:
                logger.warning(
                    "find_events failed for %s @ (%.3f,%.3f): %s",
                    sat_dict["sat_id"], target["lat"], target["lon"], exc,
                )
                continue
            out.extend(
                _windows_from_events(
                    sat_dict,
                    target,
                    es,
                    topos,
                    times,
                    events,
                    max_off_nadir_allowed=max_off_nadir_allowed,
                    min_duration_s=min_duration_s,
                )
            )

    out.sort(key=lambda a: (a["start_iso"], a["sat_id"]))
    for i, aw in enumerate(out):
        aw["window_id"] = f"AW-{i:05d}"
    return out


def _windows_from_events(
    sat_dict: Dict,
    target: Dict,
    es,
    topos,
    times,
    events,
    *,
    max_off_nadir_allowed: float,
    min_duration_s: float,
) -> List[Dict]:
    """Walk Skyfield's (rise=0, culminate=1, set=2) stream into windows.

    Defensive against the known edge cases noted in Skyfield issues #559,
    #1000, #1017: streams that begin mid-pass (no rise event) or end
    mid-pass (no set event). We synthesize the missing boundary using the
    requested ``t_start`` / ``t_end`` so the window survives.
    """
    out: List[Dict] = []
    rise: Optional[Any] = None
    cul: Optional[Any] = None
    for t, ev in zip(times, events):
        if ev == 0:        # rise
            rise = t
            cul = None
        elif ev == 1:      # culminate
            cul = t
            if rise is None:
                rise = t   # mid-pass start
        elif ev == 2:      # set
            if rise is None:
                continue   # set without rise — drop
            if cul is None:
                cul = rise + (t - rise) / 2  # synthesize culmination at midpoint
            try:
                max_elev = _altitude_at(es, topos, cul)
                sat_alt = _sat_alt_km(es, cul)
            except Exception as exc:
                logger.warning("culmination eval failed for %s: %s", sat_dict["sat_id"], exc)
                rise = cul = None
                continue
            rise_dt = rise.utc_datetime()
            cul_dt = cul.utc_datetime()
            set_dt = t.utc_datetime()
            if (set_dt - rise_dt).total_seconds() < min_duration_s:
                rise = cul = None
                continue
            off_nadir = off_nadir_at_satellite(max_elev, sat_alt)
            if off_nadir > max_off_nadir_allowed:
                rise = cul = None
                continue
            out.append(_window_dict(sat_dict, target, rise_dt, cul_dt, set_dt, max_elev, sat_alt))
            rise = cul = None
    return out


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
