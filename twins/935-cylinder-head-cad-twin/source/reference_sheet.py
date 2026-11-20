#!/usr/bin/env python3
"""Reference sheet of the confirmed machined features of the 935 head (issue #708).

Draws only the features ``feature-confirmation.json`` lists as confirmed, each on the datum axis of its group as
``feature-fits.json`` records it, with the tool ``docs/TOOLCHAIN.md`` assigns (ezdxf on a DXF sheet, as witnessed
by ``drawing_witness.py``). Every revolved feature is drawn about its own axis and placed at its station on the
datum axis, as a meridian profile; its tilt and offset from the datum are recorded, not drawn.

Every value on the sheet is a reference value, in parentheses: a number fitted on a scan whose scale is an owner
instruction (#693), not a dimension of the specimen. No tolerance, fit or thread is drawn: none has a source.

The sheet is read back like the witness: each dimension must show the fitted number it stands for (the plugs are
drawn at 2:1, so a dimension style that forgot the scale would show twice the value), from points on the drawn
profile; no text may carry a tolerance, a fit or a thread; the title block must read back; every confirmed
feature and no other must be named.

Usage: reference_sheet.py PARAMS_DIR WORK_DIR OUT.json MEDIA.png
"""

from __future__ import annotations

import json
import math
import re
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import drawing_witness as dw  # noqa: E402
from twin_common import sha256_file  # noqa: E402

SCHEMA = "935-cad-twin-reference-sheet/1"
SHEET_MM = (420.0, 297.0)  # A3 landscape
BORDER_MM = 10.0
# centre of the datum axis of each view on the sheet, and the cell it must stay in (x0, y0, x1, y1)
# the valves (about 47 mm across) are drawn at 1:1, the plugs at 2:1; each view states its scale
VIEWS = {
    "valve_y_minus": {"centre": (62.0, 226.0), "cell": (15.0, 176.0, 175.0, 287.0), "scale": 1.0},
    "valve_y_plus": {"centre": (200.0, 226.0), "cell": (180.0, 176.0, 278.0, 287.0), "scale": 1.0},
    "plug_x_plus": {"centre": (98.0, 110.0), "cell": (15.0, 64.0, 230.0, 172.0), "scale": 2.0},
    "plug_x_minus": {"centre": (290.0, 110.0), "cell": (235.0, 64.0, 405.0, 172.0), "scale": 2.0},
}
OVERSHOOT_MM = 2.0  # the datum line runs this far past the outermost features, in model millimetres
TITLE = {"insert": (260.0, 10.0), "size": (150.0, 48.0), "label_mm": 34.0}
NOTES = {"insert": (282.0, 284.0), "width": 126.0}
TABLE = {"insert": (15.0, 60.0), "row_mm": 4.0}
# no tolerance (+-, +0.x/-0.x), fit class (H7, H7/g6) or thread (M14, M14x1.25, UNF, UNC, NPT, G 1/4) may appear
FORBIDDEN = re.compile(r"±|\+/-|[+-]0[.,]\d|\b[A-Za-z]{1,2}\d{1,2}/[a-z]{1,2}\d{1,2}\b|\bH\d{1,2}\b|\bM\d{1,2}(x[\d.]+)?\b"
                       r"|\bUN[CFE]?F?\b|\bNPT\b|\bG\s?\d/\d")
SHORT = {"throat": "throat", "seat": "seat", "guide_bore_port_end": "guide bore, port end", "thread_bore": "thread bore",
         "chamber_relief": "chamber relief", "well": "well", "seat_face": "seat face"}


def fmt(value: float) -> str:
    """How the sheet's dimension style prints a length: two decimals, trailing zeros suppressed."""

    return f"{value:.2f}".rstrip("0").rstrip(".")


def short_name(rid: str, group: str) -> str:
    return SHORT[rid[len(group) + 1:]]


