#!/usr/bin/env python3
"""Re-fit the unconfirmed machined features of the 935 head under a declared rule (issue #696).

``fit_features.py`` fitted 32 windows with the assigned tool and ``check_features.py`` confirmed 4. This script
applies the changes stated in ``params/feature-refit-declaration.json``, which was committed before any re-fit
was checked:

* **window**: the station range of each revolved window is shortened by the same amount at both ends;
* **outlier model**: the primitive is refitted by robust least squares (SciPy ``least_squares``, soft-L1 loss)
  on the fitted-half vertices of the shortened window within the check band of the first fit, keeping the
  primitive family (cylinder, cone or plane);
* **guard**: a re-fit whose axis, half-angle or diameter moves more than the declared amounts is not checked.

Only fitted-half vertices are read. The split is the hash split of ``fit_features.py``: a shortened window keeps
each vertex in the half it had (the split and the window are imported from it), so every vertex the check
measures was already held out of the first fit.

For each feature the output also states, from the fitted half, how much of the residual a richer surface would
remove: a revolved surface with offset, taper and two- and three-lobe terms, or a quadratic for a plane. The
declaration uses that to name why a feature that fails the check cannot be confirmed from this scan.

The output keeps the layout of ``feature-fits.json`` so ``check_features.py`` can measure it unchanged. Nothing
here is a dimension of the specimen.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

sys.path.insert(0, str(Path(__file__).resolve().parent))
from twin_common import sha256_file, write_json  # noqa: E402
from fit_features import split_halves, vertex_normals, window as tube  # noqa: E402

SCHEMA = "935-cad-twin-feature-refits/1"
DECLARATION_SCHEMA = "935-cad-twin-feature-refit-declaration/1"


def frame(a: np.ndarray):
    e1 = np.cross(a, np.eye(3)[np.argmin(np.abs(a))])
    e1 /= np.linalg.norm(e1)
    return e1, np.cross(a, e1)


def window(points: np.ndarray, roi: dict, trim: float) -> np.ndarray:
    """The window of fit_features.py with its station range shortened by ``trim`` at both ends."""

    return tube(points, {**roi, "t_mm": [roi["t_mm"][0] + trim, roi["t_mm"][1] - trim]})


def meridian(c, a, p):
    q = p - c
    t = q @ a
    return t, np.linalg.norm(q - np.outer(t, a), axis=1)


def revolved_distance(c, a, r0, k, stations, p):
    """Distance to the finite cone or cylinder between two stations (the surface the check meshes), and the
    signed radial residual to the unbounded one."""

    t, rho = meridian(c, a, p)
    A = np.array([stations[0], r0 + k * stations[0]])
    B = np.array([stations[1], r0 + k * stations[1]])
    AB = B - A
    P = np.column_stack([t, rho])
    s = np.clip(((P - A) @ AB) / (AB @ AB), 0.0, 1.0)
    return np.linalg.norm(P - (A + np.outer(s, AB)), axis=1), (rho - r0 - k * t) / math.sqrt(1.0 + k * k), t


def plane_distance(c, n, p, half: float = 40.0):
    """Distance to the square the check meshes for a plane, and the signed height above the plane."""

    e1, e2 = frame(n)
    q = p - c
    u, w, h = q @ e1, q @ e2, q @ n
    out = np.sqrt(np.clip(np.abs(u) - half, 0, None) ** 2 + np.clip(np.abs(w) - half, 0, None) ** 2)
    return np.hypot(out, h), h, u, w


def sigmas(sol) -> np.ndarray | None:
    """Standard deviations of the parameters from the Jacobian, or None when it is rank-deficient."""

    J = sol.jac
    if np.linalg.matrix_rank(J) < J.shape[1]:
        return None
    dof = max(len(sol.fun) - J.shape[1], 1)
    s2 = float((sol.fun ** 2).sum()) / dof
    return np.sqrt(np.diag(np.linalg.inv(J.T @ J)) * s2)


def refit_revolved(fit: dict, p: np.ndarray, rule: dict):
    a0 = np.asarray(fit["axis_direction"], dtype=float)
    a0 /= np.linalg.norm(a0)
    c0 = np.asarray(fit["axis_point"], dtype=float)
    e1, e2 = frame(a0)
    cone = fit["type"] == "cone"

    def unpack(x):
        a = a0 + x[0] * e1 + x[1] * e2
        a /= np.linalg.norm(a)
        return c0 + x[2] * e1 + x[3] * e2, a, x[4], (x[5] if cone else 0.0)

    def residual(x):
        c, a, r0, k = unpack(x)
        t, rho = meridian(c, a, p)
        return (rho - r0 - k * t) / math.sqrt(1.0 + k * k)

    x0 = [0.0, 0.0, 0.0, 0.0, 0.5 * fit["diameter_mm"]]
    if cone:
        x0.append(math.tan(math.radians(fit["half_angle_deg"])))
    sol = least_squares(residual, np.asarray(x0), loss=rule["loss"], f_scale=rule["f_scale_mm"])
    return unpack(sol.x), sigmas(sol)


def refit_plane(fit: dict, p: np.ndarray, rule: dict):
    n0 = np.asarray(fit["normal"], dtype=float)
    n0 /= np.linalg.norm(n0)
    c0 = np.asarray(fit["point"], dtype=float)
    e1, e2 = frame(n0)

    def unpack(x):
        n = n0 + x[0] * e1 + x[1] * e2
        return c0 + x[2] * n0, n / np.linalg.norm(n)

    sol = least_squares(lambda x: (p - unpack(x)[0]) @ unpack(x)[1], np.zeros(3), loss=rule["loss"],
                        f_scale=rule["f_scale_mm"])
    return unpack(sol.x), sigmas(sol)


def angle_deg(u, v) -> float:
    u, v = np.asarray(u, dtype=float), np.asarray(v, dtype=float)
    return math.degrees(math.acos(min(abs(float(u @ v)) / (np.linalg.norm(u) * np.linalg.norm(v)), 1.0)))


def share_within(d: np.ndarray, band: float, tolerance: float):
    near = d < band
    return (round(float((d[near] < tolerance).mean()), 4) if near.any() else None), int(near.sum())


def richer_surface_share(kind: str, s: np.ndarray, t: np.ndarray, extra, tolerance: float) -> float:
    """Share within tolerance once a richer surface takes out what it can: for a revolved feature a constant,
    a taper and 1-, 2- and 3-lobe terms about the re-fitted axis; for a plane a quadratic."""

    if kind == "plane":
        u, w = extra
        X = np.column_stack([np.ones_like(u), u, w, u * u, u * w, w * w])
    else:
        theta = extra
        cols = [np.ones_like(t), t - t.mean()]
        for h in (1, 2, 3):
            cols += [np.cos(h * theta), np.sin(h * theta)]
        X = np.column_stack(cols)
    coefficient, *_ = np.linalg.lstsq(X, s, rcond=None)
    return round(float((np.abs(s - X @ coefficient) < tolerance).mean()), 4)


def too_few(row: dict, d: np.ndarray, q: np.ndarray, rule: dict, acceptance: dict) -> dict:
    """A shortened window that leaves too few fitted vertices near the first fit: nothing is refitted."""

    row.update({"first_fit_share_on_fitted_half": share_within(d, acceptance["band_mm"], acceptance["tolerance_mm"])[0],
                "fit": None, "refit_attempt": None, "change_from_first_fit": None, "guard_passed": False,
                "fitted_half": {"share_within_tolerance": None, "vertices_near": int(len(q)),
                                "share_with_a_richer_surface": None},
                "reason": f"fewer than {rule['guard']['min_points']} fitted vertices near the first fit "
                          "once the window is shortened"})
    return row


def refit_region(region: dict, roi: dict, v: np.ndarray, used: np.ndarray, rule: dict, acceptance: dict):
    fit = region["fit"]
    band, tol = acceptance["band_mm"], acceptance["tolerance_mm"]
    trim = rule["window_trim_mm"] if fit["type"] != "plane" else 0.0
    inside = window(v, roi, trim)
    inside = inside[used[inside]]
    fitted, held = split_halves(inside)
    p = v[fitted]
    row = {"id": region["id"], "group": region["group"], "kind": region["kind"], "window_trim_mm": trim,
           "window_vertices": int(len(inside)), "fitted_vertices": int(len(fitted)), "held_out_vertices": int(len(held))}
    if fit["type"] == "plane":
        c, n = np.asarray(fit["point"], dtype=float), np.asarray(fit["normal"], dtype=float)
        n /= np.linalg.norm(n)
        d, _, _, _ = plane_distance(c, n, p)
        q = p[d < band]
        if len(q) < rule["guard"]["min_points"]:
            return too_few(row, d, q, rule, acceptance)
        (c1, n1), sig = refit_plane(fit, q, rule)
        d1, h1, u1, w1 = plane_distance(c1, n1, p)
        near = d1 < band
        change = {"normal_deg": round(angle_deg(n1, n), 4)}
        guard = change["normal_deg"] <= rule["guard"]["max_axis_change_deg"]
        out = {"type": "plane", "point": [round(float(x), 4) for x in c1], "normal": [round(float(x), 6) for x in n1],
               "determined": sig is not None, "rms_mm": round(float(np.sqrt((h1[near] ** 2).mean())), 4),
               "points": int(near.sum()), "fit_points": int(len(q))}
        richer = richer_surface_share("plane", h1[near], None, (u1[near], w1[near]), tol)
    else:
        a = np.asarray(fit["axis_direction"], dtype=float)
        a /= np.linalg.norm(a)
        c = np.asarray(fit["axis_point"], dtype=float)
        k = math.tan(math.radians(fit.get("half_angle_deg", 0.0)))
        d, _, _ = revolved_distance(c, a, 0.5 * fit["diameter_mm"], k, fit["station_range_mm"], p)
        q = p[d < band]
        if len(q) < rule["guard"]["min_points"]:
            return too_few(row, d, q, rule, acceptance)
        (c1, a1, r1, k1), sig = refit_revolved(fit, q, rule)
        _, s_all, t_all = revolved_distance(c1, a1, r1, k1, [-1e9, 1e9], q)
        inl = np.abs(s_all) < tol
        stations = [round(float(t_all[inl].min()), 3), round(float(t_all[inl].max()), 3)]
        d1, s1, t1 = revolved_distance(c1, a1, r1, k1, stations, p)
        near = d1 < band
        half_angle = math.degrees(math.atan(k1))
        change = {"axis_deg": round(angle_deg(a1, a), 4), "half_angle_deg": round(half_angle - fit.get("half_angle_deg", 0.0), 4),
                  "diameter_mm": round(2.0 * r1 - fit["diameter_mm"], 4)}
        g = rule["guard"]
        guard = (change["axis_deg"] <= g["max_axis_change_deg"] and abs(change["half_angle_deg"]) <= g["max_half_angle_change_deg"]
                 and abs(change["diameter_mm"]) <= g["max_diameter_change_mm"])
        e1, e2 = frame(a1)
        qq = p[near] - c1
        theta = np.arctan2(qq @ e2, qq @ e1)
        out = {"type": fit["type"], "side": fit.get("side"), "determined": sig is not None,
               "axis_point": [round(float(x), 4) for x in c1], "axis_direction": [round(float(x), 6) for x in a1],
               "diameter_mm": round(2.0 * r1, 4),
               "radius_sigma_mm": None if sig is None else round(float(sig[4]), 5),
               "rms_mm": round(float(np.sqrt((s1[near] ** 2).mean())), 4),
               "station_range_mm": stations, "points": int(near.sum()), "fit_points": int(len(q))}
        if fit["type"] == "cone":
            out["half_angle_deg"] = round(half_angle, 4)
        richer = richer_surface_share("revolved", s1[near], t1[near], theta, tol)
    enough = True  # too_few() has returned already otherwise
    fit_half_share, n_near = share_within(d1, band, tol)
    row.update({
        "first_fit_share_on_fitted_half": share_within(d, band, tol)[0],
        "fit": out if (guard and enough) else None,
        "refit_attempt": out,
        "change_from_first_fit": change,
        "guard_passed": bool(guard and enough),
        "fitted_half": {"share_within_tolerance": fit_half_share, "vertices_near": n_near,
                        "share_with_a_richer_surface": richer},
    })
    if not row["guard_passed"]:
        row["reason"] = "re-fit drifted beyond the declared guard"
    return row


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--bare-scan", type=Path, required=True, help="private NPZ: v, f of the bare scan in the twin frame")
    ap.add_argument("--rois", type=Path, required=True)
    ap.add_argument("--fits", type=Path, required=True, help="params/feature-fits.json, the first fit")
    ap.add_argument("--check", type=Path, required=True, help="params/feature-check.json, the first check")
    ap.add_argument("--declaration", type=Path, required=True)
    ap.add_argument("--private-out", type=Path, required=True, help="private NPZ of the fitted and held-out indices")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    declaration = json.loads(args.declaration.read_text())
    if declaration["schema"] != DECLARATION_SCHEMA:
        raise SystemExit("unexpected declaration schema")
    first = json.loads(args.fits.read_text())
    first_check = json.loads(args.check.read_text())
    if first_check["fits_sha256"] != sha256_file(args.fits):
        raise SystemExit("the first check does not belong to these fits")
    confirmed = {r["id"] for r in first_check["regions"] if r["confirmed"]}
    scope = declaration["scope"]
    if confirmed & set(scope) or len(scope) != len(first["regions"]) - len(confirmed):
        raise SystemExit("the declared scope must be exactly the features the first check left unconfirmed")
    rois = {r["id"]: r for r in json.loads(args.rois.read_text())["regions"]}
    regions = {r["id"]: r for r in first["regions"]}
    rule = declaration["changes"]

    d = np.load(args.bare_scan)
    v, f = d["v"], d["f"]
    _, used = vertex_normals(v, f)  # the same vertices fit_features.py could use

    rows, keep = [], {}
    for rid in scope:
        row = refit_region(regions[rid], rois[rid], v, used, rule, first_check["acceptance"])
        inside = window(v, rois[rid], row["window_trim_mm"])
        fitted, held = split_halves(inside[used[inside]])
        keep[rid + "__fitted"], keep[rid + "__held"] = fitted, held
        rows.append(row)
        print(rid, "guard" if row["guard_passed"] else "REJECTED", row["fitted_half"], flush=True)

    args.private_out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(args.private_out, **keep)
    write_json(args.out, {
        "schema": SCHEMA,
        "issue": declaration["issue"],
        "scan_sha256": first["scan_sha256"],
        "units": first["units"],
        "declaration_sha256": sha256_file(args.declaration),
        "first_fits_sha256": sha256_file(args.fits),
        "first_check_sha256": sha256_file(args.check),
        "rois_sha256": hashlib.sha256(args.rois.read_bytes()).hexdigest(),
        "split": first["split"],
        "claims": "re-fitted numbers on acquired scan vertices of the fitted half, under the declared rule; "
                  "no dimension of the specimen is established",
        "rejected_by_guard": [r["id"] for r in rows if not r["guard_passed"]],
        "regions": rows,
    })


if __name__ == "__main__":
    main()
