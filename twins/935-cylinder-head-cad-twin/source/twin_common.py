"""Shared helpers for the 935 head CAD twin.

The private scan never enters Git. Every script receives the scan path and a
private output directory as arguments, and verifies the scan hash first.
Coordinates are millimetres (owner-confirmed: 1 OBJ unit = 1 mm).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

SCAN_SHA256 = "4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486"

# Initial A/B/C hint frame from ../../source/scan_frame.py (C = bore axis,
# pointing from the cam face toward the deck). fit_frame.py refines it.
C_HINT = np.array([0.09216808492652868, -0.8170262691134965, -0.5691863664033568])
B_HINT = np.array([-0.66828442, 0.37015754, -0.64527462])


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_scan(obj_path: Path, cache_dir: Path, verify: bool = True):
    """Return (vertices float64, faces int64) of the unmodified scan.

    Vertices are not merged, welded or rescaled. The decoded arrays are cached
    as NPZ next to their own hashes.
    """

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache = cache_dir / "scan-raw64.npz"
    if cache.exists():
        d = np.load(cache)
        return d["v"], d["f"]
    if verify:
        got = sha256_file(obj_path)
        if got != SCAN_SHA256:
            raise SystemExit(f"scan hash mismatch: {got}")
    import trimesh

    m = trimesh.load(obj_path, process=False, force="mesh")
    v = np.asarray(m.vertices, dtype=np.float64)
    f = np.asarray(m.faces, dtype=np.int64)
    np.savez(cache, v=v, f=f)
    return v, f


def face_geometry(v: np.ndarray, f: np.ndarray):
    tri = v[f]
    cen = tri.mean(axis=1)
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    dbl = np.linalg.norm(n, axis=1)
    area = 0.5 * dbl
    n = n / np.where(dbl > 0, dbl, 1.0)[:, None]
    return cen, n, area


def fit_plane(points: np.ndarray, weights: np.ndarray):
    """Weighted least-squares plane. Returns (unit normal, point, residuals)."""

    w = weights / weights.sum()
    mu = (points * w[:, None]).sum(axis=0)
    _, _, vt = np.linalg.svd((points - mu) * np.sqrt(w)[:, None], full_matrices=False)
    normal = vt[2]
    return normal, mu, (points - mu) @ normal


def fit_circle_2d(xy: np.ndarray):
    """Algebraic (Kasa) fit refined by Gauss-Newton on geometric distance."""

    x, y = xy[:, 0], xy[:, 1]
    a = np.column_stack((x, y, np.ones_like(x)))
    b = x * x + y * y
    c = np.linalg.lstsq(a, b, rcond=None)[0]
    cx, cy = c[0] / 2, c[1] / 2
    r = np.sqrt(c[2] + cx * cx + cy * cy)
    p = np.array([cx, cy, r])
    for _ in range(20):
        dx, dy = x - p[0], y - p[1]
        d = np.hypot(dx, dy)
        res = d - p[2]
        j = np.column_stack((-dx / d, -dy / d, -np.ones_like(d)))
        step = np.linalg.lstsq(j, -res, rcond=None)[0]
        p = p + step
        if np.abs(step).max() < 1e-10:
            break
    res = np.hypot(x - p[0], y - p[1]) - p[2]
    return p[:2], float(p[2]), res


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=False) + "\n")


def stats(x: np.ndarray) -> dict:
    x = np.abs(np.asarray(x, dtype=float))
    return {
        "n": int(x.size),
        "rms_mm": round(float(np.sqrt(np.mean(x * x))), 4),
        "p95_mm": round(float(np.percentile(x, 95)), 4),
        "max_mm": round(float(x.max()), 4),
    }
