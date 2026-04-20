"""Bid derivation: events × stakeholders → weighted requests.

A bid is one stakeholder's expression of interest in one event, scored by
their utility weights and the event's urgency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List

from .events import Event
from .locations import SENSOR_REQUIREMENTS
from .stakeholders import STAKEHOLDERS, Stakeholder


@dataclass
class Bid:
    bid_id: str
    event_id: str
    stakeholder_id: str
    priority_score: float
    urgency_multiplier: float
    severity: int
    source_confidence: float
    weight: float
    target_lat: float
    target_lon: float
    location_id: str
    observable_kind: str
    sensor_requirement: Dict[str, Any]
    ltiov_iso: str
    ltiov_hours: float
    created_t_iso: str
    phase: str
    narrative_excerpt: str
    payload: Dict[str, Any] = field(default_factory=dict)


def urgency_factor(ltiov_hours: float) -> float:
    """Step function scaling priority by time pressure."""
    if ltiov_hours <= 4.0:
        return 1.6
    if ltiov_hours <= 12.0:
        return 1.2
    if ltiov_hours <= 24.0:
        return 1.0
    if ltiov_hours <= 48.0:
        return 0.85
    return 0.7


def _excerpt(narrative: str, max_len: int = 120) -> str:
    if len(narrative) <= max_len:
        return narrative
    return narrative[: max_len - 1].rstrip() + "\u2026"


def derive_bids(
    events: List[Event],
    t0: datetime,
    stakeholders: List[Stakeholder] = STAKEHOLDERS,
) -> List[Bid]:
    """Produce one bid per (event, interested stakeholder) pair.

    A stakeholder is "interested" iff their weight for the event type is > 0.
    Priority = severity × confidence × weight × urgency_factor(ltiov_hours),
    rounded to 3 decimal places.
    """
    bids: List[Bid] = []
    counter = 0
    for ev in events:
        urgency = urgency_factor(ev.ltiov_hours)
        ltiov_at = t0 + timedelta(hours=ev.t_hours + ev.ltiov_hours)
        created_at = t0 + timedelta(hours=ev.t_hours)
        sensor_req = SENSOR_REQUIREMENTS[ev.observable_kind]
        for sh in stakeholders:
            weight = sh.weights.get(ev.event_type, 0.0)
            if weight <= 0.0:
                continue
            priority = round(
                ev.severity * ev.source_confidence * weight * urgency, 3
            )
            bid = Bid(
                bid_id=f"BID-{counter:05d}",
                event_id=ev.event_id,
                stakeholder_id=sh.stakeholder_id,
                priority_score=priority,
                urgency_multiplier=urgency,
                severity=ev.severity,
                source_confidence=ev.source_confidence,
                weight=weight,
                target_lat=ev.lat,
                target_lon=ev.lon,
                location_id=ev.location_id,
                observable_kind=ev.observable_kind.value,
                sensor_requirement=dict(sensor_req),
                ltiov_iso=ltiov_at.isoformat(),
                ltiov_hours=ev.ltiov_hours,
                created_t_iso=created_at.isoformat(),
                phase=ev.phase,
                narrative_excerpt=_excerpt(ev.narrative),
                payload=dict(ev.payload),
            )
            bids.append(bid)
            counter += 1
    return bids
