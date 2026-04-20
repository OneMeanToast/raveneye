"""Stakeholder utility functions.

Each stakeholder attaches a multiplicative weight in [0, 2] to each event
type: 0 = indifferent, 1 = standard interest, 2 = mission-critical. Different
utilities across the same events is exactly what bid derivation exposes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .events import EventType


@dataclass(frozen=True)
class Stakeholder:
    stakeholder_id: str
    name: str
    mandate: str
    weights: Dict[EventType, float]


STAKEHOLDERS: List[Stakeholder] = [
    Stakeholder(
        stakeholder_id="CENTCOM_J2",
        name="USCENTCOM J2",
        mandate="Force protection; indications and warning for allied forces in the AOR.",
        weights={
            EventType.KINETIC_STRIKE: 2.0,
            EventType.MINE_LAYING_REPORT: 2.0,
            EventType.NAVAL_POSTURE_CHANGE: 1.8,
            EventType.MOVEMENT_DETECTED: 1.5,
            EventType.BLOCKADE_RUNNER: 1.6,
            EventType.SIGINT_CUE: 1.3,
            EventType.DIPLOMATIC_STATUS_CHANGE: 1.4,
            EventType.HUMINT_REPORT: 0.9,
            EventType.FACILITY_ANOMALY: 0.8,
            EventType.VESSEL_DARK: 0.7,
            EventType.WEATHER_DEGRADATION: 0.5,
        },
    ),
    Stakeholder(
        stakeholder_id="NRO_CSPO",
        name="NRO Commercial Systems Program Office",
        mandate="Drive commercial EO utilization; satisfy national-requirement tasks.",
        weights={
            EventType.KINETIC_STRIKE: 1.6,
            EventType.MINE_LAYING_REPORT: 1.5,
            EventType.FACILITY_ANOMALY: 1.4,
            EventType.MOVEMENT_DETECTED: 1.3,
            EventType.BLOCKADE_RUNNER: 1.3,
            EventType.NAVAL_POSTURE_CHANGE: 1.2,
            EventType.VESSEL_DARK: 1.1,
            EventType.HUMINT_REPORT: 1.0,
            EventType.SIGINT_CUE: 1.0,
            EventType.DIPLOMATIC_STATUS_CHANGE: 0.9,
            EventType.WEATHER_DEGRADATION: 0.8,
        },
    ),
    Stakeholder(
        stakeholder_id="ALLIED_PARTNER",
        name="UK/FR Combined Maritime HQ",
        mandate="Merchant protection and freedom of navigation for allied-flag shipping.",
        weights={
            EventType.MINE_LAYING_REPORT: 1.9,
            EventType.KINETIC_STRIKE: 1.8,
            EventType.VESSEL_DARK: 1.5,
            EventType.DIPLOMATIC_STATUS_CHANGE: 1.3,
            EventType.NAVAL_POSTURE_CHANGE: 1.2,
            EventType.BLOCKADE_RUNNER: 1.2,
            EventType.MOVEMENT_DETECTED: 1.0,
            EventType.HUMINT_REPORT: 0.7,
            EventType.WEATHER_DEGRADATION: 0.6,
            EventType.SIGINT_CUE: 0.6,
            EventType.FACILITY_ANOMALY: 0.5,
        },
    ),
    Stakeholder(
        stakeholder_id="COMMERCIAL_INSURER",
        name="London Market War-Risk Syndicate",
        mandate="Real-time war-risk pricing and route-advisory support for underwriters.",
        weights={
            EventType.MINE_LAYING_REPORT: 1.8,
            EventType.KINETIC_STRIKE: 1.7,
            EventType.DIPLOMATIC_STATUS_CHANGE: 1.6,
            EventType.BLOCKADE_RUNNER: 1.5,
            EventType.VESSEL_DARK: 1.4,
            EventType.FACILITY_ANOMALY: 1.2,
            EventType.WEATHER_DEGRADATION: 1.0,
            EventType.NAVAL_POSTURE_CHANGE: 0.8,
            EventType.MOVEMENT_DETECTED: 0.6,
            EventType.HUMINT_REPORT: 0.4,
            EventType.SIGINT_CUE: 0.2,
        },
    ),
]
