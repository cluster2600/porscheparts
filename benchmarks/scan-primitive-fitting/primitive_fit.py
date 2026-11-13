#!/usr/bin/env python3
"""Fit planes, cylinders and cones to oriented scan points.

A scan mesh gives points with normals. This module finds the analytic
primitives they lie on, largest first, and returns each with its own fit
residual:

* a plane;
* a cylinder: bores, bosses, and fillets (a fillet is a partial cylinder);
* a cone: valve seats, and every drafted bore or boss. A cast "cylinder" with
  1 degree of draft is a cone, and a cylinder fitted to it has no single radius.

Cylinders and cones share one model, a straight generator revolved about an
axis: ``rho = r0 + k t``, with ``t`` the station along the axis, ``rho`` the
distance to it and ``k`` the tangent of the half-angle. ``k = 0`` is the
cylinder, so the same least-squares fit covers both and the draft is measured,
not assumed. A fit is reported as a cylinder only when its half-angle is below
``cylinder_max_half_angle_deg`` or within three standard deviations of zero.

Each round draws seed patches from the points still unassigned, turns each
patch into a plane, a cylinder and a cone hypothesis by linear algebra, refines
the best of each kind by least squares, and keeps the candidate that explains
the most points. It stops when no candidate holds ``min_points``.

The thresholds follow from two numbers the caller states: the scan noise and
the sample spacing. Nothing here knows about any part. The fit qualifies no
scan, fit or dimension: see the witness beside this file for what was checked.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial import cKDTree


def settings(noise_mm, pitch_mm=1.0, **overrides):
    """Thresholds derived from the scan noise (1 sigma, mm) and sample spacing (mm)."""
    eps = 3.0 * noise_mm
    out = {
        "noise_mm": noise_mm,
        "pitch_mm": pitch_mm,
        "distance_mm": eps,                       # inlier band: 3 sigma
        "normal_deg": 15.0,                       # an inlier's normal must agree with the model
        "score_distance_mm": 3.0 * eps,           # looser band used only to rank seed hypotheses
        "score_normal_deg": 25.0,
        "capture": ((10.0 * eps, 30.0), (3.0 * eps, 20.0)),   # robust refinement stages before the strict one
        "patch_radii_mm": (5.0 * pitch_mm, 12.0 * pitch_mm),
        "patch_normal_deg": 35.0,                 # a seed patch keeps neighbours facing the same way
        "patch_min_points": 12,
        "seeds_per_round": 150,
        "score_sample": 10000,
        "refine_per_kind": 3,
        "min_points": 150,
        "shared_zone_mm": 2.0 * eps,              # foot within both inlier bands of a second model
        "refit_min_points": 50,
        "refit_min_inlier_fraction": 0.9,         # a refit must keep its own points, normals included
        "max_radius_mm": 500.0,                   # beyond this a "cylinder" is a plane
        "max_half_angle_deg": 80.0,
        "cylinder_max_half_angle_deg": 0.1,
        "plane_preference": 0.95,                 # a curved model must beat a plane by this margin
        "allow_cones": True,
        "empty_rounds_to_stop": 2,
    }
    unknown = set(overrides) - set(out)
    if unknown:
        raise KeyError(f"unknown settings: {sorted(unknown)}")
    out.update(overrides)
    return out


def _unit(v):
    return v / np.linalg.norm(v)


def _frame(a):
    """Two unit vectors completing ``a`` to a right-handed orthonormal frame."""
    e1 = _unit(np.cross(a, np.eye(3)[np.argmin(np.abs(a))]))
    return e1, np.cross(a, e1)


def _cos(deg):
    return math.cos(math.radians(deg))


# --- models: {"kind": "plane", "c", "n"} or {"kind": "axial", "c", "a", "r0", "k"} ---

def _axial_terms(points, m):
    v = points - m["c"]
    t = v @ m["a"]
    radial = v - np.outer(t, m["a"])
    return t, radial, np.linalg.norm(radial, axis=1)


def _signed(m, points):
    """Signed distance of each point to the model, the model normal there, and where the model exists."""
    if m["kind"] == "plane":
        return (points - m["c"]) @ m["n"], np.broadcast_to(m["n"], points.shape), np.ones(len(points), dtype=bool)
    t, radial, rho = _axial_terms(points, m)
    k = m["k"]
    scale = math.sqrt(1.0 + k * k)
    radius = m["r0"] + k * t
    with np.errstate(invalid="ignore", divide="ignore"):
        model_normal = (radial / rho[:, None] - k * m["a"]) / scale
    return (rho - radius) / scale, model_normal, (radius > 0) & (rho > 0)


def _evaluate(m, points, normals, normal_deg):
    """Absolute distance of each point to the model, and whether its normal agrees with it."""
    d, model_normal, exists = _signed(m, points)
    with np.errstate(invalid="ignore"):
        agree = np.abs(np.einsum("ij,ij->i", normals, model_normal)) > _cos(normal_deg)
    return np.abs(d), agree & exists


def _mask(m, points, normals, distance, normal_deg):
    """Points within ``distance`` of the model whose normals agree with it."""
    d, agree = _evaluate(m, points, normals, normal_deg)
    return (d < distance) & agree


def _plane_fit(points):
    c = points.mean(axis=0)
    return {"kind": "plane", "c": c, "n": np.linalg.svd(points - c, full_matrices=False)[2][2]}


def _axial_fit(points, m, free_k, robust_scale=None):
    """Least-squares cylinder (``free_k`` false) or cone-or-cylinder about the model's current axis."""
    a0 = m["a"]
    shift = (points.mean(axis=0) - m["c"]) @ a0          # anchor at the data, so r0 and k decouple
    c0 = m["c"] + shift * a0
    r00 = m["r0"] + m["k"] * shift
    k0 = m["k"] if free_k else 0.0
    e1, e2 = _frame(a0)

    def unpack(x):
        return (c0 + x[2] * e1 + x[3] * e2, _unit(a0 + x[0] * e1 + x[1] * e2), r00 + x[4],
                k0 + x[5] if free_k else 0.0)

    def residual(x):
        c, a, r, k = unpack(x)
        v = points - c
        t = v @ a
        rho = np.linalg.norm(v - np.outer(t, a), axis=1)
        return (rho - r - k * t) / math.sqrt(1.0 + k * k)

    size = 6 if free_k else 5
    scale = np.array([1e-2, 1e-2, 1.0, 1.0, 1.0, 1e-2])[:size]
    extra = {"loss": "soft_l1", "f_scale": robust_scale} if robust_scale else {}
    res = least_squares(residual, np.zeros(size), x_scale=scale, **extra)
    c, a, r, k = unpack(res.x)
    out = {"kind": "axial", "c": c, "a": a, "r0": r, "k": k, "sigma": None}
    if not robust_scale and len(points) > size:
        # Formal 1-sigma of the parameters, for independent noise of the fitted scatter.
        cov = (2.0 * res.cost / (len(points) - size)) * np.linalg.pinv(res.jac.T @ res.jac)
        var = np.clip(np.diag(cov), 0.0, None)
        out["sigma"] = {"axis_rad": float(math.sqrt(var[0] + var[1])), "point_mm": float(math.sqrt(var[2] + var[3])),
                        "radius_mm": float(math.sqrt(var[4])), "k": float(math.sqrt(var[5])) if free_k else None}
    return out


