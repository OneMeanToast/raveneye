"""v0.1 bid derivation tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from raveneye.sim import (
    DEFAULT_T0,
    STAKEHOLDERS,
    Event,
    EventType,
    ObservableKind,
    Stakeholder,
    derive_bids,
    urgency_factor,
)


def _mk_event(**overrides) -> Event:
    base = dict(
        event_id="SCR-000",
        t_iso="2026-04-13T14:00:00+00:00",
        t_hours=2.0,
        event_type=EventType.KINETIC_STRIKE,
        location_id="strait_chokepoint",
        lat=26.567,
        lon=56.250,
        observable_kind=ObservableKind.WIDE_AREA,
        severity=4,
        source_confidence=0.9,
        ltiov_hours=6.0,
        narrative="test",
        phase="BLOCKADE_ACTIVE",
        scripted=True,
        payload={},
    )
    base.update(overrides)
    return Event(**base)


def test_bid_count_matches_interested_stakeholders():
    ev = _mk_event()
    bids = derive_bids([ev], t0=DEFAULT_T0)
    interested = [sh for sh in STAKEHOLDERS if sh.weight(ev.event_type) > 0.0]
    assert len(bids) == len(interested)


def test_same_event_bids_share_target_and_sensor():
    ev = _mk_event()
    bids = derive_bids([ev], t0=DEFAULT_T0)
    lats = {b.target_lat for b in bids}
    lons = {b.target_lon for b in bids}
    sensors = {tuple(sorted(b.sensor_requirement.items())) for b in bids}
    assert len(lats) == 1
    assert len(lons) == 1
    assert len(sensors) == 1


def test_priority_orders_with_weights_when_other_factors_equal():
    ev = _mk_event(event_type=EventType.KINETIC_STRIKE, ltiov_hours=6.0)
    bids = derive_bids([ev], t0=DEFAULT_T0)
    by_sh = {b.stakeholder_id: b for b in bids}
    # KINETIC_STRIKE: CENTCOM 2.0 > ALLIED 1.8 > COMMERCIAL 1.7 > NRO 1.6
    order = sorted(by_sh.values(), key=lambda b: b.priority_score, reverse=True)
    ids = [b.stakeholder_id for b in order]
    assert ids == ["CENTCOM_J2", "ALLIED_PARTNER", "COMMERCIAL_INSURER", "NRO_CSPO"]


def test_urgency_factor_boundaries():
    assert urgency_factor(4.0) == 1.6
    assert urgency_factor(4.0001) == 1.2
    assert urgency_factor(12.0) == 1.2
    assert urgency_factor(12.0001) == 1.0
    assert urgency_factor(24.0) == 1.0
    assert urgency_factor(24.0001) == 0.85
    assert urgency_factor(48.0) == 0.85
    assert urgency_factor(48.0001) == 0.7


def test_ltiov_iso_math():
    t0 = datetime(2026, 4, 13, 12, 0, 0, tzinfo=timezone.utc)
    ev = _mk_event(t_hours=2.0, ltiov_hours=6.0)
    bids = derive_bids([ev], t0=t0)
    expected = (t0 + timedelta(hours=8.0)).isoformat()
    for b in bids:
        assert b.ltiov_iso == expected


def test_zero_weight_stakeholder_produces_no_bid():
    # Construct a stakeholder with zero interest in KINETIC_STRIKE.
    zero_sh = Stakeholder(
        stakeholder_id="ZERO",
        display_name="Zero",
        mission="none",
        weights={EventType.VESSEL_DARK: 1.0},
    )
    ev = _mk_event(event_type=EventType.KINETIC_STRIKE)
    bids = derive_bids([ev], t0=DEFAULT_T0, stakeholders=[zero_sh])
    assert bids == []


def test_bid_ids_sequential():
    ev1 = _mk_event(event_id="SCR-000")
    ev2 = _mk_event(event_id="SCR-001", t_hours=3.0)
    bids = derive_bids([ev1, ev2], t0=DEFAULT_T0)
    ids = [b.bid_id for b in bids]
    assert ids == [f"BID-{i:05d}" for i in range(len(ids))]
