"""Tests for raveneye.orbital.build (build_supply orchestrator)."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from raveneye.orbital import (
    CONSTELLATIONS,
    build_satellites_from_fixture,
    build_supply_from_satellites,
    by_id,
    targets_from_locations,
)
from raveneye.sim.locations import LOCATIONS


FIXTURE = Path(__file__).parent / "fixtures" / "tles.txt"
T0 = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def fixture_sats():
    return build_satellites_from_fixture(FIXTURE, by_id("blacksky"), T0)


def test_targets_from_locations_shape():
    targets = targets_from_locations(LOCATIONS)
    assert len(targets) == len(LOCATIONS)
    for t in targets:
        assert {"target_id", "lat", "lon"}.issubset(t.keys())
    # Round-trip a known location
    bandar = next(t for t in targets if t["target_id"] == "bandar_abbas_naval")
    assert bandar["lat"] == pytest.approx(27.129, abs=1e-3)
    assert bandar["lon"] == pytest.approx(56.217, abs=1e-3)


def test_build_supply_from_satellites_returns_full_shape(fixture_sats):
    targets = targets_from_locations(LOCATIONS)
    supply = build_supply_from_satellites(
        fixture_sats, targets, T0, duration_hours=24.0,
        constellations=[by_id("blacksky")],
    )
    assert set(supply.keys()) == {"satellites", "access_windows", "constellations", "meta"}
    assert supply["meta"]["n_satellites"] == 5
    assert supply["meta"]["t0_iso"] == T0.replace(microsecond=0).isoformat()
    assert supply["meta"]["duration_hours"] == 24.0
    assert supply["meta"]["seed"] == 42
    assert supply["meta"]["min_elevation_deg"] == 20.0


def test_build_supply_produces_real_windows_against_hormuz_targets(fixture_sats):
    """End-to-end: 5 fixture sats × 15 Hormuz targets × 24h.

    Two fixture sats are sun-sync (NOAA 19, Terra), Landsat 9 is also
    SSO-class, ISS is mid-inclination — so we should get a healthy
    handful of windows. GOES 16 (geostationary at -75° lon) sees nothing
    over the gulf at 20° elev. Bound the count to catch regressions.
    """
    targets = targets_from_locations(LOCATIONS)
    supply = build_supply_from_satellites(
        fixture_sats, targets, T0, duration_hours=24.0,
        constellations=[by_id("blacksky")],
    )
    n_aw = supply["meta"]["n_access_windows"]
    assert 30 <= n_aw <= 200, f"expected ~30-200 windows for fixture x Hormuz, got {n_aw}"
    # No windows should reference GOES 16 (NORAD 41866)
    sat_ids = {w["sat_id"] for w in supply["access_windows"]}
    assert all("41866" not in sid for sid in sat_ids)
    # Window IDs must be monotonic
    ids = [w["window_id"] for w in supply["access_windows"]]
    assert ids == [f"AW-{i:05d}" for i in range(len(ids))]


def test_build_supply_is_deterministic(fixture_sats):
    """Same inputs → byte-identical output (modulo dict-ordering, so we
    assert via a sorted JSON dump).
    """
    import json
    targets = targets_from_locations(LOCATIONS)
    a = build_supply_from_satellites(fixture_sats, targets, T0, 24.0)
    b = build_supply_from_satellites(fixture_sats, targets, T0, 24.0)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_constellations_table_round_trips_through_build_supply(fixture_sats):
    targets = targets_from_locations(LOCATIONS)
    supply = build_supply_from_satellites(
        fixture_sats, targets, T0, 24.0,
        constellations=CONSTELLATIONS,
    )
    assert len(supply["constellations"]) == 6
    ids = [c["constellation_id"] for c in supply["constellations"]]
    assert "blacksky" in ids and "iceye" in ids


def test_build_supply_handles_empty_inputs():
    out = build_supply_from_satellites([], [], T0, 24.0)
    assert out["satellites"] == []
    assert out["access_windows"] == []
    assert out["meta"]["n_satellites"] == 0
    assert out["meta"]["n_access_windows"] == 0


def test_build_supply_min_elevation_propagates(fixture_sats):
    targets = targets_from_locations(LOCATIONS)
    supply_low = build_supply_from_satellites(
        fixture_sats, targets, T0, 24.0, min_elevation_deg=10.0,
    )
    supply_high = build_supply_from_satellites(
        fixture_sats, targets, T0, 24.0, min_elevation_deg=60.0,
    )
    assert supply_low["meta"]["n_access_windows"] >= supply_high["meta"]["n_access_windows"]
    for w in supply_high["access_windows"]:
        assert w["max_elevation_deg"] >= 60.0
