"""Bid derivation: event × stakeholder → weighted tasking request."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List

from .events import Event
from .locations import SENSOR_REQUIREMENTS
from .stakeholders import STAKEHOLDERS, Stakeholder


@dataclass
class Bid:
    bid_id: str
    event_id: str
    stakeholder_id: str
    t_submitted_iso: str
    ltiov_iso: str
    target_lat: float
    target_lon: float
    target_location_id: str
    observable_kind: str
    sensor_requirement: Dict[str, Any]
    priority_score: float
    severity: int
    source_confidence: float
    stakeholder_weight: float
    urgency_factor: float
    rationale: str
    payload: Dict[str, Any] = field(default_factory=dict)


def urgency_factor(ltiov_hours: float) -> float:
    """Step function mapping LTIOV → urgency multiplier."""
    if ltiov_hours <= 4.0:
        return 1.6
    if ltiov_hours <= 12.0:
        return 1.2
    if ltiov_hours <= 24.0:
        return 1.0
    if ltiov_hours <= 48.0:
        return 0.85
    return 0.7


def derive_bids(
    events: Iterable[Event],
    t0: datetime,
    stakeholders: List[Stakeholder] = STAKEHOLDERS,
) -> List[Bid]:
    """Produce one Bid per (event, interested stakeholder) pair.

    A stakeholder is "interested" iff its weight for the event type is > 0.
    Priority = severity × confidence × weight × urgency_factor (rounded 3dp).
    Bid IDs are assigned deterministically: BID-00000, BID-00001, ... in the
    order (event order, stakeholder order).
    """
    bids: List[Bid] = []
    counter = 0
    for ev in events:
        sensor_req = SENSOR_REQUIREMENTS.get(ev.observable_kind, {})
        t_submitted_iso = (t0 + timedelta(hours=ev.t_hours)).isoformat()
        ltiov_iso = (t0 + timedelta(hours=ev.t_hours + ev.ltiov_hours)).isoformat()
        urg = urgency_factor(ev.ltiov_hours)
        for sh in stakeholders:
            w = sh.weight(ev.event_type)
            if w <= 0.0:
                continue
            raw = ev.severity * ev.source_confidence * w * urg
            priority = round(raw, 3)
            rationale = (
                f"{sh.display_name} weights {ev.event_type.value} at {w:.2f}; "
                f"severity {ev.severity}, confidence {ev.source_confidence:.2f}, "
                f"LTIOV {ev.ltiov_hours:.1f}h → urgency {urg:.2f}."
            )
            bids.append(
                Bid(
                    bid_id=f"BID-{counter:05d}",
                    event_id=ev.event_id,
                    stakeholder_id=sh.stakeholder_id,
                    t_submitted_iso=t_submitted_iso,
                    ltiov_iso=ltiov_iso,
                    target_lat=ev.lat,
                    target_lon=ev.lon,
                    target_location_id=ev.location_id,
                    observable_kind=ev.observable_kind.value,
                    sensor_requirement=dict(sensor_req),
                    priority_score=priority,
                    severity=ev.severity,
                    source_confidence=ev.source_confidence,
                    stakeholder_weight=w,
                    urgency_factor=urg,
                    rationale=rationale,
                    payload=dict(ev.payload),
                )
            )
            counter += 1
    return bids
