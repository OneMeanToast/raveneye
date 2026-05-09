# Delivery pipeline

The mechanism layer answers *which window serves which bid*. The
delivery pipeline answers *what happens to the image after the
satellite takes the shot*. It runs once at scenario-build time,
deterministically, and bakes the entire collect→process→deliver
timeline into each allocation as a `lifecycle` sub-dict.

This doc covers chunk 2 of the v0.2.x series. It assumes you've already
read `docs/mechanism_interface.md` (Allocation schema) and
`docs/orbital_model.md` (per-vendor sensor parameters).

## State machine

```
SCHEDULED                                            (mechanism decision)
    │
    ▼  collected_iso = window.end_iso
COLLECTED                                            (image data on the bird)
    │
    ▼  + processing_latency_min  (downlink + processing pipeline)
PROCESSED  or  PROCESSING_FAILED                     (seeded probability)
    │
    ▼  + delivery_latency_min   (network/portal handoff)
DELIVERED  or  DEADLINE_MISSED                       (compare to bid.ltiov_iso)
```

The four terminal `final_status` values:

| Status | When |
|---|---|
| `DROPPED` | Mechanism found no feasible window for the bid (existed pre-chunk-2 too). |
| `DELIVERED` | Collection happened, processing succeeded, delivery time ≤ LTIOV. |
| `DEADLINE_MISSED` | Collection happened, processing succeeded, delivery time > LTIOV. The image exists; it's just past its operational window. |
| `PROCESSING_FAILED` | Collection happened, processing pipeline rejected the image (cloud cover, sensor calibration drift, frame-quality reject). |

DEADLINE_MISSED imagery is still useful for forensics / pattern
analysis but doesn't count toward the operational delivery rate.

## Per-vendor latencies

Set on the `Constellation` dataclass in `raveneye.orbital.constellations`;
v0.2 ships these defaults:

| Vendor | processing | delivery | base success | rationale |
|---|---|---|---|---|
| BlackSky        | 45 min  | 30 min  | 85% | EO HighRes, well-instrumented ground network |
| Planet SkySat   | 60 min  | 30 min  | 85% | EO HighRes, similar profile |
| Planet Dove     | 720 min | 180 min | 80% | sparser ground stations; smallsat constellation |
| Capella Space   | 30 min  | 15 min  | 92% | SAR, fast-turnaround pitch is core to the product |
| ICEYE           | 45 min  | 20 min  | 92% | SAR; cloud-independent so processing is more reliable |
| Vantor (Maxar)  | 180 min | 60 min  | 88% | VHR EO, heavier processing pipeline (PAN+MS+SWIR) |

These are notional, not authoritative. Ground-truth them against any
vendor's actual SLA before quoting. Adjust by editing
`CONSTELLATIONS` and re-running the scenario builder.

## Quality-modulated success rate

A satellite with maximum off-nadir, low elevation, and dim sun is
going to take a worse picture than one passing directly overhead in
broad daylight. The pipeline reflects that by modulating the
constellation's base `processing_success_rate` with the access window's
`quality_score`:

```
effective_success_rate = base × (0.5 + 0.5 × quality_score)
```

- `quality_score = 1.0` (overhead, full sun, zero off-nadir) → full base rate.
- `quality_score = 0.5` (typical pass) → `base × 0.75`.
- `quality_score = 0.0` (geometry barely feasible) → `base × 0.5`.

For SAR sensors the quality term drops the sun component (see
`docs/orbital_model.md`), so SAR scenes are penalized only by elevation
and off-nadir.

This coupling means **the choice of mechanism affects delivery
outcomes through quality, not just welfare**. SSI routes high-priority
bids to high-quality windows, which then have higher effective success
rates, which then translate into better delivery rates over greedy.
The integration test
`tests/test_delivery_pipeline.py::test_ssi_delivery_rate_meets_or_beats_greedy`
enforces SSI ≥ greedy on this metric.

## Allocation lifecycle dict

Every allocation in `scenario.allocations` carries a `lifecycle`
sub-dict:

