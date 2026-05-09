"""Tests for the multi-constellation offline TLE fixture path."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from raveneye.orbital import (
    CONSTELLATIONS,
    build_satellites_from_fixture_dir,
)
from raveneye.scenario import build_full_scenario_offline


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "multi_tles"
T0 = datetime(2026, 4, 13, 12, 0, 0, tzinfo=timezone.utc)


def test_fixture_dir_loads_all_six_vendors():
    sats = build_satellites_from_fixture_dir(FIXTURE_DIR, list(CONSTELLATIONS), T0)
    cons = {s["constellation_id"] for s in sats}
    assert cons == {"blacksky", "skysat", "planet_dove", "capella", "iceye", "maxar_wv"}
    # We ship 36 sats across the six vendors at the time of writing.
    # If you regen the fixture, update the bound; the assert is a guardrail
    # against silently dropping a constellation file.
    assert len(sats) >= 30
    assert len(sats) <= 60


def test_fixture_dir_sats_are_sorted_for_determinism():
    sats = build_satellites_from_fixture_dir(FIXTURE_DIR, list(CONSTELLATIONS), T0)
    keys = [(s["constellation_id"], s["norad_id"]) for s in sats]
    assert keys == sorted(keys)


def test_fixture_dir_skips_missing_files(tmp_path):
    # No files in tmp_path → all constellations skipped, returns []
    sats = build_satellites_from_fixture_dir(tmp_path, list(CONSTELLATIONS), T0)
    assert sats == []


def test_each_vendor_has_correct_metadata_attached():
    sats = build_satellites_from_fixture_dir(FIXTURE_DIR, list(CONSTELLATIONS), T0)
    by_con = {}
    for s in sats:
        by_con.setdefault(s["constellation_id"], []).append(s)

    # BlackSky sats should carry BlackSky's published-spec sensor params
    bs = by_con["blacksky"][0]
    assert bs["vendor"] == "BlackSky"
    assert bs["sensor_class"] == "EO_HIGHRES"
    assert bs["nominal_gsd_m"] == pytest.approx(1.0, abs=0.01)
    assert "PAN" in bs["spectral_bands"]

    # ICEYE sats should carry SAR sensor class
    ic = by_con["iceye"][0]
    assert ic["sensor_class"] == "SAR"
    assert ic["spectral_bands"] == ["SAR_X"]


def test_full_scenario_with_fixture_dir_uses_all_constellations():
    sats = build_satellites_from_fixture_dir(FIXTURE_DIR, list(CONSTELLATIONS), T0)
    scenario = build_full_scenario_offline(
        sats,
        seed=42,
        duration_hours=24.0,
        mechanism="greedy",
        constellations=list(CONSTELLATIONS),
        t0=T0,
    )
    # Every constellation we shipped a fixture for should appear in the
    # constellations list of the unified scenario JSON.
    con_ids_in_scenario = {c["constellation_id"] for c in scenario["constellations"]}
    assert con_ids_in_scenario == {c.constellation_id for c in CONSTELLATIONS}

    # With ~30 sats × 15 Hormuz targets × 24h, we should get many hundreds
    # of access windows — far more than the 5-sat fixture ever produced.
    assert scenario["meta"]["n_access_windows"] >= 200
    # Allocations: one per bid (should match n_bids exactly)
    assert scenario["meta"]["n_allocations"] == scenario["meta"]["n_bids"]


def test_subset_of_constellations_loads_only_those():
    """Asking for only blacksky + iceye should pull just those files."""
    from raveneye.orbital import by_id
    selected = [by_id("blacksky"), by_id("iceye")]
    sats = build_satellites_from_fixture_dir(FIXTURE_DIR, selected, T0)
    cons = {s["constellation_id"] for s in sats}
    assert cons == {"blacksky", "iceye"}
