"""Stakeholder utility weights over event types.

Weights are on [0, 2]:
  0.0  → indifferent (will not bid on this event type)
  1.0  → standard interest
  2.0  → mission-critical
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .events import EventType


@dataclass(frozen=True)
class Stakeholder:
    stakeholder_id: str
    display_name: str
    mission: str
    weights: Dict[EventType, float]

    def weight(self, event_type: EventType) -> float:
        return self.weights.get(event_type, 0.0)


STAKEHOLDERS: List[Stakeholder] = [
    Stakeholder(
        stakeholder_id="CENTCOM_J2",
        display_name="CENTCOM J2",
        mission="Force protection and indications & warning.",
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
        display_name="NRO CSPO",
        mission="Commercial space collection utilization.",
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
        display_name="Allied Maritime HQ (UK/FR)",
        mission="Merchant protection, freedom of navigation.",
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
        display_name="Commercial War-Risk Insurer",
        mission="War-risk premium pricing and exposure management.",
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
