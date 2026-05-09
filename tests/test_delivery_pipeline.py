"""Tests for raveneye.delivery.pipeline."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from raveneye.delivery import (
    apply_delivery_pipeline,
    delivery_rate,
    lifecycle_state_at,
    processing_success_rate_observed,
)
from raveneye.mechanism import Allocation
from raveneye.orbital import (
    CONSTELLATIONS,
    by_id,
    build_satellites_from_fixture,
)
from raveneye.scenario import build_full_scenario_offline


FIXTURE = Path(__file__).parent / "fixtures" / "tles.txt"
T0 = datetime(2026, 4, 13, 12, 0, 0, tzinfo=timezone.utc)


# ---------- unit tests on apply_delivery_pipeline ----------

def _bid(bid_id, ltiov_iso):
    return {"bid_id": bid_id, "ltiov_iso": ltiov_iso}


def _window(window_id, sat_id, end_iso, q=0.8):
    return {
        "window_id": window_id, "sat_id": sat_id,
        "start_iso": "2026-04-13T12:00:00+00:00",
        "end_iso": end_iso,
        "quality_score": q,
        "target_id": "siri_island",
    }


def _sat(sat_id, constellation_id="iceye"):
    return {"sat_id": sat_id, "constellation_id": constellation_id}


def _make_alloc(allocation_id, bid_id, window_id, sat_id, status="SCHEDULED",
                quality=0.8, welfare=5.0):
    return Allocation(
        allocation_id=allocation_id,
        bid_id=bid_id,
        window_id=window_id,
        mechanism="ssi",
        status=status,
        priority_score=5.0,
        decision_t_iso="2026-04-13T12:00:00+00:00",
        notes="",
        sat_id=sat_id,
        quality_score=quality,
        welfare=welfare,
    )


def test_dropped_allocation_lifecycle_is_dropped():
    a = _make_alloc("ALLOC-00000", "BID-00000", None, None, status="DROPPED",
                    welfare=None, quality=None)
    out = apply_delivery_pipeline(
        [a], bids=[_bid("BID-00000", "2026-04-13T20:00:00+00:00")],
        access_windows=[], satellites=[], constellations=CONSTELLATIONS,
    )
    lc = out[0]["lifecycle"]
    assert lc["final_status"] == "DROPPED"
    assert lc["delivered"] is False
    assert lc["collected_iso"] is None


def test_scheduled_allocation_with_room_to_deliver_succeeds_or_fails_deterministically():
    """Same seed, same inputs → same final_status."""
    a = _make_alloc("ALLOC-00001", "BID-00001", "AW-0", "ICEYE-X-1-43800")
    bid = _bid("BID-00001", "2026-04-13T20:00:00+00:00")
    win = _window("AW-0", "ICEYE-X-1-43800", "2026-04-13T13:00:00+00:00", q=0.8)
    sat = _sat("ICEYE-X-1-43800", "iceye")

    a_out = apply_delivery_pipeline([a], [bid], [win], [sat], CONSTELLATIONS, seed=42)
    b_out = apply_delivery_pipeline([a], [bid], [win], [sat], CONSTELLATIONS, seed=42)
    assert a_out[0]["lifecycle"] == b_out[0]["lifecycle"]
    # ICEYE has 92% base success, modulated by q=0.8 → ~83% effective.
    assert a_out[0]["lifecycle"]["final_status"] in {"DELIVERED", "PROCESSING_FAILED"}


def test_deadline_missed_when_delivery_iso_exceeds_ltiov():
    """A short LTIOV that lands before the window even ends should
    register as DEADLINE_MISSED if processing succeeds."""
    a = _make_alloc("ALLOC-00010", "BID-00010", "AW-X", "MAXAR-1", quality=0.95)
    # Maxar has 180min processing + 60min delivery = 240min after window end.
    # So if LTIOV is only 30 min after window end, delivery is guaranteed to miss.
    bid = _bid("BID-00010", "2026-04-13T13:30:00+00:00")
    win = _window("AW-X", "MAXAR-1", "2026-04-13T13:00:00+00:00", q=0.95)
    sat = _sat("MAXAR-1", "maxar_wv")
    out = apply_delivery_pipeline([a], [bid], [win], [sat], CONSTELLATIONS, seed=42)
    lc = out[0]["lifecycle"]
    # Either processing failed (rare with q=0.95 × 0.88 ≈ 0.84 effective)
    # or it succeeded and missed the deadline. Both branches must report
    # delivered=False because the deadline was missed.
    assert lc["final_status"] in {"DEADLINE_MISSED", "PROCESSING_FAILED"}
    assert lc["delivered"] is False


def test_lifecycle_state_at_walks_states_in_order():
    """At t < window.start the state is PENDING; at t > delivered_iso it's
    the final terminal status. The transitions in between must be in order."""
    bid = _bid("B", "2026-04-13T22:00:00+00:00")
    win = _window("AW-Z", "BLACKSKY-1", "2026-04-13T13:00:00+00:00", q=0.8)
    sat = _sat("BLACKSKY-1", "blacksky")
    a = _make_alloc("ALLOC-Z", "B", "AW-Z", "BLACKSKY-1")
    out = apply_delivery_pipeline([a], [bid], [win], [sat], CONSTELLATIONS, seed=42)
    a_dict = out[0]
    # Before window start
    assert lifecycle_state_at(a_dict, win, "2026-04-13T11:00:00+00:00") == "PENDING"
    # Mid-window
    assert lifecycle_state_at(a_dict, win, "2026-04-13T12:30:00+00:00") == "COLLECTING"
    # Right after window end (collection done, processing in progress)
    assert lifecycle_state_at(a_dict, win, "2026-04-13T13:01:00+00:00") == "PROCESSING"


def test_aggregate_metrics_make_sense_on_realistic_scenario():
    sats = build_satellites_from_fixture(FIXTURE, by_id("blacksky"), T0)
    scenario = build_full_scenario_offline(
        sats,
        seed=42,
        duration_hours=24.0,
        mechanism="greedy",
        constellations=[by_id("blacksky")],
    )
    m = scenario["meta"]

    assert m["n_allocations"] == m["n_bids"]
    assert (m["n_dropped"] + m["n_delivered"]
            + m["n_processing_failed"] + m["n_deadline_missed"]) == m["n_allocations"]
    assert 0.0 <= m["delivery_rate"] <= 1.0
    # processing_success_rate is computed over collected (non-dropped) allocations
    assert 0.0 <= m["processing_success_rate"] <= 1.0


def test_each_allocation_carries_lifecycle_field():
    sats = build_satellites_from_fixture(FIXTURE, by_id("blacksky"), T0)
    scenario = build_full_scenario_offline(
        sats, seed=42, duration_hours=24.0,
        constellations=[by_id("blacksky")],
    )
    for a in scenario["allocations"]:
        assert "lifecycle" in a
        assert "final_status" in a["lifecycle"]


def test_metric_helpers_match_meta_aggregates():
    sats = build_satellites_from_fixture(FIXTURE, by_id("blacksky"), T0)
    scenario = build_full_scenario_offline(
        sats, seed=42, duration_hours=24.0, mechanism="ssi",
        constellations=[by_id("blacksky")],
    )
    assert delivery_rate(scenario["allocations"]) == scenario["meta"]["delivery_rate"]
    assert processing_success_rate_observed(scenario["allocations"]) == scenario["meta"]["processing_success_rate"]


def test_ssi_delivery_rate_meets_or_beats_greedy():
    """SSI routes higher-priority bids to higher-quality windows, which
    plug straight into the per-allocation effective_success_rate. That
    means SSI's delivery rate must equal-or-beat greedy's on any
    scenario where the two mechanisms differ."""
    sats = build_satellites_from_fixture(FIXTURE, by_id("blacksky"), T0)
    g = build_full_scenario_offline(sats, seed=42, duration_hours=72.0,
                                    mechanism="greedy",
                                    constellations=[by_id("blacksky")])
    s = build_full_scenario_offline(sats, seed=42, duration_hours=72.0,
                                    mechanism="ssi",
                                    constellations=[by_id("blacksky")])
    assert s["meta"]["delivery_rate"] >= g["meta"]["delivery_rate"] - 0.01, (
        f"SSI delivery rate {s['meta']['delivery_rate']} should "
        f"meet-or-beat greedy {g['meta']['delivery_rate']}"
    )