def assemble(params: Path) -> dict:
    """The confirmed features in the frame of their group datum, from the committed records only."""

    fits = json.loads((params / "feature-fits.json").read_text())
    refits = {r["id"]: r for r in json.loads((params / "feature-refits.json").read_text())["regions"]}
    standing = json.loads((params / "feature-confirmation.json").read_text())
    rows = {r["id"]: r for r in standing["rows"]}
    first = {r["id"]: r for r in fits["regions"]}
    features = []
    for rid in standing["confirmed_by_first_check"] + standing["confirmed_by_declared_refit"]:
        region = first[rid]
        by_refit = rid in standing["confirmed_by_declared_refit"]
        fit = refits[rid]["fit"] if by_refit else region["fit"]
        datum = fits["group_datums"][region["group"]]
        c = np.asarray(datum["axis_point"], dtype=float)
        a = np.asarray(datum["axis_direction"], dtype=float)
        a /= np.linalg.norm(a)
        row = {"id": rid, "group": region["group"], "label": short_name(rid, region["group"]), "type": fit["type"],
               "confirmed_by": "declared re-fit (#696)" if by_refit else "first check",
               "held_out_share": rows[rid]["refit_check_share"] if by_refit else rows[rid]["first_check_share"],
               "evidence": "fitted on a scan"}
        if fit["type"] == "plane":
            n = np.asarray(fit["normal"], dtype=float)
            row["station_mm"] = float((np.asarray(fit["point"], dtype=float) - c) @ a)
            row["normal_to_datum_deg"] = math.degrees(math.acos(min(1.0, abs(float(n @ a)) / np.linalg.norm(n))))
        else:
            p = np.asarray(fit["axis_point"], dtype=float)
            u = np.asarray(fit["axis_direction"], dtype=float)
            u /= np.linalg.norm(u)
            k = math.tan(math.radians(fit.get("half_angle_deg", 0.0)))
            r0 = 0.5 * fit["diameter_mm"]
            t0, t1 = fit["station_range_mm"]
            tm = 0.5 * (t0 + t1)
            mid = p + tm * u
            off = mid - c - ((mid - c) @ a) * a
            ends = sorted(((float((p + t * u - c) @ a), r0 + k * t) for t in (t0, t1)))
            row.update({"stations_mm": [ends[0][0], ends[1][0]], "radii_mm": [ends[0][1], ends[1][1]],
                        "mid_station_mm": 0.5 * (ends[0][0] + ends[1][0]),
                        "mid_diameter_mm": ends[0][1] + ends[1][1],
                        "half_angle_deg": abs(fit.get("half_angle_deg", 0.0)), "length_mm": abs(t1 - t0),
                        "own_axis_to_datum_deg": math.degrees(math.acos(min(1.0, abs(float(u @ a))))),
                        "own_axis_off_datum_at_mid_mm": float(np.linalg.norm(off))})
        features.append(row)
    datums = {}
    for group in VIEWS:
        d = fits["group_datums"][group]
        rule = d["rule"]
        base = rule.get("axis_of")
        confirmed = {f["id"] for f in features}
        if base:
            what = f"axis of {base}, fitted" + ("" if base in confirmed else "; that surface is not confirmed")
        else:
            what = "line through the fitted centres of " + " and ".join(rule["line_through"])
        datums[group] = {"rule": rule, "what": what}
    return {"features": features, "datums": datums, "all_ids": [r["id"] for r in standing["rows"]],
            "inputs": {name: sha256_file(params / name) for name in
                       ("feature-fits.json", "feature-refits.json", "feature-confirmation.json")}}


def layout(features: list) -> dict:
    """Sheet coordinates: datum station s and radius r of a group become x = cx + k (s - s_mid), y = cy +- k r, k the view scale."""

    out = {}
    for group, view in VIEWS.items():
        mine = [f for f in features if f["group"] == group]
        stations = [s for f in mine for s in (f.get("stations_mm") or [f["station_mm"]])]
        out[group] = {"s_mid": 0.5 * (min(stations) + max(stations)), "r_max": max(r for f in mine for r in f.get("radii_mm", [0.0]))}
    return out


def to_sheet(group: str, frame: dict, s: float, r: float) -> tuple[float, float]:
    cx, cy = VIEWS[group]["centre"]
    k = VIEWS[group]["scale"]
    return (cx + k * (s - frame[group]["s_mid"]), cy + k * r)


