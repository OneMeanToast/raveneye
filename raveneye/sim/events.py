"""Event and observable taxonomy for the RavenEye demand layer.

Events are world-state changes with a time, place, and observable target.
They are stakeholder-agnostic; bids are derived from events in :mod:`bids`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict


class EventType(str, Enum):
    """Doctrinally-grounded event taxonomy for the Hormuz scenario."""

    KINETIC_STRIKE = "KINETIC_STRIKE"
    """Confirmed or suspected attack on a fixed or moving target; drives BDA requirements."""

    MINE_LAYING_REPORT = "MINE_LAYING_REPORT"
    """Suspected emplacement of sea mines in a navigable lane; time-critical for MCM planning."""

    NAVAL_POSTURE_CHANGE = "NAVAL_POSTURE_CHANGE"
    """Observed shift in naval force disposition (sortie, surge, dispersal, recall)."""

    MOVEMENT_DETECTED = "MOVEMENT_DETECTED"
    """Ground or vehicle movement of interest (convoys, launchers, force redistribution)."""

    VESSEL_DARK = "VESSEL_DARK"
    """AIS-off event on a tracked merchant or military vessel; sanctions/intent indicator."""

    BLOCKADE_RUNNER = "BLOCKADE_RUNNER"
    """Vessel assessed as attempting to circumvent a declared blockade (imminent or in progress)."""

    HUMINT_REPORT = "HUMINT_REPORT"
    """Tip from a human source; typically lower confidence, higher LTIOV."""

    SIGINT_CUE = "SIGINT_CUE"
    """Emitter-driven cue (pattern-of-life change, new waveform, DF fix) triggering collection."""

    WEATHER_DEGRADATION = "WEATHER_DEGRADATION"
    """Forecast or observed conditions impairing EO/IR collection viability."""

    DIPLOMATIC_STATUS_CHANGE = "DIPLOMATIC_STATUS_CHANGE"
    """Formal policy shift (declaration, recall, strait status) affecting targeting priorities."""

    FACILITY_ANOMALY = "FACILITY_ANOMALY"
    """Anomalous signature at a fixed site: thermal ramp, unplanned activity, unusual loading."""


class ObservableKind(str, Enum):
    """Physical class of the target being observed; drives sensor requirements."""

    VESSEL = "VESSEL"
    PORT_FACILITY = "PORT_FACILITY"
    REFINERY = "REFINERY"
    MILITARY_BASE = "MILITARY_BASE"
    ROUTE_SEGMENT = "ROUTE_SEGMENT"
    WIDE_AREA = "WIDE_AREA"
    AIRFIELD = "AIRFIELD"


@dataclass
class Event:
    """A world-state change observable by one or more stakeholders.

    Events are stakeholder-agnostic. Bids (in :mod:`raveneye.sim.bids`) are
    derived by applying each stakeholder's utility weights to an event.
    """

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
