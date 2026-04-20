"""RavenEye demand layer: events, bids, and scenario construction."""

from .bids import Bid, derive_bids, urgency_factor
from .build import DEFAULT_T0, build_events, build_sim
from .events import Event, EventType, ObservableKind
from .locations import LOCATIONS, SENSOR_REQUIREMENTS
from .phases import PHASES, Phase, phase_at
from .scripted import SCRIPTED_BEATS
from .stakeholders import STAKEHOLDERS, Stakeholder
from .stochastic import (
    BASE_RATES,
    DEFAULTS,
    PLAUSIBLE_LOCATIONS,
    jitter_location,
    poisson_sample,
    sample_stochastic_event,
)

__all__ = [
    "BASE_RATES",
    "Bid",
    "DEFAULTS",
    "DEFAULT_T0",
    "Event",
    "EventType",
    "LOCATIONS",
    "ObservableKind",
    "PHASES",
    "PLAUSIBLE_LOCATIONS",
    "Phase",
    "SCRIPTED_BEATS",
    "SENSOR_REQUIREMENTS",
    "STAKEHOLDERS",
    "Stakeholder",
    "build_events",
    "build_sim",
    "derive_bids",
    "jitter_location",
    "phase_at",
    "poisson_sample",
    "sample_stochastic_event",
    "urgency_factor",
]