```json
{
  "allocation_id": "ALLOC-00042",
  "bid_id": "BID-00123",
  "window_id": "AW-00857",
  "status": "SCHEDULED",
  "sat_id": "BLACKSKY-1-44550",
  "quality_score": 0.78,
  "welfare": 7.41,
  "lifecycle": {
    "collected_iso":          "2026-04-15T18:42:12+00:00",
    "processing_latency_min": 45.0,
    "processing_complete_iso": "2026-04-15T19:27:12+00:00",
    "processed":              true,
    "delivery_latency_min":   30.0,
    "delivered_iso":          "2026-04-15T19:57:12+00:00",
    "delivered":              true,
    "deadline_missed":        false,
    "final_status":           "DELIVERED"
  }
}
```

`DROPPED` allocations carry a lifecycle dict where every time field is
`null` and `final_status = "DROPPED"`. This keeps the schema uniform
so consumers don't need null-checks on the field's existence.

## Determinism

Per-allocation success rolls use a Random seeded by the SHA-256 of
`f"{seed}:{allocation_id}"`. Same scenario seed + same allocation_id
always produces the same outcome regardless of dict iteration order.
The integration test
`tests/test_delivery_pipeline.py::test_scheduled_allocation_with_room_to_deliver_succeeds_or_fails_deterministically`
runs the pipeline twice on the same input and asserts byte-equal
output.

## Aggregates

Surfaced in `scenario.meta`:

| Field | Meaning |
|---|---|
| `n_delivered` | count of `final_status == "DELIVERED"` |
| `n_processing_failed` | count of `final_status == "PROCESSING_FAILED"` |
| `n_deadline_missed` | count of `final_status == "DEADLINE_MISSED"` |
| `delivery_rate` | `n_delivered / n_allocations` |
| `processing_success_rate` | `n_processed / n_collected` (excludes DROPPED) |

Plus the existing `n_dropped` and `drop_rate` from the mechanism
layer. The five categorical counters partition the bid set:

```
n_allocations == n_dropped + n_delivered + n_processing_failed + n_deadline_missed
```

Asserted in `test_aggregate_metrics_make_sense_on_realistic_scenario`.

## Time-aware queries

The pipeline writes the *eventual* terminal status into each
allocation. For viewer-side rendering you often want to know what
stage an allocation is in *right now* given the playback clock —
`raveneye.delivery.lifecycle_state_at(allocation, window, t_iso)` is
the helper:

```python
from raveneye.delivery import lifecycle_state_at

stage = lifecycle_state_at(alloc, window, "2026-04-15T19:00:00+00:00")
# → one of: PENDING, COLLECTING, PROCESSING, IN_TRANSIT,
#           DELIVERED, DEADLINE_MISSED, PROCESSING_FAILED, DROPPED
```

The globe viewer's Kanban board (BOARD tab) ports this same logic to
JS so columns stay consistent between Python tests and browser UI;
see `raveneye/viewer/globe/board.js::_stageAt`.

## Extending

To add a new processing-failure cause (e.g. simulated cloud cover from
a forecast feed), edit `_lifecycle_for` in
`raveneye/delivery/pipeline.py`. The cleanest extension point is the
`processing_succeeded` roll, which is currently a single Bernoulli
draw against `effective_success_rate`. You could:

- Compose multiple independent success terms (cloud × calibration × frame_quality) before drawing, or
- Introduce additional terminal states (`CLOUD_OBSCURED`, `CALIBRATION_REJECTED`) and split the failure bucket.

If you do, add the new statuses to `LIFECYCLE_STATUSES` and update the
viewer's color palette in `coverage.js::STATUS_COLOR` and
`board.js::STAGE_COLOR` to match.

## What this layer deliberately doesn't model (yet)

- **Scheduled cloud forecasts.** Currently the per-window quality_score
  is the only proxy. v0.3+ could ingest ECMWF/GFS cloud-cover predictions
  and recompute quality dynamically.
- **Multi-step delivery.** Real-world delivery sometimes goes
  satellite → ground station → cloud bucket → customer portal →
  customer's S3, with retries at each step. v0.2 collapses all of this
  into one `delivery_latency_min` offset.
- **Re-task and recollect.** A `PROCESSING_FAILED` outcome doesn't
  trigger a re-allocation against the next available window. That's
  online-mechanism territory and is gated on the `now` parameter
  in the `Mechanism` Protocol.

These are flagged in `TODO.md` as v0.3+ work.
