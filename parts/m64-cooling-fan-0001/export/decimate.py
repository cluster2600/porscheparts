#!/usr/bin/env python3
"""Decimate PicoGK voxel-surface STLs for BRep conversion (mesh pre-step).

Input:  raw/m64-{rotor,housing}-mm.stl (PicoGK, voxel 0.65 mm, watertight)
Output: derived/m64-{rotor,housing}-decim.stl (~40k faces, watertightness re-checked)
PicoGK raw meshes remain the authoritative derived meshes; these decimated
meshes exist only so FreeCAD/OpenCascade can build a manageable STEP.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pymeshlab as pml
import trimesh

HERE = Path(__file__).resolve().parent
OUT = HERE / "derived"
OUT.mkdir(exist_ok=True)

TARGET_FACES = 40000
report = {"target_faces": TARGET_FACES, "simplifier": "pymeshlab quadric edge collapse (cluster_threshold 0)", "parts": {}}

for part in ("rotor", "housing"):
    src = HERE / "raw" / f"m64-{part}-mm.stl"
    ms = pml.MeshSet()
    ms.load_new_mesh(str(src))
    before = ms.current_mesh().face_number()
    ms.meshing_decimation_quadric_edge_collapse(
        targetfacenum=TARGET_FACES, preservenormal=True, preservetopology=True, preserveboundary=True, boundaryweight=10)
    dst = OUT / f"m64-{part}-decim.stl"
    ms.save_current_mesh(str(dst))
    m = trimesh.load(dst, force="mesh")
    report["parts"][part] = {
        "input": str(src.relative_to(HERE)), "faces_before": before,
        "faces_after": int(len(m.faces)), "watertight_after": bool(m.is_watertight),
        "euler_number_after": int(m.euler_number),
        "volume_mm3_recomputed": float(m.volume) if m.is_volume else None,
        "components": int(m.body_count),
    }
    print(part, report["parts"][part])
    ms = None

(OUT / "decimation-report.json").write_text(json.dumps(report, indent=2))
print("OK")
