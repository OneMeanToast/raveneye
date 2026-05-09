"""Image-delivery pipeline (v0.2.x).

Takes the mechanism-layer output (allocations) and computes a per-row
lifecycle: collected_iso → processing_complete_iso → delivered_iso, plus
a final terminal status (DELIVERED, DROPPED, DEADLINE_MISSED, or
PROCESSING_FAILED).

The pipeline is fully deterministic given a seed — the same scenario
JSON always produces the same lifecycle outcomes.
"""
from .pipeline import (
    LIFECYCLE_STATUSES,
    apply_delivery_pipeline,
    delivery_rate,
    lifecycle_state_at,
    processing_success_rate_observed,
)

__all__ = [
    "LIFECYCLE_STATUSES",
    "apply_delivery_pipeline",
    "delivery_rate",
    "lifecycle_state_at",
    "processing_success_rate_observed",
]
