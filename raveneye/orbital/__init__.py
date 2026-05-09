"""RavenEye orbital (supply) layer.

v0.2 — TLE ingestion, SGP4 propagation, access-window computation,
sensor-coverage geometry, and the ``build_supply()`` orchestrator that
emits a JSON-shaped supply object for the unified scenario builder.
"""
from .access import (
    find_access_windows,
    off_nadir_at_satellite,
    quality_score,
    solar_elevation_deg,
)
from .build import (
    build_supply,
    build_supply_from_satellites,
    targets_from_locations,
)
from .constellations import CONSTELLATIONS, Constellation, by_id
from .coverage import (
    ground_range_for_off_nadir_m,
    horizon_off_nadir_deg,
    sensor_cone_radius_m,
    swath_footprint_polygon,
)
from .propagate import (
    build_satellites,
    build_satellites_from_fixture,
    build_satellites_from_fixture_dir,
    make_skyfield_satellite,
    propagate_subpoint,
)

__all__ = [
    "CONSTELLATIONS",
    "Constellation",
    "build_satellites",
    "build_satellites_from_fixture",
    "build_satellites_from_fixture_dir",
    "build_supply",
    "build_supply_from_satellites",
    "by_id",
    "find_access_windows",
    "ground_range_for_off_nadir_m",
    "horizon_off_nadir_deg",
    "make_skyfield_satellite",
    "off_nadir_at_satellite",
    "propagate_subpoint",
    "quality_score",
    "sensor_cone_radius_m",
    "solar_elevation_deg",
    "swath_footprint_polygon",
    "targets_from_locations",
]
