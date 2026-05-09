"""``build_full_scenario`` — the v0.2 unified scenario assembler.

Calls ``build_sim()`` (v0.1 demand), ``build_supply()`` (v0.2 supply), and
``allocate()`` (v0.2 mechanism) and merges the three into a single JSON
object matching the §3.1 schema.

Two flavors:

* ``build_full_scenario(...)`` — production path. Pulls TLEs over the
  network (with on-disk caching). Use ``--refresh-tles`` to bypass cache.
* ``build_full_scenario_offline(satellites=..., ...)`` — uses pre-built
  satellite dicts (e.g. from ``build_satellites_from_fixture``). Used by
  tests, by the offline CLI mode, and by alt TLE sources.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

from ..delivery import (
    apply_delivery_pipeline,
    delivery_rate,
    processing_success_rate_observed,
)
from ..mechanism import Mechanism, allocate, drop_rate, total_welfare
from ..orbital import (
    CONSTELLATIONS,
    Constellation,
    build_supply,
    build_supply_from_satellites,
    targets_from_locations,
)
from ..sim import DEFAULT_T0, build_sim


DEFAULT_MECHANISM = "greedy"


def _meta(
    sim: Dict[str, Any],
    supply: Dict[str, Any],
    allocations_dicts: List[Dict[str, Any]],
    *,
    mechanism_name: str,
    welfare: float,
    drop: float,
    delivery_rate_value: float,
    processing_rate_value: float,
) -> Dict[str, Any]:
    sim_meta = sim.get("meta", {})
    sup_meta = supply.get("meta", {})

    def _final(a: Dict[str, Any]) -> str:
        return (a.get("lifecycle") or {}).get("final_status", a.get("status", ""))

    return {
        "scenario": sim_meta.get("scenario", "RavenEye scenario"),
        "t0_iso": sim_meta.get("t0_iso") or sup_meta.get("t0_iso"),
        "duration_hours": sim_meta.get("duration_hours") or sup_meta.get("duration_hours"),
        "seed": sim_meta.get("seed"),
        "mechanism": mechanism_name,
        "phases": sim_meta.get("phases", []),
        "n_events": sim_meta.get("n_events", len(sim.get("events", []))),
        "n_bids": sim_meta.get("n_bids", len(sim.get("bids", []))),
        "n_satellites": sup_meta.get("n_satellites", len(supply.get("satellites", []))),
        "n_constellations": sup_meta.get("n_constellations", 0),
        "n_access_windows": sup_meta.get("n_access_windows", len(supply.get("access_windows", []))),
        "n_allocations": len(allocations_dicts),
        "n_scheduled": sum(1 for a in allocations_dicts if a.get("status") == "SCHEDULED"),
        "n_dropped":   sum(1 for a in allocations_dicts if a.get("status") == "DROPPED"),
        # Lifecycle aggregates — terminal states from the delivery pipeline.
        "n_delivered": sum(1 for a in allocations_dicts if _final(a) == "DELIVERED"),
        "n_processing_failed": sum(1 for a in allocations_dicts if _final(a) == "PROCESSING_FAILED"),
        "n_deadline_missed": sum(1 for a in allocations_dicts if _final(a) == "DEADLINE_MISSED"),
        "min_elevation_deg": sup_meta.get("min_elevation_deg"),
        "total_welfare": welfare,
        "drop_rate": drop,
        "delivery_rate": delivery_rate_value,
        "processing_success_rate": processing_rate_value,
    }


def _assemble(
    sim: Dict[str, Any],
    supply: Dict[str, Any],
    allocation_objs,
    *,
    mechanism_name: str,
    seed: int,
    constellations: Iterable[Constellation],
) -> Dict[str, Any]:
    welfare = total_welfare(allocation_objs)
    drop = drop_rate(allocation_objs)
    # Run the delivery pipeline on the raw allocation list — produces
    # one dict per allocation with the lifecycle sub-dict attached.
    alloc_dicts = apply_delivery_pipeline(
        allocation_objs,
        bids=sim.get("bids", []),
        access_windows=supply.get("access_windows", []),
        satellites=supply.get("satellites", []),
        constellations=constellations,
        seed=seed,
    )
    return {
        "meta": _meta(
            sim, supply, alloc_dicts,
            mechanism_name=mechanism_name,
            welfare=welfare,
            drop=drop,
            delivery_rate_value=delivery_rate(alloc_dicts),
            processing_rate_value=processing_success_rate_observed(alloc_dicts),
        ),
        "locations":      sim.get("locations", {}),
        "stakeholders":   sim.get("stakeholders", []),
        "sensor_requirements": sim.get("sensor_requirements", {}),
        "constellations": supply.get("constellations", []),
        "satellites":     supply.get("satellites", []),
        "events":         sim.get("events", []),
        "bids":           sim.get("bids", []),
        "access_windows": supply.get("access_windows", []),
        "allocations":    alloc_dicts,
    }


def build_full_scenario(
    *,
    seed: int = 42,
    duration_hours: float = 168.0,
    mechanism: Union[str, Mechanism] = DEFAULT_MECHANISM,
    cache_dir: Path,
    constellations: Iterable[Constellation] = CONSTELLATIONS,
    t0: Optional[datetime] = None,
    min_elevation_deg: float = 20.0,
    max_age_hours: float = 24.0,
) -> Dict[str, Any]:
    """Production path: build demand, fetch TLEs, compute supply, allocate."""
    t0 = t0 or DEFAULT_T0
    sim = build_sim(seed=seed, duration_hours=duration_hours, t0=t0)
    targets = targets_from_locations(sim["locations"])
    supply = build_supply(
        list(constellations), targets, t0, duration_hours,
        cache_dir=Path(cache_dir),
        seed=seed,
        min_elevation_deg=min_elevation_deg,
        max_age_hours=max_age_hours,
    )
    allocations = allocate(
        sim["bids"], supply["access_windows"],
        t0=supply["meta"]["t0_iso"],
        mechanism=mechanism,
        satellites=supply["satellites"],
    )
    mech_name = mechanism if isinstance(mechanism, str) else mechanism.name
    return _assemble(
        sim, supply, allocations,
        mechanism_name=mech_name,
        seed=seed,
        constellations=constellations,
    )


def build_full_scenario_offline(
    satellites: List[Dict[str, Any]],
    *,
    seed: int = 42,
    duration_hours: float = 168.0,
    mechanism: Union[str, Mechanism] = DEFAULT_MECHANISM,
    constellations: Iterable[Constellation] = (),
    t0: Optional[datetime] = None,
    min_elevation_deg: float = 20.0,
) -> Dict[str, Any]:
    """Offline path: same shape as ``build_full_scenario`` but with
    pre-built satellite dicts. No network is touched.
    """
    t0 = t0 or DEFAULT_T0
    sim = build_sim(seed=seed, duration_hours=duration_hours, t0=t0)
    targets = targets_from_locations(sim["locations"])
    supply = build_supply_from_satellites(
        satellites, targets, t0, duration_hours,
        constellations=constellations,
        seed=seed,
        min_elevation_deg=min_elevation_deg,
    )
    allocations = allocate(
        sim["bids"], supply["access_windows"],
        t0=supply["meta"]["t0_iso"],
        mechanism=mechanism,
        satellites=satellites,
    )
    mech_name = mechanism if isinstance(mechanism, str) else mechanism.name
    # constellations may be an empty tuple in offline tests; in that case
    # the delivery pipeline falls back to default per-vendor latencies.
    return _assemble(
        sim, supply, allocations,
        mechanism_name=mech_name,
        seed=seed,
        constellations=constellations,
    )
