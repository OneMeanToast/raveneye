"""Mechanism dispatcher: ``allocate(bids, access_windows, t0, mechanism)``.

The single entry point for the unified scenario builder (v0.2 phase J).
Accepts a string name (e.g. ``"greedy"``, ``"ssi"``) or a Mechanism
instance.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Union

from .base import Allocation, Mechanism
from .greedy import GreedyPriorityMechanism
from .ssi import SequentialSingleItemMechanism


_REGISTRY: Dict[str, Mechanism] = {
    "greedy": GreedyPriorityMechanism(),
    "greedy_priority": GreedyPriorityMechanism(),
    "ssi": SequentialSingleItemMechanism(),
}


def get_mechanism(spec: Union[str, Mechanism]) -> Mechanism:
    """Resolve a mechanism by name or pass through a Mechanism instance."""
    if isinstance(spec, str):
        try:
            return _REGISTRY[spec]
        except KeyError as e:
            known = ", ".join(sorted(_REGISTRY.keys()))
            raise ValueError(f"unknown mechanism {spec!r}; known: {known}") from e
    return spec


def allocate(
    bids: List[Dict[str, Any]],
    access_windows: List[Dict[str, Any]],
    t0: str,
    mechanism: Union[str, Mechanism] = "greedy",
    *,
    satellites: Iterable[Dict[str, Any]] = (),
    now: Optional[str] = None,
) -> List[Allocation]:
    """Run a mechanism over (bids, access_windows) and return allocations.

    One ``Allocation`` is emitted per bid. Bids that no mechanism can
    match get ``status="DROPPED"`` and ``window_id=None``.
    """
    return get_mechanism(mechanism).allocate(
        bids, access_windows, t0, satellites=satellites, now=now
    )


def total_welfare(allocations: List[Allocation]) -> float:
    """Sum of ``priority_score × quality_score`` across SCHEDULED rows.

    The standard comparison metric for mechanisms in v0.2: SSI must
    achieve ≥ greedy's total_welfare on any given scenario.
    """
    return round(
        sum(a.welfare for a in allocations if a.welfare is not None),
        4,
    )


def drop_rate(allocations: List[Allocation]) -> float:
    """Fraction of allocations whose status is DROPPED."""
    if not allocations:
        return 0.0
    n_dropped = sum(1 for a in allocations if a.status == "DROPPED")
    return round(n_dropped / len(allocations), 4)
