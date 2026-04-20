"""Seeded stochastic event sampling.

Produces the background drumbeat of events around the scripted backbone.
All randomness comes from a caller-supplied ``random.Random`` instance so
that runs are reproducible under a fixed seed.
"""

from __future__ import annotations

import math
import random
from typing import Dict, List, Tuple

from .events import Event, EventType, ObservableKind
from .locations import LOCATIONS
from .phases import Phase


# Base arrival rates (events/hour) at phase multiplier 1.0. Tuned so a
# seed=42, 168h run produces ~150-160 stochastic events.
BASE_RATES: Dict[EventType, float] = {
    EventType.VESSEL_DARK: 0.14,
    EventType.MOVEMENT_DETECTED: 0.09,
    EventType.HUMINT_REPORT: 0.06,
    EventType.SIGINT_CUE: 0.07,
    EventType.KINETIC_STRIKE: 0.02,
    EventType.MINE_LAYING_REPORT: 0.008,
    EventType.NAVAL_POSTURE_CHANGE: 0.03,
    EventType.BLOCKADE_RUNNER: 0.035,
    EventType.FACILITY_ANOMALY: 0.035,
    EventType.WEATHER_DEGRADATION: 0.012,
    EventType.DIPLOMATIC_STATUS_CHANGE: 0.002,
}


# Which locations can plausibly host which event type.
PLAUSIBLE_LOCATIONS: Dict[EventType, List[str]] = {
    EventType.VESSEL_DARK: [
        "strait_chokepoint",
        "gulf_of_oman_outbound",
        "larak_island",
        "hormuz_island",
        "fujairah_port",
        "jebel_ali",
    ],
    EventType.MOVEMENT_DETECTED: [
        "bandar_abbas_naval",
        "bandar_jask",
        "qeshm_island",
        "hormuz_island",
        "larak_island",
        "kharg_terminal",
    ],
    EventType.HUMINT_REPORT: [
        "bandar_abbas_naval",
        "bandar_jask",
        "qeshm_island",
        "hormuz_island",
        "bandar_mahshahr",
        "kharg_terminal",
        "siri_island",
    ],
    EventType.SIGINT_CUE: [
        "bandar_abbas_naval",
        "bandar_jask",
        "qeshm_island",
        "hormuz_island",
        "larak_island",
    ],
    EventType.KINETIC_STRIKE: [
        "strait_chokepoint",
        "gulf_of_oman_outbound",
        "siri_island",
        "kharg_terminal",
        "mina_sulman",
        "fujairah_port",
    ],
    EventType.MINE_LAYING_REPORT: [
        "strait_chokepoint",
        "gulf_of_oman_outbound",
    ],
    EventType.NAVAL_POSTURE_CHANGE: [
        "bandar_abbas_naval",
        "bandar_jask",
        "qeshm_island",
        "mina_sulman",
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
        "jebel_ali",
        "fujairah_port",
    ],
    EventType.WEATHER_DEGRADATION: [
        "strait_chokepoint",
        "gulf_of_oman_outbound",
        "hormuz_island",
        "larak_island",
    ],
    EventType.DIPLOMATIC_STATUS_CHANGE: [
        "strait_chokepoint",
    ],
}


