"""Fit the functional frame of the 935 rotor scan from its own features.

Datum A: the front flange face carrying the bolt circle (plane fit).
Datum B: the hub bore axis (circle fit perpendicular to A).
Clocking: blade 0 is centred on +X (blade centroids of the nine blades).

It also fits the back faces separately and reports how far the back
acquisition sits from the front one, because the scan's own file name says
the back was not lined up with the centre.

Usage: fit_frame.py ROTOR.obj PRIVATE_CACHE_DIR OUT_FRAME.json
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

from fan_common import (BLADE_COUNT, ROTOR_SCAN_SHA256, SCALE_BASIS, SCALE_MM_PER_UNIT,
                        cylindrical, load_obj, write_json)


def plane_fit(p: np.ndarray, iters: int = 5) -> tuple[np.ndarray, np.ndarray, float, int]:
    keep = np.ones(len(p), bool)
    for _ in range(iters):
        q = p[keep]
        mu = q.mean(0)
        n = np.linalg.svd(q - mu, full_matrices=False)[2][2]
        d = (p - mu) @ n
        keep = np.abs(d) < max(3 * np.std(d[keep]), 0.05)
    q = p[keep]
    mu = q.mean(0)
    n = np.linalg.svd(q - mu, full_matrices=False)[2][2]
    d = (q - mu) @ n
    return n, mu, float(np.sqrt(np.mean(d ** 2))), int(keep.sum())


def circle_fit(xy: np.ndarray, r0: float) -> tuple[np.ndarray, float, float, int]:
    def res(p):
        return np.hypot(xy[:, 0] - p[0], xy[:, 1] - p[1]) - p[2]
    s = least_squares(res, [0.0, 0.0, r0], loss="soft_l1", f_scale=0.1)
    r = res(s.x)
    inl = np.abs(r) < 0.3
    return s.x[:2], float(s.x[2]), float(np.sqrt(np.mean(r[inl] ** 2))), int(inl.sum())


def basis_from_normal(n: np.ndarray) -> np.ndarray:
    z = n / np.linalg.norm(n)
    x = np.cross([0.0, 1.0, 0.0], z) if abs(z[1]) < 0.9 else np.cross([1.0, 0.0, 0.0], z)
    x /= np.linalg.norm(x)
    return np.vstack([x, np.cross(z, x), z])


def tilt_deg(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.degrees(np.arccos(min(1.0, abs(a @ b) / np.linalg.norm(a) / np.linalg.norm(b)))))


def band(p, rl, rh, zl, zh):
    r, _, z = cylindrical(p)
    return (r > rl) & (r < rh) & (z > zl) & (z < zh)


def main(obj: str, cache: str, out: str) -> int:
    v, _ = load_obj(Path(obj), ROTOR_SCAN_SHA256, Path(cache))
    c0 = v.mean(0)
    _, u = np.linalg.eigh(np.cov((v - c0).T))
    rot = basis_from_normal(u[:, 0])
    p = (v - c0) @ rot.T
    # +Z towards the open drum lip: the lip sits at the axial extreme of the r~88 band.
    r, _, z = cylindrical(p)
    drum = (r > 86) & (r < 90)
    if abs(np.percentile(z[drum], 99.5)) < abs(np.percentile(z[drum], 0.5)):
        rot = np.vstack([rot[0], -rot[1], -rot[2]])
        p = (v - c0) @ rot.T
    # Iterate: datum A plane, then bore circle, re-express, twice.
    for it in range(3):
        sel = band(p, 38, 56, 4.5, 9.5) if it == 0 else band(p, 38, 56, -2.5, 2.5)
        n, _, _, _ = plane_fit(p[sel])
        n = n if n[2] > 0 else -n
        rot = basis_from_normal(rot.T @ n)
        p = (v - c0) @ rot.T
        # Datum A height from the plane fit in the new basis.
        sel = band(p, 38, 56, -60, 60)
        zs = p[sel][:, 2]
        hist, edges = np.histogram(zs, bins=np.arange(zs.min(), zs.max(), 0.1))
        zA = float(edges[np.argmax(hist)] + 0.05)
        # Bore: the innermost wall of the flange, below datum A.
        bore = band(p, 8.5, 13.5, zA - 24, zA - 1)
        cxy, r_bore, rms_b, k_b = circle_fit(p[bore][:, :2], 11.0)
        c0 = c0 + rot.T @ np.array([cxy[0], cxy[1], zA])
        p = (v - c0) @ rot.T
    n_a, _, rms_a, k_a = plane_fit(p[band(p, 38, 56, -1.0, 1.0)])
    bore = band(p, 8.5, 13.5, -24, -1)
    cxy, r_bore, rms_b, k_b = circle_fit(p[bore][:, :2], 11.0)
    # Clocking from the nine blades: mean blade-mass angle modulo 40 degrees.
    r, th, z = cylindrical(p)
    blade = (r > 105) & (r < 125)
    pitch = 2 * np.pi / BLADE_COUNT
    ang = np.angle(np.mean(np.exp(1j * BLADE_COUNT * th[blade]))) / BLADE_COUNT
    cz, sz = np.cos(ang), np.sin(ang)
    rz = np.array([[cz, sz, 0], [-sz, cz, 0], [0, 0, 1]])
    rot = rz @ rot
    p = (v - c0) @ rot.T
    # Back faces in this frame: planes and the drum low band.
    back = {}
    for name, sel in {
        "flange_back_face": band(p, 14, 40, -27.5, -25.0),
        "boss_back_face": band(p, 20, 32, -41.5, -38.0),
    }.items():
        n, mu, rms, k = plane_fit(p[sel])
        back[name] = {"z_mm": round(float(mu[2]), 3), "tilt_vs_datum_A_deg": round(tilt_deg(n, np.array([0, 0, 1.0])), 3),
                      "normal_xy": [round(float(n[0] * np.sign(n[2])), 5), round(float(n[1] * np.sign(n[2])), 5)],
                      "rms_mm": round(rms, 3), "points": k}
    front = {}
    for name, sel in {"flange_front_face_inner": band(p, 12, 17, -1.0, 1.0),
                      "step_front": band(p, 20, 34, -10.5, -8.0), "drum_lip": band(p, 85.5, 89, 31, 34.5)}.items():
        n, mu, rms, k = plane_fit(p[sel])
        front[name] = {"z_mm": round(float(mu[2]), 3), "tilt_vs_datum_A_deg": round(tilt_deg(n, np.array([0, 0, 1.0])), 3),
                       "rms_mm": round(rms, 3), "points": k}
    drum = {}
    r, th, z = cylindrical(p)
    for name, (zl, zh) in {"drum_upper_band": (5, 30), "drum_lower_band": (-38, -30)}.items():
        sel = (r > 86.5) & (r < 91) & (z > zl) & (z < zh)
        cxy2, rr, rms, k = circle_fit(p[sel][:, :2], 89.0)
        drum[name] = {"centre_xy_mm": [round(float(x), 3) for x in cxy2], "radius_mm": round(rr, 3), "rms_mm": round(rms, 3), "inliers": k}
    frame = {
        "schema": "935-horizontal-fan-cad-twin/frame/1",
        "scan_sha256": ROTOR_SCAN_SHA256,
        "scale_mm_per_unit": SCALE_MM_PER_UNIT,
        "scale_basis": SCALE_BASIS,
        "definition": {
            "datum_A": "front flange face carrying the bolt circle; z = 0, +Z towards the open drum lip",
            "datum_B": "hub bore axis, fitted as a circle perpendicular to datum A",
            "clocking": "blade 0 centred on +X (ninefold mean of blade points at r 105-125 mm)",
        },
        "rotation": [[round(float(x), 10) for x in row] for row in rot],
        "translation_mm": [round(float(x), 6) for x in (-(rot @ c0))],
        "datum_A": {"rms_mm": round(rms_a, 3), "points": k_a},
        "bore": {"radius_mm": round(r_bore, 3), "diameter_mm": round(2 * r_bore, 3), "rms_mm": round(rms_b, 3), "inliers": k_b,
                 "centre_residual_xy_mm": [round(float(x), 4) for x in cxy]},
        "front_faces": front,
        "back_faces": back,
        "drum_circles": drum,
        "back_misregistration": {
            "tilt_deg": back["flange_back_face"]["tilt_vs_datum_A_deg"],
            "drum_centre_shift_mm": round(float(np.hypot(*(np.subtract(drum["drum_lower_band"]["centre_xy_mm"], drum["drum_upper_band"]["centre_xy_mm"])))), 3),
            "note": "Back-facing faces tilt relative to datum A and the lower drum circle is offset from the upper one. Read as acquisition misregistration of the back pass (the scan file name says so), not as part geometry.",
        },
    }
    write_json(Path(out), frame)
    print(f"bore D={2*r_bore:.3f} rms={rms_b:.3f}; datum A rms={rms_a:.3f}; back tilt={frame['back_misregistration']['tilt_deg']} deg, drum shift={frame['back_misregistration']['drum_centre_shift_mm']} mm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:]))
