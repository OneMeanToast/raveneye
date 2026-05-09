"""RavenEye mechanism (allocation) layer.

v0.2 — greedy priority + sequential single-item auction. The first two
reference mechanisms; CBBA, VCG, ILP and friends are explicitly v0.3+.
"""
from .base import (
    ALLOCATION_STATUS,
    Allocation,
    Mechanism,
    bands_satisfy,
    index_satellite_bands,
    match_bid_to_window,
    sort_bids_by_priority,
    sort_windows_by_start,
)
from .build import allocate, drop_rate, get_mechanism, total_welfare
from .greedy import GreedyPriorityMechanism
from .ssi import SequentialSingleItemMechanism

__all__ = [
    "ALLOCATION_STATUS",
    "Allocation",
    "GreedyPriorityMechanism",
    "Mechanism",
    "SequentialSingleItemMechanism",
    "allocate",
    "bands_satisfy",
    "drop_rate",
    "get_mechanism",
    "index_satellite_bands",
    "match_bid_to_window",
    "sort_bids_by_priority",
    "sort_windows_by_start",
    "total_welfare",
]