# Per-type sampling defaults: severity (inclusive int range), confidence
# (uniform float range), LTIOV hours (uniform float range).
DEFAULTS: Dict[EventType, Dict] = {
    EventType.VESSEL_DARK: {"sev": (2, 4), "conf": (0.55, 0.90), "ltiov": (6.0, 18.0)},
    EventType.MOVEMENT_DETECTED: {"sev": (2, 4), "conf": (0.60, 0.92), "ltiov": (4.0, 14.0)},
    EventType.HUMINT_REPORT: {"sev": (2, 3), "conf": (0.30, 0.65), "ltiov": (18.0, 60.0)},
    EventType.SIGINT_CUE: {"sev": (2, 4), "conf": (0.55, 0.90), "ltiov": (6.0, 20.0)},
    EventType.KINETIC_STRIKE: {"sev": (3, 5), "conf": (0.80, 0.98), "ltiov": (3.0, 10.0)},
    EventType.MINE_LAYING_REPORT: {"sev": (4, 5), "conf": (0.55, 0.80), "ltiov": (3.0, 8.0)},
    EventType.NAVAL_POSTURE_CHANGE: {"sev": (2, 4), "conf": (0.65, 0.90), "ltiov": (6.0, 18.0)},
    EventType.BLOCKADE_RUNNER: {"sev": (3, 4), "conf": (0.65, 0.90), "ltiov": (4.0, 12.0)},
    EventType.FACILITY_ANOMALY: {"sev": (2, 4), "conf": (0.70, 0.95), "ltiov": (12.0, 36.0)},
    EventType.WEATHER_DEGRADATION: {"sev": (2, 3), "conf": (0.85, 0.98), "ltiov": (6.0, 18.0)},
    EventType.DIPLOMATIC_STATUS_CHANGE: {"sev": (2, 4), "conf": (0.90, 0.99), "ltiov": (24.0, 72.0)},
}


def poisson_sample(lam: float, rng: random.Random) -> int:
    """Knuth's algorithm. Good for small lambda (<< 20), which is our regime."""
    if lam <= 0.0:
        return 0
    limit = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= limit:
            return k - 1


def jitter_location(loc_id: str, rng: random.Random, max_km: float = 8.0) -> Tuple[float, float]:
    """Flat-earth jitter around ``loc_id`` up to ``max_km`` kilometres.

    Good enough for a map viewer; the scenario AO is small and we don't need
    geodetic accuracy in v0.1.
    """
    loc = LOCATIONS[loc_id]
    # radial in km, uniform-in-disk via sqrt
    r_km = max_km * math.sqrt(rng.random())
    theta = rng.uniform(0.0, 2.0 * math.pi)
    dlat_km = r_km * math.cos(theta)
    dlon_km = r_km * math.sin(theta)
    km_per_deg_lat = 111.0
    km_per_deg_lon = 111.0 * max(0.05, math.cos(math.radians(loc["lat"])))
    lat = loc["lat"] + dlat_km / km_per_deg_lat
    lon = loc["lon"] + dlon_km / km_per_deg_lon
    return lat, lon


def _observable_for(event_type: EventType, loc_id: str) -> ObservableKind:
    """Pick a reasonable observable for this event at this location."""
    if event_type == EventType.VESSEL_DARK or event_type == EventType.BLOCKADE_RUNNER:
        return ObservableKind.VESSEL
    if event_type == EventType.MINE_LAYING_REPORT:
        return ObservableKind.ROUTE_SEGMENT
    if event_type == EventType.WEATHER_DEGRADATION or event_type == EventType.DIPLOMATIC_STATUS_CHANGE:
        return ObservableKind.WIDE_AREA
    if event_type == EventType.KINETIC_STRIKE:
        # use the location's native kind (refinery, base, etc.); VESSEL for wide areas
        native = LOCATIONS[loc_id]["kind"]
        if native == ObservableKind.WIDE_AREA:
            return ObservableKind.VESSEL
        return native
    # Most remaining types (MOVEMENT_DETECTED, HUMINT, SIGINT, NAVAL_POSTURE,
    # FACILITY_ANOMALY) use the location's native kind.
    return LOCATIONS[loc_id]["kind"]


