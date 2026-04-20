"""Schema invariants for generated events."""

from __future__ import annotations

from raveneye.sim import EventType, build_events, phase_at


def test_event_schema_invariants():
    events = build_events(seed=42)
    assert len(events) > 0
    valid_types = {e.value for e in EventType}
    for ev in events:
        assert ev.event_id, "event_id must be non-empty"
        assert ev.t_iso, "t_iso must be non-empty"
        assert ev.narrative, "narrative must be non-empty"
        assert ev.event_type.value in valid_types
        assert 1 <= ev.severity <= 5
        assert 0.0 <= ev.source_confidence <= 1.0
        assert ev.ltiov_hours > 0
        assert ev.phase == phase_at(ev.t_hours).name
        if ev.scripted:
            assert ev.event_id.startswith("SCR-")
        else:
            assert ev.event_id.startswith("STO-")


def test_events_chronological():
    events = build_events(seed=42)
    times = [ev.t_hours for ev in events]
    assert times == sorted(times)


def test_event_ids_unique():
    events = build_events(seed=42)
    ids = [ev.event_id for ev in events]
    assert len(set(ids)) == len(ids)


def test_scripted_count_is_20():
    events = build_events(seed=42)
    scripted = [e for e in events if e.scripted]
    assert len(scripted) == 20
