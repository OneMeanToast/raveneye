"""Scenario phase timeline.

A phase carries a rate multiplier applied to base stochastic rates during the
phase window. Phases are half-open: [start_hours, next_phase_start_hours).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Phase:
    name: str
    start_hours: float
    rate_multiplier: float


PHASES: List[Phase] = [
    Phase("BLOCKADE_ACTIVE", 0.0, 1.0),
    Phase("ESCALATION", 36.0, 2.2),
    Phase("CEASEFIRE_ANNOUNCED", 72.0, 0.4),
    Phase("CEASEFIRE_COLLAPSE", 96.0, 2.8),
    Phase("BLOCKADE_REINFORCED", 132.0, 1.6),
]


def phase_at(t_hours: float) -> Phase:
    """Return the active Phase at t_hours. Before-start resolves to the first
    phase; after all starts, the last phase."""
    if t_hours < PHASES[0].start_hours:
        return PHASES[0]
    active = PHASES[0]
    for p in PHASES:
        if t_hours >= p.start_hours:
            active = p
        else:
            break
    return active
