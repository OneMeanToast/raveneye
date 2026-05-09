"""Tests for raveneye.orbital.access — fully offline."""
from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path

import pytest

from raveneye.orbital.access import (
    find_access_windows,
    off_nadir_at_satellite,
    quality_score,
    solar_elevation_deg,
)
from raveneye.orbital.constellations import by_id
from raveneye.orbital.propagate import build_satellites_from_fixture


FIXTURE = Path(__file__).parent / "fixtures" / "tles.txt"
T0 = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
BANDAR_ABBAS = {"target_id": "bandar_abbas_naval", "lat": 27.129, "lon": 56.217}


@pytest.fixture(scope="module")
def fixture_sats_eo():
    """All 5 fixture sats wearing the BlackSky (EO) constellation hat."""
    return build_satellites_from_fixture(FIXTURE, by_id("blacksky"), T0)


@pytest.fixture(scope="module")
def noaa19_only(fixture_sats_eo):
    return [s for s in fixture_sats_eo if s["norad_id"] == 33591]


# -------- K3: integration test against an independently-derived count --------

def test_noaa19_passes_over_bandar_abbas_24h(noaa19_only):
    """NOAA 19 (sun-sync, ~14 revs/day, inc 99°) over a 27°N target.

    Independent calc: a near-polar SSO sat at this latitude sees ~2-4
    passes per day above 20° elevation. Computed reference from the
    committed fixture is 3 passes; assert exactly 3.
    """
    windows = find_access_windows(
        noaa19_only, [BANDAR_ABBAS], T0, duration_hours=24.0, min_elevation_deg=20.0
    )
    assert len(windows) == 3, f"expected 3 NOAA-19 passes, got {len(windows)}"
    for w in windows:
        assert w["duration_s"] >= 60.0, "passes shorter than 1 minute should be filtered"
        assert w["max_elevation_deg"] >= 20.0
        assert w["sat_id"].startswith("NOAA")
        assert w["target_id"] == "bandar_abbas_naval"


def test_window_ids_are_monotonic(noaa19_only):
    windows = find_access_windows(noaa19_only, [BANDAR_ABBAS], T0, 24.0)
    ids = [w["window_id"] for w in windows]
    assert ids == [f"AW-{i:05d}" for i in range(len(ids))]


def test_min_elevation_filters_low_passes(noaa19_only):
    high = find_access_windows(noaa19_only, [BANDAR_ABBAS], T0, 24.0, min_elevation_deg=60.0)
    low = find_access_windows(noaa19_only, [BANDAR_ABBAS], T0, 24.0, min_elevation_deg=20.0)
    assert len(high) <= len(low)
    for w in high:
        assert w["max_elevation_deg"] >= 60.0


def test_no_satellites_or_no_targets_returns_empty():
    assert find_access_windows([], [BANDAR_ABBAS], T0, 24.0) == []
    assert find_access_windows([{"sat_id": "X"}], [], T0, 24.0) == []


def test_geo_satellite_misses_off_nadir_constrained_target(fixture_sats_eo):
    """GOES 16 sits at 0° lat, ~75°W — Bandar Abbas at 56°E is on the wrong
    side of the planet, so a 24h scan should produce no windows above 20°.
    """
    goes = [s for s in fixture_sats_eo if s["norad_id"] == 41866]
    windows = find_access_windows(goes, [BANDAR_ABBAS], T0, 24.0, min_elevation_deg=20.0)
    assert windows == []


# -------- helper functions --------

def test_off_nadir_geometry():
    # Directly overhead → 0° off-nadir
    assert off_nadir_at_satellite(90.0, 600.0) == pytest.approx(0.0, abs=0.01)
    # On the horizon (elev 0) → max off-nadir; for h=600km, sin(N)=R/(R+h)≈0.914
    n = off_nadir_at_satellite(0.0, 600.0)
    assert n == pytest.approx(math.degrees(math.asin(6371.0 / 6971.0)), abs=0.01)
    # Higher altitude → smaller off-nadir for same elev
    assert off_nadir_at_satellite(20.0, 600.0) > off_nadir_at_satellite(20.0, 35786.0)


def test_quality_score_eo_vs_sar():
    # EO at perfect overhead pass with full sun should score ~1.0
    eo = quality_score(90.0, 60.0, 0.0, is_sar=False)
    assert 0.95 <= eo <= 1.0
    # SAR ignores sun
    sar_day = quality_score(90.0, 60.0, 0.0, is_sar=True)
    sar_night = quality_score(90.0, -30.0, 0.0, is_sar=True)
    assert sar_day == sar_night
    # Negative sun elevation (night) should hurt EO
    eo_night = quality_score(90.0, -10.0, 0.0, is_sar=False)
    assert eo_night < eo


def test_quality_score_off_nadir_penalty():
    base = quality_score(60.0, 30.0, 0.0, is_sar=False)
    skewed = quality_score(60.0, 30.0, 40.0, is_sar=False)
    assert skewed < base


# -------- analytical solar position --------

def test_solar_elevation_noon_summer_high_lat():
    """Local solar noon at the equator on equinox should put sun ~near zenith."""
    equinox = datetime(2024, 3, 20, 12, 0, 0, tzinfo=timezone.utc)
    e = solar_elevation_deg(0.0, 0.0, equinox)
    assert e > 80.0, f"sun should be near zenith at equator equinox noon, got {e}"


def test_solar_elevation_midnight_below_horizon():
    """Midnight local time → sun below horizon."""
    midnight = datetime(2024, 6, 21, 0, 0, 0, tzinfo=timezone.utc)
    # Bandar Abbas at UTC midnight is local 03:30 — still well before sunrise
    e = solar_elevation_deg(27.129, 56.217, midnight)
    assert e < 0.0


def test_solar_elevation_smooth_in_time():
    """Sun elevation should be a continuous function — no NaNs/jumps."""
    base = datetime(2024, 7, 1, 9, 0, 0, tzinfo=timezone.utc)
    elevs = [
        solar_elevation_deg(27.129, 56.217, base.replace(minute=m))
        for m in range(0, 60, 10)
    ]
    diffs = [abs(elevs[i + 1] - elevs[i]) for i in range(len(elevs) - 1)]
    for d in diffs:
        assert d < 5.0, "10-minute solar-elevation jumps should be small"
