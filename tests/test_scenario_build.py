"""Integration tests for the v0.2 unified scenario builder.

Uses the offline path so no network is required.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from raveneye.orbital import build_satellites_from_fixture, by_id
from raveneye.scenario import build_full_scenario_offline


FIXTURE = Path(__file__).parent / "fixtures" / "tles.txt"


@pytest.fixture(scope="module")
def fixture_sats():
    return build_satellites_from_fixture(FIXTURE, by_id("blacksky"), datetime(2026, 4, 13, 12, 0, 0, tzinfo=timezone.utc))


def test_build_full_scenario_offline_returns_unified_shape(fixture_sats):
    """A v0.2 scenario JSON contains all v0.1 fields plus the new ones."""
    scenario = build_full_scenario_offline(
        fixture_sats,
        seed=42,
        duration_hours=24.0,        # short run keeps the test fast
        mechanism="greedy",
        constellations=[by_id("blacksky")],
    )
    expected_top = {
        "meta", "locations", "stakeholders", "sensor_requirements",
        "constellations", "satellites", "events", "bids",
        "access_windows", "allocations",
    }
    assert expected_top.issubset(scenario.keys())


def test_meta_aggregates_per_layer(fixture_sats):
    scenario = build_full_scenario_offline(
        fixture_sats, seed=42, duration_hours=24.0, mechanism="greedy",
    )
    m = scenario["meta"]
    assert m["seed"] == 42
    assert m["mechanism"] == "greedy"
    assert m["duration_hours"] == 24.0
    assert m["n_events"] == len(scenario["events"])
    assert m["n_bids"] == len(scenario["bids"])
    assert m["n_satellites"] == len(scenario["satellites"]) == 5
    assert m["n_access_windows"] == len(scenario["access_windows"])
    assert m["n_allocations"] == len(scenario["allocations"]) == m["n_bids"]
    assert m["n_scheduled"] + m["n_dropped"] == m["n_allocations"]
    assert 0.0 <= m["drop_rate"] <= 1.0


def test_allocations_join_back_to_bids_and_windows(fixture_sats):
    scenario = build_full_scenario_offline(
        fixture_sats, seed=42, duration_hours=24.0, mechanism="greedy",
    )
    bid_ids = {b["bid_id"] for b in scenario["bids"]}
    win_ids = {w["window_id"] for w in scenario["access_windows"]}
    for a in scenario["allocations"]:
        assert a["bid_id"] in bid_ids, f"allocation {a['allocation_id']} refs unknown bid"
        if a["window_id"] is not None:
            assert a["window_id"] in win_ids, (
                f"allocation {a['allocation_id']} refs unknown window {a['window_id']}"
            )
            assert a["status"] == "SCHEDULED"
        else:
            assert a["status"] == "DROPPED"


def test_ssi_meets_or_beats_greedy_welfare(fixture_sats):
    """The §5.4 invariant: SSI welfare ≥ greedy welfare on any scenario."""
    g = build_full_scenario_offline(
        fixture_sats, seed=42, duration_hours=24.0, mechanism="greedy",
    )
    s = build_full_scenario_offline(
        fixture_sats, seed=42, duration_hours=24.0, mechanism="ssi",
    )
    assert s["meta"]["total_welfare"] >= g["meta"]["total_welfare"]


def test_scenario_is_deterministic_under_same_seed(fixture_sats):
    a = build_full_scenario_offline(fixture_sats, seed=42, duration_hours=12.0)
    b = build_full_scenario_offline(fixture_sats, seed=42, duration_hours=12.0)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_different_mechanisms_produce_different_allocations(fixture_sats):
    """Same demand + supply, different mechanism → may differ.

    On a small scenario with light contention the two often agree; on the
    7-day fixture they should disagree on at least a handful of bids.
    """
    g = build_full_scenario_offline(
        fixture_sats, seed=42, duration_hours=72.0, mechanism="greedy",
    )
    s = build_full_scenario_offline(
        fixture_sats, seed=42, duration_hours=72.0, mechanism="ssi",
    )
    g_map = {a["bid_id"]: a["window_id"] for a in g["allocations"]}
    s_map = {a["bid_id"]: a["window_id"] for a in s["allocations"]}
    differing = sum(1 for k in g_map if g_map[k] != s_map.get(k))
    assert differing >= 1, "expected at least one allocation difference between greedy and SSI"


def test_phase_pass_through_from_demand_layer(fixture_sats):
    scenario = build_full_scenario_offline(
        fixture_sats, seed=42, duration_hours=24.0,
    )
    # phases come from the v0.1 demand layer
    assert len(scenario["meta"]["phases"]) == 5
    names = {p["name"] for p in scenario["meta"]["phases"]}
    assert "BLOCKADE_ACTIVE" in names and "ESCALATION" in names
