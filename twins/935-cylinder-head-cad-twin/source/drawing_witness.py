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

The sheet (issue #708) puts the three views on one A4 sheet in third-angle
projection, adds seven dimensions with ezdxf and a title block whose fields are
block attributes, and reads it back:

  dimensions  each measures what it should (60 and 40 overall, the 12 mm
              diameter, 10 and 12 to the hole centre, the 20 mm height and
              the 8 mm step) from its own definition points; none carries typed text in place of the
              measurement; every definition point lies on a drawn edge or is
              the drawn hole centre, so a dimension cannot float free of the
              geometry it names;
  views       the top view stands above the front view and the side view to
              its right, with shared extents aligned;
  title block every field comes back as written, inside the border and clear
              of the views.

It witnesses the tool on this solid. It is not a drawing of the head; the tool
is assigned in docs/TOOLCHAIN.md on the strength of this witness.

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


SHEET_MM = (297.0, 210.0)  # A4 landscape, 1:1
BORDER_MM = 10.0
# third-angle layout: sheet position of each view's model origin
ORIGINS = {"front": (40.0, 60.0), "top": (40.0, 100.0), "side": (120.0, 60.0)}
TITLE_BLOCK = {"insert": (137.0, 10.0), "size": (150.0, 48.0), "label_mm": 34.0}
# Title-block fields of the witness. The reference sheet of the head fills the same tags.
TITLE_TAGS = ("TITLE", "SOURCE", "SCALE", "UNITS", "PROJECTION", "SCALE_STATUS", "EVIDENCE", "DATE")
TEXT_MM = 2.5  # ISO 3098 minimum text height on an A4 sheet
# Dimension style for a 1:1 sheet in millimetres. ezdxf's EZDXF preset scales lengths by 100 (dimlfac) for
# metre drawings and uses 0.25 mm text: on this sheet it showed 6000 for a 60 mm length.
DIMSTYLE = {"dimlfac": 1.0, "dimtxt": 3.5, "dimasz": 3.0, "dimexo": 1.0, "dimexe": 2.0, "dimgap": 1.0,
            "dimdec": 2, "dimzin": 8, "dimtad": 1}
LTSCALE = 0.4  # dash 4.8 mm, gap 1.2 mm: short hidden edges still show as dashed


def sheet_point(view: str, u: float, v: float) -> tuple[float, float]:
    """Sheet coordinates of the point (u, v) of a view, in that view's model axes."""

    ox, oy = ORIGINS[view]
    return (ox + u, oy + v)


# Dimensions of the witness sheet: (name, kind, definition, expected measurement in mm).
# Linear: two points on drawn geometry and where the dimension line runs. Diameter: centre and radius.
DIMENSIONS = [
    ("top: length", "linear", {"p1": ("top", 0, 40), "p2": ("top", 60, 40), "base": ("top", 0, 58), "angle": 0}, 60.0),
    ("top: width", "linear", {"p1": ("top", 60, 0), "p2": ("top", 60, 40), "base": ("top", 70, 0), "angle": 90}, 40.0),
    ("top: hole from the left edge", "linear", {"p1": ("top", 0, 40), "p2": ("top", 10, 12), "base": ("top", 0, 48), "angle": 0}, 10.0),
    ("top: hole from the front edge", "linear", {"p1": ("top", 0, 0), "p2": ("top", 10, 12), "base": ("top", -8, 0), "angle": 90}, 12.0),
    ("top: hole diameter", "diameter", {"centre": ("top", 10, 12), "radius": 6.0, "location": ("top", 24, 28)}, 12.0),
    ("front: height", "linear", {"p1": ("front", 0, 0), "p2": ("front", 0, 20), "base": ("front", -8, 0), "angle": 90}, 20.0),
    # (60, 20) is cut away by the step: anchor on the end of the step floor and the top of the riser
    ("front: step depth", "linear", {"p1": ("front", 60, 12), "p2": ("front", 40, 20), "base": ("front", 68, 0), "angle": 90}, 8.0),
]


def on_segment(p, line, tol: float = TOLERANCE_MM) -> bool:
    (x0, y0, x1, y1), (px, py) = line, p
    dx, dy = x1 - x0, y1 - y0
    length2 = dx * dx + dy * dy
    if length2 == 0:
        return math.hypot(px - x0, py - y0) < tol
    s = max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / length2))
    return math.hypot(px - x0 - s * dx, py - y0 - s * dy) < tol


