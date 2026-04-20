"""Stochastic inject sampler (seeded Poisson draws, phase-weighted)."""
from __future__ import annotations

import math
import random
from typing import Dict, List, Tuple

from .events import Event, EventType, ObservableKind
from .locations import LOCATIONS
from .phases import Phase


BASE_RATES: Dict[EventType, float] = {
    EventType.VESSEL_DARK: 0.16,
    EventType.MOVEMENT_DETECTED: 0.10,
    EventType.HUMINT_REPORT: 0.065,
    EventType.SIGINT_CUE: 0.07,
    EventType.KINETIC_STRIKE: 0.02,
    EventType.MINE_LAYING_REPORT: 0.008,
    EventType.NAVAL_POSTURE_CHANGE: 0.03,
    EventType.BLOCKADE_RUNNER: 0.035,
    EventType.FACILITY_ANOMALY: 0.04,
    EventType.WEATHER_DEGRADATION: 0.012,
    EventType.DIPLOMATIC_STATUS_CHANGE: 0.002,
}


PLAUSIBLE_LOCATIONS: Dict[EventType, List[str]] = {
    EventType.VESSEL_DARK: [
        "strait_chokepoint",
        "gulf_of_oman_outbound",
        "larak_island",
        "hormuz_island",
    ],
    EventType.MOVEMENT_DETECTED: [
        "bandar_abbas_naval",
        "bandar_jask",
        "qeshm_island",
        "hormuz_island",
        "larak_island",
        "kharg_terminal",
        "bandar_mahshahr",
        "mina_sulman",
    ],
    EventType.HUMINT_REPORT: [
        "bandar_abbas_naval",
        "bandar_jask",
        "qeshm_island",
        "hormuz_island",
        "kharg_terminal",
        "bandar_mahshahr",
        "siri_island",
    ],
    EventType.SIGINT_CUE: [
        "bandar_abbas_naval",
        "bandar_jask",
        "qeshm_island",
        "hormuz_island",
    ],
    EventType.KINETIC_STRIKE: [
        "strait_chokepoint",
        "gulf_of_oman_outbound",
        "siri_island",
        "fujairah_port",
        "mina_sulman",
        "kharg_terminal",
    ],
    EventType.MINE_LAYING_REPORT: [
        "strait_chokepoint",
        "gulf_of_oman_outbound",
    ],
    EventType.NAVAL_POSTURE_CHANGE: [
        "bandar_abbas_naval",
        "bandar_jask",
        "qeshm_island",
    ],
    EventType.BLOCKADE_RUNNER: [
        "strait_chokepoint",
        "gulf_of_oman_outbound",
        "kharg_terminal",
        "siri_island",
    ],
    EventType.FACILITY_ANOMALY: [
        "kharg_terminal",
        "siri_island",
        "bandar_mahshahr",
        "ras_laffan",
        "ras_tanura",
        "fujairah_port",
        "jebel_ali",
    ],
    EventType.WEATHER_DEGRADATION: [
        "strait_chokepoint",
        "gulf_of_oman_outbound",
    ],
    EventType.DIPLOMATIC_STATUS_CHANGE: [
        "strait_chokepoint",
    ],
}


# severity (int inclusive), confidence (float), ltiov_hours (float)
DEFAULTS: Dict[EventType, Dict] = {
    EventType.VESSEL_DARK: {"severity": (2, 4), "conf": (0.6, 0.9), "ltiov": (4.0, 12.0)},
    EventType.MOVEMENT_DETECTED: {"severity": (2, 4), "conf": (0.55, 0.9), "ltiov": (4.0, 14.0)},
    EventType.HUMINT_REPORT: {"severity": (2, 4), "conf": (0.35, 0.7), "ltiov": (12.0, 48.0)},
    EventType.SIGINT_CUE: {"severity": (2, 4), "conf": (0.55, 0.85), "ltiov": (6.0, 18.0)},
    EventType.KINETIC_STRIKE: {"severity": (4, 5), "conf": (0.85, 0.99), "ltiov": (2.0, 8.0)},
    EventType.MINE_LAYING_REPORT: {"severity": (4, 5), "conf": (0.55, 0.8), "ltiov": (2.0, 6.0)},
    EventType.NAVAL_POSTURE_CHANGE: {"severity": (3, 5), "conf": (0.65, 0.9), "ltiov": (6.0, 18.0)},
    EventType.BLOCKADE_RUNNER: {"severity": (3, 5), "conf": (0.7, 0.92), "ltiov": (3.0, 10.0)},
    EventType.FACILITY_ANOMALY: {"severity": (2, 4), "conf": (0.6, 0.9), "ltiov": (12.0, 36.0)},
    EventType.WEATHER_DEGRADATION: {"severity": (1, 3), "conf": (0.85, 0.98), "ltiov": (4.0, 18.0)},
    EventType.DIPLOMATIC_STATUS_CHANGE: {"severity": (3, 5), "conf": (0.9, 0.99), "ltiov": (24.0, 72.0)},
}


