"""Tests for the v0.2 constellation metadata table."""
from __future__ import annotations

import pytest

from raveneye.orbital.constellations import CONSTELLATIONS, Constellation, by_id


def test_constellation_count_and_ids():
    ids = [c.constellation_id for c in CONSTELLATIONS]
    assert len(ids) == 6
    assert set(ids) == {
        "blacksky",
        "skysat",
        "planet_dove",
        "capella",
        "iceye",
        "maxar_wv",
    }
    assert len(set(ids)) == len(ids), "constellation IDs must be unique"


def test_constellation_field_invariants():
    for c in CONSTELLATIONS:
        assert isinstance(c, Constellation)
        assert c.constellation_id and c.vendor and c.sensor_class
        assert c.sensor_class in {"EO_HIGHRES", "EO_VHR", "EO_MEDRES", "SAR"}
        assert 0.1 <= c.nominal_gsd_m <= 10.0
        assert isinstance(c.spectral_bands, tuple) and len(c.spectral_bands) >= 1
        assert 0 <= c.max_off_nadir_deg <= 90
        assert 0 < c.swath_width_km <= 100
        assert 0 < c.slew_rate_deg_s <= 10
        assert 0 < c.duty_cycle_pct <= 100
        assert c.celestrak_group  # non-empty


def test_sar_constellations_have_sar_band():
    for c in CONSTELLATIONS:
        if c.sensor_class == "SAR":
            assert any(b.startswith("SAR") for b in c.spectral_bands), (
                f"{c.constellation_id} marked SAR but bands are {c.spectral_bands}"
            )


def test_to_dict_round_trip():
    c = CONSTELLATIONS[0]
    d = c.to_dict()
    assert d["constellation_id"] == c.constellation_id
    assert d["spectral_bands"] == list(c.spectral_bands)
    assert d["nominal_gsd_m"] == c.nominal_gsd_m


def test_by_id_lookup():
    c = by_id("blacksky")
    assert c.vendor == "BlackSky"
    with pytest.raises(KeyError):
        by_id("not_a_real_constellation")
