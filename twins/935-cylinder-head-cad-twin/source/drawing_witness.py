#!/usr/bin/env python3
"""Witness for a drawing tool: three projected views of a known solid, read back.

No drawing of the head exists and no drawing tool is assigned in this
repository. Before one is used, this checks what build123d's projection and
its DXF export give on a solid whose views are known by hand, read back with
an independent reader (ezdxf):

  solid   a block 60 x 40 x 20 mm with a through hole of 12 mm at (10, 12)
          and a step 20 x 40 x 8 mm cut from the top at the +x end;
  views   top, front and side, orthographic, visible and hidden edges on
          separate layers.

Checked by hand:

  top     outline 60 x 40; the hole is a circle of radius 6 at (10, 12); the
          step is one visible line at x = 40;
  front   outline 60 x 20 with the step at x = 40, z = 12; the hole is two
          hidden lines at x = 4 and x = 16 over the full height;
  side    outline 40 x 20; the step is one visible line at z = 12; the hole
          is two hidden lines at y = 6 and y = 18.

It witnesses the tool on this solid. It is not a drawing of the head and it
assigns no tool.

Usage: drawing_witness.py WORK_DIR OUT.json
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

TOLERANCE_MM = 1e-4
CENTRE = (30.0, 20.0, 10.0)
# name: (camera position, up vector, drawing x axis in model axes, drawing y axis in model axes)
VIEWS = {"top": ((30.0, 20.0, 500.0), (0, 1, 0), 0, 1),
         "front": ((30.0, -500.0, 10.0), (0, 0, 1), 0, 2),
         "side": ((500.0, 20.0, 10.0), (0, 0, 1), 1, 2)}


def solid():
    from build123d import Box, Cylinder, Pos

    block = Pos(30, 20, 10) * Box(60, 40, 20)
    block -= Pos(10, 12, 10) * Cylinder(6, 20)
    block -= Pos(50, 20, 16) * Box(20, 40, 8)
    return block


def read_back(path: Path) -> dict:
    """Extents by layer, straight lines and circular arcs of a DXF file, with ezdxf."""

    import ezdxf
    from ezdxf import bbox

    msp = ezdxf.readfile(path).modelspace()
    out = {"entities": {}, "lines": {"visible": [], "hidden": []}, "arcs": []}
    for e in msp:
        key = f"{e.dxf.layer}:{e.dxftype()}"
        out["entities"][key] = out["entities"].get(key, 0) + 1
        if e.dxftype() == "LINE":
            out["lines"][e.dxf.layer].append((e.dxf.start.x, e.dxf.start.y, e.dxf.end.x, e.dxf.end.y))
        if e.dxftype() in ("ARC", "CIRCLE"):
            out["arcs"].append((e.dxf.layer, e.dxf.center.x, e.dxf.center.y, e.dxf.radius))
    box = bbox.extents(msp)
    out["extents"] = [box.extmin.x, box.extmin.y, box.extmax.x, box.extmax.y]
    return out


def has_line(lines, x0, y0, x1, y1) -> bool:
    """A segment from (x0, y0) to (x1, y1) is covered by the collinear segments of `lines`."""

    vertical = abs(x1 - x0) < TOLERANCE_MM
    spans = []
    for a, b, c, d in lines:
        if vertical and abs(a - x0) < TOLERANCE_MM and abs(c - x0) < TOLERANCE_MM:
            spans.append((min(b, d), max(b, d)))
        if not vertical and abs(b - y0) < TOLERANCE_MM and abs(d - y0) < TOLERANCE_MM:
            spans.append((min(a, c), max(a, c)))
    lo, hi = (min(y0, y1), max(y0, y1)) if vertical else (min(x0, x1), max(x0, x1))
    reach = lo
    for a, b in sorted(spans):
        if a <= reach + TOLERANCE_MM:
            reach = max(reach, b)
    return reach >= hi - TOLERANCE_MM


def main(work, out) -> None:
    import build123d
    import ezdxf
    from build123d import ExportDXF, LineType, Unit

    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    part = solid()
    volume = 60 * 40 * 20 - math.pi * 36 * 20 - 20 * 40 * 8
    checks = [{"check": "volume of the solid, mm3", "expected": round(volume, 3), "measured": round(part.volume, 3),
               "passed": abs(part.volume - volume) < 1e-6 * volume}]

    def add(view, what, passed, detail=None):
        checks.append({"check": f"{view}: {what}", "passed": bool(passed), **({"detail": detail} if detail else {})})

    views = {}
    for name, (eye, up, ax, ay) in VIEWS.items():
        visible, hidden = part.project_to_viewport(eye, up, CENTRE)
        export = ExportDXF(unit=Unit.MM)
        export.add_layer("visible")
        export.add_layer("hidden", line_type=LineType.ISO_DASH)
        export.add_shape(visible, layer="visible")
        if hidden:
            export.add_shape(hidden, layer="hidden")
        path = work / f"drawing-witness-{name}.dxf"
        export.write(str(path))
        views[name] = read_back(path)
        # drawing coordinates are centred on the look-at point; move them back to model coordinates
        ox, oy = CENTRE[ax], CENTRE[ay]
        views[name]["lines"] = {layer: [(a + ox, b + oy, c + ox, d + oy) for a, b, c, d in rows]
                                for layer, rows in views[name]["lines"].items()}
        views[name]["arcs"] = [(layer, x + ox, y + oy, r) for layer, x, y, r in views[name]["arcs"]]
        e = views[name]["extents"]
        views[name]["size"] = [e[2] - e[0], e[3] - e[1]]

    size = {"top": (60.0, 40.0), "front": (60.0, 20.0), "side": (40.0, 20.0)}
    for name, (w_, h_) in size.items():
        got = views[name]["size"]
        add(name, f"outline {w_:g} x {h_:g} mm", abs(got[0] - w_) < TOLERANCE_MM and abs(got[1] - h_) < TOLERANCE_MM,
            [round(v, 6) for v in got])
    top, front, side = views["top"], views["front"], views["side"]
    circle = [a for a in top["arcs"] if a[0] == "visible"]
    add("top", "the hole is a visible circle of radius 6 at (10, 12)",
        len(circle) == 1 and abs(circle[0][1] - 10) < TOLERANCE_MM and abs(circle[0][2] - 12) < TOLERANCE_MM
        and abs(circle[0][3] - 6) < TOLERANCE_MM, [round(v, 6) for v in circle[0][1:]] if circle else None)
    add("top", "the step is a visible line at x = 40", has_line(top["lines"]["visible"], 40, 0, 40, 40))
    add("front", "the step is visible at x = 40 from z = 12 to 20 and at z = 12 from x = 40 to 60",
        has_line(front["lines"]["visible"], 40, 12, 40, 20) and has_line(front["lines"]["visible"], 40, 12, 60, 12))
    add("front", "the hole is two hidden lines at x = 4 and x = 16 over the full height",
        has_line(front["lines"]["hidden"], 4, 0, 4, 20) and has_line(front["lines"]["hidden"], 16, 0, 16, 20))
    add("front", "no visible line stands at x = 4 or x = 16",
        not has_line(front["lines"]["visible"], 4, 2, 4, 18) and not has_line(front["lines"]["visible"], 16, 2, 16, 18))
    add("side", "the step is a visible line at z = 12", has_line(side["lines"]["visible"], 0, 12, 40, 12))
    add("side", "the hole is two hidden lines at y = 6 and y = 18",
        has_line(side["lines"]["hidden"], 6, 0, 6, 20) and has_line(side["lines"]["hidden"], 18, 0, 18, 20))

    record = {
        "schema": "935-cad-twin-drawing-witness/1", "date": time.strftime("%Y-%m-%d"),
        "scope": "three orthographic views of a block with a hole and a step, projected by build123d, exported to DXF and "
                 "read back with ezdxf. A witness of the tool on a known solid: not a drawing of the head, and no tool assignment",
        "tools": {"build123d": build123d.__version__, "ezdxf": ezdxf.__version__},
        "tolerance_mm": TOLERANCE_MM,
        "views": {name: {"entities": v["entities"], "size_mm": [round(x, 6) for x in v["size"]]} for name, v in views.items()},
        "checks": checks, "passed": all(c["passed"] for c in checks),
        "not_checked": ["dimension and tolerance annotations", "section views", "a title block", "a mesh body: the v2 body has no B-rep"],
    }
    Path(out).write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps({"passed": record["passed"], "failed": [c for c in checks if not c["passed"]]}))
    assert record["passed"]


if __name__ == "__main__":
    main(*sys.argv[1:])