def _fit(points, m, free_k, robust_scale=None):
    return _plane_fit(points) if m["kind"] == "plane" else _axial_fit(points, m, free_k, robust_scale)


# --- seed hypotheses from one patch, by linear algebra ---

def _plane_seed(p, n):
    return _plane_fit(p)


def _cylinder_seed(p, n):
    # Normals of a cylinder are perpendicular to its axis: the axis is the
    # direction the patch normals do not span.
    a = np.linalg.svd(n, full_matrices=False)[2][2]
    e1, e2 = _frame(a)
    q = np.column_stack([p @ e1, p @ e2])
    m = np.column_stack([n @ e1, n @ e2])
    length = np.linalg.norm(m, axis=1)
    if np.any(length < 1e-6):
        return None
    m /= length[:, None]
    # The projected normal lines all pass through the axis: least-squares intersection.
    proj = np.eye(2)[None] - m[:, :, None] * m[:, None, :]
    centre, *_ = np.linalg.lstsq(proj.sum(axis=0), np.einsum("ijk,ik->j", proj, q), rcond=None)
    return {"kind": "axial", "c": centre[0] * e1 + centre[1] * e2 + (p.mean(axis=0) @ a) * a, "a": a,
            "r0": float(np.linalg.norm(q - centre, axis=1).mean()), "k": 0.0}