def build_sheet(part, path: Path, date: str, dimensions=DIMENSIONS, dimstyle=DIMSTYLE,
                fields_override=None) -> dict:
    """Project the three views onto one sheet, add dimensions and a title block, write DXF. Returns what was written."""

    import ezdxf
    from build123d import ExportDXF, LineType, Pos, Unit
    from ezdxf.tools.standards import setup_dimstyles

    export = ExportDXF(unit=Unit.MM)
    export.add_layer("visible")
    export.add_layer("hidden", line_type=LineType.ISO_DASH)
    for name, (eye, up, ax, ay) in VIEWS.items():
        visible, hidden = part.project_to_viewport(eye, up, CENTRE)
        # view coordinates are centred on the look-at point: move them to the view's origin on the sheet
        dx, dy = ORIGINS[name][0] + CENTRE[ax], ORIGINS[name][1] + CENTRE[ay]
        export.add_shape([Pos(dx, dy, 0) * e for e in visible], layer="visible")
        if hidden:
            export.add_shape([Pos(dx, dy, 0) * e for e in hidden], layer="hidden")
    export.write(str(path))

    doc = ezdxf.readfile(path)
    setup_dimstyles(doc)
    doc.header["$LTSCALE"] = LTSCALE
    msp = doc.modelspace()
    for layer in ("dimensions", "border", "title"):
        if layer not in doc.layers:
            doc.layers.add(layer)
    w, h = SHEET_MM
    msp.add_lwpolyline([(0, 0), (w, 0), (w, h), (0, h)], close=True, dxfattribs={"layer": "border"})
    b = BORDER_MM
    msp.add_lwpolyline([(b, b), (w - b, b), (w - b, h - b), (b, h - b)], close=True, dxfattribs={"layer": "border"})
    for name, kind, d, _ in dimensions:
        if kind == "linear":
            dim = msp.add_linear_dim(base=sheet_point(*d["base"]), p1=sheet_point(*d["p1"]), p2=sheet_point(*d["p2"]),
                                     angle=d["angle"], dimstyle="EZDXF", override=dimstyle, dxfattribs={"layer": "dimensions"})
        else:
            dim = msp.add_diameter_dim(center=sheet_point(*d["centre"]), radius=d["radius"], location=sheet_point(*d["location"]),
                                       dimstyle="EZ_RADIUS", override=dimstyle, dxfattribs={"layer": "dimensions"})
        dim.render()
    fields = {**title_fields(date), **(fields_override or {})}
    tw, th = TITLE_BLOCK["size"]
    lw = TITLE_BLOCK["label_mm"]
    block = doc.blocks.new("TITLE_BLOCK")
    block.add_lwpolyline([(0, 0), (tw, 0), (tw, th), (0, th)], close=True)
    block.add_line((lw, 0), (lw, th))
    row = th / len(TITLE_TAGS)
    for i, tag in enumerate(TITLE_TAGS):
        y = th - (i + 1) * row
        block.add_line((0, y), (tw, y))
        block.add_text(tag.replace("_", " ").capitalize(), height=TEXT_MM, dxfattribs={"insert": (1.5, y + 1.75)})
        block.add_attdef(tag, insert=(lw + 1.5, y + 1.75), dxfattribs={"height": TEXT_MM})
    msp.add_blockref("TITLE_BLOCK", TITLE_BLOCK["insert"], dxfattribs={"layer": "title"}).add_auto_attribs(fields)
    doc.saveas(path)
    return fields


def title_fields(date: str) -> dict:
    return {"TITLE": "Witness: block 60 x 40 x 20, a hole and a step",
            "SOURCE": "935 head twin, source/drawing_witness.py",
            "SCALE": "1:1", "UNITS": "mm", "PROJECTION": "third angle",
            "SCALE_STATUS": "exact: a solid defined in code",
            "EVIDENCE": "witness geometry, not a part",
            "DATE": date}


def displayed(doc, dim):
    """The text a rendered dimension shows, without formatting codes or a diameter sign, and its height."""

    import re

    block = doc.blocks.get(dim.dxf.geometry)
    texts = [e for e in block if e.dxftype() in ("MTEXT", "TEXT")] if block is not None else []
    if len(texts) != 1:
        return None, None
    e = texts[0]
    raw = e.plain_text() if e.dxftype() == "MTEXT" else e.dxf.text
    shown = re.sub(r"%%[cC]|\u2205|\u00d8|\u00f8", "", raw).strip()
    return shown, round(float(e.dxf.char_height if e.dxftype() == "MTEXT" else e.dxf.height), 4)


