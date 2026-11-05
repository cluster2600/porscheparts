"""Run the pre-registered scan-vs-reference checks C1-C4 on the 935 scan.

Usage:
    python -I measure_trial.py /path/to/935-xtreme-cylinder-head.obj results.json

The OBJ is refused unless its SHA-256 matches. Thresholds and reference ranges
are read from ../thresholds.json, committed before this script was first run.
Nothing is rescaled or re-registered: the scan is read in OBJ units, taken as
millimetres by the owner's declaration.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "twins/reference-935-cylinder-head/source"))

from scan_frame import FRAME, HIGH_PORT_FACE_B, LOW_PORT_FACE_B  # noqa: E402
from scan_io import load  # noqa: E402
from sections import fit_circle_2d, polygon_area_2d, section_loops  # noqa: E402

E3 = np.eye(3)


def loop_record(p2: np.ndarray, closed: bool) -> dict:
    c, r, rms = fit_circle_2d(p2)
    ang = np.unwrap(np.arctan2(p2[:, 1] - c[1], p2[:, 0] - c[0]))
    cover = 1.0 if closed else float(min(1.0, (ang.max() - ang.min()) / (2 * np.pi)))
    return {
        "closed": bool(closed),
        "points": int(len(p2)),
        "equivalent_diameter_mm": round(2 * float(np.sqrt(polygon_area_2d(p2) / np.pi)), 3) if closed else None,
        "circle_diameter_mm": round(2 * r, 3),
        "circle_rms_mm": round(rms, 3),
        "angular_cover": round(cover, 3),
        "centre": [round(float(x), 2) for x in c],
    }


def port_stations(abc, f, face_b: float, inward: float) -> list[dict]:
    """Sections normal to B, from the flange face inward, for the port loop."""
    out = []
    for depth in np.arange(0.5, 20.01, 0.5):
        b = face_b + inward * depth
        best = None
        for p, closed in section_loops(abc, f, E3[1], b):
            q = p[:, [0, 2]]
            if len(q) < 30:
                continue
            rec = loop_record(q, closed)
            if not (25.0 < rec["circle_diameter_mm"] < 60.0):
                continue
            if rec["circle_rms_mm"] > 0.1 * rec["circle_diameter_mm"] or rec["angular_cover"] < 0.5:
                continue
            # the port is the near-circular loop closest to the face centre line A=128
            score = abs(rec["centre"][0] - 128.0)
            if best is None or score < best[0]:
                best = (score, rec)
        if best:
            out.append({"depth_from_face_mm": round(float(depth), 2), "B": round(float(b), 2), **best[1]})
    return out


def track_bore(abc, f, seed_ab, c_range):
    pts = []
    for c in np.arange(c_range[0], c_range[1] + 1e-9, 0.5):
        best = None
        for p, closed in section_loops(abc, f, E3[2], c):
            if not closed or len(p) < 30:
                continue
            q = p[:, :2]
            cc, r, rms = fit_circle_2d(q)
            dist = float(np.hypot(*(cc - np.asarray(seed_ab))))
            if dist < 4 and 4 < r < 9 and (best is None or dist < best[0]):
                best = (dist, cc, r)
        if best:
            pts.append([best[1][0], best[1][1], c])
    return np.asarray(pts)


def axis_sections(abc, f, centres: np.ndarray, opening_c: float, min_depth: float):
    """Fit the bore axis through C-section centres, then cut normal to it."""
    mean = centres.mean(0)
    _, _, vt = np.linalg.svd(centres - mean)
    axis = vt[0] / np.linalg.norm(vt[0])
    if axis[2] > 0:
        axis = -axis  # point away from the chamber side, toward more negative C
    tilt = float(np.degrees(np.arccos(abs(axis[2]))))
    # local frame normal to the axis
    u = np.cross(axis, [1.0, 0.0, 0.0])
    u /= np.linalg.norm(u)
    w = np.cross(axis, u)
    # axial position of the opening: where the axis crosses C = opening_c
    s_open = (opening_c - mean[2]) / axis[2]
    s_end = (centres[:, 2].min() - mean[2]) / axis[2]
    rows = []
    for s in np.arange(s_open + min_depth, s_end + 1e-9, 0.5):
        o = mean + s * axis
        best = None
        for p, closed in section_loops(abc, f, axis, float(o @ axis)):
            rel = p - o
            q = np.column_stack([rel @ u, rel @ w])
            if len(q) < 30:
                continue
            rec = loop_record(q, closed)
            dist = float(np.hypot(*rec["centre"]))
            if dist < 3 and 8 < rec["circle_diameter_mm"] < 18 and (best is None or dist < best[0]):
                best = (dist, rec)
        if best:
            rows.append({"depth_below_opening_mm": round(float(s - s_open), 2), **best[1]})
    return {
        "axis_point_abc": [round(float(x), 3) for x in mean],
        "axis_direction_abc": [round(float(x), 4) for x in axis],
        "tilt_from_C_deg": round(tilt, 2),
        "opening_C": opening_c,
        "stations": rows,
    }


def judge(values: list[float], lo: float, hi: float, T: float) -> str:
    if not values:
        return "not_observable"
    return "pass" if all(lo - T <= x <= hi + T for x in values) else "fail"


def main() -> None:
    obj, out = Path(sys.argv[1]), Path(sys.argv[2])
    contract = json.loads((HERE.parent / "thresholds.json").read_text())
    checks = {c["id"]: c for c in contract["checks"]}
    v, f, digest = load(obj)
    abc = v @ FRAME.T

    # C1/C2 ports at the two flange faces. Which face is intake is not
    # established by this script; both assignments are judged.
    faces = {
        "low_B_face": port_stations(abc, f, LOW_PORT_FACE_B, +1.0),
        "high_B_face": port_stations(abc, f, HIGH_PORT_FACE_B, -1.0),
    }
    port_values = {}
    for name, st in faces.items():
        closed = [s for s in st if s["closed"]]
        port_values[name] = {
            "check_value_mm": closed[0]["equivalent_diameter_mm"] if closed else None,
            "check_station": closed[0] if closed else None,
            "closed_stations": len(closed),
            "open_stations": len(st) - len(closed),
            "smallest_closed_equivalent_diameter_mm": min((s["equivalent_diameter_mm"] for s in closed), default=None),
        }
    assignments = {}
    for intake_face, exhaust_face in (("low_B_face", "high_B_face"), ("high_B_face", "low_B_face")):
        res = {}
        for cid, face in (("C1", intake_face), ("C2", exhaust_face)):
            lo, hi = checks[cid]["reference_range_mm"]
            val = port_values[face]["check_value_mm"]
            res[cid] = {"face": face, "value_mm": val,
                        "outcome": judge([val] if val is not None else [], lo, hi, checks[cid]["threshold_T_mm"])}
        assignments[f"intake={intake_face}"] = res

    # C3 spark-plug bores: two inclined ~12 mm bores either side of A=128.
    plugs = {}
    for name, seed in (("plug_bore_A_high", (155.6, -176.2)), ("plug_bore_A_low", (100.7, -169.6))):
        centres = track_bore(abc, f, seed, (-119.5, -114.0))
        plugs[name] = axis_sections(abc, f, centres, opening_c=-113.5, min_depth=3.0)
        plugs[name]["tracked_C_sections"] = int(len(centres))
    c3_values = [s["circle_diameter_mm"] for p in plugs.values() for s in p["stations"] if s["closed"]]
    lo, hi = checks["C3"]["reference_range_mm"]
    c3 = {"values_mm": c3_values, "outcome": judge(c3_values, lo, hi, checks["C3"]["threshold_T_mm"])}

    # C4 valve-guide bores: closed 6-11 mm loops inside the head body
    # (deck C=-88 to head back C=-175), within 15 mm of the valve plane A=128.
    candidates = []
    for c in np.arange(-174.0, -95.0, 1.0):
        for p, closed in section_loops(abc, f, E3[2], c):
            if not closed or len(p) < 30:
                continue
            rec = loop_record(p[:, :2], closed)
            if 6 < rec["equivalent_diameter_mm"] < 11 and abs(rec["centre"][0] - 128) < 15 and rec["circle_rms_mm"] < 0.5:
                candidates.append({"C": float(c), **rec})
    # A bore cannot continue outside the material. A candidate whose section
    # (closed, or open with at least half its circle) persists 5 mm beyond the
    # head back (C=-175) with the same diameter is a solid protrusion (stud or
    # hardware), not a guide bore.
    for cand in candidates:
        beyond = []
        for p, closed in section_loops(abc, f, E3[2], -180.0):
            if len(p) >= 30:
                rec = loop_record(p[:, :2], closed)
                same = abs(rec["circle_diameter_mm"] - cand["circle_diameter_mm"]) < 0.5
                near = np.hypot(rec["centre"][0] - cand["centre"][0], rec["centre"][1] - cand["centre"][1]) < 1.0
                if same and near and rec["angular_cover"] >= 0.5:
                    beyond.append({"circle_diameter_mm": rec["circle_diameter_mm"], "closed": rec["closed"],
                                   "angular_cover": rec["angular_cover"]})
        cand["section_at_C_minus_180"] = beyond
        cand["identification"] = ("solid protrusion beyond the head back (stud or hardware), not a guide bore"
                                  if beyond else "unidentified")
    guide = [c for c in candidates if c["identification"] == "unidentified"]
    c4 = {"candidates_in_head_body": candidates,
          "outcome": "not_observable" if not guide else "needs_identification"}

    result = {
        "schema": "capture-protocol-scan-trial-results-v1",
        "trial_id": contract["trial_id"],
        "scan_sha256": digest,
        "vertices": int(len(v)),
        "triangles": int(len(f)),
        "frame": "twins/reference-935-cylinder-head/source/scan_frame.py (A, B, C); C normal to the combustion face",
        "ports": {"stations": faces, "values": port_values, "assignments": assignments},
        "C3": {"bores": plugs, **c3},
        "C4": c4,
    }
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"ports": port_values, "assignments": assignments, "C3": c3,
                      "C4": c4["outcome"], "C4_candidates": len(candidates)}, indent=1))


if __name__ == "__main__":
    main()
