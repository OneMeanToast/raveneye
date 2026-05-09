"""Unified scenario builder.

Joins the v0.1 demand layer (events + bids) with the v0.2 supply layer
(satellites + access_windows) and the v0.2 mechanism layer (allocations)
into a single Scenario JSON object matching ``raveneyebuildspec.md`` §3.1.
"""
from .build import (
    DEFAULT_MECHANISM,
    build_full_scenario,
    build_full_scenario_offline,
)

__all__ = [
    "DEFAULT_MECHANISM",
    "build_full_scenario",
    "build_full_scenario_offline",
]
