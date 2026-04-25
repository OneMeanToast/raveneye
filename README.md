# RavenEye

Multi-constellation EO tasking simulation for evaluating satellite-tasking
allocation mechanisms under realistic military collection demand.

This repo is in early development. v0.1 ships the **demand layer**: events,
stakeholder bids, phase-driven scenario tempo, and a flat choke-point map
viewer for the Strait of Hormuz blockade arc (April 2026).

## Install

```
pip install -e ".[dev]"
```

Python 3.10+. v0.1 has no runtime dependencies beyond the standard library.

## Generate a scenario

```
raveneye-generate --seed 42 --out data/sample_sim.json --stats
```

Optional `--viewer out/` stages the flat-map viewer into `out/`; serve with
`python3 -m http.server` from that directory.

## Canonical reference output

`data/sample_sim.json` is the canonical `seed=42`, `duration=168h` reference
output, committed to the repo. Tests pin invariants against this seed; if you
change `BASE_RATES`, sampling logic, or any data shape, regenerate it with the
command above and review the diff.

## License

MIT. See `LICENSE`.
