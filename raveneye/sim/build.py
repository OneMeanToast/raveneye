"""Top-level builder: turn a seed and a duration into a scenario dict."""

from __future__ import annotations

import random
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .bids import Bid, derive_bids
from .events import Event
from .locations import LOCATIONS, SENSOR_REQUIREMENTS
from .phases import PHASES, phase_at
from .scripted import SCRIPTED_BEATS
from .stakeholders import STAKEHOLDERS
from .stochastic import BASE_RATES, poisson_sample, sample_stochastic_event


DEFAULT_T0 = datetime(2026, 4, 13, 12, 0, 0, tzinfo=timezone.utc)


def build_events(
    t0: datetime = DEFAULT_T0,
    duration_hours: float = 168.0,
    tick_hours: float = 0.5,
    seed: int = 42,
) -> List[Event]:
    """Emit scripted beats + seeded Poisson-sampled stochastic injects.

    Returns events sorted chronologically. IDs are ``SCR-NNN`` for scripted
    (ordered by ``t_hours``) and ``STO-NNNN`` for stochastic (ordered by
    emission time, which equals chronological order since we walk time
    forward).
    """
    rng = random.Random(seed)
    events: List[Event] = []

    # Scripted beats first — stable ID ordering by chronological time.
    scripted_sorted = sorted(SCRIPTED_BEATS, key=lambda b: b["t_hours"])
    for i, beat in enumerate(scripted_sorted):
        t_h = float(beat["t_hours"])
        ph = phase_at(t_h)
        loc = LOCATIONS[beat["location_id"]]
        t_iso = (t0 + timedelta(hours=t_h)).isoformat()
        ev = Event(
            event_id=f"SCR-{i:03d}",
            t_iso=t_iso,
            t_hours=t_h,
            event_type=beat["event_type"],
            location_id=beat["location_id"],
            lat=loc["lat"],
            lon=loc["lon"],
            observable_kind=beat["observable_kind"],
            severity=int(beat["severity"]),
            source_confidence=float(beat["source_confidence"]),
            ltiov_hours=float(beat["ltiov_hours"]),
            narrative=beat["narrative"],
            phase=ph.name,
            scripted=True,
            payload=dict(beat.get("payload", {})),
        )
        events.append(ev)

    # Stochastic walk.
    total_rate = sum(BASE_RATES.values())
    sto_counter = 0
    t = 0.0
    while t < duration_hours:
        ph = phase_at(t)
        lam = total_rate * ph.demand_multiplier * tick_hours
        n = min(4, poisson_sample(lam, rng))
        for _ in range(n):
            t_h = t + rng.uniform(0.0, tick_hours)
            if t_h >= duration_hours:
                continue
            ev = sample_stochastic_event(t_h, rng, ph)
            ev.event_id = f"STO-{sto_counter:04d}"
            ev.t_iso = (t0 + timedelta(hours=ev.t_hours)).isoformat()
            events.append(ev)
            sto_counter += 1
        t += tick_hours

    events.sort(key=lambda e: (e.t_hours, e.event_id))
    return events


def _to_jsonable(obj: Any) -> Any:
    if isinstance(obj, Enum):
        return obj.value
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: _to_jsonable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(x) for x in obj]
    return obj


def _locations_jsonable() -> Dict[str, Dict]:
    out: Dict[str, Dict] = {}
    for loc_id, loc in LOCATIONS.items():
        out[loc_id] = {
            "name": loc["name"],
            "kind": loc["kind"].value,
            "lat": loc["lat"],
            "lon": loc["lon"],
            "country": loc["country"],
        }
    return out


def _sensor_requirements_jsonable() -> Dict[str, Dict]:
    return {k.value: dict(v) for k, v in SENSOR_REQUIREMENTS.items()}


def _stakeholders_jsonable() -> List[Dict]:
    out: List[Dict] = []
    for sh in STAKEHOLDERS:
        out.append(
            {
                "stakeholder_id": sh.stakeholder_id,
                "name": sh.name,
                "mandate": sh.mandate,
                "weights": {k.value: v for k, v in sh.weights.items()},
            }
        )
    return out


def _phases_jsonable(t0: datetime) -> List[Dict]:
    out: List[Dict] = []
    for p in PHASES:
        out.append(
            {
                "name": p.name,
                "start_h": p.start_h,
                "start_iso": (t0 + timedelta(hours=p.start_h)).isoformat(),
                "demand_multiplier": p.demand_multiplier,
            }
        )
    return out


def build_sim(
    seed: int = 42,
    duration_hours: float = 168.0,
    t0: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Build the full v0.1 scenario dict.

    Schema is the v0.2-ready shape from the build spec §3.1, with v0.2-only
    keys (``constellations``, ``satellites``, ``access_windows``,
    ``allocations``) absent in v0.1.
    """
    if t0 is None:
        t0 = DEFAULT_T0
    events = build_events(t0=t0, duration_hours=duration_hours, seed=seed)
    bids = derive_bids(events, t0=t0)

    scenario = {
        "meta": {
            "scenario": "Strait of Hormuz Blockade Arc (Apr 2026)",
            "t0_iso": t0.isoformat(),
            "duration_hours": duration_hours,
            "seed": seed,
            "n_events": len(events),
            "n_bids": len(bids),
            "phases": _phases_jsonable(t0),
            "raveneye_version": "0.1.0",
        },
        "locations": _locations_jsonable(),
        "sensor_requirements": _sensor_requirements_jsonable(),
        "stakeholders": _stakeholders_jsonable(),
        "events": [_to_jsonable(e) for e in events],
        "bids": [_to_jsonable(b) for b in bids],
    }
    return scenario
