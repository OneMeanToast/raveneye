"""Stage the v0.1 flat-map viewer into an output directory."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict


_TEMPLATE = Path(__file__).parent / "template.html"


def stage_viewer(out_dir: Path, sim: Dict[str, Any]) -> Path:
    """Copy template.html → out_dir/index.html and write sim.json alongside.

    Returns the absolute path to the staged directory.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_TEMPLATE, out_dir / "index.html")
    with (out_dir / "sim.json").open("w", encoding="utf-8") as f:
        json.dump(sim, f, indent=2, sort_keys=True)
    return out_dir.resolve()
