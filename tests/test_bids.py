"""Bid derivation behavior."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from raveneye.sim import (
    DEFAULT_T0,
    Event,
    EventType,
    ObservableKind,
    STAKEHOLDERS,
    build_events,
    derive_bids,
    urgency_factor,
)


def _event(
    t_hours: float = 10.0,
    event_type: EventType = EventType.KINETIC_STRIKE,
    severity: int = 4,
    confidence: float = 0.9,
    ltiov: float = 8.0,
) -> Event:
    return Event(
        event_id="TST-000",
        t_iso="2026-04-13T22:00:00+00:00",
        t_hours=t_hours,
        event_type=event_type,
        location_id="strait_chokepoint",
        lat=26.567,
        lon=56.250,
        observable_kind=ObservableKind.WIDE_AREA,
        severity=severity,
        source_confidence=confidence,
        ltiov_hours=ltiov,
        narrative="Test event",
        phase="BLOCKADE_ACTIVE",
        scripted=True,
    )


def test_urgency_boundaries():
    assert urgency_factor(4.0) == 1.6
    assert urgency_factor(4.01) == 1.2
    assert urgency_factor(12.0) == 1.2
    assert urgency_factor(12.01) == 1.0
    assert urgency_factor(24.0) == 1.0
    assert urgency_factor(24.01) == 0.85
    assert urgency_factor(48.0) == 0.85
    assert urgency_factor(48.01) == 0.7


def test_one_bid_per_interested_stakeholder():
    ev = _event()
    bids = derive_bids([ev], DEFAULT_T0)
    expected = sum(
        1 for sh in STAKEHOLDERS if sh.weights.get(ev.event_type, 0) > 0
    )
    assert len(bids) == expected


def test_bids_share_target_and_sensor_for_same_event():
    ev = _event()
    bids = derive_bids([ev], DEFAULT_T0)
    assert len({(b.target_lat, b.target_lon) for b in bids}) == 1
    assert len({tuple(sorted(b.sensor_requirement.items())) for b in bids}) == 1


def test_priority_ordering_reflects_weight_when_other_factors_equal():
    ev = _event()
    bids = derive_bids([ev], DEFAULT_T0)
    # Sort by priority desc; expect CENTCOM_J2 (weight=2.0) first for KINETIC_STRIKE.
    bids.sort(key=lambda b: b.priority_score, reverse=True)
    assert bids[0].stakeholder_id == "CENTCOM_J2"


def test_ltiov_iso_math():
    ev = _event(t_hours=5.5, ltiov=8.0)
    bids = derive_bids([ev], DEFAULT_T0)
    expected = (DEFAULT_T0 + timedelta(hours=13.5)).isoformat()
    for b in bids:
        assert b.ltiov_iso == expected


def test_bid_count_matches_interested_total():
    events = build_events(seed=42)
    bids = derive_bids(events, DEFAULT_T0)
    # All 4 stakeholders have non-zero weights for every EventType, so
    # each event produces exactly len(STAKEHOLDERS) bids.
    assert len(bids) == len(events) * len(STAKEHOLDERS)
