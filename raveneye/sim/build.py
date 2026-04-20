"""Top-level sim builder: events + bids + meta bundle."""
from __future__ import annotations

import random
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .bids import derive_bids
from .events import Event, EventType, ObservableKind
from .locations import LOCATIONS, SENSOR_REQUIREMENTS
from .phases import PHASES, Phase, phase_at
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
    """Build the full event stream: scripted beats + seeded stochastic injects."""
    rng = random.Random(seed)
    events: List[Event] = []

    for i, beat in enumerate(SCRIPTED_BEATS):
        t_hours = float(beat["t_hours"])
        loc = LOCATIONS[beat["location_id"]]
        ev = Event(
            event_id=f"SCR-{i:03d}",
            t_iso=(t0 + timedelta(hours=t_hours)).isoformat(),
            t_hours=t_hours,
            event_type=beat["event_type"],
            location_id=beat["location_id"],
            lat=loc["lat"],
            lon=loc["lon"],
            observable_kind=beat["observable_kind"],
            severity=int(beat["severity"]),
            source_confidence=float(beat["source_confidence"]),
            ltiov_hours=float(beat["ltiov_hours"]),
            narrative=beat["narrative"],
            phase=phase_at(t_hours).name,
            scripted=True,
            payload=dict(beat.get("payload", {})),
        )
        events.append(ev)

    total_rate = sum(BASE_RATES.values())
    sto_counter = 0
    t = 0.0
    n_ticks = int(round(duration_hours / tick_hours))
    for tick_idx in range(n_ticks):
        tick_start = tick_idx * tick_hours
        phase = phase_at(tick_start)
        lam = total_rate * phase.rate_multiplier * tick_hours
        count = min(4, poisson_sample(lam, rng))
        for _ in range(count):
            t_hours = tick_start + rng.uniform(0.0, tick_hours)
            ev = sample_stochastic_event(t_hours, rng, phase)
            ev.event_id = f"STO-{sto_counter:04d}"
            ev.t_iso = (t0 + timedelta(hours=ev.t_hours)).isoformat()
            events.append(ev)
            sto_counter += 1

    events.sort(key=lambda e: (e.t_hours, e.event_id))
    return events


def build_sim(
    seed: int = 42,
    duration_hours: float = 168.0,
    t0: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Build the full v0.1 sim bundle (JSON-ready dict).

    Shape matches the v0.2 Scenario JSON (§3.1) but only populates the fields
    the demand layer owns: meta, locations, stakeholders, phases, events, bids.
    """
    if t0 is None:
        t0 = DEFAULT_T0

    events = build_events(t0=t0, duration_hours=duration_hours, seed=seed)
    bids = derive_bids(events, t0=t0, stakeholders=STAKEHOLDERS)

    phases_out = [
        {
            "name": p.name,
            "start_hours": p.start_hours,
            "rate_multiplier": p.rate_multiplier,
            "start_iso": (t0 + timedelta(hours=p.start_hours)).isoformat(),
        }
        for p in PHASES
    ]

    stakeholders_out = [
        {
            "stakeholder_id": sh.stakeholder_id,
            "display_name": sh.display_name,
            "mission": sh.mission,
            "weights": {et.value: w for et, w in sh.weights.items()},
        }
        for sh in STAKEHOLDERS
    ]

    locations_out = {
        loc_id: {
            "name": v["name"],
            "kind": v["kind"].value,
            "lat": v["lat"],
            "lon": v["lon"],
            "country": v["country"],
        }
        for loc_id, v in LOCATIONS.items()
    }

    sensor_requirements_out = {
        kind.value: req for kind, req in SENSOR_REQUIREMENTS.items()
    }

    meta = {
        "scenario": "Strait of Hormuz Blockade Arc (Apr 2026)",
        "t0_iso": t0.isoformat(),
        "duration_hours": duration_hours,
        "seed": seed,
        "n_events": len(events),
        "n_bids": len(bids),
        "phases": phases_out,
    }

    scenario = {
        "meta": meta,
        "locations": locations_out,
        "sensor_requirements": sensor_requirements_out,
        "stakeholders": stakeholders_out,
        "events": [_to_jsonable(e) for e in events],
        "bids": [_to_jsonable(b) for b in bids],
    }
    return scenario


def _to_jsonable(obj: Any) -> Any:
    """Recursively convert dataclasses, enums, and nested containers to
    JSON-serializable primitives."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: _to_jsonable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    return obj
