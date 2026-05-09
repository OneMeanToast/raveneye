"""Tests for raveneye.viewer.build_viewer."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from raveneye.orbital import build_satellites_from_fixture, by_id
from raveneye.scenario import build_full_scenario_offline
from raveneye.viewer.build_viewer import stage_viewer


FIXTURE = Path(__file__).parent / "fixtures" / "tles.txt"


@pytest.fixture(scope="module")
def scenario_24h():
    sats = build_satellites_from_fixture(
        FIXTURE, by_id("blacksky"),
        datetime(2026, 4, 13, 12, 0, 0, tzinfo=timezone.utc),
    )
    return build_full_scenario_offline(sats, seed=42, duration_hours=24.0)


def test_stage_flat_writes_index_and_sim_json(tmp_path, scenario_24h):
    out = stage_viewer(tmp_path / "flat_out", scenario_24h, kind="flat")
    assert (out / "index.html").is_file()
    assert (out / "sim.json").is_file()
    parsed = json.loads((out / "sim.json").read_text(encoding="utf-8"))
    assert parsed["meta"]["seed"] == 42
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "<title>RavenEye" in html


def test_stage_globe_writes_full_directory(tmp_path, scenario_24h):
    out = stage_viewer(tmp_path / "globe_out", scenario_24h, kind="globe")
    assert (out / "index.html").is_file()
    assert (out / "scenario.json").is_file()
    # All globe modules should land (skeleton + coverage + board)
    for fname in ("style.css", "main.js", "orbits.js", "ground.js",
                  "coverage.js", "panels.js", "timeline.js", "board.js"):
        assert (out / fname).is_file(), f"missing {fname} in staged globe viewer"
    # The board overlay markup must be present in index.html
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "tab-board" in html
    assert "tab-globe" in html
    assert "board-overlay" in html
    assert "gantt-svg" in html
    assert "kanban-body" in html
    parsed = json.loads((out / "scenario.json").read_text(encoding="utf-8"))
    assert parsed["meta"]["n_satellites"] == 5
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "Cesium.js" in html
    assert "satellite.min.js" in html


def test_stage_default_kind_is_flat(tmp_path, scenario_24h):
    out = stage_viewer(tmp_path / "default_out", scenario_24h)
    assert (out / "sim.json").is_file()
    assert not (out / "scenario.json").exists()


def test_stage_rejects_unknown_kind(tmp_path, scenario_24h):
    with pytest.raises(ValueError):
        stage_viewer(tmp_path / "bad", scenario_24h, kind="orbital")
