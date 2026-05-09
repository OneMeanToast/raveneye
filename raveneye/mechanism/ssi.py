"""Sequential Single-Item (SSI) auction.

The first mechanism in v0.2 with real auction content. Bids still sort
by priority desc, but each bid auctions among **all** matching available
windows and takes the one that maximizes welfare for that bid:

    welfare(bid, window) = bid.priority_score × window.quality_score

A window matching a bid poorly (low elevation, bad sun, high off-nadir)
loses to a higher-quality window even for a later, lower-priority bid —
which is what greedy can't do, since greedy locks in the *earliest*
window without looking at quality.

Determinism: sorted inputs + deterministic argmax tiebreakers
(``window_id`` lexicographic ascending) + no randomness.
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


class SequentialSingleItemMechanism:
    """Sequential single-item auction. Welfare = priority × quality."""

    name = "ssi"

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
            best: Optional[Dict[str, Any]] = None
            best_welfare = -1.0
            for w in sorted_windows:
                if w["window_id"] in taken:
                    continue
                bands = sat_bands.get(w["sat_id"]) if sat_bands else None
                if not match_bid_to_window(bid, w, sat_bands=bands):
                    continue
                welfare = float(bid.get("priority_score", 0.0)) * float(
                    w.get("quality_score", 0.0)
                )
                # Strict > so the first feasible window wins ties; with
                # sorted_windows that's the lexicographically smallest
                # window_id, which is deterministic.
                if welfare > best_welfare:
                    best = w
                    best_welfare = welfare

            alloc_id = f"ALLOC-{i:05d}"
            if best is None:
                out.append(make_dropped(
                    bid,
                    mechanism=self.name,
                    decision_t_iso=decision_t,
                    allocation_id=alloc_id,
                ))
            else:
                taken.add(best["window_id"])
                out.append(make_scheduled(
                    bid, best,
                    mechanism=self.name,
                    decision_t_iso=decision_t,
                    notes=(
                        f"welfare-maximizing window (welfare={best_welfare:.3f}, "
                        f"q={best.get('quality_score')}, rank {i + 1} of {len(sorted_bids)})"
                    ),
                    allocation_id=alloc_id,
                ))
        return out


_INSTANCE: Mechanism = SequentialSingleItemMechanism()


def allocate(*args, **kwargs):
    return _INSTANCE.allocate(*args, **kwargs)