def rounded(value):
    """Numbers as the record keeps them: 4 decimals."""

    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, list):
        return [rounded(v) for v in value]
    if isinstance(value, dict):
        return {k: rounded(v) for k, v in value.items()}
    return value


def build(data: dict, path: Path, date: str, forget_scale: bool = False) -> dict:
    """Write the sheet. Returns the dimensions with the value each must show and the title-block fields."""

    import ezdxf

    doc = ezdxf.new("R2010", setup=True, units=4)
    doc.header["$LTSCALE"] = dw.LTSCALE
    msp = doc.modelspace()
    for name, linetype in (("text", "CONTINUOUS"), ("border", "CONTINUOUS"), ("title", "CONTINUOUS")):
        doc.layers.add(name, linetype=linetype)
    for group in VIEWS:  # one set of layers per view, so the read-back can tell the views apart
        for kind, linetype, weight in (("profile", "CONTINUOUS", 50), ("datum", "CENTER", 18), ("plane", "PHANTOM", 35),
                                       ("dims", "CONTINUOUS", 18), ("labels", "CONTINUOUS", 18)):
            doc.layers.add(f"{kind}-{group}", linetype=linetype, lineweight=weight)
    w, h = SHEET_MM
    b = BORDER_MM
    msp.add_lwpolyline([(0, 0), (w, 0), (w, h), (0, h)], close=True, dxfattribs={"layer": "border"})
    msp.add_lwpolyline([(b, b), (w - b, b), (w - b, h - b), (b, h - b)], close=True, dxfattribs={"layer": "border"})
    frame = layout(data["features"])
    dims = []

    def reference(group, name, p1, p2, base, angle, expected):
        # a drawn length is the fitted one times the view's scale: the style divides it back
        style = {**dw.DIMSTYLE, "dimlfac": 1.0 if forget_scale else 1.0 / VIEWS[group]["scale"]}
        dim = msp.add_linear_dim(base=base, p1=p1, p2=p2, angle=angle, text="(<>)", dimstyle="EZDXF",
                                 override=style, dxfattribs={"layer": f"dims-{group}"})
        dim.render()
        dims.append({"dimension": name, "expected_mm": round(expected, 4), "shows": f"({fmt(expected)})"})

    for group in VIEWS:
        mine = sorted((f for f in data["features"] if f["group"] == group),
                      key=lambda f: f.get("mid_station_mm", f.get("station_mm")))
        fr = frame[group]
        lo = min(s for f in mine for s in (f.get("stations_mm") or [f["station_mm"]]))
        hi = max(s for f in mine for s in (f.get("stations_mm") or [f["station_mm"]]))
        msp.add_line(to_sheet(group, frame, lo - OVERSHOOT_MM, 0.0), to_sheet(group, frame, hi + OVERSHOOT_MM, 0.0),
                     dxfattribs={"layer": f"datum-{group}"})
        lx, ly = to_sheet(group, frame, lo - OVERSHOOT_MM, -fr["r_max"])
        scale = f"{VIEWS[group]['scale']:g}:1"
        msp.add_text(f"{group}, {scale}, on its datum axis (notes)", height=dw.TEXT_MM,
                     dxfattribs={"layer": f"labels-{group}", "insert": (lx, ly - 11.0)})
        # a numbered callout under each feature, and a legend to the right of the view
        rx, _ = to_sheet(group, frame, hi + OVERSHOOT_MM, 0.0)
        legend_y = VIEWS[group]["centre"][1] + 4.0 * (len(mine) - 1) / 2.0
        for i, f in enumerate(mine):
            if f["type"] == "plane":
                kind = f"plane {f['normal_to_datum_deg']:.2f}°"
                callout = to_sheet(group, frame, f["station_mm"], -fr["r_max"] - 1.5)
            else:
                kind = "cylinder" if f["type"] == "cylinder" else f"cone {f['half_angle_deg']:.2f}°"
                callout = to_sheet(group, frame, f["mid_station_mm"], -max(f["radii_mm"]))
            msp.add_text(str(i + 1), height=dw.TEXT_MM, dxfattribs={"layer": f"labels-{group}",
                                                                     "insert": (callout[0] - 0.8, callout[1] - 4.0)})
            msp.add_text(f"{i + 1}  {f['label']}, {kind}", height=dw.TEXT_MM,
                         dxfattribs={"layer": f"labels-{group}", "insert": (rx + 3.0, legend_y - 4.0 * i)})
        for i, f in enumerate(mine):
            if f["type"] == "plane":
                reach = fr["r_max"] + 1.5
                msp.add_line(to_sheet(group, frame, f["station_mm"], -reach), to_sheet(group, frame, f["station_mm"], reach),
                             dxfattribs={"layer": f"plane-{group}"})
                continue
            (s0, s1), (r0, r1) = f["stations_mm"], f["radii_mm"]
            for sign in (1.0, -1.0):
                msp.add_line(to_sheet(group, frame, s0, sign * r0), to_sheet(group, frame, s1, sign * r1),
                             dxfattribs={"layer": f"profile-{group}"})
            sm, rm = f["mid_station_mm"], 0.5 * f["mid_diameter_mm"]
            # the diameter at mid-band, from the upper to the lower generator
            reference(group, f"{group}: {f['label']} diameter at mid-band", to_sheet(group, frame, sm, -rm),
                      to_sheet(group, frame, sm, rm), to_sheet(group, frame, sm, 0.0), 90, f["mid_diameter_mm"])
        # stations along the datum, between neighbouring features, above the view
        anchors = [(f, f.get("mid_station_mm", f.get("station_mm"))) for f in mine]
        for j, ((fa, sa), (fb, sb)) in enumerate(zip(anchors, anchors[1:])):
            ya = fr["r_max"] + 1.5 if fa["type"] == "plane" else 0.5 * fa["mid_diameter_mm"]
            yb = fr["r_max"] + 1.5 if fb["type"] == "plane" else 0.5 * fb["mid_diameter_mm"]
            bx, by = to_sheet(group, frame, sa, fr["r_max"] + 1.5)
            base = (bx, by + 5.0 + 6.0 * j)
            reference(group, f"{group}: {fa['label']} to {fb['label']} along the datum", to_sheet(group, frame, sa, ya),
                      to_sheet(group, frame, sb, yb), base, 0, abs(sb - sa))

    notes = ("Values in parentheses are reference values fitted on a scan of the 935 head: not dimensions of the specimen. "
             "1 scan unit = 1 mm by owner instruction; no length is measured (#693). "
             "Each feature is drawn about its own axis at its station on its group datum; tilts and offsets from the datum "
             "are in params/reference-sheet.json; a plane's angle is that of its normal to the datum. Datums: "
             + "; ".join(f"{g}: {d['what']}" for g, d in data["datums"].items())
             + ". No tolerance, fit or thread is drawn: none has a source. "
             f"{len(data['features'])} of 32 features are confirmed; the others are not drawn (params/feature-confirmation.json).")
    msp.add_mtext(notes, dxfattribs={"layer": "text", "char_height": dw.TEXT_MM, "width": NOTES["width"],
                                     "insert": NOTES["insert"], "attachment_point": 1})
    x0, y0 = TABLE["insert"]
    header = ("feature", "confirmed by", "held-out share", "evidence")
    columns = (0.0, 78.0, 140.0, 172.0)
    for col, text in zip(columns, header):
        msp.add_text(text, height=dw.TEXT_MM, dxfattribs={"layer": "text", "insert": (x0 + col, y0)})
    for i, f in enumerate(data["features"]):
        y = y0 - (i + 1) * TABLE["row_mm"]
        for col, text in zip(columns, (f["id"], f["confirmed_by"], f"{100 * f['held_out_share']:.1f}%", f["evidence"])):
            msp.add_text(text, height=dw.TEXT_MM, dxfattribs={"layer": "text", "insert": (x0 + col, y)})

    fields = {"TITLE": "935 head: confirmed machined features", "SOURCE": "935 head twin, source/reference_sheet.py",
              "SCALE": "plugs 2:1, valves 1:1", "UNITS": "mm, 1 scan unit = 1 mm (owner)", "PROJECTION": "profiles about fitted datum axes",
              "SCALE_STATUS": "uncalibrated: no measured length (#693)",
              "EVIDENCE": "fitted on a scan; (values) are references", "DATE": date}
    tw, th = TITLE["size"]
    lw = TITLE["label_mm"]
    block = doc.blocks.new("TITLE_BLOCK")
    block.add_lwpolyline([(0, 0), (tw, 0), (tw, th), (0, th)], close=True)
    block.add_line((lw, 0), (lw, th))
    row = th / len(dw.TITLE_TAGS)
    for i, tag in enumerate(dw.TITLE_TAGS):
        y = th - (i + 1) * row
        block.add_line((0, y), (tw, y))
        block.add_text(tag.replace("_", " ").capitalize(), height=dw.TEXT_MM, dxfattribs={"insert": (1.5, y + 1.75)})
        block.add_attdef(tag, insert=(lw + 1.5, y + 1.75), dxfattribs={"height": dw.TEXT_MM})
    msp.add_blockref("TITLE_BLOCK", TITLE["insert"], dxfattribs={"layer": "title"}).add_auto_attribs(fields)
    doc.saveas(path)
    return {"dimensions": dims, "title_block": fields, "frame": frame}


