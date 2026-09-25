#!/usr/bin/env python3
"""K16 wheel pair on a display stand: engraved 1:1 mock-ups plus the stand.

Both wheels are `prohibited_pending_engineering`: no copy of either may ever spin
in a turbocharger. Per decision 0011 they are published only as display mock-ups
with MOCK-UP / NOT FOR USE engraved into their back face (mirrored, so it reads
correctly from behind). The wheel geometry is otherwise the unchanged master:

- compressor: 993-ENG-K16-COMPRESSOR-WHEEL-AL2139-F1-0001, derived/compressor_wheel_al2139_f1.step
- turbine:    993-ENG-K16-TURBINE-WHEEL-IN718-F0-0001,     derived/turbine_wheel_in718_f0.step

The stand is a new, non-critical display design of the repository: a base with a
pocket for each wheel's back, a peg in the compressor's 6 mm bore, and an
engraved nameplate.

    python3 parts/993-eng-k16-compressor-wheel-al2139-f1-0001/source/k16_display_pair.py   # cadsim image
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
COMP = ROOT / "parts" / "993-eng-k16-compressor-wheel-al2139-f1-0001"
TURB = ROOT / "parts" / "993-eng-k16-turbine-wheel-in718-f0-0001"
COMP_STEP = COMP / "derived" / "compressor_wheel_al2139_f1.step"
TURB_STEP = TURB / "derived" / "turbine_wheel_in718_f0.step"

DEPTH = 0.6                       # engraving, 3 layers at 0.2 mm
# stand (repository design, display only)
BASE_W, BASE_D, BASE_H, BASE_R = 150.0, 95.0, 8.0, 6.0
COMP_XY, TURB_XY = (-38.0, 8.0), (40.0, 8.0)
POCKET_DEPTH, POCKET_CLEAR = 2.0, 0.25          # radial clearance
COMP_BACK_D, TURB_BACK_D = 60.5, 48.96          # back faces measured on the masters
COMP_BORE_D, PEG_CLEAR, PEG_H = 6.0, 0.15, 8.0
PLATE_Y = -34.0


def engrave_back(shape, lines, size):
    """Cut text into the back face (z = 0), mirrored so it reads correctly from behind."""
    from build123d import BuildPart, BuildSketch, Locations, Mode, Plane, Text, add, extrude
    back = Plane(origin=(0, 0, 0), x_dir=(1, 0, 0), z_dir=(0, 0, -1))
    with BuildPart() as p:
        add(shape)
        with BuildSketch(back):
            for y, label in lines:
                with Locations((0, y)):
                    Text(label, font_size=size)
        extrude(amount=-DEPTH, mode=Mode.SUBTRACT)   # back plane faces -Z: -DEPTH cuts into the part
    return p.part


def stand():
    from build123d import (Align, BuildPart, BuildSketch, Cylinder, Location, Locations, Mode,
                           Plane, RectangleRounded, Text, chamfer, extrude)
    with BuildPart() as p:
        with BuildSketch(Plane.XY):
            RectangleRounded(BASE_W, BASE_D, BASE_R)
        extrude(amount=BASE_H)
        chamfer(p.edges().group_by()[-1], 1.0)                      # top edge
        for (x, y), d in ((COMP_XY, COMP_BACK_D), (TURB_XY, TURB_BACK_D)):
            with Locations(Location((x, y, BASE_H))):
                Cylinder(d / 2 + POCKET_CLEAR, POCKET_DEPTH * 2, mode=Mode.SUBTRACT)
        with Locations(Location((COMP_XY[0], COMP_XY[1], BASE_H - POCKET_DEPTH))):
            Cylinder(COMP_BORE_D / 2 - PEG_CLEAR, PEG_H, align=(Align.CENTER, Align.CENTER, Align.MIN))
        with BuildSketch(Plane.XY.offset(BASE_H)):
            with Locations((0, PLATE_Y + 6)):
                Text("K16  COMPRESSOR Al2139 F1   |   TURBINE IN718 F0", font_size=4.2)
            with Locations((0, PLATE_Y - 1)):
                Text("MOCK-UPS - NOT FOR USE  -  porscheparts 993", font_size=3.4)
        extrude(amount=-DEPTH, mode=Mode.SUBTRACT)
    return p.part


def main() -> int:
    from build123d import Compound, Location, export_step, export_stl, import_step

    comp = import_step(str(COMP_STEP))
    turb = import_step(str(TURB_STEP))
    comp_m = engrave_back(comp, [(9.0, "MOCK-UP"), (-9.0, "NOT FOR USE")], 5.0)
    turb_m = engrave_back(turb, [(7.5, "MOCK-UP"), (-7.5, "NOT FOR USE")], 4.4)
    base = stand()
    for name, s in (("compressor", comp_m), ("turbine", turb_m), ("stand", base)):
        if len(s.solids()) != 1 or not s.is_valid:
            raise SystemExit(f"{name}: expected one valid solid")
    removed = {"compressor": comp.volume - comp_m.volume, "turbine": turb.volume - turb_m.volume}
    if min(removed.values()) <= 1.0:
        raise SystemExit(f"engraving did not cut: {removed}")

    for folder in (COMP / "print", TURB / "print"):
        folder.mkdir(exist_ok=True)
    export_stl(comp_m, str(COMP / "print" / "k16_compressor_wheel_mockup.stl"), tolerance=0.01, angular_tolerance=0.08)
    export_stl(turb_m, str(TURB / "print" / "k16_turbine_wheel_mockup.stl"), tolerance=0.01, angular_tolerance=0.08)
    export_stl(base, str(COMP / "print" / "k16_display_stand.stl"), tolerance=0.01, angular_tolerance=0.08)
    # one plate: stand in the middle, wheels either side, all on their backs
    plate = Compound(children=[
        base,
        comp_m.moved(Location((0, 90, 0))),
        turb_m.moved(Location((70, 90, 0))),
    ])
    export_stl(plate, str(COMP / "print" / "k16_display_pair_plate.stl"), tolerance=0.01, angular_tolerance=0.08)
    export_step(plate, str(COMP / "print" / "k16_display_pair_plate.step"))

    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    common = {
        "kind": "mockup",
        "purpose": "1:1 display mock-up on a stand; engraved MOCK-UP / NOT FOR USE on the back face; "
                   "never for a turbocharger (decision 0011)",
        "engraving_depth_mm": DEPTH,
        "generator": "parts/993-eng-k16-compressor-wheel-al2139-f1-0001/source/k16_display_pair.py",
    }
    (COMP / "print" / "print.json").write_text(json.dumps(dict(common,
        part_id="993-ENG-K16-COMPRESSOR-WHEEL-AL2139-F1-0001",
        master="derived/compressor_wheel_al2139_f1.step", master_sha256=digest(COMP_STEP),
        print_file="k16_compressor_wheel_mockup.stl",
        pair_plate="k16_display_pair_plate.stl", stand="k16_display_stand.stl",
        volume_mm3=round(comp_m.volume, 1)), indent=2) + "\n", encoding="utf-8")
    (TURB / "print" / "print.json").write_text(json.dumps(dict(common,
        part_id="993-ENG-K16-TURBINE-WHEEL-IN718-F0-0001",
        master="derived/turbine_wheel_in718_f0.step", master_sha256=digest(TURB_STEP),
        print_file="k16_turbine_wheel_mockup.stl",
        pair_folder="../../993-eng-k16-compressor-wheel-al2139-f1-0001/print/",
        volume_mm3=round(turb_m.volume, 1)), indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: round(v, 1) for k, v in removed.items()}), "mm3 engraved;",
          "stand", round(base.volume, 1), "mm3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