_NARRATIVE_TEMPLATES: Dict[EventType, List[str]] = {
    EventType.VESSEL_DARK: [
        "Commercial vessel drops AIS near {name}; last heading inconsistent with plan.",
        "Tracked merchant near {name} goes dark; possible sanction-evasion profile.",
        "Sporadic AIS gaps on a tanker transiting {name}; investigation tasked.",
    ],
    EventType.MOVEMENT_DETECTED: [
        "Vehicle movement detected at {name}; composition consistent with force redistribution.",
        "Convoy exits {name} under partial cover; possible launcher relocation.",
        "New activity signature at {name}; previously dormant revetment line reactivated.",
    ],
    EventType.HUMINT_REPORT: [
        "Source reports unusual activity at {name}; corroboration tasked.",
        "Second-hand account of personnel buildup near {name}.",
        "Low-grade source claims materiel transfer through {name}.",
    ],
    EventType.SIGINT_CUE: [
        "C2 emitter pattern change detected at {name}.",
        "New waveform observed from the vicinity of {name}; geolocation in progress.",
        "Emitter silence followed by brief burst from {name}; DF fix pending.",
    ],
    EventType.KINETIC_STRIKE: [
        "Strike reported at {name}; BDA imagery required.",
        "Explosion observed at {name}; damage assessment tasked.",
        "Projectile impact near {name}; extent not yet confirmed.",
    ],
    EventType.MINE_LAYING_REPORT: [
        "Possible mine-laying activity reported in lane off {name}.",
        "Surface track consistent with minelayer observed near {name}.",
    ],
    EventType.NAVAL_POSTURE_CHANGE: [
        "Fast-boat sortie detected at {name}.",
        "Unusual dispersal pattern from {name}; posture shift likely.",
        "Pier-side turnover at {name} consistent with surge-readiness.",
    ],
    EventType.BLOCKADE_RUNNER: [
        "Vessel near {name} assessed as likely blockade runner.",
        "Dark VLCC loading pattern near {name}; imminent departure suspected.",
    ],
    EventType.FACILITY_ANOMALY: [
        "Thermal anomaly at {name}; out-of-cycle loading activity.",
        "Unexpected venting signature at {name}; operational tempo shift.",
        "Lighting pattern at {name} inconsistent with reported status.",
    ],
    EventType.WEATHER_DEGRADATION: [
        "Forecast reduced visibility across {name}; EO viability degraded.",
        "Marine haze advisory over {name}; prefer SAR/TIR this window.",
    ],
    EventType.DIPLOMATIC_STATUS_CHANGE: [
        "Public statement by regional party re-characterizes {name} status.",
        "Allied press briefing adjusts stated posture regarding {name}.",
    ],
}


def _narrative_for(event_type: EventType, loc_id: str, rng: random.Random) -> str:
    templates = _NARRATIVE_TEMPLATES[event_type]
    idx = rng.randrange(len(templates))
    return templates[idx].format(name=LOCATIONS[loc_id]["name"])


def sample_stochastic_event(
    t_hours: float,
    rng: random.Random,
    phase: Phase,
) -> Event:
    """Sample a single stochastic event at (roughly) ``t_hours``.

    Returns an :class:`Event` with empty ``event_id``/``t_iso`` — the caller
    (``build.build_events``) is responsible for assigning IDs and ISO times.
    """
    # Pick an event type proportional to its base rate (phase multiplier is
    # applied once at arrival time; type mix stays relatively stable).
    types = list(BASE_RATES.keys())
    weights = [BASE_RATES[t] for t in types]
    total = sum(weights)
    r = rng.uniform(0.0, total)
    acc = 0.0
    event_type = types[-1]
    for t, w in zip(types, weights):
        acc += w
        if r <= acc:
            event_type = t
            break

    loc_id = rng.choice(PLAUSIBLE_LOCATIONS[event_type])
    lat, lon = jitter_location(loc_id, rng)
    defaults = DEFAULTS[event_type]
    sev_lo, sev_hi = defaults["sev"]
    conf_lo, conf_hi = defaults["conf"]
    ltiov_lo, ltiov_hi = defaults["ltiov"]
    severity = rng.randint(sev_lo, sev_hi)
    confidence = round(rng.uniform(conf_lo, conf_hi), 3)
    ltiov = round(rng.uniform(ltiov_lo, ltiov_hi), 2)
    observable = _observable_for(event_type, loc_id)
    narrative = _narrative_for(event_type, loc_id, rng)

    return Event(
        event_id="",
        t_iso="",
        t_hours=round(t_hours, 4),
        event_type=event_type,
        location_id=loc_id,
        lat=round(lat, 5),
        lon=round(lon, 5),
        observable_kind=observable,
        severity=severity,
        source_confidence=confidence,
        ltiov_hours=ltiov,
        narrative=narrative,
        phase=phase.name,
        scripted=False,
        payload={},
    )
