"""Tests for raveneye.orbital.propagate.

Run fully offline against ``tests/fixtures/tles.txt``.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from raveneye.orbital.constellations import by_id
from raveneye.orbital.propagate import (
    build_satellites_from_fixture,
    make_skyfield_satellite,
    propagate_subpoint,
    _epoch_iso_from_satrec,
    _safe_sat_id,
)


FIXTURE = Path(__file__).parent / "fixtures" / "tles.txt"
T0 = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def fixture_sats():
    """All 5 fixture satellites built once per test module."""
    return build_satellites_from_fixture(FIXTURE, by_id("blacksky"), T0)


def test_fixture_yields_five_satellites(fixture_sats):
    assert len(fixture_sats) == 5
    norad_ids = [s["norad_id"] for s in fixture_sats]
    assert sorted(norad_ids) == norad_ids, "fixture must be sorted by NORAD ID"
    assert set(norad_ids) == {25544, 25994, 33591, 41866, 49260}


def test_satellite_dict_schema(fixture_sats):
    iss = next(s for s in fixture_sats if s["norad_id"] == 25544)
    required = {
        "sat_id", "name", "norad_id", "constellation_id", "vendor",
        "tle_line1", "tle_line2", "tle_epoch_iso", "tle_age_days",
        "sensor_class", "nominal_gsd_m", "spectral_bands",
        "max_off_nadir_deg", "swath_width_km", "slew_rate_deg_s", "duty_cycle_pct",
    }
    assert required.issubset(iss.keys())
    assert iss["sat_id"] == "ISS_ZARYA-25544"
    assert iss["name"] == "ISS (ZARYA)"
    assert iss["constellation_id"] == "blacksky"
    assert iss["tle_line1"].startswith("1 25544")
    assert iss["tle_line2"].startswith("2 25544")
    assert isinstance(iss["spectral_bands"], list)


def test_iss_propagation_matches_skyfield_reference(fixture_sats):
    """K2: propagate ISS at a known time; assert lat/lon/alt agree.

    Reference values were captured from a clean Skyfield 1.49+ run on the
    committed fixture. Tolerance: 10 km horizontal, 1 km vertical.
    """
    iss = next(s for s in fixture_sats if s["norad_id"] == 25544)
    sub = propagate_subpoint(iss, T0)
    REF = {"lat": -0.089178, "lon": 165.485265, "alt_km": 417.479}

    # Convert lat/lon error to km (1° lat ≈ 111 km; lon scaled by cos(lat))
    import math
    dlat_km = abs(sub["lat"] - REF["lat"]) * 111.0
    dlon_km = abs(sub["lon"] - REF["lon"]) * 111.0 * math.cos(math.radians(REF["lat"]))
    horiz_err_km = math.hypot(dlat_km, dlon_km)
    vert_err_km = abs(sub["alt_km"] - REF["alt_km"])
    assert horiz_err_km < 10.0, f"horizontal error {horiz_err_km:.2f} km > 10 km"
    assert vert_err_km < 1.0, f"vertical error {vert_err_km:.2f} km > 1 km"


def test_propagation_is_deterministic(fixture_sats):
    """Same satellite + same time → byte-identical sub-points."""
    iss = next(s for s in fixture_sats if s["norad_id"] == 25544)
    a = propagate_subpoint(iss, T0)
    b = propagate_subpoint(iss, T0)
    assert a == b


def test_propagation_changes_with_time(fixture_sats):
    """ISS sub-point must move materially over 30 minutes."""
    iss = next(s for s in fixture_sats if s["norad_id"] == 25544)
    p0 = propagate_subpoint(iss, T0)
    p1 = propagate_subpoint(iss, T0 + timedelta(minutes=30))
    # ~7.7 km/s ground speed → ~13800 km in 30 min → many degrees of motion
    assert (abs(p1["lon"] - p0["lon"]) + abs(p1["lat"] - p0["lat"])) > 5.0


def test_make_skyfield_satellite_produces_propagatable_object(fixture_sats):
    es = make_skyfield_satellite(fixture_sats[0])
    # Sanity: name and model attached
    assert es.name == fixture_sats[0]["name"]
    assert es.model.satnum == fixture_sats[0]["norad_id"]


def test_old_tle_logs_warning_but_still_returns_sat(caplog):
    """An old TLE epoch must not drop the sat — only warn."""
    far_future = datetime(2030, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    with caplog.at_level("WARNING", logger="raveneye.orbital.propagate"):
        sats = build_satellites_from_fixture(FIXTURE, by_id("blacksky"), far_future)
    assert len(sats) == 5
    assert any("SGP4 accuracy degrades" in r.message for r in caplog.records)


def test_safe_sat_id_handles_messy_names():
    assert _safe_sat_id("ISS (ZARYA)", 25544) == "ISS_ZARYA-25544"
    assert _safe_sat_id("BLACKSKY 14", 56216) == "BLACKSKY_14-56216"
    assert _safe_sat_id("", 99999) == "SAT-99999"


def test_epoch_iso_round_trip(fixture_sats):
    iss = next(s for s in fixture_sats if s["norad_id"] == 25544)
    epoch = datetime.fromisoformat(iss["tle_epoch_iso"])
    # Fixture TLE epoch is 24015.5 (2024-01-15 12:00 UTC)
    expected = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    assert abs((epoch - expected).total_seconds()) < 2.0