_EARTH_R_KM = 6371.0088


def poisson_sample(lam: float, rng: random.Random) -> int:
    """Knuth's algorithm for small lambdas. Returns a non-negative int count."""
    if lam <= 0.0:
        return 0
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= L:
            return k - 1


def jitter_location(loc_id: str, rng: random.Random, max_km: float = 8.0) -> Tuple[float, float]:
    """Apply flat-earth uniform-disk jitter to a named location's coordinates."""
    loc = LOCATIONS[loc_id]
    base_lat = loc["lat"]
    base_lon = loc["lon"]
    r_km = rng.uniform(0.0, max_km)
    theta = rng.uniform(0.0, 2.0 * math.pi)
    dlat_deg = (r_km * math.cos(theta) / _EARTH_R_KM) * (180.0 / math.pi)
    dlon_deg = (r_km * math.sin(theta) / _EARTH_R_KM) * (180.0 / math.pi) / max(
        math.cos(math.radians(base_lat)), 1e-6
    )
    return base_lat + dlat_deg, base_lon + dlon_deg


def sample_stochastic_event(t_hours: float, rng: random.Random, phase: Phase) -> Event:
    """Draw a single stochastic event at time t_hours.

    Event type is sampled proportionally to BASE_RATES (weights only; no phase
    coupling to type here — the phase multiplier acts on counts in build.py).
    """
    types = list(BASE_RATES.keys())
    weights = [BASE_RATES[t] for t in types]
    event_type = rng.choices(types, weights=weights, k=1)[0]

    candidates = PLAUSIBLE_LOCATIONS[event_type]
    loc_id = rng.choice(candidates)
    lat, lon = jitter_location(loc_id, rng)

    cfg = DEFAULTS[event_type]
    sev_lo, sev_hi = cfg["severity"]
    severity = rng.randint(sev_lo, sev_hi)
    conf_lo, conf_hi = cfg["conf"]
    confidence = round(rng.uniform(conf_lo, conf_hi), 3)
    ltiov_lo, ltiov_hi = cfg["ltiov"]
    ltiov = round(rng.uniform(ltiov_lo, ltiov_hi), 2)

    loc = LOCATIONS[loc_id]
    observable_kind = loc["kind"]
    if event_type in {
        EventType.VESSEL_DARK,
        EventType.BLOCKADE_RUNNER,
    }:
        observable_kind = ObservableKind.VESSEL

    narrative = _narrative(event_type, loc["name"])

    return Event(
        event_id="",
        t_iso="",
        t_hours=round(t_hours, 4),
        event_type=event_type,
        location_id=loc_id,
        lat=round(lat, 5),
        lon=round(lon, 5),
        observable_kind=observable_kind,
        severity=severity,
        source_confidence=confidence,
        ltiov_hours=ltiov,
        narrative=narrative,
        phase=phase.name,
        scripted=False,
        payload={},
    )


def _narrative(event_type: EventType, loc_name: str) -> str:
    templates = {
        EventType.VESSEL_DARK: f"AIS blackout reported by vessel of interest near {loc_name}.",
        EventType.MOVEMENT_DETECTED: f"Unscheduled movement observed in vicinity of {loc_name}.",
        EventType.HUMINT_REPORT: f"Source reporting activity at {loc_name}; corroboration pending.",
        EventType.SIGINT_CUE: f"Emitter activity change at {loc_name} crosses tasking threshold.",
        EventType.KINETIC_STRIKE: f"Kinetic event reported at {loc_name}; BDA requested.",
        EventType.MINE_LAYING_REPORT: f"Mine-laying activity indicated near {loc_name}.",
        EventType.NAVAL_POSTURE_CHANGE: f"Surface-combatant posture change at {loc_name}.",
        EventType.BLOCKADE_RUNNER: f"Blockade-running vessel profile detected near {loc_name}.",
        EventType.FACILITY_ANOMALY: f"Anomalous activity signature at {loc_name}.",
        EventType.WEATHER_DEGRADATION: f"EO collection viability degraded over {loc_name}.",
        EventType.DIPLOMATIC_STATUS_CHANGE: f"Declared policy shift affecting {loc_name}.",
    }
    return templates[event_type]
