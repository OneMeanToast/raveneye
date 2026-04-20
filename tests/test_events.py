"""v0.1 event schema invariants."""
from __future__ import annotations

from raveneye.sim import EventType, build_events, phase_at
from raveneye.sim.events import ObservableKind


def test_schema_invariants():
    events = build_events(seed=42)
    assert len(events) > 0
    valid_types = {e.value for e in EventType}
    valid_kinds = {e.value for e in ObservableKind}

    for ev in events:
        assert ev.event_id, "event_id must be non-empty"
        assert ev.t_iso, "t_iso must be non-empty"
        assert ev.narrative and len(ev.narrative) > 10
        assert 1 <= ev.severity <= 5
        assert 0.0 <= ev.source_confidence <= 1.0
        assert ev.ltiov_hours > 0.0
        assert ev.event_type.value in valid_types
        assert ev.observable_kind.value in valid_kinds
        assert ev.phase == phase_at(ev.t_hours).name
        if ev.scripted:
            assert ev.event_id.startswith("SCR-")
        else:
            assert ev.event_id.startswith("STO-")


def test_chronological_order():
    events = build_events(seed=42)
    times = [ev.t_hours for ev in events]
    assert times == sorted(times)


def test_scripted_count_and_first_ids():
    events = build_events(seed=42)
    scripted = [ev for ev in events if ev.scripted]
    assert len(scripted) == 20
    # Lowest-t scripted beat is the t=2.0 DIPLOMATIC_STATUS_CHANGE (SCR-000).
    first_scripted = min(scripted, key=lambda e: e.t_hours)
    assert first_scripted.event_id == "SCR-000"
    assert first_scripted.event_type == EventType.DIPLOMATIC_STATUS_CHANGE


def test_all_scripted_beats_present():
    events = build_events(seed=42)
    scripted_ids = {ev.event_id for ev in events if ev.scripted}
    expected = {f"SCR-{i:03d}" for i in range(20)}
    assert scripted_ids == expected
