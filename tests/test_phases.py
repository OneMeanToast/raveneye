"""Phase boundary tests."""
from __future__ import annotations

from raveneye.sim import phase_at


def test_before_start_is_first_phase():
    assert phase_at(-5.0).name == "BLOCKADE_ACTIVE"


def test_t_zero_is_first_phase():
    assert phase_at(0.0).name == "BLOCKADE_ACTIVE"


def test_just_before_boundary():
    assert phase_at(35.999).name == "BLOCKADE_ACTIVE"


def test_at_boundary_enters_next():
    assert phase_at(36.0).name == "ESCALATION"


def test_after_all_phases_is_last():
    assert phase_at(1000.0).name == "BLOCKADE_REINFORCED"


def test_ceasefire_window():
    assert phase_at(72.0).name == "CEASEFIRE_ANNOUNCED"
    assert phase_at(95.999).name == "CEASEFIRE_ANNOUNCED"
    assert phase_at(96.0).name == "CEASEFIRE_COLLAPSE"


def test_reinforced_start():
    assert phase_at(131.999).name == "CEASEFIRE_COLLAPSE"
    assert phase_at(132.0).name == "BLOCKADE_REINFORCED"