def check_sheet(path: Path, written: dict, dimensions=DIMENSIONS) -> tuple[list, dict]:
    """Read the sheet back with a fresh ezdxf reader and check views, dimensions and title block."""

    import ezdxf
    from ezdxf import bbox

    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    checks = []

    def add(what, passed, detail=None):
        checks.append({"check": f"sheet: {what}", "passed": bool(passed), **({"detail": detail} if detail is not None else {})})

    lines = [(e.dxf.start.x, e.dxf.start.y, e.dxf.end.x, e.dxf.end.y) for e in msp.query("LINE")
             if e.dxf.layer in ("visible", "hidden")]
    circles = [(e.dxf.center.x, e.dxf.center.y, e.dxf.radius) for e in msp.query("CIRCLE") if e.dxf.layer == "visible"]
    extents = {}
    # outer edges of each view in its own model axes; the step takes the top-right corner off the front view
    outline = {"top": [(0, 0, 60, 0), (60, 0, 60, 40), (0, 40, 60, 40), (0, 0, 0, 40)],
               "front": [(0, 0, 60, 0), (60, 0, 60, 12), (40, 12, 60, 12), (40, 12, 40, 20), (0, 20, 40, 20), (0, 0, 0, 20)],
               "side": [(0, 0, 40, 0), (40, 0, 40, 20), (0, 20, 40, 20), (0, 0, 0, 20)]}
    for name in VIEWS:
        ox, oy = ORIGINS[name]
        edges = [(ox + a, oy + b, ox + c, oy + d) for a, b, c, d in outline[name]]
        add(f"{name} view outline drawn at its third-angle place", all(has_line(lines, *e) for e in edges))
        extents[name] = (ox, oy, ox + max(e[2] for e in outline[name]), oy + max(e[3] for e in outline[name]))
    add("top view above the front view, x extents aligned",
        extents["top"][1] > extents["front"][3] and extents["top"][0] == extents["front"][0] and extents["top"][2] == extents["front"][2])
    add("side view right of the front view, z extents aligned",
        extents["side"][0] > extents["front"][2] and extents["side"][1] == extents["front"][1] and extents["side"][3] == extents["front"][3])

    dims = list(msp.query("DIMENSION"))
    add(f"{len(dimensions)} dimensions read back", len(dims) == len(dimensions), len(dims))
    measured = []
    for (name, kind, d, expected), dim in zip(dimensions, dims):
        value = float(dim.get_measurement())
        text = dim.dxf.get("text", "")
        shown, height = displayed(doc, dim)
        wanted = f"{expected:.2f}".rstrip("0").rstrip(".")
        if kind == "linear":
            points = [(dim.dxf.defpoint2.x, dim.dxf.defpoint2.y), (dim.dxf.defpoint3.x, dim.dxf.defpoint3.y)]
            anchored = all(any(on_segment(p, ln) for ln in lines) or any(math.hypot(p[0] - cx, p[1] - cy) < TOLERANCE_MM
                                                                          for cx, cy, _ in circles) for p in points)
        else:
            centre = sheet_point(*d["centre"])
            anchored = any(math.hypot(centre[0] - cx, centre[1] - cy) < TOLERANCE_MM and abs(r - d["radius"]) < TOLERANCE_MM
                           for cx, cy, r in circles)
        measured.append({"dimension": name, "expected_mm": expected, "measured_mm": round(value, 6),
                         "displayed": shown, "text_height_mm": height,
                         "text_override": text not in ("", "<>"), "anchored_on_geometry": anchored})
        add(f"{name}: measures {expected:g} mm, no typed text, anchored on drawn geometry",
            abs(value - expected) < TOLERANCE_MM and text in ("", "<>") and anchored, round(value, 6))
        add(f"{name}: shows {wanted} at a legible height", shown == wanted and height is not None and height >= TEXT_MM,
            [shown, height])

    inserts = list(msp.query("INSERT[name=='TITLE_BLOCK']"))
    got = {a.dxf.tag: a.dxf.text for a in inserts[0].attribs} if len(inserts) == 1 else {}
    add("title block: every field comes back as written", got == written, sorted(got))
    x0, y0 = TITLE_BLOCK["insert"]
    tw, th = TITLE_BLOCK["size"]
    w, h = SHEET_MM
    b = BORDER_MM
    inside = b <= x0 and x0 + tw <= w - b and b <= y0 and y0 + th <= h - b
    clear = all(x0 >= e[2] or x0 + tw <= e[0] or y0 >= e[3] or y0 + th <= e[1] for e in extents.values())
    add("title block inside the border and clear of the views", inside and clear)
    fits = all(x0 - TOLERANCE_MM <= t.extmin.x and t.extmax.x <= x0 + tw + TOLERANCE_MM
               for t in (bbox.extents([a]) for a in inserts[0].attribs)) if len(inserts) == 1 else False
    add("title block: every field fits inside it", fits)
    box = bbox.extents(msp)
    add("everything drawn lies on the sheet", box.extmin.x >= -TOLERANCE_MM and box.extmin.y >= -TOLERANCE_MM
        and box.extmax.x <= w + TOLERANCE_MM and box.extmax.y <= h + TOLERANCE_MM,
        [round(box.extmin.x, 3), round(box.extmin.y, 3), round(box.extmax.x, 3), round(box.extmax.y, 3)])
    return checks, {"dimensions": measured, "title_block": got,
                    "entities": {k: sum(1 for e in msp if f"{e.dxf.layer}:{e.dxftype()}" == k)
                                 for k in sorted({f"{e.dxf.layer}:{e.dxftype()}" for e in msp})}}


