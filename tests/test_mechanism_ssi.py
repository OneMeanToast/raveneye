"""K5: SSI auction tests.

Same handcrafted fixture as the greedy tests. Goal: SSI must produce a
*different* allocation than greedy when window quality varies, and its
total welfare must be ≥ greedy's. SSI is allowed to lose nothing in this
fixture; it should win.

Reasoning for the fixture:
  Greedy gives BID-0 (top priority) the earliest window AW-00 (q=0.40).
  SSI lets BID-0 see all 5 windows, picks AW-04 (q=0.95), then BID-1
  picks the next-best feasible (AW-01, q=0.85, ends before its 14:30
  deadline), then BID-2 picks the next (AW-00 or AW-02 — whichever has
  higher quality and fits).
  Net welfare uplift comes from giving the highest-priority bid the
  highest-quality window.
"""
from __future__ import annotations

import pytest

from raveneye.mechanism import (
    SequentialSingleItemMechanism,
    allocate,
    total_welfare,
)

from .test_mechanism_greedy import fixture_3b_5w  # noqa: F401  (pytest fixture import)


T0 = "2026-04-13T12:00:00+00:00"


def test_ssi_pairs_top_bid_with_top_quality_window(fixture_3b_5w):
    bids, windows, sats = fixture_3b_5w
    allocs = allocate(bids, windows, T0, "ssi", satellites=sats)
    by_bid = {a.bid_id: a for a in allocs}
    # BID-0 has priority 10 → SSI gives it the highest-quality window (AW-04, q=0.95)
    assert by_bid["BID-00000"].window_id == "AW-00004"
    assert by_bid["BID-00000"].status == "SCHEDULED"
    # BID-1 (priority 6, deadline 14:30) → AW-01 (q=0.85, ends 12:55) wins;
    # AW-04 already taken anyway. AW-02 (q=0.55) loses to AW-01 (q=0.85).
    assert by_bid["BID-00001"].window_id == "AW-00001"
    # BID-2 (priority 3) auctions the remaining {AW-00, AW-02, AW-03}
    # max q = 0.55 → AW-00002
    assert by_bid["BID-00002"].window_id == "AW-00002"


def test_ssi_total_welfare_beats_greedy(fixture_3b_5w):
    """The whole point: welfare(SSI) >= welfare(greedy), strictly here."""
    bids, windows, sats = fixture_3b_5w
    g = allocate(bids, windows, T0, "greedy", satellites=sats)
    s = allocate(bids, windows, T0, "ssi", satellites=sats)
    w_g = total_welfare(g)
    w_s = total_welfare(s)
    # Greedy: 10*0.40 + 6*0.85 + 3*0.55 = 10.75
    # SSI:    10*0.95 + 6*0.85 + 3*0.55 = 16.25
    assert w_s >= w_g, f"SSI welfare {w_s} should be >= greedy {w_g}"
    assert w_s > w_g, "in this fixture SSI should strictly beat greedy"
    assert w_s == pytest.approx(16.25, abs=1e-3)


def test_ssi_and_greedy_disagree_on_at_least_one_bid(fixture_3b_5w):
    bids, windows, sats = fixture_3b_5w
    g = {a.bid_id: a.window_id for a in allocate(bids, windows, T0, "greedy", satellites=sats)}
    s = {a.bid_id: a.window_id for a in allocate(bids, windows, T0, "ssi", satellites=sats)}
    diffs = {k for k in g if g[k] != s[k]}
    assert len(diffs) >= 1


def test_ssi_is_deterministic(fixture_3b_5w):
    bids, windows, sats = fixture_3b_5w
    a = [x.to_dict() for x in allocate(bids, windows, T0, "ssi", satellites=sats)]
    b = [x.to_dict() for x in allocate(bids, windows, T0, "ssi", satellites=sats)]
    assert a == b


def test_ssi_drops_bids_with_no_feasible_window():
    from .test_mechanism_greedy import _bid, _window, _sat
    bids = [
        _bid("BID-00000", "siri_island", 10.0, "2026-04-13T13:00:00+00:00"),
        _bid("BID-00001", "ras_tanura", 5.0, "2026-04-13T13:00:00+00:00"),
    ]
    windows = [_window("AW-0", "Sat-A", "siri_island",
                       "2026-04-13T12:30:00+00:00", "2026-04-13T12:35:00+00:00", 0.5)]
    sats = [_sat("Sat-A")]
    allocs = allocate(bids, windows, T0, "ssi", satellites=sats)
    by_bid = {a.bid_id: a for a in allocs}
    assert by_bid["BID-00001"].status == "DROPPED"
    assert by_bid["BID-00000"].status == "SCHEDULED"


def test_ssi_emits_allocation_per_bid(fixture_3b_5w):
    bids, windows, sats = fixture_3b_5w
    allocs = allocate(bids, windows, T0, "ssi", satellites=sats)
    assert {a.bid_id for a in allocs} == {b["bid_id"] for b in bids}


def test_mechanism_protocol_satisfied():
    """SSI and Greedy classes both expose the `name` attribute and the
    `allocate(...)` signature shape that the Mechanism Protocol expects."""
    m = SequentialSingleItemMechanism()
    assert isinstance(m.name, str)
    assert callable(m.allocate)
