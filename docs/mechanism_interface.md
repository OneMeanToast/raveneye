# Mechanism interface

The mechanism layer matches **bids** to **access windows**. v0.2 ships
two reference mechanisms (`GreedyPriorityMechanism`,
`SequentialSingleItemMechanism`) and a small protocol so you can drop in
your own without touching demand or supply.

The bid schema and the bid → mechanism contract are documented in
`docs/bidding_interface.md`. This file covers the mechanism *side* of
the interface: what your `allocate()` is handed, what it must return,
and how to plug it into the unified scenario builder.

## The Allocation object

One `Allocation` per bid — every bid produces exactly one row, even if
no window matched (status `DROPPED`, `window_id = null`). This invariant
makes drop-rate metrics, the viewer's "what got dropped" panel, and any
mechanism diff trivial — no diffing against the bid list required.

```python
@dataclass
class Allocation:
    allocation_id: str             # ALLOC-NNNNN
    bid_id: str                    # which bid this row resolves
    window_id: Optional[str]       # AW-NNNNN, or None for DROPPED
    mechanism: str                 # e.g. "greedy_priority", "ssi"
    status: str                    # SCHEDULED | DROPPED | COLLECTED | DEADLINE_MISSED
    priority_score: float          # echoed from bid
    decision_t_iso: str            # when the mechanism made this decision
    notes: str = ""                # free-form rationale (shown in viewer)
    sat_id: Optional[str] = None   # convenience field for downstream joins
    quality_score: Optional[float] = None
    welfare: Optional[float] = None  # priority * quality (None for DROPPED)
```

`status` enumeration:

| Status | When v0.2 emits it |
|---|---|
| `SCHEDULED` | bid matched to a window |
| `DROPPED` | no feasible window matched (target / deadline / band) |
| `COLLECTED` | reserved — not emitted by v0.2 batch mechanisms |
| `DEADLINE_MISSED` | reserved — for future runtime simulation |

## The Mechanism Protocol

```python
class Mechanism(typing.Protocol):
    name: str

    def allocate(
        self,
        bids: list[dict],
        access_windows: list[dict],
        t0: str,
        *,
        satellites: Iterable[dict] = (),
        now: Optional[str] = None,
    ) -> list[Allocation]:
        ...
```

Three constraints on implementations:

1. **Pure function.** Same inputs → identical outputs. No global state,
   no system clock reads, no RNG. (If you need randomness, take a `seed`
   in your constructor and seed a local `random.Random`.)
2. **Deterministic ordering.** Sort all internal collections with a
   tiebreaker that's not Python's dict-iteration order. The provided
   helpers `sort_bids_by_priority` (priority desc, `bid_id` tiebreak)
   and `sort_windows_by_start` (start_iso asc, `window_id` tiebreak)
   are conventional starting points.
3. **One row per bid.** Even for bids with no feasible window. Use
   `make_dropped(bid, mechanism=name, decision_t_iso=...)` from
   `raveneye.mechanism.base`.

`now` is reserved for future online mechanisms that restrict to bids
and windows known as of a given sim time. v0.2's batch mechanisms
ignore it (operate on the full scenario at once).

## Compatibility helper: `match_bid_to_window`

```python
match_bid_to_window(bid, window, *, sat_bands=None,
                    target_tolerance_deg=0.005) -> bool
```

Three checks:

1. **Target match** — by `target_id` when both sides carry one,
   otherwise by lat/lon proximity. Default tolerance ≈ 555 m.
2. **Deadline** — `window.end_iso ≤ bid.ltiov_iso`.
3. **Sensor band** — when `sat_bands` is provided. Mapping table:

   | Bid band | Required satellite band |
   |---|---|
   | `EO_PAN` | `PAN` |
   | `EO_MS` | `MS` |
   | `EO_MS+TIR` | `MS` (TIR is informational; v0.2 does not model TIR sensors) |
   | `SAR_X` | `SAR_X` |

   Use `index_satellite_bands(satellites)` to build a `sat_id → bands`
   lookup once, then pass `sat_bands=index[w["sat_id"]]` per window.

