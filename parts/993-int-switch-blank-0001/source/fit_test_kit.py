#!/usr/bin/env python3
"""Fit-test print kit for 993-INT-SWITCH-BLANK-0001 — six sizes on one plate.

No dimension of the real opening has been measured (see
evidence/measurement-plan.md), and the project measures none (PROJECT_CHARTER.md).
Three level-C forum figures exist, and they disagree by 2 to 3 mm
(decision 0013, section 7):

- console switch opening 17.0 x 27.9 mm (0.67 x 1.10 in), thread 750484
  (SRC-RENNLIST-993-CONSOLE-SWITCH-HOLE-DIMENSIONS);
- faceplate opening of a switch housing about 17 x 28 mm, and passage under
  the covering about 19 x 31 mm, thread 1202129
  (SRC-RENNLIST-993-DASHBOARD-LIGHTING-DIMENSIONS).

The kit no longer bets on one of them. It brackets each hypothesis with three
blanks whose insert is 0.4 mm under, equal to and 0.4 mm over that opening:

- set A, opening 17.0 x 27.9 mm: marked with 1, 2 or 3 dimples on the back;
- set B, opening 19.0 x 31.0 mm: the same dimples plus a groove across the back.

Whichever blank clicks in and sits flush tells which hypothesis holds and the
size within it; a kit in which no blank fits is also a result (decision 0009).

This is a fit-test print of a non-critical trim part (decision 0009), not a
released part. Every value below except the declared openings is a hypothesis.

    python3 parts/993-int-switch-blank-0001/source/fit_test_kit.py   # cadsim image
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "parts" / "993-int-switch-blank-0001" / "print"

# Declared openings, level C, not measured. Each is bracketed by DELTAS.
HYPOTHESES = {
    "A": {
        "opening_mm": (17.0, 27.9),
        "source": "SRC-RENNLIST-993-CONSOLE-SWITCH-HOLE-DIMENSIONS (console switch opening, 0.67 x 1.10 in); "
                  "SRC-RENNLIST-993-DASHBOARD-LIGHTING-DIMENSIONS gives about 17 x 28 mm for a faceplate opening",
        "measurement_records": ["MEAS-DECLARED-993-INT-SWITCH-BLANK-0001-RL-750484",
                                "MEAS-DECLARED-993-INT-SWITCH-BLANK-0001-RL-1202129"],
        "mark": "dimples only",
    },
    "B": {
        "opening_mm": (19.0, 31.0),
        "source": "SRC-RENNLIST-993-DASHBOARD-LIGHTING-DIMENSIONS (passage under the covering, about 19 x 31 mm)",
        "measurement_records": ["MEAS-DECLARED-993-INT-SWITCH-BLANK-0001-RL-1202129"],
        "mark": "dimples and a groove",
    },
}
DELTAS = (-0.4, 0.0, +0.4)   # insert size relative to the declared opening, mm

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
GROOVE_W, GROOVE_DEPTH = 0.8, 0.4
PITCH_X, PITCH_Y = 30.0, 42.0   # plate layout


def blank(opening: tuple[float, float], delta: float, marks: int, groove: bool):
    from build123d import (Box, BuildPart, BuildSketch, Cylinder, Locations, Mode, Plane, Polygon,
                           Rectangle, RectangleRounded, chamfer, extrude)

    ow, oh = opening
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
        # hypothesis mark: set B carries a groove across the back of the face
        if groove:
            with Locations((0, ih / 2 - RIM_WALL - 2.2, z0)):
                Box(iw - 2 * RIM_WALL - 2.0, GROOVE_W, GROOVE_DEPTH * 2, mode=Mode.SUBTRACT)
    return p.part


def write_3mf(stl: Path, out: Path) -> None:
    """Write a core-specification 3MF (one object, millimetres) from a binary STL.

    Deterministic: fixed zip timestamps, vertices merged exactly.
    """
    import struct
    import zipfile

    data = stl.read_bytes()
    n = struct.unpack_from("<I", data, 80)[0]
    index: dict[tuple[float, float, float], int] = {}
    verts, tris = [], []
    for k in range(n):
        vals = struct.unpack_from("<12f", data, 84 + 50 * k)
        tri = []
        for j in range(3):
            key = tuple(round(x, 5) for x in vals[3 + 3 * j: 6 + 3 * j])
            if key not in index:
                index[key] = len(verts)
                verts.append(key)
            tri.append(index[key])
        if len(set(tri)) == 3:
            tris.append(tri)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">',
             '<resources><object id="1" type="model"><mesh><vertices>']
    lines += [f'<vertex x="{x:g}" y="{y:g}" z="{z:g}"/>' for x, y, z in verts]
    lines.append("</vertices><triangles>")
    lines += [f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in tris]
    lines.append('</triangles></mesh></object></resources><build><item objectid="1"/></build></model>')
    parts = {
        "[Content_Types].xml": '<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>',
        "_rels/.rels": '<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
        'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>',
        "3D/3dmodel.model": "\n".join(lines) + "\n",
    }
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in parts.items():
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, text)


def main() -> int:
    from build123d import Compound, Location, export_step, export_stl

    OUT.mkdir(parents=True, exist_ok=True)
    for stale in OUT.glob("switch_blank_fit_[0-9].stl"):
        stale.unlink()
    solids, report = [], []
    for row, (hyp, spec) in enumerate(HYPOTHESES.items()):
        opening = spec["opening_mm"]
        for marks, delta in enumerate(DELTAS, start=1):
            s = blank(opening, delta, marks, groove=(hyp == "B"))
            if not s.is_valid:
                raise SystemExit(f"variant {hyp}{marks}: invalid solid")
            name = f"switch_blank_fit_{hyp}{marks}"
            export_stl(s, str(OUT / f"{name}.stl"), tolerance=0.01, angular_tolerance=0.1)
            bb = s.bounding_box()
            report.append({"variant": f"{hyp}{marks}", "hypothesis": hyp, "dimples": marks,
                           "groove": hyp == "B",
                           "insert_mm": [round(opening[0] + delta, 2), round(opening[1] + delta, 2)],
                           "delta_vs_declared_opening_mm": delta,
                           "bounding_box_mm": [round(bb.size.X, 2), round(bb.size.Y, 2), round(bb.size.Z, 2)],
                           "volume_mm3": round(s.volume, 1), "file": f"{name}.stl"})
            solids.append(s.moved(Location(((marks - 2) * PITCH_X, (0.5 - row) * PITCH_Y, 0))))
    plate = Compound(children=solids)
    export_stl(plate, str(OUT / "switch_blank_fit_plate.stl"), tolerance=0.01, angular_tolerance=0.1)
    # One STEP per hypothesis row: a single six-blank STEP exceeds the
    # repository's 1 MiB file gate (scripts/validate_file_sizes.py).
    (OUT / "switch_blank_fit_plate.step").unlink(missing_ok=True)
    for row, hyp in enumerate(HYPOTHESES):
        export_step(Compound(children=solids[3 * row: 3 * row + 3]),
                    str(OUT / f"switch_blank_fit_plate_{hyp}.step"))

    write_3mf(OUT / "switch_blank_fit_plate.stl", OUT / "switch_blank_fit_plate.3mf")

    (OUT / "kit.json").write_text(json.dumps({
        "part_id": "993-INT-SWITCH-BLANK-0001",
        "purpose": "fit test of a non-critical trim part; not a released part (decision 0009)",
        "basis": "brackets both sourced hypotheses of the opening (decision 0013, section 7; decision 0016)",
        "hypotheses": {k: {"declared_opening_mm": list(v["opening_mm"]), "source": v["source"],
                           "measurement_records": v["measurement_records"], "mark": v["mark"]}
                       for k, v in HYPOTHESES.items()},
        "declared_range_mm": {"width": [17.0, 19.0], "height": [27.9, 31.0]},
        "evidence_level": "C, declared, not measured",
        "orientation": "visible face down on the build plate, clips up, no supports",
        "variants": report,
        "generator": "parts/993-int-switch-blank-0001/source/fit_test_kit.py",
    }, indent=2) + "\n", encoding="utf-8")
    for r in report:
        print(r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
