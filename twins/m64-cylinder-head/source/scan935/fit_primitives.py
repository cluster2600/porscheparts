"""Ajustements robustes de primitives (plan, cercle, cylindre) en numpy pur.

Module sans dépendance hors numpy afin d'être testé dans la CI. Il ne lit
aucun scan : les points sont fournis par l'appelant. Les incertitudes
retournées sont statistiques (bootstrap sur les inliers) et n'incluent ni
l'erreur du scanner ni l'échelle inconnue de l'OBJ.
"""

from __future__ import annotations

import numpy as np


def residual_stats(residuals: np.ndarray) -> dict:
    r = np.abs(np.asarray(residuals, dtype=float))
    return {
        "points": int(r.size),
        "rms": float(np.sqrt(np.mean(r ** 2))) if r.size else None,
        "p95": float(np.percentile(r, 95)) if r.size else None,
        "max": float(r.max()) if r.size else None,
    }


# ---------------------------------------------------------------- plan
def fit_plane_lsq(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Plan des moindres carrés orthogonaux : (centroïde, normale unitaire)."""
    pts = np.asarray(points, dtype=float)
    centroid = pts.mean(axis=0)
    _, _, vt = np.linalg.svd(pts - centroid, full_matrices=False)
    normal = vt[-1]
    return centroid, normal / np.linalg.norm(normal)


def plane_residuals(points, centroid, normal):
    return (np.asarray(points, dtype=float) - centroid) @ normal


def ransac_plane(points, threshold, trials=500, seed=935, reference_normal=None,
                 max_angle_deg=None):
    """RANSAC puis moindres carrés sur les inliers.

    ``reference_normal``/``max_angle_deg`` restreignent les hypothèses à une
    famille d'orientations (utile quand la région contient d'autres faces).
    """
    pts = np.asarray(points, dtype=float)
    rng = np.random.default_rng(seed)
    best = None
    cos_lim = None if max_angle_deg is None else np.cos(np.radians(max_angle_deg))
    for _ in range(trials):
        sample = pts[rng.choice(len(pts), 3, replace=False)]
        n = np.cross(sample[1] - sample[0], sample[2] - sample[0])
        norm = np.linalg.norm(n)
        if norm < 1e-12:
            continue
        n /= norm
        if cos_lim is not None and abs(n @ reference_normal) < cos_lim:
            continue
        inl = np.abs((pts - sample[0]) @ n) < threshold
        count = int(inl.sum())
        if best is None or count > best[0]:
            best = (count, inl)
    if best is None:
        raise ValueError("RANSAC plane: no valid hypothesis")
    inliers = best[1]
    for _ in range(3):
        c, n = fit_plane_lsq(pts[inliers])
        inliers = np.abs(plane_residuals(pts, c, n)) < threshold
    c, n = fit_plane_lsq(pts[inliers])
    if reference_normal is not None and n @ reference_normal < 0:
        n = -n
    return c, n, inliers


# ---------------------------------------------------------------- cercle 2D
def fit_circle_algebraic(xy: np.ndarray) -> tuple[np.ndarray, float]:
    """Cercle de Kåsa (linéaire)."""
    p = np.asarray(xy, dtype=float)
    a = np.column_stack((2 * p[:, 0], 2 * p[:, 1], np.ones(len(p))))
    b = (p ** 2).sum(axis=1)
    sol, *_ = np.linalg.lstsq(a, b, rcond=None)
    centre = sol[:2]
    radius = float(np.sqrt(max(sol[2] + centre @ centre, 0.0)))
    return centre, radius


def fit_circle_geometric(xy, centre=None, radius=None, iterations=50):
    """Gauss-Newton sur la distance géométrique, initialisé par Kåsa."""
    p = np.asarray(xy, dtype=float)
    if centre is None:
        centre, radius = fit_circle_algebraic(p)
    c = np.asarray(centre, dtype=float).copy()
    r = float(radius)
    for _ in range(iterations):
        d = p - c
        dist = np.linalg.norm(d, axis=1)
        dist = np.maximum(dist, 1e-12)
        res = dist - r
        jac = np.column_stack((-d[:, 0] / dist, -d[:, 1] / dist, -np.ones(len(p))))
        step, *_ = np.linalg.lstsq(jac, -res, rcond=None)
        c += step[:2]
        r += step[2]
        if np.linalg.norm(step) < 1e-10:
            break
    return c, abs(r)


def circle_residuals(xy, centre, radius):
    return np.linalg.norm(np.asarray(xy, dtype=float) - centre, axis=1) - radius


def ransac_circle(xy, threshold, trials=800, seed=935, radius_range=None):
    p = np.asarray(xy, dtype=float)
    if len(p) < 6:
        raise ValueError("not enough points for a circle")
    rng = np.random.default_rng(seed)
    best = None
    for _ in range(trials):
        s = p[rng.choice(len(p), 3, replace=False)]
        try:
            c, r = fit_circle_algebraic(s)
        except np.linalg.LinAlgError:
            continue
        if not np.isfinite(r) or r <= 0:
            continue
        if radius_range and not (radius_range[0] <= r <= radius_range[1]):
            continue
        inl = np.abs(circle_residuals(p, c, r)) < threshold
        count = int(inl.sum())
        if best is None or count > best[0]:
            best = (count, inl)
    if best is None:
        raise ValueError("RANSAC circle: no valid hypothesis")
    inliers = best[1]
    for _ in range(3):
        c, r = fit_circle_geometric(p[inliers])
        inliers = np.abs(circle_residuals(p, c, r)) < threshold
    c, r = fit_circle_geometric(p[inliers])
    return c, r, inliers


def angular_coverage_deg(xy, centre, bins=36):
    ang = np.degrees(np.arctan2(*(np.asarray(xy) - centre).T[::-1])) % 360
    hist, _ = np.histogram(ang, bins=bins, range=(0, 360))
    return float(360.0 * np.count_nonzero(hist) / bins)


def bootstrap(fn, data, n=100, seed=935):
    """Écart-type bootstrap de chaque sortie scalaire de ``fn(data)``."""
    rng = np.random.default_rng(seed)
    outs = []
    for _ in range(n):
        idx = rng.integers(0, len(data), len(data))
        outs.append(np.atleast_1d(np.asarray(fn(data[idx]), dtype=float)))
    return np.std(np.vstack(outs), axis=0)


# ---------------------------------------------------------------- cylindre
def orthonormal_basis(axis):
    axis = np.asarray(axis, dtype=float)
    axis = axis / np.linalg.norm(axis)
    helper = np.array([1.0, 0, 0]) if abs(axis[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(axis, helper)
    u /= np.linalg.norm(u)
    return u, np.cross(axis, u)


def fit_cylinder(points, axis_hint, iterations=30):
    """Cylindre par Gauss-Newton : point sur l'axe, axe unitaire, rayon.

    Paramétrage local (deux angles d'inclinaison autour de l'axe courant et
    deux translations transverses) ; renvoie aussi les résidus radiaux.
    """
    pts = np.asarray(points, dtype=float)
    axis = np.asarray(axis_hint, dtype=float)
    axis /= np.linalg.norm(axis)
    u, v = orthonormal_basis(axis)
    q = pts @ np.column_stack((u, v))
    c2, r = fit_circle_geometric(q)
    origin = c2[0] * u + c2[1] * v
    for _ in range(iterations):
        u, v = orthonormal_basis(axis)
        d = pts - origin
        t = d @ axis
        perp = d - np.outer(t, axis)
        dist = np.maximum(np.linalg.norm(perp, axis=1), 1e-12)
        res = dist - r
        e = perp / dist[:, None]
        # dérivées : translation origine (u, v), inclinaison axe (u, v), rayon
        j = np.column_stack((-(e @ u), -(e @ v), -t * (e @ u), -t * (e @ v), -np.ones(len(pts))))
        step, *_ = np.linalg.lstsq(j, -res, rcond=None)
        origin = origin + step[0] * u + step[1] * v
        axis = axis + step[2] * u + step[3] * v
        axis /= np.linalg.norm(axis)
        r += step[4]
        if np.linalg.norm(step) < 1e-10:
            break
    d = pts - origin
    t = d @ axis
    origin = origin + t.mean() * axis
    perp = d - np.outer(t, axis)
    res = np.linalg.norm(perp, axis=1) - r
    if axis @ np.asarray(axis_hint) < 0:
        axis = -axis
    return origin, axis, abs(r), res


def ransac_cylinder(points, axis_hint, threshold, trials=60, subset=60, seed=935,
                    radius_range=None):
    """Consensus par sous-échantillons ajustés, puis raffinement sur inliers."""
    pts = np.asarray(points, dtype=float)
    rng = np.random.default_rng(seed)
    best = None
    for _ in range(trials):
        sub = pts[rng.choice(len(pts), min(subset, len(pts)), replace=False)]
        try:
            o, a, r, _ = fit_cylinder(sub, axis_hint, iterations=15)
        except np.linalg.LinAlgError:
            continue
        if radius_range and not (radius_range[0] <= r <= radius_range[1]):
            continue
        if abs(a @ axis_hint) < np.cos(np.radians(25)):
            continue
        d = pts - o
        perp = d - np.outer(d @ a, a)
        inl = np.abs(np.linalg.norm(perp, axis=1) - r) < threshold
        if best is None or inl.sum() > best[0]:
            best = (int(inl.sum()), inl)
    if best is None:
        raise ValueError("RANSAC cylinder: no valid hypothesis")
    inl = best[1]
    for _ in range(3):
        o, a, r, res = fit_cylinder(pts[inl], axis_hint)
        d = pts - o
        perp = d - np.outer(d @ a, a)
        inl = np.abs(np.linalg.norm(perp, axis=1) - r) < threshold
    o, a, r, res = fit_cylinder(pts[inl], axis_hint)
    return o, a, r, res, inl


def angle_between_deg(a, b, undirected=True):
    a = np.asarray(a, float) / np.linalg.norm(a)
    b = np.asarray(b, float) / np.linalg.norm(b)
    c = float(np.clip(a @ b, -1, 1))
    if undirected:
        c = abs(c)
    return float(np.degrees(np.arccos(c)))