A window that fails any of these checks is not a valid candidate.

## Worked example: greedy vs SSI

Both mechanisms iterate bids in priority-descending order. They
disagree on **which** feasible window each bid is given:

| Mechanism | Per-bid choice |
|---|---|
| `greedy_priority` | first feasible window in `start_iso` order |
| `ssi`             | argmax over feasible unallocated windows of `bid.priority × window.quality` |

A small handcrafted fixture (3 bids × 5 windows, same target) makes the
difference vivid:

| Window | Quality | Time |
|---|---|---|
| AW-00 | 0.40 | 12:30 |
| AW-01 | 0.85 | 12:50 |
| AW-02 | 0.55 | 13:10 |
| AW-03 | 0.30 | 13:40 |
| AW-04 | 0.95 | 14:20 |

Bid priorities: 10.0 / 6.0 / 3.0.

| Bid | Greedy → window (q) | SSI → window (q) |
|---|---|---|
| BID-0 (10.0) | AW-00 (0.40) | AW-04 (0.95) |
| BID-1  (6.0) | AW-01 (0.85) | AW-01 (0.85) |
| BID-2  (3.0) | AW-02 (0.55) | AW-02 (0.55) |
| **welfare** | **10.75** | **16.25** |

SSI's welfare lift comes from giving the highest-priority bid the
highest-quality window — exactly the redistribution greedy can't do
because it commits to the earliest fit before seeing later candidates.

The `tests/test_mechanism_ssi.py` test enforces this 16.25 number, and
`test_scenario_build.py::test_ssi_meets_or_beats_greedy_welfare`
enforces SSI ≥ greedy on any built scenario.

## Welfare and drop-rate metrics

```python
from raveneye.mechanism import total_welfare, drop_rate

total_welfare(allocations)  # Σ priority × quality across SCHEDULED
drop_rate(allocations)      # fraction with status == "DROPPED"
```

`total_welfare` is the standard comparison metric. Any new mechanism
must beat or tie the greedy baseline on welfare for the committed
canonical scenario; if it doesn't, that's a red flag (per
`raveneyebuildspec.md` §6).

## Adding a new mechanism

```python
# raveneye/mechanism/my_mech.py
from typing import Any, Dict, Iterable, List, Optional

from .base import (
    Allocation, Mechanism, index_satellite_bands,
    make_dropped, make_scheduled, match_bid_to_window,
    sort_bids_by_priority, sort_windows_by_start,
)


class MyMechanism:
    name = "my_mech"

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
            chosen = None
            for w in sorted_windows:
                if w["window_id"] in taken:
                    continue
                bands = sat_bands.get(w["sat_id"]) if sat_bands else None
                if not match_bid_to_window(bid, w, sat_bands=bands):
                    continue
                # ... your decision logic here ...
                chosen = w
                break
            alloc_id = f"ALLOC-{i:05d}"
            if chosen is None:
                out.append(make_dropped(bid, mechanism=self.name,
                                        decision_t_iso=decision_t,
                                        allocation_id=alloc_id))
            else:
                taken.add(chosen["window_id"])
                out.append(make_scheduled(bid, chosen, mechanism=self.name,
                                          decision_t_iso=decision_t,
                                          allocation_id=alloc_id))
        return out
```

Then register it in `raveneye/mechanism/build.py`:

```python
_REGISTRY["my_mech"] = MyMechanism()
```

…and `--mechanism my_mech` works on the CLI.

## What v0.2 deliberately does not include

- **CBBA / VCG / ILP combinatorial mechanisms.** Listed in `TODO.md`
  for v0.3+.
- **Constraint enforcement beyond published-spec defaults** — v0.2's
  `match_bid_to_window` does not enforce per-satellite duty-cycle
  budgets, slew constraints between consecutive collects, or downlink
  latency. Those are flagged in `TODO.md` as supply-layer follow-ons.
- **Online / streaming mechanisms.** `now` is in the protocol for
  forward compatibility, but no v0.2 mechanism uses it.

If you build any of these, please open an issue first to discuss
where it slots into the architecture before implementing.
