"""Stage the v0.1 flat-map viewer into a directory alongside ``sim.json``."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Dict


def stage_viewer(out_dir: Path, sim: Dict) -> Path:
    """Copy the HTML template + write ``sim.json`` into ``out_dir``.

    Returns the path to the staged ``index.html``.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    template = Path(__file__).resolve().parent / "template.html"
    index_path = out_dir / "index.html"
    shutil.copyfile(template, index_path)
    (out_dir / "sim.json").write_text(json.dumps(sim, indent=2, sort_keys=True) + "\n")
    return index_path
