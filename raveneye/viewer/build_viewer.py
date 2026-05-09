"""Stage either the v0.1 flat-map viewer or the v0.2 globe viewer.

Two output shapes:

* ``kind="flat"``  — copies ``template.html`` to ``out_dir/index.html`` and
  writes the scenario JSON as ``sim.json`` (the name the v0.1 template
  fetches). v0.2 scenarios are a strict superset of v0.1 sim shape, so
  events/bids render correctly; the new fields are simply ignored.
* ``kind="globe"`` — copies the ``globe/`` directory contents
  (index.html, *.js, *.css) into ``out_dir`` and writes the scenario JSON
  as ``scenario.json`` (the name the globe's main.js fetches).

Both shapes are static-only: no build step, no bundler, no npm. The
output of either is deployable to any static host (Render, GitHub Pages,
S3+CloudFront, a local ``python3 -m http.server``).
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict


_HERE = Path(__file__).parent
_FLAT_TEMPLATE = _HERE / "template.html"
_GLOBE_DIR = _HERE / "globe"


def stage_viewer(
    out_dir: Path,
    scenario: Dict[str, Any],
    *,
    kind: str = "flat",
) -> Path:
    """Stage a viewer + its data file into ``out_dir``.

    Returns the absolute resolved path to the staged directory.
    """
    if kind not in ("flat", "globe"):
        raise ValueError(f"kind must be 'flat' or 'globe', got {kind!r}")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if kind == "flat":
        shutil.copyfile(_FLAT_TEMPLATE, out_dir / "index.html")
        with (out_dir / "sim.json").open("w", encoding="utf-8") as f:
            json.dump(scenario, f, indent=2, sort_keys=True)
    else:  # globe
        if not _GLOBE_DIR.is_dir():
            raise FileNotFoundError(
                f"globe assets not found at {_GLOBE_DIR}; reinstall the package "
                "(pip install -e .) so package_data is included"
            )
        for src in _GLOBE_DIR.iterdir():
            if src.is_file():
                shutil.copyfile(src, out_dir / src.name)
        with (out_dir / "scenario.json").open("w", encoding="utf-8") as f:
            json.dump(scenario, f, indent=2, sort_keys=True)

    return out_dir.resolve()
