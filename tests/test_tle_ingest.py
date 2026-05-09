"""Offline tests for raveneye.orbital.tle_ingest.

These tests do NOT touch the network — ``requests.get`` is monkeypatched.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest
import requests

from raveneye.orbital import tle_ingest


FIXTURE = Path(__file__).parent / "fixtures" / "tles.txt"


# ---------- Parsing ----------

def test_parse_tle_text_uses_committed_fixture():
    triples = tle_ingest.parse_tle_text(FIXTURE.read_text(encoding="utf-8"))
    assert len(triples) == 5
    names = [t[0] for t in triples]
    assert "ISS (ZARYA)" in names
    assert "LANDSAT 9" in names
    for name, l1, l2 in triples:
        assert name
        assert l1.startswith("1 ")
        assert l2.startswith("2 ")
        assert len(l1) >= 68
        assert len(l2) >= 68


def test_parse_tle_text_skips_malformed_blocks():
    bad = (
        "GOOD SAT\n"
        "1 25544U 98067A   24015.50000000  .00000000  00000-0  00000-0 0  9991\n"
        "2 25544  51.6400 100.0000 0001234  90.0000 270.0000 15.50000000123450\n"
        "BAD HEADER\n"
        "not a real tle line\n"
        "another not-tle line\n"
        "ANOTHER GOOD\n"
        "1 12345U 24001A   24015.50000000  .00000000  00000-0  00000-0 0  9990\n"
        "2 12345  98.0000  60.0000 0001234  90.0000 270.0000 14.50000000111110\n"
    )
    triples = tle_ingest.parse_tle_text(bad)
    names = [t[0] for t in triples]
    assert "GOOD SAT" in names
    assert "ANOTHER GOOD" in names
    assert "BAD HEADER" not in names


def test_parse_omm_json_handles_list_and_singleton():
    sample = [{"OBJECT_NAME": "FOO", "TLE_LINE0": "0 FOO", "TLE_LINE1": "1 ...", "TLE_LINE2": "2 ..."}]
    out = tle_ingest.parse_omm_json(json.dumps(sample))
    assert isinstance(out, list) and len(out) == 1
    assert out[0]["OBJECT_NAME"] == "FOO"

    out2 = tle_ingest.parse_omm_json(json.dumps(sample[0]))
    assert isinstance(out2, list) and out2[0]["OBJECT_NAME"] == "FOO"

    assert tle_ingest.parse_omm_json("") == []


def test_parse_omm_json_rejects_unexpected_shape():
    with pytest.raises(ValueError):
        tle_ingest.parse_omm_json('"a string is not an OMM payload"')


# ---------- Fetch / cache ----------

def _mock_response(text: str, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.text = text
    resp.status_code = status
    if status >= 400:
        resp.raise_for_status.side_effect = requests.HTTPError(f"HTTP {status}")
    else:
        resp.raise_for_status.return_value = None
    return resp


def test_fetch_tle_group_writes_cache_and_parses(tmp_path, monkeypatch):
    text = FIXTURE.read_text(encoding="utf-8")
    mock_get = MagicMock(return_value=_mock_response(text))
    monkeypatch.setattr(tle_ingest.requests, "get", mock_get)

    triples = tle_ingest.fetch_tle_group("blacksky", tmp_path)
    assert len(triples) == 5
    cached = list(tmp_path.glob("blacksky__*.tle"))
    assert len(cached) == 1
    assert cached[0].read_text(encoding="utf-8") == text
    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert args[0] == tle_ingest.CELESTRAK_GP_URL
    assert kwargs["params"] == {"GROUP": "blacksky", "FORMAT": "tle"}


def test_fetch_tle_group_uses_cache_when_present(tmp_path, monkeypatch):
    text = FIXTURE.read_text(encoding="utf-8")
    cache_path = tle_ingest._cache_path(tmp_path, "iceye", "tle")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(text, encoding="utf-8")

    mock_get = MagicMock(side_effect=AssertionError("network must not be touched"))
    monkeypatch.setattr(tle_ingest.requests, "get", mock_get)

    triples = tle_ingest.fetch_tle_group("iceye", tmp_path)
    assert len(triples) == 5
    mock_get.assert_not_called()


def test_fetch_tle_group_force_refresh_bypasses_cache(tmp_path, monkeypatch):
    text = FIXTURE.read_text(encoding="utf-8")
    cache_path = tle_ingest._cache_path(tmp_path, "skysat", "tle")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text("STALE\n1 X\n2 X\n", encoding="utf-8")

    mock_get = MagicMock(return_value=_mock_response(text))
    monkeypatch.setattr(tle_ingest.requests, "get", mock_get)

    triples = tle_ingest.fetch_tle_group("skysat", tmp_path, force_refresh=True)
    assert len(triples) == 5
    mock_get.assert_called_once()


def test_fetch_omm_group_writes_cache_and_parses(tmp_path, monkeypatch):
    sample: list[Dict[str, Any]] = [
        {"OBJECT_NAME": "DEMO 1", "NORAD_CAT_ID": 99001},
        {"OBJECT_NAME": "DEMO 2", "NORAD_CAT_ID": 99002},
    ]
    mock_get = MagicMock(return_value=_mock_response(json.dumps(sample)))
    monkeypatch.setattr(tle_ingest.requests, "get", mock_get)

    out = tle_ingest.fetch_omm_group("capella", tmp_path)
    assert len(out) == 2 and out[0]["NORAD_CAT_ID"] == 99001
    cached = list(tmp_path.glob("capella__*.json"))
    assert len(cached) == 1


def test_load_cached_or_fetch_falls_back_to_omm_on_tle_failure(tmp_path, monkeypatch):
    omm_payload = [{
        "OBJECT_NAME": "POST-OVERFLOW SAT",
        "TLE_LINE0": "0 POST-OVERFLOW SAT",
        "TLE_LINE1": "1 25544U 98067A   24015.50000000  .00000000  00000-0  00000-0 0  9991",
        "TLE_LINE2": "2 25544  51.6400 100.0000 0001234  90.0000 270.0000 15.50000000123450",
    }]

    call_log = []

    def fake_get(url, params=None, headers=None, timeout=None):
        call_log.append(params.get("FORMAT"))
        if params.get("FORMAT") == "tle":
            return _mock_response("", status=503)
        return _mock_response(json.dumps(omm_payload))

    monkeypatch.setattr(tle_ingest.requests, "get", fake_get)
    triples = tle_ingest.load_cached_or_fetch("planet", tmp_path, max_age_hours=0.0)
    assert len(triples) == 1
    assert triples[0][0] == "POST-OVERFLOW SAT"
    assert call_log == ["tle", "json"]


def test_load_cached_or_fetch_uses_fresh_cache(tmp_path, monkeypatch):
    text = FIXTURE.read_text(encoding="utf-8")
    cache_path = tle_ingest._cache_path(tmp_path, "blacksky", "tle")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(text, encoding="utf-8")

    mock_get = MagicMock(side_effect=AssertionError("no fetch when fresh cache exists"))
    monkeypatch.setattr(tle_ingest.requests, "get", mock_get)

    triples = tle_ingest.load_cached_or_fetch("blacksky", tmp_path, max_age_hours=24.0)
    assert len(triples) == 5
    mock_get.assert_not_called()


def test_omm_records_to_tle_triples_skips_records_without_tle_lines():
    records = [
        {"OBJECT_NAME": "WITH TLE", "TLE_LINE1": "1 ...", "TLE_LINE2": "2 ..."},
        {"OBJECT_NAME": "POST-OVERFLOW NO TLE"},
    ]
    triples = tle_ingest.omm_records_to_tle_triples(records)
    assert len(triples) == 1
    assert triples[0][0] == "WITH TLE"


def test_load_cached_or_fetch_rejects_bad_prefer(tmp_path):
    with pytest.raises(ValueError):
        tle_ingest.load_cached_or_fetch("blacksky", tmp_path, prefer="garbage")
