"""K4: greedy priority mechanism tests with a handcrafted fixture.

3 bids × 5 windows. The fixture is sized so the expected greedy
allocation can be reasoned about by hand in ~5 minutes.
"""
from __future__ import annotations

import pytest

from raveneye.mechanism import (
    Allocation,
    GreedyPriorityMechanism,
    allocate,
    drop_rate,
    match_bid_to_window,
    total_welfare,
)


T0 = "2026-04-13T12:00:00+00:00"


def _bid(bid_id, target_id, priority, ltiov_iso, band="EO_PAN"):
    return {
        "bid_id": bid_id,
        "event_id": f"EV-{bid_id[-3:]}",
        "stakeholder_id": "TEST_STAKE",
        "stakeholder_weight": 1.0,
        "priority_score": priority,
        "urgency_factor": 1.0,
        "severity": 4,
        "source_confidence": 0.9,
        "t_submitted_iso": T0,
        "ltiov_iso": ltiov_iso,
        "target_location_id": target_id,
        "target_lat": 27.13,
        "target_lon": 56.22,
        "observable_kind": "MILITARY_BASE",
        "sensor_requirement": {"gsd_m": 0.5, "band": band, "revisit_h": 8},
        "rationale": "test",
        "payload": {},
    }


def _window(window_id, sat_id, target_id, start_iso, end_iso, quality, lat=27.13, lon=56.22):
    return {
        "window_id": window_id,
        "sat_id": sat_id,
        "target_id": target_id,
        "target_lat": lat,
        "target_lon": lon,
        "start_iso": start_iso,
        "end_iso": end_iso,
        "duration_s": 360.0,
        "max_elevation_deg": 60.0,
        "off_nadir_at_culminate_deg": 20.0,
        "sun_elevation_deg": 30.0,
        "quality_score": quality,
    }


def _sat(sat_id, bands=("PAN",)):
    return {
        "sat_id": sat_id,
        "spectral_bands": list(bands),
        "max_off_nadir_deg": 45.0,
    }


@pytest.fixture
def fixture_3b_5w():
    """The reusable test fixture for greedy and SSI tests.

    Bids:
      BID-0  priority 10.0  target=siri_island  deadline=15:00
      BID-1  priority  6.0  target=siri_island  deadline=14:30
      BID-2  priority  3.0  target=siri_island  deadline=15:00

    Windows (all over siri_island):
      AW-00  Sat-A  12:30→12:35  q=0.40
      AW-01  Sat-B  12:50→12:55  q=0.85   ← high quality, mid time
      AW-02  Sat-C  13:10→13:15  q=0.55
      AW-03  Sat-D  13:40→13:45  q=0.30
      AW-04  Sat-E  14:20→14:25  q=0.95   ← highest quality, latest

    Greedy will allocate by priority desc, picking the EARLIEST feasible
    window each time:
      BID-0 (10.0) → AW-00  (q=0.40, welfare=4.00)
      BID-1 ( 6.0) → AW-01  (q=0.85, welfare=5.10)
      BID-2 ( 3.0) → AW-02  (q=0.55, welfare=1.65)
      Total welfare = 10.75. No drops.
    """
    bids = [
        _bid("BID-00000", "siri_island", 10.0, "2026-04-13T15:00:00+00:00"),
        _bid("BID-00001", "siri_island",  6.0, "2026-04-13T14:30:00+00:00"),
        _bid("BID-00002", "siri_island",  3.0, "2026-04-13T15:00:00+00:00"),
    ]
    windows = [
        _window("AW-00000", "Sat-A", "siri_island", "2026-04-13T12:30:00+00:00", "2026-04-13T12:35:00+00:00", 0.40),
        _window("AW-00001", "Sat-B", "siri_island", "2026-04-13T12:50:00+00:00", "2026-04-13T12:55:00+00:00", 0.85),
        _window("AW-00002", "Sat-C", "siri_island", "2026-04-13T13:10:00+00:00", "2026-04-13T13:15:00+00:00", 0.55),
        _window("AW-00003", "Sat-D", "siri_island", "2026-04-13T13:40:00+00:00", "2026-04-13T13:45:00+00:00", 0.30),
        _window("AW-00004", "Sat-E", "siri_island", "2026-04-13T14:20:00+00:00", "2026-04-13T14:25:00+00:00", 0.95),
    ]
    sats = [_sat(f"Sat-{c}") for c in "ABCDE"]
    return bids, windows, sats


# ---------- match_bid_to_window ----------

def test_match_target_id_required(fixture_3b_5w):
    bids, windows, _ = fixture_3b_5w
    other_target = dict(windows[0])
    other_target["target_id"] = "ras_tanura"
    assert not match_bid_to_window(bids[0], other_target)


