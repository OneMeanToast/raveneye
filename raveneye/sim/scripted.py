"""Hand-curated scripted narrative beats for the Hormuz April 2026 scenario.

Each beat is a deterministic event: same seed or not, these always fire.
They supply the narrative anchors around which stochastic injects cluster.
IDs are assigned by :func:`raveneye.sim.build.build_events` as ``SCR-NNN``.
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
            "CENTCOM reaffirms Strait of Hormuz blockade in a formal press "
            "statement; IRGCN advised to disperse. Allied maritime HQs raise "
            "force-protection posture across the Gulf."
        ),
        "payload": {"declaring_party": "US_CENTCOM", "blockade_status": "AFFIRMED"},
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
            "Panamanian-flagged VLCC drops AIS approximately 4 nm north of "
            "Larak Island. Last observed speed 11.3 kn on heading 295. "
            "Pattern consistent with recent sanction-evasion profiles."
        ),
        "payload": {
            "imo": "9412387",
            "last_flag": "PA",
            "last_speed_kn": 11.3,
            "last_heading_deg": 295,
        },
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
            "Marshall Islands-flagged container ship reports projectile "
            "impact near superstructure while transiting outbound from the "
            "strait. No casualties reported; fire contained. BDA imagery "
            "required for insurance and attribution."
        ),
        "payload": {"vessel_type": "CONTAINER", "flag": "MH", "casualties": 0},
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
            "Multiple IRGCN fast boats (Peykaap and Tondar class) observed "
            "sortieing from Bandar Abbas in rapid succession. Dispersal to "
            "known forward basing at Qeshm and Larak suspected."
        ),
        "payload": {"boats_count_est": 14, "classes": ["Peykaap", "Tondar"]},
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
            "Allied liaison reports overnight IRGC minelayer activity in the "
            "northbound TSS lane. Type suspected EM-52 bottom-moored. High "
            "urgency for MCM route survey before sunrise transit window."
        ),
        "payload": {"suspected_type": "EM-52", "lane": "TSS_NORTHBOUND"},
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
            "Crude-oil storage tank on Siri Island struck; thermal plume "
            "visible to commercial EO. Facility rated ~1M bbl total capacity. "
            "BDA and environmental-extent assessment priority."
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
            "Source of moderate reliability reports nightly tanker-truck "
            "convoys entering the Mahshahr petrochemical complex. Possible "
            "sanctioned-fuel diversion; corroboration required."
        ),
        "payload": {"source_grade": "C2", "convoy_size_est": 8},
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
            "Six-plus vehicles exit a hardened garrison on Qeshm Island; "
            "length/width signatures consistent with anti-ship cruise "
            "missile transporter-erector-launchers. Dispersal direction east."
        ),
        "payload": {"vehicle_count_est": 7, "suspected_system": "ASCM_TEL"},
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
            "Regional dust and marine haze forecast across the strait for "
            "the next 12-16 hours. Visible-band collection viability "
            "degraded; SAR and TIR preferred during this window."
        ),
        "payload": {"vis_km_est": 3.0, "preferred_bands": ["SAR_X", "TIR"]},
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
            "Qatar-mediated ceasefire announced. Iranian state media declares "
            "the strait 'fully open' to international shipping. Allied naval "
            "posture de-escalates; insurers prepare to re-rate."
        ),
        "payload": {"mediator": "QA", "strait_status": "OPEN"},
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
            "Thermal and commercial optical imagery of Kharg shows an "
            "unseasonal ramp in loading activity. One VLCC alongside, "
            "two more at anchor. Consistent with rapid pre-escalation lift."
        ),
        "payload": {"vlccs_alongside": 1, "vlccs_at_anchor": 2},
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
            "IRGCN gunboats open fire on two Indian-flagged bulk carriers "
            "transiting the strait northbound. Ceasefire effectively broken. "
            "Indian Navy element inbound; allied ROE review active."
        ),
        "payload": {"vessels_engaged": 2, "flag": "IN"},
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
            "Iran re-declares the strait closed to 'hostile' flag vessels "
            "and asserts a 12-nm exclusion. Allied task force recalls "
            "merchants; convoy escort mission planning initiated."
        ),
        "payload": {"strait_status": "CLOSED", "exclusion_nm": 12},
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
            "Dark VLCC observed loading at Kharg for approximately eight "
            "hours. AIS spoofed to a South-China-Sea track. Likely imminent "
            "departure attempting to run the restored blockade."
        ),
        "payload": {"vessel_type": "VLCC", "ais_spoof_origin": "SCS"},
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
            "One-way attack UAV detonates near the NSA Bahrain perimeter. "
            "Minor fragmentation damage; no US casualties. Force-protection "
            "elevation ordered across allied facilities Gulf-wide."
        ),
        "payload": {"weapon": "OWA_UAV", "casualties_us": 0},
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
            "Change in C2 emitter pattern detected at Bandar-e Jask, "
            "consistent with establishment of a southern ASCM cell. "
            "Emitter DF fixes cluster on the eastern revetment line."
        ),
        "payload": {"emitter_class": "C2", "activity": "PATTERN_SHIFT"},
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
            "Previously-dark VLCC 'RHN' departs Kharg under a fraudulent "
            "Vanuatu flag with AIS spoofed to a different hull. Track "
            "consistent with the run-vector forecast 36 hours ago."
        ),
        "payload": {"vessel_name": "RHN", "spoofed_flag": "VU"},
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
            "Low-reliability source alleges new IRGC ASCM revetment "
            "construction on the south face of Hormuz Island. Coordinates "
            "approximate; imagery required for location and validation."
        ),
        "payload": {"source_grade": "D3", "suspected_system": "ASCM"},
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
            "Dense marine fog forecast across the Gulf of Oman approach "
            "for the pre-dawn window. EO viability near zero; SAR tasking "
            "recommended for ongoing merchant-tracking cues."
        ),
        "payload": {"vis_km_est": 0.5, "preferred_bands": ["SAR_X"]},
    },
    {
        "t_hours": 164.0,
        "event_type": EventType.SIGINT_CUE,
        "location_id": "qeshm_island",
        "observable_kind": ObservableKind.MILITARY_BASE,
        "severity": 3,
        "source_confidence": 0.72,
        "ltiov_hours": 18.0,
        "narrative": (
            "Late-scenario emitter silence across previously-active Qeshm "
            "ASCM sites. Consistent with displacement to alternate hides; "
            "wide-area imagery tasking requested to recover the picture."
        ),
        "payload": {"activity": "EMITTER_SILENCE", "suspected": "DISPLACEMENT"},
    },
]
