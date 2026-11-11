#!/usr/bin/env python3
"""Fit the revolved machined features of the 935 head with the assigned tool.

The assigned tool is ``benchmarks/scan-primitive-fitting/primitive_fit.py``
(one model for cylinder and cone, standard deviations from the fit, shared
zones left out). It is run here on windows of the acquired scan, one window per
feature: a valve throat, a guide, a plug bore, a stud passage.

A window is a tube about a seed axis, stated in ``params/feature-rois.json`` as
a station range and a radius range. It selects points by position only. The
windows were drawn by hand from radius-against-station plots of the scan; they
are inputs, not results, and the fit may leave a window empty.

Half of the vertices of each window are fitted and the other half are kept out
of the fit: ``check_features.py`` measures those with CloudCompare.

Nothing here knows which valve is the intake, what a thread is, or what the
part should measure. The output is fitted numbers on scan data whose scale is
an owner instruction: no dimension of the specimen is established.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path

import numpy as np

from twin_common import sha256_file, write_json

SCHEMA = "935-cad-twin-feature-fits/1"


def load_tool(tool_path: Path):
    spec = importlib.util.spec_from_file_location("primitive_fit", tool_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def vertex_normals(v: np.ndarray, f: np.ndarray):
    """Area-weighted vertex normals; vertices that no facet uses get none."""

    tri = v[f]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    vn = np.zeros_like(v)
    for i in range(3):
        np.add.at(vn, f[:, i], n)
    length = np.linalg.norm(vn, axis=1)
    used = length > 0
    vn[used] /= length[used, None]
    return vn, used


def window(points: np.ndarray, roi: dict) -> np.ndarray:
    """Indices of the points inside the tube of a region of interest."""

    a = np.asarray(roi["seed_axis"], dtype=float)
    a /= np.linalg.norm(a)
    v = points - np.asarray(roi["seed_point"], dtype=float)
    t = v @ a
    rho = np.linalg.norm(v - np.outer(t, a), axis=1)
    return np.flatnonzero(
        (t >= roi["t_mm"][0]) & (t <= roi["t_mm"][1]) & (rho >= roi["rho_mm"][0]) & (rho <= roi["rho_mm"][1])
    )


def split_halves(index: np.ndarray):
    """Deterministic split of scan vertex indices into a fitted and a held-out half.

    The parity of a hash of the vertex index decides, so the split does not
    depend on the window, on the order of the regions or on a random state.
    """

    mixed = (index.astype(np.uint64) * np.uint64(2654435761)) >> np.uint64(7)
    fitted = (mixed & np.uint64(1)) == 0
    return index[fitted], index[~fitted]


def _angle_deg(u, v) -> float:
    """Angle between two directions, sign ignored."""

    u, v = np.asarray(u, dtype=float), np.asarray(v, dtype=float)
    cosine = abs(float(u @ v)) / (np.linalg.norm(u) * np.linalg.norm(v))
    return math.degrees(math.acos(min(cosine, 1.0)))


def choose(found: list, roi: dict):
    """The primitive of the stated kind holding the most points, determined ones first, or None.

    ``plane``: a plane whose normal lies along the seed axis. ``seat``: a cone
    of at least 20 degrees. ``bore`` and ``boss``: a cylinder, or a cone under
    20 degrees, on the stated side. The tool reports a primitive as not
    determined when the points it does not share with another model do not fix
    it; such a primitive is chosen only if no determined one qualifies, and it
    stays flagged: detected, not measured.
    """

    limit = roi.get("max_axis_angle_deg", 10.0)
    best = None
    for q in found:
        if roi["kind"] == "plane":
            if q["type"] != "plane" or _angle_deg(q["normal"], roi["seed_axis"]) > limit:
                continue
        else:
            if q["type"] == "plane" or q["side"] != roi["side"]:
                continue
            if _angle_deg(q["axis_direction"], roi["seed_axis"]) > limit:
                continue
            steep = q["type"] == "cone" and q["half_angle_deg"] >= 20.0
            if steep != (roi["kind"] == "seat"):
                continue
        if best is None or (q["determined"], q["points"]) > (best["determined"], best["points"]):
            best = q
    return best


def brief(q: dict, roi: dict) -> dict:
    """One line per primitive found in a window, chosen or not."""

    if q["type"] == "plane":
        return {"type": "plane", "points": q["points"], "determined": q["determined"]}
    return {
        "type": q["type"],
        "side": q["side"],
        "determined": q["determined"],
        "points": q["points"],
        "diameter_mm": round(2.0 * radius_at(q), 3),
        "half_angle_deg": round(q.get("half_angle_deg", 0.0), 3),
        "arc_deg": round(q["arc_deg"], 1),
        "length_mm": round(q["length_mm"], 2),
        "axis_to_seed_deg": round(_angle_deg(q["axis_direction"], roi["seed_axis"]), 3),
    }


def radius_at(q: dict, station: float = 0.0) -> float:
    if q["type"] == "cylinder":
        return q["radius_mm"]
    return q["radius_at_axis_point_mm"] + math.tan(math.radians(q["half_angle_deg"])) * station


def station_range(q: dict, points: np.ndarray, band: float):
    """Stations, from the axis point, of the fitted vertices within ``band`` of a revolved primitive."""

    a = np.asarray(q["axis_direction"], dtype=float)
    v = points - np.asarray(q["axis_point"], dtype=float)
    t = v @ a
    rho = np.linalg.norm(v - np.outer(t, a), axis=1)
    k = math.tan(math.radians(q.get("half_angle_deg", 0.0)))
    near = np.abs(rho - radius_at(q) - k * t) / math.sqrt(1.0 + k * k) < band
    return [round(float(t[near].min()), 3), round(float(t[near].max()), 3)]


def rounded(q: dict, points: np.ndarray, band: float) -> dict:
    """The public numbers of one fitted primitive."""

    if q["type"] == "plane":
        return {
            "type": "plane",
            "point": [round(x, 4) for x in q["point"]],
            "normal": [round(x, 6) for x in q["normal"]],
            "determined": q["determined"],
            "rms_mm": round(q["rms_mm"], 4),
            "points": q["points"],
            "fit_points": q["fit_points"],
        }
    sigma = (lambda key, digits=5: round(q[key], digits)) if q["determined"] else (lambda key, digits=5: None)
    out = {
        "type": q["type"],
        "side": q["side"],
        "determined": q["determined"],
        "axis_point": [round(x, 4) for x in q["axis_point"]],
        "axis_direction": [round(x, 6) for x in q["axis_direction"]],
        "diameter_mm": round(2.0 * radius_at(q), 4),
        "radius_sigma_mm": sigma("radius_sigma_mm"),
        "axis_direction_sigma_deg": sigma("axis_direction_sigma_deg"),
        "axis_point_sigma_mm": sigma("axis_point_sigma_mm"),
        "rms_mm": round(q["rms_mm"], 4),
        "arc_deg": round(q["arc_deg"], 1),
        "length_mm": round(q["length_mm"], 2),
        "station_range_mm": station_range(q, points, band),
        "points": q["points"],
        "fit_points": q["fit_points"],
    }
    if q["type"] == "cone":
        out["half_angle_deg"] = round(q["half_angle_deg"], 4)
        out["half_angle_sigma_deg"] = sigma("half_angle_sigma_deg")
        out["diameter_range_mm"] = [round(2.0 * r, 4) for r in q["radius_range_mm"]]
    return out


def group_datums(rules: dict, by_id: dict) -> dict:
    """The datum axis of each group, from the rule the region table states for it.

    ``axis_of``: the axis of one determined revolved fit. ``line_through``: the
    line through the axis points of two fits. A short feature fixes where its
    axis is far better than where it points, so two centres far apart give a
    better direction than either feature does.
    """

    out = {}
    for group, rule in rules.items():
        if "axis_of" in rule:
            fit = by_id[rule["axis_of"]]["fit"]
            if fit and fit["determined"]:
                out[group] = {"rule": rule, "axis_point": fit["axis_point"], "axis_direction": fit["axis_direction"]}
            continue
        first, second = (by_id[i]["fit"] for i in rule["line_through"])
        if first and second:
            d = np.asarray(second["axis_point"], dtype=float) - np.asarray(first["axis_point"], dtype=float)
            span = float(np.linalg.norm(d))
            out[group] = {"rule": rule, "axis_point": first["axis_point"],
                          "axis_direction": [round(x, 6) for x in (d / span)], "span_mm": round(span, 3)}
    return out


def about_axis(points: np.ndarray, axis_point, axis_direction) -> dict:
    """A revolved surface measured about a given axis instead of its own.

    Least squares of ``rho = r0 + k t + ex cos(theta) + ey sin(theta)``: the
    half-angle and diameter the surface has about that axis, and how far its
    centre sits from it (the eccentricity, half the run-out of a round feature).
    The half-angle is positive when the radius grows along the axis direction.
    On a band a few millimetres long a tilt of the surface and an offset of its
    centre change the radius alike, so the eccentricity stands for both.
    """

    a = np.asarray(axis_direction, dtype=float)
    a = a / np.linalg.norm(a)
    e1 = np.cross(a, np.eye(3)[np.argmin(np.abs(a))])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(a, e1)
    v = points - np.asarray(axis_point, dtype=float)
    t = v @ a
    x, y = v @ e1, v @ e2
    rho, theta = np.hypot(x, y), np.arctan2(y, x)
    station = float(t.mean())
    design = np.column_stack([np.ones_like(t), t - station, np.cos(theta), np.sin(theta)])
    coefficient, *_ = np.linalg.lstsq(design, rho, rcond=None)
    residual = rho - design @ coefficient
    return {
        "diameter_mm": round(2.0 * float(coefficient[0]), 4),
        "half_angle_deg": round(math.degrees(math.atan(float(coefficient[1]))), 3),
        "eccentricity_mm": round(float(math.hypot(coefficient[2], coefficient[3])), 4),
        "station_mm": round(station, 3),
        "radial_rms_mm": round(float(np.sqrt((residual ** 2).mean())), 4),
        "points": int(len(t)),
    }


def near_fit(q: dict, points: np.ndarray, band: float) -> np.ndarray:
    """The points within ``band`` of a fitted revolved primitive."""

    a = np.asarray(q["axis_direction"], dtype=float)
    v = points - np.asarray(q["axis_point"], dtype=float)
    t = v @ a
    rho = np.linalg.norm(v - np.outer(t, a), axis=1)
    k = math.tan(math.radians(q.get("half_angle_deg", 0.0)))
    return points[np.abs(rho - 0.5 * q["diameter_mm"] - k * t) / math.sqrt(1.0 + k * k) < band]


def relate(fit: dict, datum: dict) -> dict:
    """Where a fitted primitive sits against the datum axis of its group."""

    a = np.asarray(datum["axis_direction"], dtype=float)
    c = np.asarray(datum["axis_point"], dtype=float)
    if fit["type"] == "plane":
        v = np.asarray(fit["point"], dtype=float) - c
        return {"normal_to_datum_axis_deg": round(_angle_deg(fit["normal"], a), 3),
                "station_on_datum_axis_mm": round(float(v @ a), 3)}
    v = np.asarray(fit["axis_point"], dtype=float) - c
    t = float(v @ a)
    return {"own_axis_to_datum_axis_deg": round(_angle_deg(fit["axis_direction"], a), 3),
            "own_axis_point_off_datum_axis_mm": round(float(np.linalg.norm(v - t * a)), 4),
            "station_on_datum_axis_mm": round(t, 3)}


def describe(b: dict) -> str:
    state = "" if b["determined"] else " (detected, not determined)"
    if b["type"] == "plane":
        return f"plane{state}, rms {b['rms_mm']:.3f} mm, {b['points']} points"
    extra = f", half-angle {b['half_angle_deg']:.3f} deg" if b["type"] == "cone" else ""
    return (f"{b['type']}{state} D {b['diameter_mm']:.3f} mm{extra}, rms {b['rms_mm']:.3f}, "
            f"arc {b['arc_deg']:.0f} deg, stations {b['station_range_mm']}, {b['points']} points")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--bare-scan", type=Path, required=True, help="private NPZ: v, f of the bare scan in the twin frame")
    ap.add_argument("--rois", type=Path, required=True)
    ap.add_argument("--tool", type=Path, required=True, help="benchmarks/scan-primitive-fitting/primitive_fit.py")
    ap.add_argument("--frame", type=Path, required=True, help="params/frame.json: the deck fit gives the noise")
    ap.add_argument("--only", nargs="*", help="fit these region ids only (exploration; no output is committed from it)")
    ap.add_argument("--private-out", type=Path, required=True, help="private NPZ of the fitted and held-out vertex indices")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    spec = json.loads(args.rois.read_text())
    frame = json.loads(args.frame.read_text())
    deck = next(p for p in frame["planes"] if p["name"] == "deck")
    noise = deck["residual"]["rms_mm"]
    pf = load_tool(args.tool)

    d = np.load(args.bare_scan)
    v, f = d["v"], d["f"]
    normals, used = vertex_normals(v, f)

    results, keep, fitted_points, band = [], {}, {}, None
    for roi in spec["regions"]:
        if args.only and roi["id"] not in args.only:
            continue
        inside = window(v, roi)
        inside = inside[used[inside]]
        fitted, held = split_halves(inside)
        st = pf.settings(noise, spec["pitch_mm"], min_points=roi.get("min_points", spec["min_points"]))
        found, unassigned = pf.detect(v[fitted], normals[fitted], st, spec["seed"])
        best = choose(found, roi)
        row = {
            "id": roi["id"],
            "group": roi["group"],
            "kind": roi["kind"],
            "window_vertices": int(len(inside)),
            "fitted_vertices": int(len(fitted)),
            "held_out_vertices": int(len(held)),
            "primitives_found_in_window": [brief(q, roi) for q in found],
            "fit": None if best is None else rounded(best, v[fitted], st["distance_mm"]),
        }
        results.append(row)
        fitted_points[roi["id"]] = v[fitted]
        band = st["distance_mm"]
        keep[roi["id"] + "__fitted"] = fitted
        keep[roi["id"] + "__held"] = held
        print(roi["id"], "no fit" if best is None else describe(row["fit"]), flush=True)

    by_id = {r["id"]: r for r in results}
    datums = {} if args.only else group_datums(spec["datums"], by_id)
    for r in results:
        datum = datums.get(r["group"])
        if not (r["fit"] and datum):
            continue
        r["to_group_datum"] = relate(r["fit"], datum)
        if r["fit"]["type"] != "plane":
            near = near_fit(r["fit"], fitted_points[r["id"]], band)
            r["to_group_datum"]["about_datum_axis"] = about_axis(near, datum["axis_point"], datum["axis_direction"])
    checks = []
    for check in ([] if args.only else spec.get("datum_checks", [])):
        other = group_datums({"check": {"line_through": check["line_through"]}}, by_id).get("check")
        if other and check["group"] in datums:
            checks.append({**check, "span_mm": other["span_mm"], "angle_to_group_datum_deg": round(
                _angle_deg(other["axis_direction"], datums[check["group"]]["axis_direction"]), 3)})
    angles = [{"between": pair, "angle_deg": round(_angle_deg(*(datums[g]["axis_direction"] for g in pair)), 3)}
              for pair in ([] if args.only else spec.get("datum_angles", [])) if all(g in datums for g in pair)]
    for datum in datums.values():
        datum["angle_to_frame_z_deg"] = round(_angle_deg(datum["axis_direction"], [0.0, 0.0, 1.0]), 3)

    args.private_out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(args.private_out, **keep)
    write_json(args.out, {
        "schema": SCHEMA,
        "scan_sha256": frame["scan_sha256"],
        "units": frame["units"],
        "tool": {
            "path": "benchmarks/scan-primitive-fitting/primitive_fit.py",
            "sha256": sha256_file(args.tool),
            "noise_mm": noise,
            "noise_source": "RMS of the deck plane fit in params/frame.json",
            "pitch_mm": spec["pitch_mm"],
            "seed": spec["seed"],
        },
        "rois_sha256": hashlib.sha256(args.rois.read_bytes()).hexdigest(),
        "split": "each window's vertices are split in two by a hash of the vertex index; one half is fitted, "
                 "the other is measured by check_features.py",
        "claims": "fitted numbers on acquired scan vertices in the twin frame; the standard deviations assume "
                  "independent noise and are a lower bound; no dimension of the specimen is established",
        "datum_rule": spec["datum_rule"],
        "group_datums": datums,
        "datum_checks": checks,
        "datum_angles": angles,
        "regions": results,
    })


if __name__ == "__main__":
    main()