def check(path: Path, written: dict, data: dict) -> tuple[list, list]:
    """Read the sheet back with a fresh reader."""

    import ezdxf
    from ezdxf import bbox

    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    checks = []

    def add(what, passed, detail=None):
        checks.append({"check": what, "passed": bool(passed), **({"detail": detail} if detail is not None else {})})

    lines = [(e.dxf.start.x, e.dxf.start.y, e.dxf.end.x, e.dxf.end.y) for e in msp.query("LINE")
             if e.dxf.layer.startswith(("profile-", "plane-"))]
    dims = list(msp.query("DIMENSION"))
    add(f"{len(written['dimensions'])} dimensions read back", len(dims) == len(written["dimensions"]), len(dims))
    shown_all = []
    for want, dim in zip(written["dimensions"], dims):
        shown, height = dw.displayed(doc, dim)
        points = [(dim.dxf.defpoint2.x, dim.dxf.defpoint2.y), (dim.dxf.defpoint3.x, dim.dxf.defpoint3.y)]
        anchored = all(any(dw.on_segment(p, ln, 1e-6) for ln in lines) for p in points)
        reference_form = dim.dxf.get("text", "") == "(<>)"
        shown_all.append({**want, "displayed": shown, "text_height_mm": height})
        add(f"{want['dimension']}: shows {want['shows']}, a reference value, from points on the drawn profile",
            shown == want["shows"] and reference_form and anchored and height is not None and height >= dw.TEXT_MM,
            [shown, height, anchored])
    texts = [e.plain_text() if e.dxftype() == "MTEXT" else e.dxf.text for e in msp.query("TEXT MTEXT")]
    texts += [dw.displayed(doc, d)[0] or "" for d in dims]
    inserts = list(msp.query("INSERT[name=='TITLE_BLOCK']"))
    got = {a.dxf.tag: a.dxf.text for a in inserts[0].attribs} if len(inserts) == 1 else {}
    texts += list(got.values())
    bad = [t for t in texts if FORBIDDEN.search(t)]
    add("no tolerance, fit or thread anywhere on the sheet", not bad, bad[:3])
    add("no dimension carries a tolerance or limits",
        all(not d.override().get("dimtol", 0) and not d.override().get("dimlim", 0) for d in dims))
    add("title block: every field comes back as written", got == written["title_block"], sorted(got))
    add("title block: the scale is stated as uncalibrated, with its issue",
        "uncalibrated" in got.get("SCALE_STATUS", "") and "#693" in got.get("SCALE_STATUS", ""))
    tx, ty = TITLE["insert"]
    tw, th = TITLE["size"]
    fits = all(tx - 1e-6 <= t.extmin.x and t.extmax.x <= tx + tw + 1e-6
               for t in (bbox.extents([a]) for a in inserts[0].attribs)) if len(inserts) == 1 else False
    add("title block: every field fits inside it", fits)
    table = " ".join(texts)
    confirmed = {f["id"] for f in data["features"]}
    others = [rid for rid in data["all_ids"] if rid not in confirmed]
    add("every confirmed feature is named", all(rid in table for rid in confirmed))
    # a datum statement names the fitted feature the datum comes from; nothing else may name an unconfirmed one
    named = " ".join(t for t in texts if "datum" not in t)
    add("no unconfirmed feature is named, except as the source of a datum",
        not [rid for rid in others if re.search(rf"\b{re.escape(rid)}\b", named)])
    for group, view in VIEWS.items():
        x0, y0, x1, y1 = view["cell"]
        mine = [e for e in msp if e.dxf.layer.endswith(f"-{group}")]
        box = bbox.extents(mine)
        add(f"{group}: profile, labels and dimensions stay in its cell", x0 <= box.extmin.x and box.extmax.x <= x1 and y0 <= box.extmin.y and box.extmax.y <= y1,
            [round(box.extmin.x, 1), round(box.extmin.y, 1), round(box.extmax.x, 1), round(box.extmax.y, 1)])
    box = bbox.extents(msp)
    w, h = SHEET_MM
    add("everything drawn lies on the sheet", box.extmin.x >= -1e-6 and box.extmin.y >= -1e-6 and box.extmax.x <= w + 1e-6
        and box.extmax.y <= h + 1e-6)
    return checks, shown_all


