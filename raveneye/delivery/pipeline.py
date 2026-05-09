"""Allocation-to-delivery lifecycle.

Mechanism layer answers "which window serves which bid?". The delivery
pipeline answers "what happens after the satellite takes the shot?":

    SCHEDULED            (mechanism decision)
        │
        ▼  collected_iso = window.end_iso
    COLLECTED            (image data is on the satellite)
        │
        ▼  + processing_latency_min (downlink + processing pipeline)
    PROCESSED  (or PROCESSING_FAILED, with seeded probability)
        │
        ▼  + delivery_latency_min (network/portal handoff)
    DELIVERED  (or DEADLINE_MISSED if delivered_iso > bid.ltiov_iso)

The pipeline is **fully deterministic** given a seed: it draws a single
``random.Random(seed + hash(allocation_id))`` per allocation so a
re-run with the same seed produces byte-identical outcomes.

Effective per-allocation success rate is the constellation's published
``processing_success_rate`` modulated by the access window's quality
score:

    effective = base × (0.5 + 0.5 × quality_score)

— a sat-window pair with q=1.0 gets the full base rate; q=0.0 gets half.
This ties supply quality directly to delivery outcomes, so an SSI
mechanism (which routes to higher-quality windows) shows a measurable
delivery-rate uplift over greedy.
"""
from __future__ import annotations

import hashlib
import logging
import random
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)


LIFECYCLE_STATUSES = (
    "DROPPED",
    "DELIVERED",
    "DEADLINE_MISSED",
    "PROCESSING_FAILED",
)


def _parse(iso: Optional[str]) -> Optional[datetime]:
    if not iso:
        return None
    return datetime.fromisoformat(iso)


