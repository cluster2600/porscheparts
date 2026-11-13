#!/usr/bin/env python3
"""Software witness for the fatigue post-processor (pyLife).

Two checks, each against a reference that does not come from pyLife:

1. Rainflow counting of the worked example in ASTM E1049-85 (reapproved 2017),
   the load history -2, 1, -3, 5, -1, 3, -4, 4, -2. Counting it by hand with the
   standard's three-point procedure gives ranges 3, 4, 6, 8, 9 with 0.5, 1.5,
   0.5, 1.0, 0.5 cycles; ``astm_rainflow`` below implements that procedure
   independently and must agree.
2. Palmgren-Miner damage of that collective on a Basquin S-N line,
   N = ND (S/SD)^-k, against the closed form, for Miner "original" (no damage
   below SD) and Miner "elementary" (the line continued below SD).

The S-N parameters are arbitrary round numbers. This qualifies the counting
and damage arithmetic only: no material, alloy, process, mean-stress or
notch property of any part follows from it.
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np

HISTORY = (-2.0, 1.0, -3.0, 5.0, -1.0, 3.0, -4.0, 4.0, -2.0)
ASTM_TABLE = {3.0: 0.5, 4.0: 1.5, 6.0: 0.5, 8.0: 1.0, 9.0: 0.5}
UNIT_RANGE_MPA = 40.0          # one history unit of range = 40 MPa, so amplitude = 20 MPa per unit
SN = {"k_1": 5.0, "ND": 1.0e6, "SD": 100.0}   # amplitude SD in MPa


def astm_rainflow(history):
    """ASTM E1049 three-point rainflow, steps 1-6, as written in the standard."""
    points, start, counts = [], 0, Counter()
    for value in history:
        points.append(value)
        while len(points) >= 3:
            x = abs(points[-1] - points[-2])
            y = abs(points[-2] - points[-3])
            if x < y:
                break
            if len(points) - 3 == start:          # Y contains the starting point S
                counts[y] += 0.5
                points.pop(-3)
            else:
                counts[y] += 1.0
                del points[-3:-1]
    for a, b in zip(points[:-1], points[1:]):
        counts[abs(b - a)] += 0.5
    return dict(sorted(counts.items()))


def pylife_rainflow(history):
    import pylife.stress.rainflow as rainflow
    import pylife.stress.rainflow.recorders as recorders

    recorder = recorders.FullRecorder()
    detector = rainflow.ThreePointDetector(recorder=recorder).process(np.asarray(history))
    counts = Counter()
    for a, b in zip(recorder.values_from, recorder.values_to):
        counts[float(abs(b - a))] += 1.0
    residuals = list(detector.residuals)
    for a, b in zip(residuals[:-1], residuals[1:]):
        counts[float(abs(b - a))] += 0.5
    return dict(sorted(counts.items()))


def closed_form_damage(collective, elementary):
    damage = 0.0
    for amplitude, n in collective.items():
        if amplitude < SN["SD"] and not elementary:
            continue
        damage += n / (SN["ND"] * (amplitude / SN["SD"]) ** -SN["k_1"])
    return damage


def pylife_damage(collective, elementary):
    import pandas as pd
    from pylife.materiallaws import WoehlerCurve

    curve = WoehlerCurve(pd.Series({**SN, "TN": 1.0, "TS": 1.0}))
    curve = curve.miner_elementary() if elementary else curve.miner_original()
    amplitudes = np.array(list(collective))
    cycles = np.asarray(curve.cycles(amplitudes), dtype=float)
    return float(np.sum(np.array(list(collective.values())) / cycles))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    import pylife

    reference = astm_rainflow(HISTORY)
    if reference != ASTM_TABLE:
        raise SystemExit(f"Independent ASTM implementation disagrees with the standard's table: {reference}")
    counted = pylife_rainflow(HISTORY)
    collective = {UNIT_RANGE_MPA * r / 2: n for r, n in counted.items()}
    damage = {}
    for name, elementary in (("miner_original", False), ("miner_elementary", True)):
        expected = closed_form_damage(collective, elementary)
        got = pylife_damage(collective, elementary)
        damage[name] = {"pylife": got, "closed_form": expected, "relative_error": abs(got / expected - 1)}
    report = {
        "schema": "fatigue-postprocessor-witness/1",
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "lock_sha256": hashlib.sha256((Path(__file__).parent / "requirements.lock.txt").read_bytes()).hexdigest(),
        "pylife": pylife.__version__,
        "numpy": np.__version__,
        "rainflow": {"history": list(HISTORY), "astm_e1049_table": {str(k): v for k, v in ASTM_TABLE.items()},
                     "pylife_three_point": {str(k): v for k, v in counted.items()},
                     "matches_astm": counted == ASTM_TABLE},
        "damage": {"sn_line": SN, "amplitude_mpa_per_range_unit": UNIT_RANGE_MPA / 2,
                   "collective_amplitude_mpa": {str(k): v for k, v in collective.items()}, **damage},
        "passed": counted == ASTM_TABLE and all(d["relative_error"] < 1e-12 for d in damage.values()),
        "claims": "counting and damage arithmetic only; no material, alloy, AM process, mean-stress or notch data",
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"matches_astm": report["rainflow"]["matches_astm"],
                      **{k: v["relative_error"] for k, v in damage.items()}, "passed": report["passed"]}))


if __name__ == "__main__":
    main()
