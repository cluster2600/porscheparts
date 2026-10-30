"""Small analytic controls for paper-guided scan studies, not engineering approval.

The cavity statistic follows Eqs. 10--12 of arXiv:2610.13466v1. This module
does not reproduce its complete graph-wire-search or learned segmentation.
"""
from __future__ import annotations

import numpy as np


def points3(value, minimum=3):
    points = np.asarray(value, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) < minimum or not np.isfinite(points).all():
        raise ValueError("expected finite 3D points")
    return points


def axis_frame(axis):
    axis = np.asarray(axis, dtype=float)
    if axis.shape != (3,) or not np.isfinite(axis).all() or np.linalg.norm(axis) < 1e-12:
        raise ValueError("invalid axis")
    axis = axis / np.linalg.norm(axis)
    reference = np.eye(3)[np.argmin(abs(axis))]
    first = np.cross(axis, reference)
    first /= np.linalg.norm(first)
    return np.array([first, np.cross(axis, first), axis])


def split_source_ids(source_ids):
    ids = np.asarray(source_ids)
    if ids.ndim != 1 or ids.dtype.kind not in "iu" or (ids < 0).any() or len(np.unique(ids)) != len(ids):
        raise ValueError("source IDs must be unique nonnegative integers")
    return ids[ids % 5 != 0], ids[ids % 5 == 0]


def cavity_variance(centroids, normals, areas, *, offset_mm=1., safeguard=1.05):
    """Compare area-weighted spreads of oriented normal offsets.

    Normals must already have known outward orientation relative to a solid.
    A positive score alone cannot distinguish a blind hole from a through-hole.
    """
    points = points3(centroids)
    normal = points3(normals)
    weights = np.asarray(areas, dtype=float)
    if normal.shape != points.shape or weights.shape != (len(points),):
        raise ValueError("normal/area shape mismatch")
    if (not np.isfinite(weights).all() or (weights <= 0).any()
            or not np.isfinite([offset_mm, safeguard]).all() or offset_mm <= 0 or safeguard <= 1):
        raise ValueError("invalid cavity-test parameters")
    lengths = np.linalg.norm(normal, axis=1)
    if (lengths < 1e-12).any():
        raise ValueError("zero normal")
    normal = normal / lengths[:, None]

    def variance(values):
        mean = np.average(values, axis=0, weights=weights)
        return float(np.average(np.sum((values - mean) ** 2, axis=1), weights=weights))

    plus = variance(points + offset_mm * normal)
    minus = variance(points - offset_mm * normal)
    return {"variance_plus_mm2": plus, "variance_minus_mm2": minus,
            "offset_mm": offset_mm, "safeguard": safeguard,
            "hollow_candidate": bool(minus > safeguard * plus),
            "through_or_blind": "unresolved_by_this_statistic"}


def fit_plane(training_points):
    points = points3(training_points, 6)
    center = points.mean(axis=0)
    _, singular, basis = np.linalg.svd(points - center, full_matrices=False)
    if singular[1] < max(1e-10, singular[0] * 1e-8):
        raise ValueError("plane support is collinear")
    normal = basis[-1]
    normal *= 1 if normal[np.argmax(abs(normal))] >= 0 else -1
    return {"kind": "plane", "normal": normal.tolist(), "offset_mm": float(center @ normal)}


def inspect_circle(points):
    """Describe an existing rim without closing it or identifying its function."""
    points = points3(points, 6)
    origin = points.mean(axis=0)
    _, singular, frame = np.linalg.svd(points - origin, full_matrices=False)
    if singular[1] < 1e-10:
        raise ValueError("rim support is collinear")
    local = (points - origin) @ frame.T
    xy = local[:, :2]
    solution, _, rank, _ = np.linalg.lstsq(np.c_[2 * xy, np.ones(len(xy))], (xy * xy).sum(axis=1), rcond=None)
    if rank < 3:
        raise ValueError("rim support is degenerate")
    radius_squared = solution[2] + solution[:2] @ solution[:2]
    if radius_squared <= 0:
        raise ValueError("nonpositive rim radius")
    radius = float(np.sqrt(radius_squared))
    residual = abs(np.linalg.norm(xy - solution[:2], axis=1) - radius)
    radial_p95 = float(np.quantile(residual, .95))
    plane_max = float(abs(local[:, 2]).max())
    coverage = angular_coverage(xy - solution[:2])
    return {"center_mm": (origin + np.r_[solution[:2], 0.] @ frame).tolist(),
            "normal": frame[2].tolist(), "diameter_mm": 2 * radius,
            "radial_p95_mm": radial_p95, "plane_max_mm": plane_max,
            "angular_coverage_degrees": coverage,
            "circular_rim_candidate": bool(radius >= .5 and radial_p95 <= min(.3, .05 * radius)
                                           and plane_max <= .25 and coverage >= 300),
            "functional_hole_identity_accepted": False}


