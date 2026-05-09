# Orbital model — TLEs, SGP4, access windows, quality scoring

The v0.2 supply layer wraps three pieces of public infrastructure:

- **CelesTrak** — public catalog of TLEs / OMM elsets for active payloads.
- **`sgp4`** (Brandon Rhodes / Dave Vallado) — Python wrapper around the
  reference SGP4 propagator from AIAA 2006-6753.
- **`skyfield`** (Brandon Rhodes) — high-level astronomical computations,
  including `EarthSatellite` (which itself wraps `sgp4`) and the
  `find_events()` rise/culminate/set search.

Citations for vendor-spec defaults in `constellations.py` are listed at
the bottom of this document.

## TLE primer

A two-line element set encodes Keplerian orbit parameters as published by
USSF for cataloged objects. Format reference: NASA / NORAD memo
`SPACETRK Report #3` and the Vallado *Fundamentals* §SGP4 chapter. Each
TLE has:

```
ISS (ZARYA)
1 25544U 98067A   24015.50000000  .00012345  00000-0  22345-3 0  9998
2 25544  51.6400 100.0000 0001234  90.0000 270.0000 15.50000000123450
```

| Field (line 1) | Meaning |
|---|---|
| col 3–7    | NORAD catalog ID |
| col 19–32  | epoch (year + day-of-year fractional UTC) |
| col 34–43  | first time-derivative of mean motion / 2 |
| col 45–52  | second time-derivative of mean motion / 6 (decimal-exponent format) |
| col 54–61  | B* drag term (decimal-exponent format) |
| col 65–68  | element-set classification + element number |
| col 69     | line-1 checksum |

| Field (line 2) | Meaning |
|---|---|
| col 9–16   | inclination (degrees) |
| col 18–25  | RAAN (degrees) |
| col 27–33  | eccentricity (×1e-7) |
| col 35–42  | argument of perigee (degrees) |
| col 44–51  | mean anomaly (degrees) |
| col 53–63  | mean motion (revs/day) + revolution number |
| col 69     | line-2 checksum |

`raveneye.orbital.tle_ingest.parse_tle_text` is tolerant of trailing
whitespace and of malformed three-line blocks (logs and skips them).

## OMM — the post-overflow successor

CelesTrak's 5-digit NORAD catalog will exhaust around **2026-07-20**.
After that, new objects are published only as OMM (Orbit Mean-Elements
Message, CCSDS standard) JSON records — TLE-format becomes lossy for
6-digit catalog IDs.

The v0.2 supply layer plans for OMM from day one:

- `tle_ingest.fetch_omm_group(group, cache_dir)` fetches OMM JSON.
- `tle_ingest.load_cached_or_fetch(...)` tries TLE first, falls back to
  OMM on any HTTP error or empty response, then converts back to TLE
  triples via `omm_records_to_tle_triples`.
- For genuinely 6-digit catalog records that lack legacy TLE lines,
  `propagate.py` will need a small future patch to use `sgp4`'s OMM
  ingestion path (`Satrec.sgp4init` from OMM fields). v0.2 does not
  contain that yet — it is the only known forward-compatibility hook.

## SGP4 accuracy bounds

SGP4 propagation error grows with TLE epoch age:

| Δt from TLE epoch | Typical position error |
|---|---|
| 0 – 24 h  | < 1 km |
| 24 – 72 h | 1 – 3 km |
| 3 – 7 days | 3 – 10 km |
| > 7 days  | degrades non-linearly; refresh TLEs |

`build_satellites()` logs (does not drop) any sat whose TLE epoch is
more than 7 days from scenario t0.

The v0.2 quality_score does not attempt to model position error — for
the scenario lengths we run (≤ 168 h) and a daily TLE refresh policy,
the geometry is dominated by access-window topology, not propagation
drift.

## Cesium / satellite.js position-agreement requirement

The viewer propagates satellite positions in the browser via
`satellite.js` (a separate, MIT-licensed JS implementation of the
Vallado SGP4 reference). The v0.2 spec demands ≤1 km horizontal
disagreement between Python (Skyfield) and JS (satellite.js) at any
sample time within the scenario span.

Both implementations descend from the same Vallado source; the most
common cause of disagreement in a deployment is a coordinate-frame
mistake — TEME vs ECI vs ECEF — at the consumer. RavenEye's globe
uses ECEF (Earth-Fixed) for both propagators and Cesium scene graph,
so the chain is consistent.

`scripts/verify_position_agreement.py` emits a JSON reference table of
WGS84 (lat, lon, alt) for the configured satellite × time grid; the
companion JS-side comparator is small (~30 lines) and slots into the
viewer behind a `?agreement=1` URL flag in chunk-8 follow-on work.

## Access windows

`access.find_access_windows(satellites, targets, t0, duration_hours,
min_elevation_deg=20.0)` walks each (sat, target) pair through Skyfield's
`EarthSatellite.find_events()` and assembles rise / culminate / set
triples into windows. Defensive handling for the well-known Skyfield
edge cases (mid-pass start, missing culmination, sub-30 s blips) lives
in `_windows_from_events`.

