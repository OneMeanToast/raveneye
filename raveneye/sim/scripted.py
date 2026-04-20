"""Scripted narrative beats for the Hormuz blockade scenario (April 2026).

These 20 beats are the narrative spine. Same every run, regardless of seed.
IDs are assigned by the builder in build.py as SCR-NNN. Stochastic injects
(STO-NNNN) weave around these beats.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .events import EventType, ObservableKind


SCRIPTED_BEATS: List[Dict[str, Any]] = [
    {
        "t_hours": 2.0,
        "event_type": EventType.DIPLOMATIC_STATUS_CHANGE,
        "location_id": "strait_chokepoint",
        "observable_kind": ObservableKind.WIDE_AREA,
        "severity": 4,
        "source_confidence": 0.99,
        "ltiov_hours": 24.0,
        "narrative": (
            "CENTCOM reaffirms blockade posture following overnight SECDEF "
            "call; strait declared closed to non-coalition traffic. PAO "
            "statement 0400Z."
        ),
        "payload": {"policy_action": "BLOCKADE_REAFFIRMED"},
    },
    {
        "t_hours": 5.5,
        "event_type": EventType.VESSEL_DARK,
        "location_id": "strait_chokepoint",
        "observable_kind": ObservableKind.VESSEL,
        "severity": 3,
        "source_confidence": 0.85,
        "ltiov_hours": 8.0,
        "narrative": (
            "VLCC (Panama-flagged) extinguished AIS 14nm NW of Larak Island "
            "at 0530Z; last reported 11.3 kn on southerly course. Pattern "
            "consistent with prior dark-fleet transits."
        ),
        "payload": {"imo": "9XXXXXX", "last_flag": "PA", "last_speed_kn": 11.3},
    },
    {
        "t_hours": 11.0,
        "event_type": EventType.KINETIC_STRIKE,
        "location_id": "gulf_of_oman_outbound",
        "observable_kind": ObservableKind.VESSEL,
        "severity": 4,
        "source_confidence": 0.90,
        "ltiov_hours": 6.0,
        "narrative": (
            "Merchant container ship struck by projectile outbound from "
            "Fujairah; vessel reports fire on deck, no casualties. BDA "
            "imagery required for insurer and allied maritime HQ."
        ),
        "payload": {"vessel_type": "CONTAINER"},
    },
    {
        "t_hours": 14.0,
        "event_type": EventType.NAVAL_POSTURE_CHANGE,
        "location_id": "bandar_abbas_naval",
        "observable_kind": ObservableKind.MILITARY_BASE,
        "severity": 4,
        "source_confidence": 0.75,
        "ltiov_hours": 12.0,
        "narrative": (
            "IRGCN fast-attack boats observed surging from pier complex; "
            "est. 20+ hulls underway. No declared exercise NOTMAR."
        ),
        "payload": {"hulls_est": 20, "declared_exercise": False},
    },
    {
        "t_hours": 38.0,
        "event_type": EventType.MINE_LAYING_REPORT,
        "location_id": "strait_chokepoint",
        "observable_kind": ObservableKind.ROUTE_SEGMENT,
        "severity": 5,
        "source_confidence": 0.70,
        "ltiov_hours": 4.0,
        "narrative": (
            "HUMINT + SIGINT fusion indicates IRGC minelayer activity "
            "overnight in inbound TSS lane. MCM cueing requested; transit "
            "warnings issued to merchant traffic."
        ),
        "payload": {"lane": "INBOUND_TSS"},
    },
    {
        "t_hours": 41.5,
        "event_type": EventType.KINETIC_STRIKE,
        "location_id": "siri_island",
        "observable_kind": ObservableKind.REFINERY,
        "severity": 5,
        "source_confidence": 0.95,
        "ltiov_hours": 8.0,
        "narrative": (
            "Storage tank at Siri Island facility struck; plume visible on "
            "commercial EO. Approx. 1M bbl facility. BDA + collateral "
            "assessment needed before redirect decisions."
        ),
        "payload": {"target_class": "OIL_STORAGE", "capacity_bbl": 1_000_000},
    },
    {
        "t_hours": 48.0,
        "event_type": EventType.HUMINT_REPORT,
        "location_id": "bandar_mahshahr",
        "observable_kind": ObservableKind.REFINERY,
        "severity": 3,
        "source_confidence": 0.55,
        "ltiov_hours": 36.0,
        "narrative": (
            "Reporting from local source: tanker truck convoy staging near "
            "petrochemical complex; possible fuel diversion to IRGC ground "
            "elements. Low-to-moderate confidence."
        ),
        "payload": {"convoy_size_est": 12},
    },
    {
        "t_hours": 52.0,
        "event_type": EventType.MOVEMENT_DETECTED,
        "location_id": "qeshm_island",
        "observable_kind": ObservableKind.MILITARY_BASE,
        "severity": 4,
        "source_confidence": 0.80,
        "ltiov_hours": 10.0,
        "narrative": (
            "6+ HET-class vehicles observed off Qeshm garrison on coastal "
            "road; profile consistent with CM launcher redeployment. "
            "Follow-on EO at N+6h requested."
        ),
        "payload": {"vehicles_est": 6, "suspected_class": "CM_LAUNCHER"},
    },
    {
        "t_hours": 61.0,
        "event_type": EventType.WEATHER_DEGRADATION,
        "location_id": "strait_chokepoint",
        "observable_kind": ObservableKind.WIDE_AREA,
        "severity": 3,
        "source_confidence": 0.92,
        "ltiov_hours": 14.0,
        "narrative": (
            "NWS + MetOc forecast dust/haze event over strait next 14h; "
            "EO collection viability degraded. SAR cueing recommended for "
            "critical targets."
        ),
        "payload": {"phenomenon": "DUST_HAZE"},
    },
    {
        "t_hours": 72.5,
        "event_type": EventType.DIPLOMATIC_STATUS_CHANGE,
        "location_id": "strait_chokepoint",
        "observable_kind": ObservableKind.WIDE_AREA,
        "severity": 3,
        "source_confidence": 0.95,
        "ltiov_hours": 72.0,
        "narrative": (
            "Oman-brokered ceasefire announced; Tehran declares strait "
            "'fully open' to commercial traffic. Coalition maintains "
            "watchful posture pending verification."
        ),
        "payload": {"policy_action": "CEASEFIRE_ANNOUNCED", "broker": "OM"},
    },
    {
        "t_hours": 80.0,
        "event_type": EventType.FACILITY_ANOMALY,
        "location_id": "kharg_terminal",
        "observable_kind": ObservableKind.REFINERY,
        "severity": 3,
        "source_confidence": 0.88,
        "ltiov_hours": 24.0,
        "narrative": (
            "Thermal ramp detected at Kharg loading berths; VLCC moored at "
            "SBM-2 consistent with export run. Ceasefire window export "
            "surge anticipated."
        ),
        "payload": {"berth": "SBM-2"},
    },
    {
        "t_hours": 96.5,
        "event_type": EventType.KINETIC_STRIKE,
        "location_id": "strait_chokepoint",
        "observable_kind": ObservableKind.VESSEL,
        "severity": 5,
        "source_confidence": 0.98,
        "ltiov_hours": 4.0,
        "narrative": (
            "IRGC gunboats fired on two Indian-flagged merchants transiting "
            "inbound TSS; ceasefire broken. One merchant aflame. Immediate "
            "force-protection reallocation underway."
        ),
        "payload": {"merchants_hit": 2, "flag": "IN"},
    },
    {
        "t_hours": 98.0,
        "event_type": EventType.DIPLOMATIC_STATUS_CHANGE,
        "location_id": "strait_chokepoint",
        "observable_kind": ObservableKind.WIDE_AREA,
        "severity": 5,
        "source_confidence": 0.99,
        "ltiov_hours": 48.0,
        "narrative": (
            "Iran re-closes Strait of Hormuz to all non-Iranian flagged "
            "traffic. MARAD issues advisory; insurers suspend war-risk "
            "cover for transiting hulls."
        ),
        "payload": {"policy_action": "STRAIT_CLOSED"},
    },
    {
        "t_hours": 104.0,
        "event_type": EventType.BLOCKADE_RUNNER,
        "location_id": "kharg_terminal",
        "observable_kind": ObservableKind.VESSEL,
        "severity": 4,
        "source_confidence": 0.82,
        "ltiov_hours": 6.0,
        "narrative": (
            "Dark VLCC observed loading at Kharg under no declared flag; "
            "departure imminent. Likely run attempt via outbound TSS. "
            "Cueing requested for N+2h."
        ),
        "payload": {"ship_class": "VLCC", "state": "LOADING"},
    },
    {
        "t_hours": 112.0,
        "event_type": EventType.KINETIC_STRIKE,
        "location_id": "mina_sulman",
        "observable_kind": ObservableKind.MILITARY_BASE,
        "severity": 4,
        "source_confidence": 0.85,
        "ltiov_hours": 6.0,
        "narrative": (
            "One-way UAS impact in vicinity of NSA Bahrain; no casualties "
            "reported. Force-protection posture elevated; tasking for "
            "origin back-track requested."
        ),
        "payload": {"munition": "OWA_UAS"},
    },
    {
        "t_hours": 134.0,
        "event_type": EventType.SIGINT_CUE,
        "location_id": "bandar_jask",
        "observable_kind": ObservableKind.MILITARY_BASE,
        "severity": 4,
        "source_confidence": 0.78,
        "ltiov_hours": 12.0,
        "narrative": (
            "Change in C2 emitter pattern at Bandar-e Jask; net activity "
            "consistent with ASCM unit preparation. Collateral HUMINT "
            "corroboration pending."
        ),
        "payload": {"emitter_class": "C2", "pattern": "PRE_LAUNCH_PROFILE"},
    },
    {
        "t_hours": 140.0,
        "event_type": EventType.MOVEMENT_DETECTED,
        "location_id": "kharg_terminal",
        "observable_kind": ObservableKind.VESSEL,
        "severity": 3,
        "source_confidence": 0.90,
        "ltiov_hours": 10.0,
        "narrative": (
            "VLCC RHN departing Kharg under St. Kitts flag assessed "
            "fraudulent. Ground-track confirmation and bunkering imagery "
            "requested at Gulf of Oman egress."
        ),
        "payload": {"vessel_name": "RHN", "flag_apparent": "KN"},
    },
    {
        "t_hours": 150.0,
        "event_type": EventType.HUMINT_REPORT,
        "location_id": "hormuz_island",
        "observable_kind": ObservableKind.WIDE_AREA,
        "severity": 3,
        "source_confidence": 0.48,
        "ltiov_hours": 48.0,
        "narrative": (
            "Walk-in source reports new IRGC anti-ship cruise missile "
            "construction on Hormuz Island ridge; coordinates approximate. "
            "Low confidence; corroboration tasked."
        ),
        "payload": {"reported_site": "RIDGE_NORTH"},
    },
    {
        "t_hours": 158.0,
        "event_type": EventType.WEATHER_DEGRADATION,
        "location_id": "gulf_of_oman_outbound",
        "observable_kind": ObservableKind.WIDE_AREA,
        "severity": 2,
        "source_confidence": 0.95,
        "ltiov_hours": 8.0,
        "narrative": (
            "Dense marine fog forecast across Gulf of Oman approach next "
            "8h; EO viability degraded. SAR cueing recommended for any "
            "outbound BDA tasking."
        ),
        "payload": {"phenomenon": "MARINE_FOG"},
    },
    {
        "t_hours": 164.0,
        "event_type": EventType.FACILITY_ANOMALY,
        "location_id": "bandar_abbas_naval",
        "observable_kind": ObservableKind.MILITARY_BASE,
        "severity": 4,
        "source_confidence": 0.82,
        "ltiov_hours": 12.0,
        "narrative": (
            "Post-collapse posture assessment: Bandar Abbas pierside count "
            "shows reinforced surface-combatant laydown + additional "
            "FAC hulls. Blockade-reinforcement indicator."
        ),
        "payload": {"combatants_added": 4},
    },
]

assert len(SCRIPTED_BEATS) == 20, "SCRIPTED_BEATS must contain exactly 20 beats"
