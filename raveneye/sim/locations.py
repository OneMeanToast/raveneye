"""Named locations for the Hormuz scenario and their sensor requirements.

Coordinates are WGS84 decimal degrees, approximate. All placements are drawn
from public maps; this is an unclassified demo scenario.
"""
from __future__ import annotations

from typing import Dict

from .events import ObservableKind


LOCATIONS: Dict[str, Dict] = {
    "bandar_abbas_naval": {
        "name": "Bandar Abbas Naval Base",
        "kind": ObservableKind.MILITARY_BASE,
        "lat": 27.129,
        "lon": 56.217,
        "country": "IR",
    },
    "bandar_jask": {
        "name": "Bandar-e Jask Naval Base",
        "kind": ObservableKind.MILITARY_BASE,
        "lat": 25.644,
        "lon": 57.776,
        "country": "IR",
    },
    "qeshm_island": {
        "name": "Qeshm Island IRGC Facilities",
        "kind": ObservableKind.MILITARY_BASE,
        "lat": 26.954,
        "lon": 56.270,
        "country": "IR",
    },
    "larak_island": {
        "name": "Larak Island",
        "kind": ObservableKind.WIDE_AREA,
        "lat": 26.867,
        "lon": 56.367,
        "country": "IR",
    },
    "hormuz_island": {
        "name": "Hormuz Island",
        "kind": ObservableKind.WIDE_AREA,
        "lat": 27.093,
        "lon": 56.462,
        "country": "IR",
    },
    "kharg_terminal": {
        "name": "Kharg Island Oil Terminal",
        "kind": ObservableKind.REFINERY,
        "lat": 29.232,
        "lon": 50.325,
        "country": "IR",
    },
    "siri_island": {
        "name": "Siri Island Storage",
        "kind": ObservableKind.REFINERY,
        "lat": 25.900,
        "lon": 54.508,
        "country": "IR",
    },
    "bandar_mahshahr": {
        "name": "Bandar Mahshahr Petrochemical",
        "kind": ObservableKind.REFINERY,
        "lat": 30.558,
        "lon": 49.198,
        "country": "IR",
    },
    "fujairah_port": {
        "name": "Port of Fujairah",
        "kind": ObservableKind.PORT_FACILITY,
        "lat": 25.162,
        "lon": 56.358,
        "country": "AE",
    },
    "jebel_ali": {
        "name": "Jebel Ali Port",
        "kind": ObservableKind.PORT_FACILITY,
        "lat": 25.013,
        "lon": 55.062,
        "country": "AE",
    },
    "ras_laffan": {
        "name": "Ras Laffan LNG Terminal",
        "kind": ObservableKind.REFINERY,
        "lat": 25.919,
        "lon": 51.568,
        "country": "QA",
    },
    "ras_tanura": {
        "name": "Ras Tanura Refinery",
        "kind": ObservableKind.REFINERY,
        "lat": 26.642,
        "lon": 50.154,
        "country": "SA",
    },
    "mina_sulman": {
        "name": "Mina Sulman / NSA Bahrain",
        "kind": ObservableKind.MILITARY_BASE,
        "lat": 26.203,
        "lon": 50.613,
        "country": "BH",
    },
    "strait_chokepoint": {
        "name": "Strait of Hormuz Narrowest Point",
        "kind": ObservableKind.WIDE_AREA,
        "lat": 26.567,
        "lon": 56.250,
        "country": "INTL",
    },
    "gulf_of_oman_outbound": {
        "name": "Gulf of Oman Approach",
        "kind": ObservableKind.WIDE_AREA,
        "lat": 25.200,
        "lon": 57.500,
        "country": "INTL",
    },
}


SENSOR_REQUIREMENTS: Dict[ObservableKind, Dict] = {
    ObservableKind.VESSEL: {"gsd_m": 0.5, "band": "EO_PAN", "revisit_h": 6},
    ObservableKind.PORT_FACILITY: {"gsd_m": 0.5, "band": "EO_MS", "revisit_h": 12},
    ObservableKind.REFINERY: {"gsd_m": 1.0, "band": "EO_MS+TIR", "revisit_h": 12},
    ObservableKind.MILITARY_BASE: {"gsd_m": 0.3, "band": "EO_PAN", "revisit_h": 8},
    ObservableKind.ROUTE_SEGMENT: {"gsd_m": 1.0, "band": "EO_MS", "revisit_h": 4},
    ObservableKind.WIDE_AREA: {"gsd_m": 3.0, "band": "SAR_X", "revisit_h": 6},
    ObservableKind.AIRFIELD: {"gsd_m": 0.5, "band": "EO_PAN", "revisit_h": 8},
}
