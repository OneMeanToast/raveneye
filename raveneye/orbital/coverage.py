"""Sensor-coverage geometry helpers for the v0.2 globe viewer.

These helpers are NOT used inside ``find_access_windows`` — windows already
encode the (sat, target, time) feasibility decision. Coverage is purely
visual: when the viewer wants to draw an instantaneous swath polygon under
a satellite during a scheduled collect, it asks these functions where on
the ground the sensor footprint sits.

All math is spherical-Earth approximation. Errors scale with swath width:
sub-1% for typical commercial-EO swaths (≤25 km) at LEO altitudes.
"""
from __future__ import annotations

import math
from typing import List, Tuple

EARTH_RADIUS_M = 6371_000.0


def horizon_off_nadir_deg(altitude_m: float) -> float:
    """Off-nadir angle (deg) at which the line of sight is tangent to Earth.

    Beyond this, no surface intercept exists. For h=600 km this is ≈66°.
    """
    h = max(1.0, altitude_m)
    return math.degrees(math.asin(EARTH_RADIUS_M / (EARTH_RADIUS_M + h)))


def sensor_cone_radius_m(altitude_m: float, max_off_nadir_deg: float) -> float:
    """Ground-distance from sub-satellite point to the farthest reachable
    pixel at a given off-nadir limit.

    Geometry: in the triangle (Earth-center, satellite, surface-target),
    let θ be the central angle. Then for off-nadir N the corresponding
    minimum ground elevation is ``E = arccos(sin(N)·(R+h)/R)``, and
    ``θ = 90° − N − E``. The ground-arc distance is ``R · θ``.
    """
    h = max(1.0, altitude_m)
    n_horizon = horizon_off_nadir_deg(h)
    n = min(abs(max_off_nadir_deg), n_horizon)
    n_rad = math.radians(n)
    cos_emin = math.sin(n_rad) * (EARTH_RADIUS_M + h) / EARTH_RADIUS_M
    cos_emin = max(-1.0, min(1.0, cos_emin))
    e_min = math.acos(cos_emin)
    central_arc = math.pi / 2 - n_rad - e_min
    return max(0.0, EARTH_RADIUS_M * central_arc)


def ground_range_for_off_nadir_m(altitude_m: float, off_nadir_deg: float) -> float:
    """Same geometry as ``sensor_cone_radius_m`` but for an arbitrary single
    off-nadir angle (not the maximum). Used to project a boresight onto the
    ground for swath polygon construction.
    """
    h = max(1.0, altitude_m)
    n = min(abs(off_nadir_deg), horizon_off_nadir_deg(h))
    n_rad = math.radians(n)
    cos_emin = math.sin(n_rad) * (EARTH_RADIUS_M + h) / EARTH_RADIUS_M
    cos_emin = max(-1.0, min(1.0, cos_emin))
    e_min = math.acos(cos_emin)
    return max(0.0, EARTH_RADIUS_M * (math.pi / 2 - n_rad - e_min))


def _offset_latlon(
    lat_deg: float,
    lon_deg: float,
    distance_m: float,
    azimuth_deg: float,
) -> Tuple[float, float]:
    """Equirectangular offset from (lat, lon) by ``distance_m`` in
    direction ``azimuth_deg`` (0=N, 90=E, clockwise from north).

    Adequate for the scale of v0.2 swath polygons (few tens of km).
    """
    az = math.radians(azimuth_deg)
    dlat_m = distance_m * math.cos(az)
    dlon_m = distance_m * math.sin(az)
    dlat_deg = dlat_m / 111_000.0
    cos_lat = max(0.01, math.cos(math.radians(lat_deg)))
    dlon_deg = dlon_m / (111_000.0 * cos_lat)
    return lat_deg + dlat_deg, lon_deg + dlon_deg


def swath_footprint_polygon(
    lat: float,
    lon: float,
    alt_m: float,
    off_nadir_deg: float,
    az_deg: float,
    swath_width_km: float,
) -> List[Tuple[float, float]]:
    """Approximate rectangular footprint of an instantaneous sensor swath.

    Inputs:
      lat, lon       — satellite sub-point (deg)
      alt_m          — satellite altitude above WGS84 (m)
      off_nadir_deg  — boresight off-nadir angle (deg)
      az_deg         — boresight azimuth from north, clockwise (deg)
      swath_width_km — sensor swath width perpendicular to boresight (km)

    Returns a closed list of ``(lat, lon)`` corners (5 points; last == first).
    The "along-track" footprint length is approximated as equal to the
    swath width — adequate for visual overlay; not meant for coverage
    bookkeeping.
    """
    range_m = ground_range_for_off_nadir_m(alt_m, off_nadir_deg)
    center_lat, center_lon = _offset_latlon(lat, lon, range_m, az_deg)
    half_w_m = max(1.0, swath_width_km) * 1000.0 / 2.0
    half_l_m = half_w_m  # treat as square for visualization purposes
    perp = az_deg + 90.0

    corners: List[Tuple[float, float]] = []
    for sl, sw in [(-1, -1), (-1, 1), (1, 1), (1, -1), (-1, -1)]:
        # offset center by along-track sl*half_l, then cross-track sw*half_w
        c_lat, c_lon = _offset_latlon(center_lat, center_lon, sl * half_l_m, az_deg)
        c_lat, c_lon = _offset_latlon(c_lat, c_lon, sw * half_w_m, perp)
        corners.append((c_lat, c_lon))
    return corners