def _cone_seed(p, n, max_half_angle_deg):
    # The tangent planes of a cone all pass through its apex.
    apex, *_ = np.linalg.lstsq(n.T @ n, n.T @ np.einsum("ij,ij->i", n, p), rcond=None)
    d = p - apex
    length = np.linalg.norm(d, axis=1)
    if np.any(length < 1e-6):
        return None
    d /= length[:, None]
    # Rulings make one angle with the axis: their unit vectors lie in a plane.
    a = np.linalg.svd(d - d.mean(axis=0), full_matrices=False)[2][2]
    cosine = float((d @ a).mean())
    if cosine < 0:
        a, cosine = -a, -cosine
    half_angle = math.degrees(math.acos(min(cosine, 1.0)))
    if not 0.05 < half_angle < max_half_angle_deg:
        return None
    k = math.tan(math.radians(half_angle))
    station = float(((p - apex) @ a).mean())
    return {"kind": "axial", "c": apex + station * a, "a": a, "r0": k * station, "k": k}


# --- refinement and classification ---

def _refine(m, points, normals, st, free_k):
    eps = st["distance_mm"]
    for distance, normal_deg in st["capture"]:
        idx = np.flatnonzero(_mask(m, points, normals, distance, normal_deg))
        if len(idx) < st["min_points"]:
            return None, None
        m = _fit(points[idx], m, free_k, robust_scale=eps)
    previous = None
    for _ in range(10):
        idx = np.flatnonzero(_mask(m, points, normals, eps, st["normal_deg"]))
        if len(idx) < st["min_points"]:
            return None, None
        if previous is not None and len(idx) == len(previous) and np.array_equal(idx, previous):
            break
        m = _fit(points[idx], m, free_k)
        previous = idx
    return m, idx


def _is_cylinder(m, st):
    if m["k"] == 0.0:
        return True
    half_angle = abs(math.degrees(math.atan(m["k"])))
    k_sigma = (m.get("sigma") or {}).get("k") or 0.0
    return half_angle <= max(st["cylinder_max_half_angle_deg"], 3.0 * math.degrees(k_sigma / (1.0 + m["k"] ** 2)))


def _candidate(seed, points, normals, st):
    """Refine one seed; return (model, inlier indices) or None."""
    free_k = st["allow_cones"]
    m, idx = _refine(seed, points, normals, st, free_k)
    if m is None:
        return None
    if m["kind"] == "axial":
        if free_k and _is_cylinder(m, st):
            m, idx = _refine({**m, "k": 0.0}, points, normals, {**st, "capture": ()}, False)
            if m is None:
                return None
        t, _, _ = _axial_terms(points[idx], m)
        radius = m["r0"] + m["k"] * t
        if radius.max() > st["max_radius_mm"] or abs(math.degrees(math.atan(m["k"]))) > st["max_half_angle_deg"]:
            return None
    return m, idx


def _final_fit(points, normals, m, st):
    """Unbiased refit of one model, or None when these points do not determine it."""
    if len(points) < st["refit_min_points"]:
        return None
    if m["kind"] == "plane":
        return _plane_fit(points)
    fitted = _axial_fit(points, m, st["allow_cones"])
    if st["allow_cones"] and _is_cylinder(fitted, st):
        fitted = _axial_fit(points, {**fitted, "k": 0.0}, False)
    sigma = fitted["sigma"]
    # A fit whose own uncertainty exceeds the inlier band has not located the surface.
    if sigma is None or max(sigma["radius_mm"], sigma["point_mm"]) > st["distance_mm"]:
        return None
    # Distances alone can be satisfied by a wrong surface: two columns of a
    # fillet lie on a cylinder a sixth of its radius. The normals expose it.
    if _mask(fitted, points, normals, st["distance_mm"], st["normal_deg"]).mean() < st["refit_min_inlier_fraction"]:
        return None
    return fitted


