"""Seed determinism + pinned invariants for seed=42."""
from __future__ import annotations

import json

from raveneye.sim import EventType, build_sim


def test_same_seed_identical_output():
    a = build_sim(seed=42)
    b = build_sim(seed=42)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_different_seeds_diverge():
    a = build_sim(seed=42)
    b = build_sim(seed=43)
    assert json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True)


def test_seed42_pinned_invariants():
    s = build_sim(seed=42)
    assert s["meta"]["n_events"] == 176 or abs(s["meta"]["n_events"] - 176) <= 2
    assert s["meta"]["n_bids"] == 704 or abs(s["meta"]["n_bids"] - 704) <= 8

    first = s["events"][0]
    assert first["event_id"] == "SCR-000"
    assert first["event_type"] == EventType.DIPLOMATIC_STATUS_CHANGE.value
