"""Seed determinism and pinned invariants for the canonical seed=42 run."""

from __future__ import annotations

import json

from raveneye.sim import build_sim


def test_same_seed_identical_output():
    a = json.dumps(build_sim(seed=42), sort_keys=True)
    b = json.dumps(build_sim(seed=42), sort_keys=True)
    assert a == b


def test_different_seeds_differ():
    a = json.dumps(build_sim(seed=42), sort_keys=True)
    b = json.dumps(build_sim(seed=7), sort_keys=True)
    assert a != b


# Pinned invariants for seed=42, duration=168h. Changes to BASE_RATES,
# SCRIPTED_BEATS, or the stochastic sampler will likely shift these; update
# the pins deliberately when that happens.
_PINNED_N_EVENTS = 154
_PINNED_N_BIDS = 616
_TOLERANCE = 2


def test_pinned_counts_seed42():
    s = build_sim(seed=42)
    assert abs(s["meta"]["n_events"] - _PINNED_N_EVENTS) <= _TOLERANCE
    assert abs(s["meta"]["n_bids"] - _PINNED_N_BIDS) <= _TOLERANCE


def test_first_scripted_event_is_scr000_diplomatic():
    s = build_sim(seed=42)
    scripted = [e for e in s["events"] if e["scripted"]]
    scripted.sort(key=lambda e: e["event_id"])
    assert scripted[0]["event_id"] == "SCR-000"
    assert scripted[0]["event_type"] == "DIPLOMATIC_STATUS_CHANGE"
