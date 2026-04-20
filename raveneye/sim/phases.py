"""Scenario phase model: ordered narrative chunks with a demand multiplier."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Phase:
    name: str
    start_h: float
    demand_multiplier: float


PHASES: List[Phase] = [
    Phase("BLOCKADE_ACTIVE", 0.0, 1.0),
    Phase("ESCALATION", 36.0, 2.2),
    Phase("CEASEFIRE_ANNOUNCED", 72.0, 0.4),
    Phase("CEASEFIRE_COLLAPSE", 96.0, 2.8),
    Phase("BLOCKADE_REINFORCED", 132.0, 1.6),
]


def phase_at(t_hours: float) -> Phase:
    """Return the phase active at ``t_hours`` (half-open, clamps below/above)."""
    if t_hours < PHASES[0].start_h:
        return PHASES[0]
    active = PHASES[0]
    for p in PHASES:
        if t_hours >= p.start_h:
            active = p
        else:
            break
    return active