def test_match_deadline_enforced(fixture_3b_5w):
    bids, windows, _ = fixture_3b_5w
    # BID-1 deadline is 14:30; AW-04 ends 14:25 → fits
    assert match_bid_to_window(bids[1], windows[4])
    # Build a window ending after the deadline
    past = dict(windows[4])
    past["end_iso"] = "2026-04-13T14:35:00+00:00"
    assert not match_bid_to_window(bids[1], past)


def test_match_band_compatibility():
    eo_bid = _bid("X", "siri_island", 5.0, "2026-04-13T20:00:00+00:00", band="EO_PAN")
    sar_bid = _bid("Y", "siri_island", 5.0, "2026-04-13T20:00:00+00:00", band="SAR_X")
    w = _window("W1", "Sat-A", "siri_island", "2026-04-13T13:00:00+00:00", "2026-04-13T13:05:00+00:00", 0.5)
    assert match_bid_to_window(eo_bid, w, sat_bands=["PAN"])
    assert not match_bid_to_window(sar_bid, w, sat_bands=["PAN"])
    assert match_bid_to_window(sar_bid, w, sat_bands=["SAR_X"])


# ---------- greedy core ----------

def test_greedy_allocates_three_bids_to_earliest_feasible_windows(fixture_3b_5w):
    bids, windows, sats = fixture_3b_5w
    allocs = allocate(bids, windows, T0, mechanism="greedy", satellites=sats)
    assert len(allocs) == 3
    by_bid = {a.bid_id: a for a in allocs}
    assert by_bid["BID-00000"].window_id == "AW-00000"
    assert by_bid["BID-00001"].window_id == "AW-00001"
    assert by_bid["BID-00002"].window_id == "AW-00002"
    assert all(a.status == "SCHEDULED" for a in allocs)


def test_greedy_emits_allocation_per_bid(fixture_3b_5w):
    bids, windows, sats = fixture_3b_5w
    allocs = allocate(bids, windows, T0, "greedy", satellites=sats)
    # Same number of allocations as bids
    assert {a.bid_id for a in allocs} == {b["bid_id"] for b in bids}


def test_greedy_drops_bid_when_no_window_matches():
    bids = [
        _bid("BID-00000", "siri_island", 10.0, "2026-04-13T13:00:00+00:00"),
        _bid("BID-00001", "ras_tanura",  5.0, "2026-04-13T13:00:00+00:00"),  # no window
    ]
    windows = [
        _window("AW-0", "Sat-A", "siri_island", "2026-04-13T12:30:00+00:00", "2026-04-13T12:35:00+00:00", 0.5),
    ]
    sats = [_sat("Sat-A")]
    allocs = allocate(bids, windows, T0, "greedy", satellites=sats)
    by_bid = {a.bid_id: a for a in allocs}
    assert by_bid["BID-00000"].status == "SCHEDULED"
    assert by_bid["BID-00001"].status == "DROPPED"
    assert by_bid["BID-00001"].window_id is None
    assert drop_rate(allocs) == 0.5


def test_greedy_is_deterministic(fixture_3b_5w):
    bids, windows, sats = fixture_3b_5w
    a = allocate(bids, windows, T0, "greedy", satellites=sats)
    b = allocate(bids, windows, T0, "greedy", satellites=sats)
    assert [x.to_dict() for x in a] == [x.to_dict() for x in b]


def test_greedy_total_welfare_matches_handcalc(fixture_3b_5w):
    bids, windows, sats = fixture_3b_5w
    allocs = allocate(bids, windows, T0, "greedy", satellites=sats)
    # 10*0.40 + 6*0.85 + 3*0.55 = 4.00 + 5.10 + 1.65 = 10.75
    assert total_welfare(allocs) == pytest.approx(10.75, abs=1e-3)


def test_greedy_skips_taken_windows(fixture_3b_5w):
    """If two bids both want the earliest window, only one gets it."""
    bids, _, sats = fixture_3b_5w
    # Force only one window
    only_window = [_window("AW-0", "Sat-A", "siri_island",
                           "2026-04-13T12:30:00+00:00",
                           "2026-04-13T12:35:00+00:00", 0.5)]
    allocs = allocate(bids, only_window, T0, "greedy", satellites=sats)
    statuses = {a.bid_id: a.status for a in allocs}
    n_scheduled = sum(1 for s in statuses.values() if s == "SCHEDULED")
    assert n_scheduled == 1
    assert sum(1 for s in statuses.values() if s == "DROPPED") == 2


def test_greedy_unknown_mechanism_name_raises():
    with pytest.raises(ValueError):
        allocate([], [], T0, mechanism="not_real")


def test_allocation_dict_round_trip(fixture_3b_5w):
    bids, windows, sats = fixture_3b_5w
    allocs = allocate(bids, windows, T0, "greedy", satellites=sats)
    d = allocs[0].to_dict()
    assert {"allocation_id", "bid_id", "window_id", "mechanism",
            "status", "priority_score", "decision_t_iso"}.issubset(d.keys())
