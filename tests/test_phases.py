"""Phase lookup boundary behavior."""

from __future__ import annotations

from raveneye.sim import phase_at


def test_before_start_clamps_to_first():
    assert phase_at(-5.0).name == "BLOCKADE_ACTIVE"


def test_at_zero_is_first_phase():
    assert phase_at(0.0).name == "BLOCKADE_ACTIVE"


def test_just_before_escalation():
    assert phase_at(35.999).name == "BLOCKADE_ACTIVE"


def test_escalation_starts_at_36():
    assert phase_at(36.0).name == "ESCALATION"


def test_ceasefire_announced_at_72():
    assert phase_at(72.0).name == "CEASEFIRE_ANNOUNCED"
    assert phase_at(71.999).name == "ESCALATION"


def test_ceasefire_collapse_at_96():
    assert phase_at(96.0).name == "CEASEFIRE_COLLAPSE"


def test_blockade_reinforced_at_132():
    assert phase_at(132.0).name == "BLOCKADE_REINFORCED"


def test_after_scenario_clamps_to_last():
    assert phase_at(1000.0).name == "BLOCKADE_REINFORCED"
