# Bidding interface

The bidding layer is the **boundary contract** between RavenEye's demand
side and any downstream allocation mechanism. v0.1 produces the input
(`bids`); v0.2 will provide the first reference mechanisms (greedy + SSI).

This document specifies the I/O contract so a third party can plug a new
mechanism in without touching the demand-layer code.

## Input: list of `Bid` objects

A `Bid` represents one stakeholder's request for collection on one event,
scored against that stakeholder's utility weights.

### Schema (JSON)

```json
{
  "bid_id": "BID-00123",
  "event_id": "SCR-005",
  "stakeholder_id": "CENTCOM_J2",
  "stakeholder_weight": 2.0,
  "priority_score": 9.504,
  "urgency_factor": 1.2,
  "severity": 5,
  "source_confidence": 0.95,
  "t_submitted_iso": "2026-04-15T05:30:00+00:00",
  "ltiov_iso":     "2026-04-15T13:30:00+00:00",
  "target_location_id": "siri_island",
  "target_lat": 25.900,
  "target_lon": 54.508,
  "observable_kind": "REFINERY",
  "sensor_requirement": {
    "gsd_m": 1.0,
    "band":  "EO_MS+TIR",
    "revisit_h": 12
  },
  "rationale": "CENTCOM J2 weights KINETIC_STRIKE at 2.00; severity 5, confidence 0.95, LTIOV 8.0h → urgency 1.20.",
  "payload": {
    "target_class": "OIL_STORAGE"
  }
}
```

### Field semantics

| Field | Type | Description |
|---|---|---|
| `bid_id` | str | Unique per scenario, format `BID-NNNNN`, zero-padded. |
| `event_id` | str | The event this bid derives from. |
| `stakeholder_id` | str | Owning stakeholder (e.g. `CENTCOM_J2`). |
| `stakeholder_weight` | float | This stakeholder's weight on the event's type. Range `[0, 2]`. |
| `priority_score` | float | `severity × source_confidence × stakeholder_weight × urgency_factor`, rounded to 3 dp. |
| `urgency_factor` | float | Step function of LTIOV (see below). |
| `severity` | int | 1–5, copied from the event. |
| `source_confidence` | float | 0–1, copied from the event. |
| `t_submitted_iso` | ISO 8601 | Wall-clock time the bid is considered active. v0.1 sets this equal to event time. |
| `ltiov_iso` | ISO 8601 | `t_submitted_iso + event.ltiov_hours`. Hard deadline. |
| `target_location_id` | str | Named location ID from the `locations` table. |
| `target_lat`, `target_lon` | float | Decimal degrees. |
| `observable_kind` | str | One of seven `ObservableKind` values. |
| `sensor_requirement` | object | `{gsd_m, band, revisit_h}` from `SENSOR_REQUIREMENTS`. |
| `rationale` | str | Human-readable explanation; useful in the viewer and for debugging mechanism choices. |
| `payload` | object | Pass-through bag from the source event (vessel IMO, target class, etc.). |

### Priority formula

```
priority_score = severity × source_confidence × stakeholder_weight × urgency_factor
```

All four factors are non-negative; ranges are bounded. Practical envelope:

- min reasonable: `1 × 0.3 × 0.2 × 0.7 ≈ 0.04` (low-sev HUMINT for an
  uninterested stakeholder)
- max reasonable: `5 × 0.99 × 2.0 × 1.6 ≈ 15.84` (sev-5 imminent KINETIC for
  a fully-weighted stakeholder)

Mechanisms should treat `priority_score` as a unitless utility — comparable
across bids within the same scenario, not across scenarios.

### Urgency factor

```
ltiov ≤ 4h   → 1.6
ltiov ≤ 12h  → 1.2
ltiov ≤ 24h  → 1.0
ltiov ≤ 48h  → 0.85
ltiov  > 48h → 0.7
```

Step function (not continuous) by design — it makes priority diffs explicit
in test assertions and easy to reason about during demos.

## Output: list of `Allocation` objects

(*Specified here for forward compatibility. v0.1 does not produce
allocations — they appear in v0.2.*)

```json
{
  "allocation_id": "ALLOC-00042",
  "bid_id":        "BID-00123",
  "window_id":     "AW-00857",
  "mechanism":     "greedy_priority",
  "status":        "SCHEDULED",
  "priority_score": 9.504,
  "decision_t_iso": "2026-04-15T05:35:00+00:00",
  "notes":          "Highest-priority bid in window; no conflicts."
}
```

| Field | Type | Description |
|---|---|---|
| `allocation_id` | str | `ALLOC-NNNNN`. |
| `bid_id` | str | The bid this allocation resolves. Required. |
| `window_id` | str or null | Matched access window. `null` for `DROPPED`. |
| `mechanism` | str | Identifier of the mechanism that produced this row (e.g. `greedy_priority`, `ssi`). |
| `status` | str | One of `COLLECTED`, `SCHEDULED`, `DROPPED`, `DEADLINE_MISSED`. |
| `priority_score` | float | Echoed from the bid for convenience. |
| `decision_t_iso` | ISO 8601 | Wall-clock time the mechanism finalized this row. |
| `notes` | str | Free-form rationale; surfaced in the viewer. |

**Dropped bids must still appear** in the allocation list with `status =
"DROPPED"` and `window_id = null`. This makes drop-rate metrics and the
viewer's "what got dropped" panel trivial to compute — no diffs against the
bid list required.

## Mechanism contract (v0.2 sketch)

```python
from typing import Protocol

class Mechanism(Protocol):
    def allocate(
        self,
        bids: list[dict],
        access_windows: list[dict],
        t0: datetime,
        now: datetime | None = None,
    ) -> list[dict]:
        """Return allocation dicts in the order the mechanism decided them.

        `now` lets future work restrict to bids/windows known as of a given
        sim time; v0.2 mechanisms ignore it and operate offline on the full
        scenario.
        """
```

## What v0.1 does *not* do

- No allocations. v0.1 is strictly demand. Plug in your own mechanism if
  you want to experiment.
- No conflict resolution between bids targeting the same site. They all
  exist independently; the mechanism layer decides what wins.
- No state — `derive_bids` is a pure function. If you re-run with the same
  events and stakeholders, you get the same bids.
- No bid revision. A v0.1 bid is fire-and-forget. Stakeholders cannot
  withdraw or update bids once submitted. (This is on the v0.3+ list.)

## Reference scenario invariants (seed=42, 168h)

For sanity-checking a mechanism integration:

- `n_events` ≈ 170–180 (20 scripted + ~150–160 stochastic)
- `n_bids` ≈ 680–720 (~4× events; one per stakeholder per event, with
  zero-weight pairings filtered)
- 4 stakeholders: `CENTCOM_J2`, `NRO_CSPO`, `ALLIED_PARTNER`,
  `COMMERCIAL_INSURER`
- The first scripted event is `SCR-000` of type `DIPLOMATIC_STATUS_CHANGE`

If your integration disagrees with these counts on `seed=42`, you are
either using a different seed or have modified the demand layer — recheck
the canonical `data/sample_sim.json`.