def main(params, work, out, media) -> None:
    import ezdxf
    from ezdxf.addons.drawing.config import Configuration, LinePolicy
    from ezdxf.addons.drawing.matplotlib import qsave

    params, work = Path(params), Path(work)
    if work.exists():
        raise SystemExit(f"{work} exists: give a new directory")
    work.mkdir(parents=True)
    data = assemble(params)
    date = time.strftime("%Y-%m-%d")
    sheet = work / "reference-sheet.dxf"
    written = build(data, sheet, date)
    checks, shown = check(sheet, written, data)
    # control: the same sheet with a dimension style that forgets the 2:1 scale must be caught
    control = work / "control-forgot-scale.dxf"
    wrong = build(data, control, date, forget_scale=True)
    caught = any(not c["passed"] and "shows" in c["check"] for c in check(control, wrong, data)[0])
    checks.append({"check": "control: a dimension style that forgets the 2:1 scale: caught", "passed": caught})
    from ezdxf.addons.drawing.config import LineweightPolicy
    qsave(ezdxf.readfile(sheet).modelspace(), str(media), bg="#FFFFFF", dpi=150,
          config=Configuration(line_policy=LinePolicy.ACCURATE, lineweight_policy=LineweightPolicy.ABSOLUTE))
    record = {
        "schema": SCHEMA, "date": date, "issue": "#708",
        "claims": "a reference sheet of fitted numbers: every value is fitted on a scan whose scale is an owner instruction "
                  "(#693); none is a dimension, a tolerance, a fit or a thread of the specimen",
        "tool": "ezdxf on a DXF sheet, as assigned in docs/TOOLCHAIN.md and witnessed by drawing_witness.py",
        "inputs_sha256": data["inputs"],
        "sheet": {"size_mm": list(SHEET_MM), "scale": {g: f"{v['scale']:g}:1" for g, v in VIEWS.items()},
                  "dxf": "private (work directory)",
                  "image": Path(media).name, "image_sha256": sha256_file(Path(media))},
        "datums": data["datums"], "features": rounded(data["features"]), "dimensions": rounded(shown),
        "checks": checks, "passed": all(c["passed"] for c in checks),
    }
    Path(out).write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({"passed": record["passed"], "failed": [c for c in checks if not c["passed"]]}, ensure_ascii=False))
    assert record["passed"]


if __name__ == "__main__":
    main(*sys.argv[1:])
