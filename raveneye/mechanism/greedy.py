"""Greedy priority-first allocation.

The baseline. This is what ops centers actually do when there's no
formal mechanism: highest-priority bid takes the earliest available
window that fits its target and deadline. More sophisticated mechanisms
must beat this on welfare metrics to justify their complexity.

Algorithm:
    1. Sort bids by priority descending (stable, ``bid_id`` tiebreak).
    2. Sort windows by start_iso ascending (so "earliest available" is
       a single linear scan).
    3. For each bid:
         scan windows in order, allocate the first that matches and is
         not yet taken. Otherwise emit a DROPPED row.

Determinism: sorted inputs + deterministic tiebreakers + no randomness
inside the loop. Same scenario JSON → byte-identical allocation list.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .base import (
    Allocation,
    Mechanism,
    index_satellite_bands,
    make_dropped,
    make_scheduled,
    match_bid_to_window,
    sort_bids_by_priority,
    sort_windows_by_start,
)


class GreedyPriorityMechanism:
    """Concrete ``Mechanism``: priority-first, earliest-available window."""

    name = "greedy_priority"

    def allocate(
        self,
        bids: List[Dict[str, Any]],
        access_windows: List[Dict[str, Any]],
        t0: str,
        *,
        satellites: Iterable[Dict[str, Any]] = (),
        now: Optional[str] = None,
    ) -> List[Allocation]:
        decision_t = now or t0
        sat_bands = index_satellite_bands(satellites)

        sorted_bids = sort_bids_by_priority(bids)
        sorted_windows = sort_windows_by_start(access_windows)
        taken: set = set()
        out: List[Allocation] = []

        for i, bid in enumerate(sorted_bids):
            chosen: Optional[Dict[str, Any]] = None
            for w in sorted_windows:
                if w["window_id"] in taken:
                    continue
                bands = sat_bands.get(w["sat_id"]) if sat_bands else None
                if not match_bid_to_window(bid, w, sat_bands=bands):
                    continue
                chosen = w
                break

            alloc_id = f"ALLOC-{i:05d}"
            if chosen is None:
                out.append(make_dropped(
                    bid,
                    mechanism=self.name,
                    decision_t_iso=decision_t,
                    allocation_id=alloc_id,
                ))
            else:
                taken.add(chosen["window_id"])
                out.append(make_scheduled(
                    bid, chosen,
                    mechanism=self.name,
                    decision_t_iso=decision_t,
                    notes=f"earliest feasible window (rank {i + 1} of {len(sorted_bids)})",
                    allocation_id=alloc_id,
                ))
        return out


# Module-level instance is fine — the mechanism is stateless.
_INSTANCE: Mechanism = GreedyPriorityMechanism()


def allocate(*args, **kwargs):
    return _INSTANCE.allocate(*args, **kwargs)