def _fmt(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.replace(microsecond=0).isoformat()


def _alloc_rng(seed: int, allocation_id: str) -> random.Random:
    """Per-allocation RNG seeded reproducibly off the master seed."""
    h = hashlib.sha256(f"{seed}:{allocation_id}".encode("utf-8")).digest()
    salt = int.from_bytes(h[:8], "big")
    return random.Random(salt)


def _index_satellites(satellites: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {s["sat_id"]: s for s in satellites}


def _index_constellations(constellations: Iterable[Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for c in constellations:
        if hasattr(c, "constellation_id"):
            out[c.constellation_id] = c
        elif isinstance(c, dict):
            out[c["constellation_id"]] = c
    return out


def _resolve_constellation_params(
    sat: Optional[Dict[str, Any]],
    con_index: Dict[str, Any],
) -> Dict[str, float]:
    """Pull processing/delivery parameters from the satellite's
    constellation, falling back to sensible defaults if metadata is
    missing.
    """
    defaults = {
        "processing_latency_min": 60.0,
        "delivery_latency_min": 30.0,
        "processing_success_rate": 0.85,
    }
    if sat is None:
        return defaults
    con_id = sat.get("constellation_id")
    con = con_index.get(con_id)
    if con is None:
        return defaults
    if hasattr(con, "processing_latency_min"):
        return {
            "processing_latency_min": float(con.processing_latency_min),
            "delivery_latency_min": float(con.delivery_latency_min),
            "processing_success_rate": float(con.processing_success_rate),
        }
    # dict (pre-converted via to_dict)
    return {
        "processing_latency_min": float(con.get("processing_latency_min", defaults["processing_latency_min"])),
        "delivery_latency_min": float(con.get("delivery_latency_min", defaults["delivery_latency_min"])),
        "processing_success_rate": float(con.get("processing_success_rate", defaults["processing_success_rate"])),
    }


def _lifecycle_for(
    allocation_dict: Dict[str, Any],
    bid_dict: Dict[str, Any],
    window_dict: Optional[Dict[str, Any]],
    sat_dict: Optional[Dict[str, Any]],
    con_index: Dict[str, Any],
    *,
    seed: int,
) -> Dict[str, Any]:
    """Compute the lifecycle for one allocation. Returns the lifecycle
    dict; never mutates inputs.
    """
    if allocation_dict.get("status") == "DROPPED" or window_dict is None:
        return {
            "collected_iso": None,
            "processing_latency_min": None,
            "processing_complete_iso": None,
            "processed": False,
            "delivery_latency_min": None,
            "delivered_iso": None,
            "delivered": False,
            "deadline_missed": False,
            "final_status": "DROPPED",
        }

    params = _resolve_constellation_params(sat_dict, con_index)

    collected = _parse(window_dict.get("end_iso"))
    if collected is None:
        # Defensive: shouldn't happen, but degrade gracefully
        return {
            "collected_iso": None,
            "processing_latency_min": params["processing_latency_min"],
            "processing_complete_iso": None,
            "processed": False,
            "delivery_latency_min": params["delivery_latency_min"],
            "delivered_iso": None,
            "delivered": False,
            "deadline_missed": False,
            "final_status": "PROCESSING_FAILED",
        }

    processing_complete = collected + timedelta(minutes=params["processing_latency_min"])
    delivered_dt = processing_complete + timedelta(minutes=params["delivery_latency_min"])

    # Processing success roll, modulated by window quality
    rng = _alloc_rng(seed, allocation_dict["allocation_id"])
    q = float(window_dict.get("quality_score", 0.5) or 0.0)
    base = float(params["processing_success_rate"])
    effective = base * (0.5 + 0.5 * max(0.0, min(1.0, q)))
    processing_succeeded = rng.random() < effective

    # Deadline check (only meaningful if processing succeeded)
    ltiov = _parse(bid_dict.get("ltiov_iso"))
    deadline_missed = False
    if processing_succeeded and ltiov is not None:
        deadline_missed = delivered_dt > ltiov

    if not processing_succeeded:
        final = "PROCESSING_FAILED"
        delivered_dt_out: Optional[datetime] = None
        delivered_flag = False
    elif deadline_missed:
        final = "DEADLINE_MISSED"
        delivered_dt_out = delivered_dt
        delivered_flag = False
    else:
        final = "DELIVERED"
        delivered_dt_out = delivered_dt
        delivered_flag = True

    return {
        "collected_iso": _fmt(collected),
        "processing_latency_min": round(params["processing_latency_min"], 1),
        "processing_complete_iso": _fmt(processing_complete) if processing_succeeded else None,
        "processed": processing_succeeded,
        "delivery_latency_min": round(params["delivery_latency_min"], 1),
        "delivered_iso": _fmt(delivered_dt_out),
        "delivered": delivered_flag,
        "deadline_missed": deadline_missed,
        "final_status": final,
    }


def apply_delivery_pipeline(
    allocations: List[Any],
    bids: List[Dict[str, Any]],
    access_windows: List[Dict[str, Any]],
    satellites: Iterable[Dict[str, Any]],
    constellations: Iterable[Any],
    *,
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """Compute the lifecycle for each allocation; return allocation
    dicts (not Allocation objects) with the new ``lifecycle`` sub-dict.

    Why dicts: this is the boundary where we cross from in-process
    objects to scenario JSON. The scenario builder calls this once and
    serializes the result.
    """
    bid_by_id = {b["bid_id"]: b for b in bids}
    win_by_id = {w["window_id"]: w for w in access_windows}
    sat_by_id = _index_satellites(satellites)
    con_by_id = _index_constellations(constellations)

    out: List[Dict[str, Any]] = []
    for a in allocations:
        # Allocation may be a dataclass or a dict (post to_dict()). Normalize.
        a_dict = a.to_dict() if hasattr(a, "to_dict") else dict(a)
        bid = bid_by_id.get(a_dict["bid_id"], {})
        window = win_by_id.get(a_dict.get("window_id")) if a_dict.get("window_id") else None
        sat = sat_by_id.get(a_dict.get("sat_id")) if a_dict.get("sat_id") else None
        a_dict["lifecycle"] = _lifecycle_for(
            a_dict, bid, window, sat, con_by_id, seed=seed
        )
        out.append(a_dict)
    return out


# ----------------------------------------------------------------------
# Aggregate metrics for the meta block
# ----------------------------------------------------------------------

def delivery_rate(allocation_dicts: List[Dict[str, Any]]) -> float:
    """Fraction of allocations whose final_status is DELIVERED."""
    if not allocation_dicts:
        return 0.0
    n_delivered = sum(
        1 for a in allocation_dicts
        if a.get("lifecycle", {}).get("final_status") == "DELIVERED"
    )
    return round(n_delivered / len(allocation_dicts), 4)


def processing_success_rate_observed(allocation_dicts: List[Dict[str, Any]]) -> float:
    """Fraction of *collected* allocations (status==SCHEDULED) that
    successfully processed. None of the DROPPED rows count toward the
    denominator.
    """
    collected = [a for a in allocation_dicts if a.get("status") == "SCHEDULED"]
    if not collected:
        return 0.0
    n_processed = sum(
        1 for a in collected
        if a.get("lifecycle", {}).get("processed")
    )
    return round(n_processed / len(collected), 4)


# ----------------------------------------------------------------------
# Viewer-side helper (Python equivalent of what the JS will compute per
# render frame)
# ----------------------------------------------------------------------

def lifecycle_state_at(allocation_dict: Dict[str, Any], window_dict: Optional[Dict[str, Any]],
                       t_iso: str) -> str:
    """At wall-clock ``t_iso``, what stage is this allocation in?

    Returned values:
        PENDING       — t < window.start
        COLLECTING    — window.start ≤ t < window.end
        PROCESSING    — window.end ≤ t < processing_complete_iso
        IN_TRANSIT    — processing_complete_iso ≤ t < delivered_iso
        DELIVERED     — t ≥ delivered_iso (and deadline not missed and processed)
        DEADLINE_MISSED — terminal: delivered after LTIOV
        PROCESSING_FAILED — terminal: collection happened, processing failed
        DROPPED       — terminal: never had a window

    Tests + viewer both call this so Python and JS agree on edge cases.
    """
    lc = allocation_dict.get("lifecycle") or {}
    final = lc.get("final_status", allocation_dict.get("status", "DROPPED"))
    if final == "DROPPED":
        return "DROPPED"

    t = _parse(t_iso)
    if t is None:
        return final

    if window_dict is None:
        return final

    start = _parse(window_dict.get("start_iso"))
    end = _parse(window_dict.get("end_iso"))
    proc_done = _parse(lc.get("processing_complete_iso"))
    delivered = _parse(lc.get("delivered_iso"))

    if start is not None and t < start:
        return "PENDING"
    if end is not None and t < end:
        return "COLLECTING"
    if proc_done is not None and t < proc_done:
        return "PROCESSING"
    if delivered is not None and t < delivered:
        return "IN_TRANSIT"
    return final
