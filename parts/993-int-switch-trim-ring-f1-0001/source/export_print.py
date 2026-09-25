#!/usr/bin/env python3
"""Export the F1 master of 993-INT-SWITCH-TRIM-RING-F1-0001 for polymer FFF printing.

The geometry is the repository's F1 design, unchanged: derived/switch_trim_ring_f1.step
is re-tessellated finely into print/. Nothing is added or compensated in the CAD;
first-layer compensation is a slicer setting (see print/README.md).
Run in the cadsim image (build123d).
"""
import hashlib, json
from pathlib import Path
from build123d import import_step, export_stl

HERE = Path(__file__).resolve().parents[1]
step = HERE / "derived" / "switch_trim_ring_f1.step"
out = HERE / "print"
out.mkdir(exist_ok=True)
shape = import_step(str(step))
if not shape.is_valid:
    raise SystemExit("invalid master")
export_stl(shape, str(out / "switch_trim_ring_f1_print.stl"), tolerance=0.005, angular_tolerance=0.05)
bb = shape.bounding_box()
print(json.dumps({"volume_mm3": round(shape.volume, 1),
                  "bounding_box_mm": [round(bb.size.X, 2), round(bb.size.Y, 2), round(bb.size.Z, 2)],
                  "master_sha256": hashlib.sha256(step.read_bytes()).hexdigest()}))
