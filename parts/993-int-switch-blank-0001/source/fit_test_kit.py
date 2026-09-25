#!/usr/bin/env python3
"""Fit-test print kit for 993-INT-SWITCH-BLANK-0001 — three sizes on one plate.

No dimension of the real dashboard opening has been measured (see
evidence/measurement-plan.md). The only published figure is an opening of about
19 x 31 mm, a level-C forum value (SRC-RENNLIST-993-DASHBOARD-LIGHTING-DIMENSIONS).
Rather than pretend to know the fit, this script brackets it: three blanks whose
insert is 0.4 mm under, 0.0 mm and 0.4 mm over the declared opening, each marked
on its back with 1, 2 or 3 dimples. Whichever clicks in and sits flush tells the
real size — that fit result is the evidence the record is missing.

This is a fit-test print of a non-critical trim part (decision 0009), not a
released part. Every value below except the declared opening is a hypothesis.

    python3 parts/993-int-switch-blank-0001/source/fit_test_kit.py   # cadsim image
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "parts" / "993-int-switch-blank-0001" / "print"

DECLARED_OPENING = (19.0, 31.0)          # published, level C — not measured
VARIANTS = {1: -0.4, 2: 0.0, 3: +0.4}    # insert size relative to the declared opening, mm

# Hypotheses (no source): sized for a 0.4 mm nozzle, FFF in ASA or PETG.
FACE_OVERLAP = 1.5      # face margin beyond the declared opening, each side
FACE_THICKNESS = 2.0
FACE_RADIUS = 1.5
FACE_CHAMFER = 0.4      # visible edge, on the build plate
INSERT_DEPTH = 3.0      # locating rim behind the face
RIM_WALL = 1.2
CLIP_WIDTH = 8.0        # flexible tabs on the long sides
CLIP_THICKNESS = 1.2
CLIP_LENGTH = 9.0       # from the back of the face
CLIP_SLOT = 0.6         # gap that frees each tab from the rim
BARB = 0.5              # catch at the tab tip
BARB_HEIGHT = 1.5
DIMPLE_D, DIMPLE_DEPTH = 1.4, 0.5


def blank(delta: float, marks: int):
    from build123d import (BuildPart, BuildSketch, Cylinder, Locations, Mode, Plane, Polygon,
                           Rectangle, RectangleRounded, chamfer, extrude)

    ow, oh = DECLARED_OPENING
    iw, ih = ow + delta, oh + delta                   # insert outer size
    fw, fh = ow + 2 * FACE_OVERLAP, oh + 2 * FACE_OVERLAP
    z0 = FACE_THICKNESS
    with BuildPart() as p:
        # face, visible side on the build plate (z = 0)
        with BuildSketch(Plane.XY):
            RectangleRounded(fw, fh, FACE_RADIUS)
        extrude(amount=FACE_THICKNESS)
        chamfer(p.edges().group_by()[0], FACE_CHAMFER)

        # locating rim, open on the long sides where the clips flex
        with BuildSketch(Plane.XY.offset(z0)):
            Rectangle(iw, ih)
            Rectangle(iw - 2 * RIM_WALL, ih - 2 * RIM_WALL, mode=Mode.SUBTRACT)
            with Locations((iw / 2 - RIM_WALL / 2, 0), (-iw / 2 + RIM_WALL / 2, 0)):
                Rectangle(RIM_WALL + 0.02, CLIP_WIDTH + 2 * CLIP_SLOT, mode=Mode.SUBTRACT)
        extrude(amount=INSERT_DEPTH)

        # two cantilever clips: outer face flush with the insert, barb outward
        tip = z0 + CLIP_LENGTH
        for side in (-1, 1):
            x_out = side * iw / 2
            x_in = x_out - side * CLIP_THICKNESS
            with BuildSketch(Plane.XZ):
                Polygon((x_in, z0 - 0.01), (x_out, z0 - 0.01), (x_out, tip - BARB_HEIGHT),
                        (x_out + side * BARB, tip - BARB_HEIGHT * 0.6), (x_out, tip), (x_in, tip),
                        align=None)
            extrude(amount=CLIP_WIDTH / 2, both=True)

        # size marks: 1, 2 or 3 dimples on the back of the face
        spacing = 2.4
        xs = [(i - (marks - 1) / 2) * spacing for i in range(marks)]
        with Locations(*[(x, -ih / 2 + RIM_WALL + 2.2, z0) for x in xs]):
            Cylinder(DIMPLE_D / 2, DIMPLE_DEPTH * 2, mode=Mode.SUBTRACT)
    return p.part


def main() -> int:
    from build123d import Location, Compound, export_step, export_stl

    OUT.mkdir(parents=True, exist_ok=True)
    solids, report = [], []
    for marks, delta in VARIANTS.items():
        s = blank(delta, marks)
        if not s.is_valid:
            raise SystemExit(f"variant {marks}: invalid solid")
        name = f"switch_blank_fit_{marks}"
        export_stl(s, str(OUT / f"{name}.stl"), tolerance=0.01, angular_tolerance=0.1)
        bb = s.bounding_box()
        report.append({"variant": marks, "dimples": marks,
                       "insert_mm": [round(DECLARED_OPENING[0] + delta, 2), round(DECLARED_OPENING[1] + delta, 2)],
                       "delta_vs_declared_opening_mm": delta,
                       "bounding_box_mm": [round(bb.size.X, 2), round(bb.size.Y, 2), round(bb.size.Z, 2)],
                       "volume_mm3": round(s.volume, 1), "file": f"{name}.stl"})
        solids.append(s.moved(Location(((marks - 2) * 30.0, 0, 0))))
    plate = Compound(children=solids)
    export_stl(plate, str(OUT / "switch_blank_fit_plate.stl"), tolerance=0.01, angular_tolerance=0.1)
    export_step(plate, str(OUT / "switch_blank_fit_plate.step"))
    (OUT / "kit.json").write_text(json.dumps({
        "part_id": "993-INT-SWITCH-BLANK-0001",
        "purpose": "fit test of a non-critical trim part; not a released part (decision 0009)",
        "declared_opening_mm": list(DECLARED_OPENING),
        "declared_opening_source": "SRC-RENNLIST-993-DASHBOARD-LIGHTING-DIMENSIONS (level C, not measured)",
        "orientation": "visible face down on the build plate, clips up, no supports",
        "variants": report,
        "generator": "parts/993-int-switch-blank-0001/source/fit_test_kit.py",
    }, indent=2) + "\n", encoding="utf-8")
    for r in report:
        print(r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
