"""Mechanism-layer base types: Allocation, Mechanism Protocol, matcher.

A *mechanism* consumes bids and access windows and produces allocations —
one per bid. Mechanisms are stateless: ``allocate`` is a pure function of
its inputs.

Every bid produces exactly one ``Allocation`` row, even if no window
matched: the dropped row carries ``status="DROPPED"`` and
``window_id=None``. This invariant makes drop-rate metrics and the
viewer's "what got dropped" panel trivial — no diffs against the bid list
required.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Protocol


# Status enumeration. v0.2 mechanisms emit SCHEDULED or DROPPED;
# COLLECTED and DEADLINE_MISSED are reserved for future runtime simulation
# of actual collection execution against the schedule.
ALLOCATION_STATUS = ("SCHEDULED", "DROPPED", "COLLECTED", "DEADLINE_MISSED")


@dataclass
class Allocation:
    allocation_id: str
    bid_id: str
    window_id: Optional[str]
    mechanism: str
    status: str
    priority_score: float
    decision_t_iso: str
    notes: str = ""
    sat_id: Optional[str] = None
    quality_score: Optional[float] = None
    welfare: Optional[float] = None  # priority_score × quality_score, or None for DROPPED

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class Mechanism(Protocol):
    """A mechanism allocates bids to access windows.

    Implementations must be pure: same inputs → identical outputs (modulo
    Python set/dict iteration ordering, which means callers should pass
    pre-sorted inputs if they need byte-equal output across processes).
    """

    name: str

    def allocate(
        self,
        bids: List[Dict[str, Any]],
        access_windows: List[Dict[str, Any]],
        t0: str,
        *,
        satellites: Iterable[Dict[str, Any]] = (),
        now: Optional[str] = None,
    ) -> List[Allocation]:
        ...


# ----------------------------------------------------------------------
# Compatibility helpers
# ----------------------------------------------------------------------

# Map a bid's required band string to the set of satellite spectral bands
# that satisfy it. The bid's "band" comes from
# raveneye.sim.locations.SENSOR_REQUIREMENTS.
#
# Rules:
#   "EO_PAN"     → satellite must have "PAN".
#   "EO_MS"      → satellite must have "MS".
#   "EO_MS+TIR"  → satellite must have "MS" (TIR is informational; v0.2
#                  doesn't model TIR sensors).
#   "SAR_X"      → satellite must have "SAR_X".
_BAND_REQUIRES: Dict[str, set] = {
    "EO_PAN":    {"PAN"},
    "EO_MS":     {"MS"},
    "EO_MS+TIR": {"MS"},
    "SAR_X":     {"SAR_X"},
}


def _bid_target_id(bid: Dict[str, Any]) -> Optional[str]:
    return bid.get("target_location_id") or bid.get("target_id")


def bands_satisfy(required_band: str, sat_bands: Iterable[str]) -> bool:
    """Does a satellite with ``sat_bands`` satisfy a bid asking for
    ``required_band``? Returns True when no required_band is specified
    (caller chose to skip the band check).
    """
    if not required_band:
        return True
    have = set(sat_bands)
    needed = _BAND_REQUIRES.get(required_band, {required_band})
    return bool(needed & have)


def match_bid_to_window(
    bid: Dict[str, Any],
    window: Dict[str, Any],
    *,
    sat_bands: Optional[Iterable[str]] = None,
    target_tolerance_deg: float = 0.005,
) -> bool:
    """True iff this window can satisfy this bid.

    Three checks:
      1. Target match — by ``target_id`` when both sides carry one,
         otherwise by lat/lon proximity (tolerance ≈ 555 m at default).
      2. Deadline — window must end on or before the bid's LTIOV.
      3. Sensor band — when ``sat_bands`` is provided, at least one
         satellite band must satisfy the bid's required band.
    """
    bid_tid = _bid_target_id(bid)
    win_tid = window.get("target_id")
    if bid_tid is not None and win_tid is not None:
        if bid_tid != win_tid:
            return False
    else:
        try:
            dlat = abs(float(bid.get("target_lat", 0.0)) - float(window.get("target_lat", 0.0)))
            dlon = abs(float(bid.get("target_lon", 0.0)) - float(window.get("target_lon", 0.0)))
        except (TypeError, ValueError):
            return False
        if dlat > target_tolerance_deg or dlon > target_tolerance_deg:
            return False

    bid_ltiov = bid.get("ltiov_iso")
    win_end = window.get("end_iso")
    if bid_ltiov and win_end and win_end > bid_ltiov:
        return False

    if sat_bands is not None:
        required = bid.get("sensor_requirement", {}).get("band", "")
        if not bands_satisfy(required, sat_bands):
            return False

    return True


# ----------------------------------------------------------------------
# Convenience indexes for mechanisms
# ----------------------------------------------------------------------

def index_satellite_bands(satellites: Iterable[Dict[str, Any]]) -> Dict[str, List[str]]:
    """sat_id → list of spectral bands. Used by mechanisms to do band
    compatibility checks per (sat, bid) pair without re-scanning the sat
    list.
    """
    return {s["sat_id"]: list(s.get("spectral_bands", [])) for s in satellites}


def sort_bids_by_priority(bids: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Stable sort: priority desc, with ``bid_id`` as deterministic
    tiebreaker."""
    return sorted(bids, key=lambda b: (-float(b.get("priority_score", 0.0)), b.get("bid_id", "")))


def sort_windows_by_start(windows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(windows, key=lambda w: (w.get("start_iso", ""), w.get("window_id", "")))


def make_dropped(
    bid: Dict[str, Any],
    *,
    mechanism: str,
    decision_t_iso: str,
    notes: str = "",
    allocation_id: str = "",
) -> Allocation:
    return Allocation(
        allocation_id=allocation_id,
        bid_id=bid["bid_id"],
        window_id=None,
        mechanism=mechanism,
        status="DROPPED",
        priority_score=float(bid.get("priority_score", 0.0)),
        decision_t_iso=decision_t_iso,
        notes=notes or "no feasible window matched (target/deadline/band)",
    )


def make_scheduled(
    bid: Dict[str, Any],
    window: Dict[str, Any],
    *,
    mechanism: str,
    decision_t_iso: str,
    notes: str = "",
    allocation_id: str = "",
) -> Allocation:
    p = float(bid.get("priority_score", 0.0))
    q = float(window.get("quality_score", 0.0))
    return Allocation(
        allocation_id=allocation_id,
        bid_id=bid["bid_id"],
        window_id=window["window_id"],
        mechanism=mechanism,
        status="SCHEDULED",
        priority_score=p,
        decision_t_iso=decision_t_iso,
        notes=notes,
        sat_id=window.get("sat_id"),
        quality_score=q,
        welfare=round(p * q, 4),
    )
