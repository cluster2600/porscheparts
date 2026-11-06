"""T5: print-ready study file of the bare-head twin (3MF, fit-check only).

Writes the closed T1 surface as a single-object 3MF in millimetres and
re-reads it to check the round trip. It is a polymer study and fit-check
object: never an engine part, never a metal build file.

Usage: export_print.py T1.stl OUT.3mf REPORT.json
"""

from __future__ import annotations

import hashlib
import json
import sys

import numpy as np

NOTICE = "935 bare-head CAD twin, study only: fit-check object, not an engine part, not a metal build file"


def main(src, out, report):
    import trimesh

    m = trimesh.load(src, force="mesh")
    m.metadata["name"] = "935-bare-head-twin-study"
    m.metadata["notice"] = NOTICE
    data = trimesh.exchange.threemf.export_3mf(m)
    with open(out, "wb") as fh:
        fh.write(data)
    back = trimesh.load(out, force="mesh")
    rep = {
        "schema": "935-cad-twin-print/1",
        "notice": NOTICE,
        "units": "millimeter",
        "triangles": int(len(back.faces)),
        "watertight": bool(back.is_watertight),
        "winding_consistent": bool(back.is_winding_consistent),
        "volume_mm3": round(float(back.volume), 1),
        "source_volume_mm3": round(float(m.volume), 1),
        "round_trip_volume_relative_difference": float(abs(back.volume - m.volume) / m.volume),
        "bounds_mm": np.round(back.bounds, 3).tolist(),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    with open(report, "w") as fh:
        json.dump(rep, fh, indent=2)
    print(json.dumps(rep))


if __name__ == "__main__":
    main(*sys.argv[1:4])
