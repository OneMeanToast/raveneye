"""Event taxonomy for the RavenEye demand layer.

An Event is a world-state change observed (or reported) in the scenario. It is
NOT a bid — stakeholders turn events into bids through their utility weights.
See docs/event_taxonomy.md for doctrinal analogs per type.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict


class EventType(str, Enum):
    KINETIC_STRIKE = "KINETIC_STRIKE"
    """Munition impact (or credible report thereof). Doctrinal analog:
    FM 3-60 targeting, BDA trigger."""

    MINE_LAYING_REPORT = "MINE_LAYING_REPORT"
    """Mine emplacement activity. Doctrinal analog: MCM tasking priority
    per JP 3-15; immediate area-denial threat."""

    NAVAL_POSTURE_CHANGE = "NAVAL_POSTURE_CHANGE"
    """Change in surface-combatant disposition, tempo, or readiness state.
    Doctrinal analog: FM 34-2 indicators-and-warning tripwire."""

    MOVEMENT_DETECTED = "MOVEMENT_DETECTED"
    """Unexpected ground or sea movement consistent with adversary TTP.
    Doctrinal analog: ATP 2-01 pattern activity / I&W."""

    VESSEL_DARK = "VESSEL_DARK"
    """AIS blackout by a vessel of interest. Doctrinal analog: anomaly
    cueing for maritime pattern-of-life analysis."""

    BLOCKADE_RUNNER = "BLOCKADE_RUNNER"
    """Specific vessel attempting to run a declared interdiction zone.
    Doctrinal analog: maritime interdiction operations (MIO) cue."""

    HUMINT_REPORT = "HUMINT_REPORT"
    """Human-source-derived report. Doctrinal analog: ATP 2-22.3, low-to-
    moderate confidence; corroboration required."""

    SIGINT_CUE = "SIGINT_CUE"
    """Emitter activity or C2 pattern consistent with tasking-worthy events.
    Doctrinal analog: ATP 2-22.5 / SIGINT triggers."""

    WEATHER_DEGRADATION = "WEATHER_DEGRADATION"
    """Forecast window where EO collection is degraded. Doctrinal analog:
    weather effects on operations (ATP 2-01.3 step 4)."""

    DIPLOMATIC_STATUS_CHANGE = "DIPLOMATIC_STATUS_CHANGE"
    """Declared policy change altering collection priorities (ceasefire,
    blockade declaration, etc.). Doctrinal analog: CCIRs shift."""

    FACILITY_ANOMALY = "FACILITY_ANOMALY"
    """Observed deviation at a fixed site (thermal, flaring, vehicle counts,
    construction). Doctrinal analog: pattern-of-life anomaly cueing."""


class ObservableKind(str, Enum):
    VESSEL = "VESSEL"
    PORT_FACILITY = "PORT_FACILITY"
    REFINERY = "REFINERY"
    MILITARY_BASE = "MILITARY_BASE"
    ROUTE_SEGMENT = "ROUTE_SEGMENT"
    WIDE_AREA = "WIDE_AREA"
    AIRFIELD = "AIRFIELD"


@dataclass
class Event:
    event_id: str
    t_iso: str
    t_hours: float
    event_type: EventType
    location_id: str
    lat: float
    lon: float
    observable_kind: ObservableKind
    severity: int
    source_confidence: float
    ltiov_hours: float
    narrative: str
    phase: str
    scripted: bool
    payload: Dict[str, Any] = field(default_factory=dict)