Per-window fields:

| Field | Source |
|---|---|
| `start_iso`, `end_iso` | rise-time, set-time UTC |
| `culminate_iso` | culmination time (inserted ~midpoint when Skyfield omits it) |
| `duration_s` | end − start |
| `max_elevation_deg` | altitude angle at culmination |
| `off_nadir_at_culminate_deg` | spherical-Earth law-of-sines: `arcsin(R/(R+h)·cos(elev))` |
| `sun_elevation_deg` | analytical NOAA solar position at the target lat/lon at mid-window |
| `quality_score` | composite, see below |

Off-nadir constraint: a window whose required off-nadir at culmination
exceeds the satellite's `max_off_nadir_deg` is dropped at the source.

Sun-elevation: the v0.2 supply layer does not require the JPL ephemeris
file (`de421.bsp`) — the analytical NOAA solar position approximation
is accurate to < 1° everywhere on Earth, which is more than adequate for
a tasking quality score that just discounts by `max(0, sun_elev/30)`.
Tests therefore stay fully offline.

## Quality score

```
EO:  q = 0.4 · (max_elev / 90)
       + 0.3 · max(0, sun_elev / 30)
       + 0.3 · max(0, 1 − |off_nadir| / 45)

SAR: q = 0.55 · (max_elev / 90)
       + 0.45 · max(0, 1 − |off_nadir| / 45)
       (sun term dropped — SAR is illumination-independent)
```

All three terms are clipped to [0, 1] so `q ∈ [0, 1]`. Tuning rationale:
elevation dominates because higher-elevation passes have shorter ground
range and longer integration; sun matters for EO but not SAR; off-nadir
captures both image-quality (foreshortening) and slew-cost terms.

## Sensor-coverage geometry (`coverage.py`)

These helpers are used only by the globe viewer to draw instantaneous
swath polygons during access windows — they're not in the access-window
feasibility decision (windows already encode that).

```python
horizon_off_nadir_deg(altitude_m)           # tangent-to-Earth limit
sensor_cone_radius_m(altitude_m, max_n_deg) # ground reach at max off-nadir
ground_range_for_off_nadir_m(alt_m, n_deg)  # boresight ground-range
swath_footprint_polygon(lat, lon, alt_m,
                        off_nadir_deg, az_deg,
                        swath_width_km)     # 5-corner closed polygon
```

Spherical-Earth approximation; sub-1% error at typical commercial-EO
swath scales (≤ 25 km).

## Constellations and vendor specs

`raveneye.orbital.constellations.CONSTELLATIONS` lists six commercial
constellations with public-spec sensor parameters:

| ID | Vendor | Class | GSD (m) | Bands | Off-nadir | Swath (km) | Slew (°/s) | Duty (%) |
|---|---|---|---|---|---|---|---|---|
| `blacksky` | BlackSky | EO_HIGHRES | 1.0 | PAN | 45° | 5.5 | 1.0 | 20 |
| `skysat` | Planet | EO_HIGHRES | 0.5 | PAN, MS | 30° | 5.9 | 0.8 | 15 |
| `planet_dove` | Planet | EO_MEDRES | 3.0 | MS | 5° | 25 | 0.1 | 80 |
| `capella` | Capella Space | SAR | 0.5 | SAR_X | 60° | 5 | 1.5 | 12 |
| `iceye` | ICEYE | SAR | 1.0 | SAR_X | 50° | 10 | 1.5 | 15 |
| `maxar_wv` | Vantor (Maxar) | EO_VHR | 0.3 | PAN, MS, SWIR | 45° | 13 | 3.5 | 10 |

Sources (all public marketing / capability briefs as of late 2024):

- BlackSky: <https://www.blacksky.com/our-platform/>
- Planet SkySat: <https://www.planet.com/products/skysat/>
- Planet Dove / SuperDove: <https://www.planet.com/products/planet-imagery/>
- Capella Space: <https://www.capellaspace.com/products/>
- ICEYE: <https://www.iceye.com/satellite-data/sar-products>
- Maxar (Vantor): <https://www.maxar.com/products/imagery>

Numbers are *approximate*. Operational systems negotiate finer specs per
contract; this table is for unclassified evaluation work and should not
be cited as authoritative for any specific bird.

## CelesTrak rate-limit and cache policy

CelesTrak asks for ≤ 1 request per group per 2 hours. RavenEye's
default cache window is 24 hours per group (`max_age_hours=24`), keyed
by group name + UTC date. The on-disk cache lives under
`data/tle_cache/<group>__YYYYMMDD.{tle,json}`; contents are gitignored,
the directory is kept via `.gitkeep`.

CI never fetches: every test in `tests/test_tle_ingest.py` and
`tests/test_propagate.py` uses a committed fixture (`tests/fixtures/tles.txt`)
with `requests.get` monkeypatched. `--refresh-tles` on the CLI bypasses
the cache for users with a fresh-elements need.
