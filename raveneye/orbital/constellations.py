"""Constellation metadata for the v0.2 supply layer.

Each entry describes a commercial EO constellation we'll pull TLEs for and
treat as a single source of supply. Numbers are public-spec approximations
(see ``docs/orbital_model.md`` for citations); they are not classified or
operationally authoritative.

Add a new constellation by appending a Constellation to ``CONSTELLATIONS``
and verifying that ``celestrak_group`` resolves on
``https://celestrak.org/NORAD/elements/gp.php?GROUP={group}&FORMAT=tle``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class Constellation:
    constellation_id: str
    vendor: str
    sensor_class: str          # EO_HIGHRES | EO_VHR | EO_MEDRES | SAR
    nominal_gsd_m: float
    spectral_bands: Tuple[str, ...]
    max_off_nadir_deg: float
    swath_width_km: float
    slew_rate_deg_s: float
    duty_cycle_pct: float
    celestrak_group: str
    # Delivery-pipeline parameters (notional, vendor-published-spec scale).
    # processing_latency_min — wall-clock from collection end to "image
    # processed and ready to ship". Includes downlink to ground + on-prem
    # processing. Vendors that pitch fast turnaround (Capella, ICEYE) sit
    # at 30-45 min; high-res EO with heavier processing pipelines (Maxar)
    # sits at 3 h; small-sat constellations with a sparser ground network
    # (Planet Dove) sit at 12 h.
    processing_latency_min: float = 60.0
    # delivery_latency_min — handoff from "processed and ready" to "in
    # the customer's hands". Network/API/portal time. Always shorter than
    # processing.
    delivery_latency_min: float = 30.0
    # processing_success_rate — fraction of collected images that survive
    # the processing pipeline. Cloud cover, sensor calibration drift,
    # bad-frame rejection. SAR is illumination-independent so its base
    # rate is higher than EO. The actual roll per allocation is modulated
    # by the access window's quality_score:
    #     effective = base × (0.5 + 0.5 × quality_score)
    processing_success_rate: float = 0.85

    def to_dict(self) -> dict:
        return {
            "constellation_id": self.constellation_id,
            "vendor": self.vendor,
            "sensor_class": self.sensor_class,
            "nominal_gsd_m": self.nominal_gsd_m,
            "spectral_bands": list(self.spectral_bands),
            "max_off_nadir_deg": self.max_off_nadir_deg,
            "swath_width_km": self.swath_width_km,
            "slew_rate_deg_s": self.slew_rate_deg_s,
            "duty_cycle_pct": self.duty_cycle_pct,
            "celestrak_group": self.celestrak_group,
            "processing_latency_min": self.processing_latency_min,
            "delivery_latency_min": self.delivery_latency_min,
            "processing_success_rate": self.processing_success_rate,
        }


CONSTELLATIONS: List[Constellation] = [
    Constellation(
        constellation_id="blacksky",
        vendor="BlackSky",
        sensor_class="EO_HIGHRES",
        nominal_gsd_m=1.0,
        spectral_bands=("PAN",),
        max_off_nadir_deg=45.0,
        swath_width_km=5.5,
        slew_rate_deg_s=1.0,
        duty_cycle_pct=20.0,
        celestrak_group="blacksky",
        processing_latency_min=45.0,
        delivery_latency_min=30.0,
        processing_success_rate=0.85,
    ),
    Constellation(
        constellation_id="skysat",
        vendor="Planet",
        sensor_class="EO_HIGHRES",
        nominal_gsd_m=0.5,
        spectral_bands=("PAN", "MS"),
        max_off_nadir_deg=30.0,
        swath_width_km=5.9,
        slew_rate_deg_s=0.8,
        duty_cycle_pct=15.0,
        celestrak_group="skysat",
        processing_latency_min=60.0,
        delivery_latency_min=30.0,
        processing_success_rate=0.85,
    ),
    Constellation(
        constellation_id="planet_dove",
        vendor="Planet",
        sensor_class="EO_MEDRES",
        nominal_gsd_m=3.0,
        spectral_bands=("MS",),
        max_off_nadir_deg=5.0,
        swath_width_km=25.0,
        slew_rate_deg_s=0.1,
        duty_cycle_pct=80.0,
        celestrak_group="planet",
        processing_latency_min=720.0,   # 12h — sparser ground-station network
        delivery_latency_min=180.0,
        processing_success_rate=0.80,
    ),
    Constellation(
        constellation_id="capella",
        vendor="Capella Space",
        sensor_class="SAR",
        nominal_gsd_m=0.5,
        spectral_bands=("SAR_X",),
        max_off_nadir_deg=60.0,
        swath_width_km=5.0,
        slew_rate_deg_s=1.5,
        duty_cycle_pct=12.0,
        celestrak_group="capella",
        processing_latency_min=30.0,    # SAR fast-turnaround pitch
        delivery_latency_min=15.0,
        processing_success_rate=0.92,   # SAR ignores cloud cover
    ),
    Constellation(
        constellation_id="iceye",
        vendor="ICEYE",
        sensor_class="SAR",
        nominal_gsd_m=1.0,
        spectral_bands=("SAR_X",),
        max_off_nadir_deg=50.0,
        swath_width_km=10.0,
        slew_rate_deg_s=1.5,
        duty_cycle_pct=15.0,
        celestrak_group="iceye",
        processing_latency_min=45.0,
        delivery_latency_min=20.0,
        processing_success_rate=0.92,
    ),
    Constellation(
        constellation_id="maxar_wv",
        vendor="Vantor (Maxar)",
        sensor_class="EO_VHR",
        nominal_gsd_m=0.3,
        spectral_bands=("PAN", "MS", "SWIR"),
        max_off_nadir_deg=45.0,
        swath_width_km=13.0,
        slew_rate_deg_s=3.5,
        duty_cycle_pct=10.0,
        celestrak_group="maxar",
        processing_latency_min=180.0,   # heavier processing for VHR
        delivery_latency_min=60.0,
        processing_success_rate=0.88,
    ),
]


def by_id(constellation_id: str) -> Constellation:
    for c in CONSTELLATIONS:
        if c.constellation_id == constellation_id:
            return c
    raise KeyError(f"unknown constellation: {constellation_id!r}")
