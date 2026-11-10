"""T5: print-ready study file of the bare-head twin (3MF, fit-check only).

Writes the closed T1 surface as a single-object 3MF in millimetres and
re-reads it to check the round trip. It is a polymer study and fit-check
object: never an engine part, never a metal build file.

Usage: export_print.py SURFACE(.stl|.npz) OUT.3mf REPORT.json
"""

from __future__ import annotations

import hashlib
import json
import sys

import numpy as np

NOTICE = "935 bare-head CAD twin, study only: fit-check object, not an engine part, not a metal build file"


def read_back(path):
    """Stream-parse the written 3MF (no full DOM) and rebuild the mesh."""

    import zipfile

    import trimesh
    from lxml import etree

    verts, tris = [], []
    with zipfile.ZipFile(path) as z:
        name = next(n for n in z.namelist() if n.endswith(".model"))
        with z.open(name) as fh:
            for _, el in etree.iterparse(fh, events=("end",)):
                tag = el.tag.rsplit("}", 1)[-1]
                if tag == "vertex":
                    verts.append((float(el.get("x")), float(el.get("y")), float(el.get("z"))))
                elif tag == "triangle":
                    tris.append((int(el.get("v1")), int(el.get("v2")), int(el.get("v3"))))
                el.clear()
    return trimesh.Trimesh(np.array(verts), np.array(tris), process=False)


def main(src, out, report):
    import trimesh

    if str(src).endswith(".npz"):
        # Indexed body in double precision (loft_stack.py). Its STL is single
        # precision: rounding welds neighbouring vertices of the thinnest
        # triangles and the read-back is no longer watertight (measured).
        d = np.load(src)
        m = trimesh.Trimesh(d["v"], d["f"], process=False)
    else:
        m = trimesh.load(src, force="mesh")
    m.metadata["name"] = "935-bare-head-twin-study"
    m.metadata["notice"] = NOTICE
    data = trimesh.exchange.threemf.export_3MF(m)
    with open(out, "wb") as fh:
        fh.write(data)
    back = read_back(out)
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