def _assign(models, points, normals, st):
    """Give each point to the nearest model it is an inlier of, and flag the shared zones.

    ``owner`` is the model index or -1. ``shared`` marks a point whose foot on
    its own model also lies on another model with an agreeing normal: the two
    surfaces are tangent or coincident there, and the point cannot say which one
    it belongs to. The zone is set by the models, not by the noise, so leaving
    it out of both fits removes points without selecting them by their residual.
    """
    nearest = np.full(len(points), np.inf)
    owner = np.full(len(points), -1)
    for i, m in enumerate(models):
        d, agree = _evaluate(m, points, normals, st["normal_deg"])
        take = agree & (d < st["distance_mm"]) & (d < nearest)
        nearest[take], owner[take] = d[take], i
    shared = np.zeros(len(points), dtype=bool)
    for i, m in enumerate(models):
        mine = np.flatnonzero(owner == i)
        if not len(mine):
            continue
        d, model_normal, _ = _signed(m, points[mine])
        foot = points[mine] - d[:, None] * model_normal
        for j, other in enumerate(models):
            if j != i:
                dj, agree = _evaluate(other, foot, model_normal, 2.0 * st["normal_deg"])
                shared[mine[(dj < st["shared_zone_mm"]) & agree]] = True
    return owner, shared


def _report(m, points, normals, fit_points, determined):
    """A JSON-ready description of a fitted primitive and its own residual.

    ``determined`` is false when the points outside the shared zones were too
    few, or spanned too little, to fix the model: the parameters are then the
    biased first estimate and carry no uncertainty. Treat such a primitive as
    detected, not measured.
    """
    if m["kind"] == "plane":
        n = m["n"] if (normals @ m["n"]).mean() >= 0 else -m["n"]
        distance = (points - m["c"]) @ n
        return {"type": "plane", "normal": n.tolist(), "point": m["c"].tolist(), "points": int(len(points)),
                "fit_points": fit_points, "determined": determined,
                "rms_mm": float(np.sqrt((distance ** 2).mean()))}
    t, radial, rho = _axial_terms(points, m)
    k, a = m["k"], m["a"]
    scale = math.sqrt(1.0 + k * k)
    residual = (rho - m["r0"] - k * t) / scale
    e1, e2 = _frame(a)
    angle = np.sort(np.arctan2(radial @ e2, radial @ e1))
    gaps = np.diff(np.concatenate([angle, angle[:1] + 2 * math.pi]))
    outward = (np.einsum("ij,ij->i", normals, radial) / rho).mean()
    sigma = (m.get("sigma") or {}) if determined else {}
    common = {"points": int(len(points)), "fit_points": fit_points, "determined": determined,
              "rms_mm": float(np.sqrt((residual ** 2).mean())),
              "arc_deg": float(360.0 - math.degrees(gaps.max())), "length_mm": float(np.ptp(t)),
              "side": "convex" if outward > 0 else "concave",
              "axis_direction_sigma_deg": None if not sigma else math.degrees(sigma["axis_rad"]),
              "axis_point_sigma_mm": sigma.get("point_mm"), "radius_sigma_mm": sigma.get("radius_mm")}
    centre = m["c"] + t.mean() * a                     # the axis point at the middle of the data
    radius_here = m["r0"] + k * t.mean()
    if k == 0.0:
        return {"type": "cylinder", "axis_point": centre.tolist(), "axis_direction": a.tolist(),
                "radius_mm": float(m["r0"]), **common}
    if k < 0:                                          # orient the axis from the apex to the opening
        a, k, t = -a, -k, -t
    return {"type": "cone", "axis_point": centre.tolist(), "axis_direction": a.tolist(),
            "radius_at_axis_point_mm": float(radius_here), "half_angle_deg": math.degrees(math.atan(k)),
            "half_angle_sigma_deg": math.degrees(sigma["k"] / (1.0 + k * k)) if sigma.get("k") else None,
            "apex": (centre - (radius_here / k) * a).tolist(),
            "radius_range_mm": [float(radius_here + k * (t.min() - t.mean())),
                                float(radius_here + k * (t.max() - t.mean()))], **common}


