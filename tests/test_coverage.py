"""Tests for raveneye.orbital.coverage geometry helpers."""
from __future__ import annotations

import math

import pytest

from raveneye.orbital.coverage import (
    EARTH_RADIUS_M,
    ground_range_for_off_nadir_m,
    horizon_off_nadir_deg,
    sensor_cone_radius_m,
    swath_footprint_polygon,
)


def test_horizon_off_nadir_at_typical_leo():
    # h=600 km → ~66°
    h_deg = horizon_off_nadir_deg(600_000.0)
    assert 64.0 < h_deg < 68.0


def test_horizon_decreases_with_altitude():
    assert horizon_off_nadir_deg(400_000.0) > horizon_off_nadir_deg(2000_000.0)


def test_sensor_cone_radius_overhead_zero():
    assert sensor_cone_radius_m(600_000.0, 0.0) == pytest.approx(0.0, abs=1.0)


def test_sensor_cone_radius_grows_with_off_nadir():
    r10 = sensor_cone_radius_m(600_000.0, 10.0)
    r45 = sensor_cone_radius_m(600_000.0, 45.0)
    r60 = sensor_cone_radius_m(600_000.0, 60.0)
    assert 0.0 < r10 < r45 < r60


def test_sensor_cone_radius_at_45deg_leo_is_a_few_hundred_km():
    # h=600km, N=45° → expect a few hundred km on the ground.
    r = sensor_cone_radius_m(600_000.0, 45.0)
    assert 400_000.0 < r < 900_000.0


def test_sensor_cone_radius_capped_at_horizon():
    # Asking for off-nadir beyond the horizon should clamp to horizon range.
    r_horizon = sensor_cone_radius_m(600_000.0, horizon_off_nadir_deg(600_000.0))
    r_beyond = sensor_cone_radius_m(600_000.0, 89.0)
    assert r_beyond == pytest.approx(r_horizon, rel=1e-6)


def test_ground_range_consistent_with_cone_at_max():
    h = 600_000.0
    n = 30.0
    a = ground_range_for_off_nadir_m(h, n)
    b = sensor_cone_radius_m(h, n)
    assert a == pytest.approx(b, rel=1e-9)


def test_swath_footprint_polygon_returns_closed_polygon():
    pts = swath_footprint_polygon(
        lat=27.0, lon=56.0, alt_m=600_000.0,
        off_nadir_deg=10.0, az_deg=90.0, swath_width_km=10.0,
    )
    assert len(pts) == 5
    assert pts[0] == pts[-1], "polygon must be closed"


def test_swath_footprint_polygon_is_near_target():
    """Footprint center should be roughly within the cone radius of the
    sub-satellite point (sanity check on offset math)."""
    sub_lat, sub_lon = 27.0, 56.0
    pts = swath_footprint_polygon(
        lat=sub_lat, lon=sub_lon, alt_m=600_000.0,
        off_nadir_deg=20.0, az_deg=90.0, swath_width_km=10.0,
    )
    cone_r_km = sensor_cone_radius_m(600_000.0, 20.0) / 1000.0
    for p_lat, p_lon in pts:
        # rough km distance via equirectangular
        dlat_km = (p_lat - sub_lat) * 111.0
        dlon_km = (p_lon - sub_lon) * 111.0 * math.cos(math.radians(sub_lat))
        d_km = math.hypot(dlat_km, dlon_km)
        # bound: cone radius + half of swath diagonal
        bound = cone_r_km + math.hypot(10.0, 10.0)
        assert d_km < bound, f"polygon corner {p_lat},{p_lon} too far ({d_km:.1f}km > {bound:.1f}km)"


def test_swath_footprint_polygon_azimuth_matters():
    """Different azimuths should put the footprint center in different
    directions from the sub-point."""
    sub_lat, sub_lon = 0.0, 0.0
    pts_north = swath_footprint_polygon(
        lat=sub_lat, lon=sub_lon, alt_m=600_000.0,
        off_nadir_deg=20.0, az_deg=0.0, swath_width_km=5.0,
    )
    pts_east = swath_footprint_polygon(
        lat=sub_lat, lon=sub_lon, alt_m=600_000.0,
        off_nadir_deg=20.0, az_deg=90.0, swath_width_km=5.0,
    )
    # north footprint should have higher mean latitude
    mean_lat_n = sum(p[0] for p in pts_north) / len(pts_north)
    mean_lat_e = sum(p[0] for p in pts_east) / len(pts_east)
    assert mean_lat_n > mean_lat_e
    # east footprint should have higher mean longitude
    mean_lon_n = sum(p[1] for p in pts_north) / len(pts_north)
    mean_lon_e = sum(p[1] for p in pts_east) / len(pts_east)
    assert mean_lon_e > mean_lon_n