def controls(part, work: Path, date: str) -> list:
    """Three faults the sheet check must catch; a check that cannot fail witnesses nothing."""

    import ezdxf

    out = []

    def failed(checks, fragment):
        return any(not c["passed"] and fragment in c["check"] for c in checks)

    # 1. typed text in place of the measurement
    path = work / "control-typed-text.dxf"
    written = build_sheet(part, path, date)
    doc = ezdxf.readfile(path)
    next(iter(doc.modelspace().query("DIMENSION"))).dxf.text = "60"
    doc.saveas(path)
    out.append({"control": "a dimension shows typed text instead of its measurement",
                "detected": failed(check_sheet(path, written)[0], DIMENSIONS[0][0])})
    # 2. a dimension anchored on a corner the step has cut away
    loose = [row if row[0] != "front: step depth" else
             (row[0], "linear", {**row[2], "p2": ("front", 60, 20)}, row[3]) for row in DIMENSIONS]
    path = work / "control-loose-anchor.dxf"
    written = build_sheet(part, path, date, loose)
    out.append({"control": "a dimension anchored on the corner the step removed",
                "detected": failed(check_sheet(path, written, loose)[0], "front: step depth")})
    # 4. the preset that showed 6000 for 60: lengths scaled by 100
    path = work / "control-scaled-text.dxf"
    written = build_sheet(part, path, date, dimstyle={**DIMSTYLE, "dimlfac": 100.0})
    out.append({"control": "dimensions styled to show lengths times 100",
                "detected": failed(check_sheet(path, written)[0], "shows 60 at a legible height")})
    # 3. a title-block field changed after writing
    path = work / "control-title.dxf"
    written = build_sheet(part, path, date)
    doc = ezdxf.readfile(path)
    insert = next(iter(doc.modelspace().query("INSERT[name=='TITLE_BLOCK']")))
    next(a for a in insert.attribs if a.dxf.tag == "SCALE_STATUS").dxf.text = "calibrated"
    doc.saveas(path)
    out.append({"control": "a title-block field changed after it was written",
                "detected": failed(check_sheet(path, written)[0], "title block: every field")})
    # 5. a field longer than its row
    path = work / "control-long-field.dxf"
    long = {"SOURCE": "twins/935-cylinder-head-cad-twin/source/drawing_witness.py, read back by ezdxf with every check"}
    written = build_sheet(part, path, date, fields_override=long)
    out.append({"control": "a title-block field longer than its row",
                "detected": failed(check_sheet(path, written)[0], "every field fits inside it")})
    return out


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

    date = time.strftime("%Y-%m-%d")
    sheet_path = work / "drawing-witness-sheet.dxf"
    written = build_sheet(part, sheet_path, date)
    sheet_checks, sheet = check_sheet(sheet_path, written)
    checks += sheet_checks
    negative = controls(part, work, date)
    checks += [{"check": f"control: {c['control']}: caught", "passed": c["detected"]} for c in negative]
    from ezdxf.addons.drawing.matplotlib import qsave
    from ezdxf.addons.drawing.config import Configuration, LinePolicy
    qsave(ezdxf.readfile(sheet_path).modelspace(), str(work / "drawing-witness-sheet.png"), bg="#FFFFFF", dpi=200,
          config=Configuration(line_policy=LinePolicy.ACCURATE))

    record = {
        "schema": "935-cad-twin-drawing-witness/2", "date": date,
        "scope": "three orthographic views of a block with a hole and a step, projected by build123d, exported to DXF and "
                 "read back with ezdxf, then one third-angle sheet with ezdxf dimensions and a title block, read back. "
                 "A witness of the tool on a known solid, not a drawing of the head; docs/TOOLCHAIN.md assigns the tool on it",
        "tools": {"build123d": build123d.__version__, "ezdxf": ezdxf.__version__},
        "tolerance_mm": TOLERANCE_MM,
        "views": {name: {"entities": v["entities"], "size_mm": [round(x, 6) for x in v["size"]]} for name, v in views.items()},
        "sheet": {"size_mm": list(SHEET_MM), "projection": "third angle", "scale": "1:1", **sheet},
        "checks": checks, "passed": all(c["passed"] for c in checks),
        "not_checked": ["tolerance, fit and thread annotations: none is drawn, and none may be without a source",
                        "section views", "a mesh body: the v2 body has no B-rep"],
    }
    Path(out).write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps({"passed": record["passed"], "failed": [c for c in checks if not c["passed"]]}))
    assert record["passed"]


if __name__ == "__main__":
    main(*sys.argv[1:])