def detect(points, normals, st, seed=0):
    """Return the primitives found, largest first, and the indices left unassigned."""
    points = np.asarray(points, dtype=float)
    normals = np.asarray(normals, dtype=float)
    normals = normals / np.linalg.norm(normals, axis=1, keepdims=True)
    rng = np.random.default_rng(seed)
    remaining = np.arange(len(points))
    models, empty = [], 0
    hypotheses = [("plane", _plane_seed), ("cylinder", _cylinder_seed)]
    if st["allow_cones"]:
        hypotheses.append(("cone", lambda p, n: _cone_seed(p, n, st["max_half_angle_deg"])))
    while len(remaining) >= st["min_points"] and empty < st["empty_rounds_to_stop"]:
        p_all, n_all = points[remaining], normals[remaining]
        tree = cKDTree(p_all)
        seeds = rng.choice(len(p_all), size=min(st["seeds_per_round"], len(p_all)), replace=False)
        sample = rng.choice(len(p_all), size=min(st["score_sample"], len(p_all)), replace=False)
        p_s, n_s = p_all[sample], n_all[sample]
        ranked = {name: [] for name, _ in hypotheses}
        for s in seeds:
            for radius in st["patch_radii_mm"]:
                near = np.asarray(tree.query_ball_point(p_all[s], radius))
                near = near[n_all[near] @ n_all[s] > _cos(st["patch_normal_deg"])]
                if len(near) < st["patch_min_points"]:
                    continue
                for name, make in hypotheses:
                    m = make(p_all[near], n_all[near])
                    if m is not None:
                        score = int(_mask(m, p_s, n_s, st["score_distance_mm"], st["score_normal_deg"]).sum())
                        ranked[name].append((score, len(ranked[name]), m))
        best = None
        for name, _ in hypotheses:
            for _, _, m in sorted(ranked[name], key=lambda r: (-r[0], r[1]))[:st["refine_per_kind"]]:
                candidate = _candidate(m, p_all, n_all, st)
                if candidate is None:
                    continue
                weight = len(candidate[1]) * (1.0 if candidate[0]["kind"] == "plane" else st["plane_preference"])
                if best is None or weight > best[0]:
                    best = (weight, *candidate)
        if best is None:
            empty += 1
            continue
        empty = 0
        _, m, idx = best
        models.append(m)
        remaining = np.delete(remaining, idx)
    # Sequential extraction gives every point near a tangency to the larger
    # neighbour, chosen by its residual, which biases a fillet's radius. Refit
    # each model on the points it owns outside the shared zones, and decide
    # there, on the unbiased fit, whether it is a cylinder or a cone.
    owner, shared = _assign(models, points, normals, st)
    first, determined = list(models), [True] * len(models)
    for _ in range(3):
        for i, m in enumerate(models):
            mine = (owner == i) & ~shared
            fitted = _final_fit(points[mine], normals[mine], m, st)
            determined[i] = fitted is not None
            models[i] = first[i] if fitted is None else fitted   # undetermined: keep the first estimate, flagged
        owner, shared = _assign(models, points, normals, st)
    found = []
    for i, m in enumerate(models):
        mine = owner == i
        if mine.sum() >= st["refit_min_points"]:
            found.append(_report(m, points[mine], normals[mine], int((mine & ~shared).sum()), determined[i]))
    return found, np.flatnonzero(owner < 0)


def load_oriented_points(path):
    """Points and normals of a point cloud with normals, or of a mesh, read with Open3D."""
    import open3d as o3d

    cloud = o3d.io.read_point_cloud(str(path))
    if cloud.has_normals():
        return np.asarray(cloud.points), np.asarray(cloud.normals)
    mesh = o3d.io.read_triangle_mesh(str(path))
    if not len(mesh.triangles):
        raise SystemExit(f"{path} has no normals and no triangles: estimate normals first")
    mesh.compute_vertex_normals()
    return np.asarray(mesh.vertices), np.asarray(mesh.vertex_normals)


def main():
    ap = argparse.ArgumentParser(description="Fit planes, cylinders and cones to an oriented scan (units: mm).")
    ap.add_argument("scan", type=Path, help="mesh or point cloud with normals, readable by Open3D")
    ap.add_argument("--noise-mm", type=float, required=True, help="scan noise, 1 sigma, from a measured flat or the scanner record")
    ap.add_argument("--pitch-mm", type=float, default=1.0, help="typical sample spacing")
    ap.add_argument("--min-points", type=int, default=150)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    st = settings(args.noise_mm, args.pitch_mm, min_points=args.min_points)
    points, normals = load_oriented_points(args.scan)
    found, remaining = detect(points, normals, st, args.seed)
    report = {"schema": "scan-primitive-fit/1", "scan": args.scan.name, "points": int(len(points)),
              "unassigned_points": int(len(remaining)), "settings": st, "seed": args.seed, "primitives": found,
              "claims": "fitted primitives with their own residuals; check each against an independent deviation measure"}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"{len(found)} primitives, {len(remaining)} of {len(points)} points unassigned")


if __name__ == "__main__":
    main()