def fit_cylinder(training_points, axis_seed):
    """Fit only the supplied training points; no validation data or nominal radius."""
    from scipy.optimize import least_squares

    points = points3(training_points, 40)
    frame = axis_frame(axis_seed)
    origin = points.mean(axis=0)
    local = (points - origin) @ frame.T
    if np.ptp(local[:, 2]) < 1e-6:
        raise ValueError("cylinder support has no axial extent")
    xy = local[:, :2]
    solution, _, rank, _ = np.linalg.lstsq(np.c_[2 * xy, np.ones(len(xy))], (xy * xy).sum(axis=1), rcond=None)
    if rank < 3:
        raise ValueError("cylinder support is degenerate")
    center = solution[:2]
    radius = np.sqrt(max(1e-12, solution[2] + center @ center))

    def residual(parameters):
        direction = np.array([parameters[2], parameters[3], 1.])
        direction /= np.linalg.norm(direction)
        delta = local - np.r_[parameters[:2], 0.]
        perpendicular = delta - np.outer(delta @ direction, direction)
        return np.linalg.norm(perpendicular, axis=1) - parameters[4]

    fitted = least_squares(residual, np.r_[center, 0., 0., radius],
                           bounds=([-np.inf, -np.inf, -.5, -.5, 1e-6],
                                   [np.inf, np.inf, .5, .5, np.inf]),
                           loss="soft_l1", f_scale=.1, max_nfev=300)
    if not fitted.success or not np.isfinite(fitted.x).all():
        raise ValueError("cylinder fit did not converge")
    direction = np.r_[fitted.x[2:4], 1.]
    direction /= np.linalg.norm(direction)
    return {"kind": "cylinder", "axis_origin_mm": (origin + np.r_[fitted.x[:2], 0.] @ frame).tolist(),
            "axis_direction": (direction @ frame).tolist(), "radius_mm": float(fitted.x[4]),
            "training_points": len(points), "optimizer_evaluations": fitted.nfev}


def angular_coverage(vectors):
    vectors = np.asarray(vectors, dtype=float)
    if vectors.ndim != 2 or vectors.shape[1] != 2 or len(vectors) < 2 or not np.isfinite(vectors).all():
        return 0.
    angle = np.sort(np.mod(np.arctan2(vectors[:, 1], vectors[:, 0]), 2 * np.pi))
    return float(360 - np.degrees(np.diff(np.r_[angle, angle[0] + 2 * np.pi]).max()))


def inspect_cylinder(model, evaluation_points, axis_seed, *, p95_limit_mm=.4,
                     minimum_span_mm=3., minimum_coverage_degrees=300., maximum_tilt_degrees=15.):
    """Independent evaluation uses cross products, not the fitting residual code."""
    points = points3(evaluation_points, 20)
    origin = np.asarray(model["axis_origin_mm"], dtype=float)
    axis = np.asarray(model["axis_direction"], dtype=float)
    radius = float(model["radius_mm"])
    limits = [p95_limit_mm, minimum_span_mm, minimum_coverage_degrees, maximum_tilt_degrees]
    if (origin.shape != (3,) or axis.shape != (3,) or not np.isfinite(np.r_[origin, axis, radius, limits]).all()
            or abs(np.linalg.norm(axis) - 1) > 1e-7 or radius <= 0 or min(limits) <= 0):
        raise ValueError("invalid cylinder or evaluation limits")
    delta = points - origin
    residual = abs(np.linalg.norm(np.cross(delta, axis), axis=1) - radius)
    axial = delta @ axis
    frame = axis_frame(axis)
    inlier = residual <= p95_limit_mm
    coverage = angular_coverage((delta @ frame.T)[inlier, :2])
    cuts = np.linspace(axial.min(), axial.max(), 4)
    bins = np.minimum(np.searchsorted(cuts[1:], axial, side="right"), 2)
    per_bin = []
    for index in range(3):
        selected = inlier & (bins == index)
        per_bin.append(angular_coverage((delta @ frame.T)[selected, :2]) if selected.sum() >= 20 else 0.)
    seed = axis_frame(axis_seed)[2]
    tilt = float(np.degrees(np.arccos(np.clip(abs(seed @ axis), 0, 1))))
    p95 = float(np.quantile(residual, .95))
    span = float(np.ptp(axial))
    reasons = []
    if p95 > p95_limit_mm:
        reasons.append("evaluation_residual_exceeds_limit")
    if span < minimum_span_mm:
        reasons.append("insufficient_observed_axial_span")
    if coverage < minimum_coverage_degrees or min(per_bin) < minimum_coverage_degrees:
        reasons.append("insufficient_angular_support_in_three_axial_bins")
    if tilt > maximum_tilt_degrees:
        reasons.append("axis_leaves_registered_search_cone")
    return {"evaluation_points": len(points), "p95_mm": p95, "max_mm": float(residual.max()),
            "observed_axial_span_mm": span, "angular_coverage_degrees": coverage,
            "coverage_by_axial_third_degrees": per_bin, "axis_seed_angle_degrees": tilt,
            "retained_as_scan_fit_candidate": not reasons, "rejection_reasons": reasons,
            "physical_dimension_accepted": False}
