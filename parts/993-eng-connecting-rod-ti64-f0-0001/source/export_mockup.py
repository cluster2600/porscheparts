#!/usr/bin/env python3
"""Display and fit mock-up of 993-ENG-CONNECTING-ROD-TI64-F0-0001, for polymer FFF.

The rod is `prohibited_pending_engineering`: no polymer or metal copy may ever go
into an engine. This script takes the unchanged F0 master and engraves
"MOCK-UP / NOT FOR USE" 0.6 mm deep into both struts and the cap, so the printed
object carries its own warning (decision 0011). The geometry is otherwise the
F0 design: published center distance, pin and big-end bores, the repository's
own truss topology, rod and cap as two bodies.

    python3 parts/993-eng-connecting-rod-ti64-f0-0001/source/export_mockup.py   # cadsim image
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
MASTER = HERE / "derived" / "connecting_rod_ti64_f0.step"
OUT = HERE / "print"

STRUT_TOP_Z = 7.0            # flat top of the struts in the master
CAP_TOP_Z = 9.375            # flat top of the cap
DEPTH = 0.6                  # engraving depth: 3 layers at 0.2 mm
# The two struts of the F0 master cross in an X: (25, +20) -> (110, -10) and
# (25, -20) -> (110, +10). Each label sits on the long half, before the crossing.
STRUTS = [((25.0, 20.0), (110.0, -10.0), "NOT FOR USE"),
          ((25.0, -20.0), (110.0, 10.0), "MOCK-UP")]
LABEL_X = 52.0               # label center along X, clear of the big-end ring and the crossing


def engrave(shape):
    from build123d import BuildPart, BuildSketch, Location, Locations, Mode, Plane, Text, add, extrude

    with BuildPart() as p:
        add(shape)
        for (x0, y0), (x1, y1), label in STRUTS:
            angle = math.degrees(math.atan2(y1 - y0, x1 - x0))
            cx = LABEL_X
            cy = y0 + (y1 - y0) * (cx - x0) / (x1 - x0)
            with BuildSketch(Plane.XY.offset(STRUT_TOP_Z)):
                with Locations(Location((cx, cy), angle)):
                    Text(label, font_size=4.2)
            extrude(amount=-DEPTH, mode=Mode.SUBTRACT)
        with BuildSketch(Plane.XY.offset(CAP_TOP_Z)):
            with Locations(Location((-34.0, 0.0), 90)):
                Text("MOCK-UP", font_size=4.2)
        extrude(amount=-DEPTH, mode=Mode.SUBTRACT)
    return p.part


def main() -> int:
    from build123d import export_step, export_stl, import_step

    OUT.mkdir(exist_ok=True)
    master = import_step(str(MASTER))
    mock = engrave(master)
    solids = mock.solids()
    if len(solids) != 2 or not all(s.is_valid for s in solids):
        raise SystemExit(f"expected two valid solids (rod, cap), got {len(solids)}")
    # Lay each body on the build plate on its own bottom face, the cap 12 mm clear
    # of the rod. The rod's small end is thicker than its big end and struts, so
    # those print on supports (see print/README.md); the cap is flat and needs none.
    from build123d import Compound, Location
    bb = mock.bounding_box()
    rod, cap = sorted(solids, key=lambda s: -s.volume)
    rb, cb = rod.bounding_box(), cap.bounding_box()
    rod = rod.moved(Location((0, 0, -rb.min.Z)))
    cap = cap.moved(Location((-12.0, 0, -cb.min.Z)))
    mock = Compound(children=[rod, cap])
    export_step(mock, str(OUT / "connecting_rod_f0_mockup.step"))
    export_stl(mock, str(OUT / "connecting_rod_f0_mockup.stl"), tolerance=0.01, angular_tolerance=0.08)
    info = {
        "kind": "mockup",
        "part_id": "993-ENG-CONNECTING-ROD-TI64-F0-0001",
        "purpose": "1:1 display and fit mock-up in polymer; engraved MOCK-UP / NOT FOR USE; "
                   "never for an engine (decision 0011)",
        "master": "derived/connecting_rod_ti64_f0.step",
        "master_sha256": hashlib.sha256(MASTER.read_bytes()).hexdigest(),
        "engraving": [s[2] for s in STRUTS] + ["MOCK-UP (cap)"],
        "engraving_depth_mm": DEPTH,
        "bodies": ["rod", "cap"],
        "volume_mm3": round(mock.volume, 1),
        "bounding_box_mm": [round(v, 2) for v in (bb.size.X, bb.size.Y, bb.size.Z)],
        "print_file": "connecting_rod_f0_mockup.stl",
        "generator": "source/export_mockup.py",
    }
    (OUT / "print.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(info, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
