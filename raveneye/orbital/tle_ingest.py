"""TLE / OMM ingestion from CelesTrak with on-disk caching.

CelesTrak asks for ≤1 request per group per 2 hours. We cache by group name
and date so repeat runs in the same day reuse a single fetch.

The 5-digit NORAD catalog overflows around 2026-07-20; once that happens,
new satellites are only published in OMM (CCSDS JSON). ``fetch_omm_group``
exists to handle that path; the loader prefers TLE when available and falls
back to OMM.

This module does NOT propagate orbits. SGP4/Skyfield wiring lives in
``raveneye.orbital.propagate``.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


CELESTRAK_GP_URL = "https://celestrak.org/NORAD/elements/gp.php"
DEFAULT_TIMEOUT_S = 30.0
DEFAULT_USER_AGENT = "RavenEye/0.2 (+https://github.com/OneMeanToast/raveneye)"

# Tuple shape for parsed TLE: (satellite_name, line1, line2)
TleTriple = Tuple[str, str, str]


# ----------------------------------------------------------------------
# Cache helpers
# ----------------------------------------------------------------------

def _cache_path(cache_dir: Path, group_name: str, fmt: str, *, date: Optional[str] = None) -> Path:
    """Cache file path: ``<cache_dir>/<group>__<YYYYMMDD>.<fmt>``."""
    date = date or datetime.now(timezone.utc).strftime("%Y%m%d")
    safe_group = group_name.replace("/", "_")
    return Path(cache_dir) / f"{safe_group}__{date}.{fmt}"


def _cache_age_hours(path: Path) -> float:
    if not path.exists():
        return float("inf")
    age_s = datetime.now(timezone.utc).timestamp() - path.stat().st_mtime
    return age_s / 3600.0


# ----------------------------------------------------------------------
# Parsing
# ----------------------------------------------------------------------

def parse_tle_text(text: str) -> List[TleTriple]:
    """Parse a CelesTrak TLE-format response into ``(name, l1, l2)`` triples.

    Tolerates trailing whitespace/blank lines. Rejects malformed groups by
    skipping them with a warning rather than raising.
    """
    triples: List[TleTriple] = []
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    i = 0
    while i + 2 < len(lines) + 1:
        if i + 2 >= len(lines):
            break
        name = lines[i].strip()
        l1 = lines[i + 1]
        l2 = lines[i + 2]
        if l1.startswith("1 ") and l2.startswith("2 "):
            triples.append((name, l1, l2))
            i += 3
        else:
            logger.warning("skipping malformed TLE block at line %d: %r", i, name[:40])
            i += 1
    return triples


def parse_omm_json(text: str) -> List[Dict[str, Any]]:
    """Parse a CelesTrak OMM-JSON response into a list of dicts.

    Returns the raw OMM records. Downstream callers can hand these to
    ``sgp4.api.Satrec.twoline2rv`` indirectly via the OMM-to-elements path,
    or use sgp4's ``omm.initialize`` (sgp4 >= 2.20).
    """
    if not text.strip():
        return []
    payload = json.loads(text)
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        raise ValueError(f"unexpected OMM payload type: {type(payload).__name__}")
    return payload


# ----------------------------------------------------------------------
# Fetchers
# ----------------------------------------------------------------------

def _fetch_text(url: str, *, params: Dict[str, str], timeout_s: float) -> str:
    headers = {"User-Agent": DEFAULT_USER_AGENT, "Accept": "*/*"}
    resp = requests.get(url, params=params, headers=headers, timeout=timeout_s)
    resp.raise_for_status()
    return resp.text


def fetch_tle_group(
    group_name: str,
    cache_dir: Path,
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    force_refresh: bool = False,
) -> List[TleTriple]:
    """Fetch a CelesTrak TLE group (or read today's cache).

    Writes the raw response to ``<cache_dir>/<group>__YYYYMMDD.tle`` so the
    same dev cycle can re-import without re-fetching.

    Raises:
        requests.HTTPError on non-2xx response.
        OSError on filesystem error writing the cache.
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = _cache_path(cache_dir, group_name, "tle")
    if path.exists() and not force_refresh:
        return parse_tle_text(path.read_text(encoding="utf-8"))

    params = {"GROUP": group_name, "FORMAT": "tle"}
    text = _fetch_text(CELESTRAK_GP_URL, params=params, timeout_s=timeout_s)
    path.write_text(text, encoding="utf-8")
    return parse_tle_text(text)


def fetch_omm_group(
    group_name: str,
    cache_dir: Path,
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    force_refresh: bool = False,
) -> List[Dict[str, Any]]:
    """Fetch a CelesTrak OMM (JSON) group with caching.

    Use this as a fallback when TLE format is unavailable (post-NORAD-overflow
    satellites) or to access richer fields than TLEs encode.
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = _cache_path(cache_dir, group_name, "json")
    if path.exists() and not force_refresh:
        return parse_omm_json(path.read_text(encoding="utf-8"))

    params = {"GROUP": group_name, "FORMAT": "json"}
    text = _fetch_text(CELESTRAK_GP_URL, params=params, timeout_s=timeout_s)
    path.write_text(text, encoding="utf-8")
    return parse_omm_json(text)


def load_cached_or_fetch(
    group_name: str,
    cache_dir: Path,
    *,
    max_age_hours: float = 24.0,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    prefer: str = "tle",
) -> List[TleTriple]:
    """Return TLE triples, using cache when fresh, else re-fetching.

    ``max_age_hours`` enforces the rate-limit-friendly default of 1 fetch per
    24 hours per group. Set to a smaller value for dev iteration; do NOT set
    below 2.0 in CI — CelesTrak will throttle.

    ``prefer`` controls fallback: with ``prefer="tle"``, we try TLE first and
    only fall back to OMM->TLE conversion on failure. With ``prefer="omm"``,
    we go straight to OMM.
    """
    cache_dir = Path(cache_dir)
    tle_path = _cache_path(cache_dir, group_name, "tle")

    if prefer == "tle":
        if tle_path.exists() and _cache_age_hours(tle_path) <= max_age_hours:
            return parse_tle_text(tle_path.read_text(encoding="utf-8"))
        try:
            return fetch_tle_group(group_name, cache_dir, timeout_s=timeout_s, force_refresh=True)
        except (requests.HTTPError, requests.ConnectionError, requests.Timeout) as e:
            logger.warning(
                "TLE fetch for %r failed (%s); falling back to OMM", group_name, e
            )
            omm = fetch_omm_group(group_name, cache_dir, timeout_s=timeout_s, force_refresh=True)
            return omm_records_to_tle_triples(omm)
    elif prefer == "omm":
        omm = fetch_omm_group(group_name, cache_dir, timeout_s=timeout_s)
        return omm_records_to_tle_triples(omm)
    raise ValueError(f"prefer must be 'tle' or 'omm', got {prefer!r}")


# ----------------------------------------------------------------------
# OMM -> TLE shim
# ----------------------------------------------------------------------

def omm_records_to_tle_triples(records: List[Dict[str, Any]]) -> List[TleTriple]:
    """Best-effort conversion of OMM JSON records to (name, l1, l2) triples.

    OMM records from CelesTrak typically include ``TLE_LINE0``,
    ``TLE_LINE1``, ``TLE_LINE2`` fields when the original elset was a TLE.
    For post-overflow records that lack TLE lines, we skip the entry and
    log — proper sgp4 OMM ingestion is owned by ``propagate.py`` so we don't
    silently lose information here.
    """
    out: List[TleTriple] = []
    for rec in records:
        line0 = rec.get("TLE_LINE0") or rec.get("OBJECT_NAME") or ""
        line1 = rec.get("TLE_LINE1")
        line2 = rec.get("TLE_LINE2")
        name = line0.replace("0 ", "", 1).strip() or rec.get("OBJECT_NAME", "UNKNOWN")
        if line1 and line2:
            out.append((name, line1, line2))
        else:
            logger.info(
                "OMM record for %r has no TLE lines; propagation must use sgp4 OMM path",
                name,
            )
    return out
