#!/usr/bin/env python3
"""Synthetic witness: can a primitive detector recover drafted fin faces?

On 2026-11-09 the 935 head twin's level detector (horizontal faces binned in Z)
found only 7 of 28 fin faces: cast fins are drafted, so each face spreads over
1 to 2 mm of height and never forms a sharp level peak. This witness builds a
fin stack whose every face carries a known draft (tilt and azimuth), meshes it
with scan-like noise, and asks two detectors to recover the faces:

* ``open3d_patches``: Open3D ``detect_planar_patches`` (robust region growing
  on points with normals), the candidate tool;
* ``z_level_histogram``: the level detector that failed, as a negative control.

The ground truth is generated here and never comes from a detector, so the
result is an independent check of the tool on this geometry class. It
qualifies the software chain for drafted planar faces only; it says nothing
about any real part.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

SEED = 20261110
FINS = 12
R_IN, R_OUT = 40.0, 80.0          # mm, annular fin face
PITCH, THICKNESS = 7.0, 3.0       # mm
DRAFTS_DEG = (0.0, 0.5, 1.0, 1.5, 2.0, 3.0)
GRID_MM = 1.0                     # triangle size, close to a 1 mm scan pitch
NOISE_MM = 0.03                   # normal noise, the 935 deck-plane RMS order

# Sequential RANSAC parameters, fixed from the noise model before its first run.
RANSAC_DISTANCE_MM = 0.1          # about 3 x NOISE_MM
RANSAC_NORMAL_DEG = 15.0          # inliers must also agree in normal (excludes facing faces)
RANSAC_MIN_POINTS = 2000          # stop when the best plane holds fewer samples
RANSAC_ITERATIONS = 2000

# Acceptance fixed before the first run.
MATCH_ANGLE_DEG = 1.0             # a detection may claim a truth plane within this
MATCH_OFFSET_MM = 0.5
REQUIRED_RECALL = 0.95
MAX_TILT_ERROR_DEG = 0.1
MAX_OFFSET_ERROR_MM = 0.05


def unit(v):
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def truth_faces(rng):
    """One plane per fin face: outward normal and the face height on the axis."""
    faces = []
    for k in range(FINS):
        z_mid = k * PITCH
        for side, sign in (("bottom", -1.0), ("top", 1.0)):
            draft = DRAFTS_DEG[(2 * k + (side == "top")) % len(DRAFTS_DEG)]
            azimuth = rng.uniform(0, 2 * math.pi)
            t = math.radians(draft)
            # Outward normal tilted by the draft about a horizontal axis.
            n = np.array([math.sin(t) * math.cos(azimuth), math.sin(t) * math.sin(azimuth), sign * math.cos(t)])
            faces.append({"fin": k, "side": side, "draft_deg": draft, "azimuth_deg": math.degrees(azimuth),
                          "normal": n, "z_axis_mm": z_mid + sign * THICKNESS / 2})
    return faces


def face_mesh(face, rng):
    """Regular triangle grid on the face plane, clipped to the annulus, with noise along the normal."""
    n = face["normal"]
    axis = np.arange(-R_OUT, R_OUT + 1e-9, GRID_MM)
    gx, gy = np.meshgrid(axis, axis, indexing="ij")
    m = len(axis)
    idx = np.arange(m * m).reshape(m, m)
    quads = np.column_stack([idx[:-1, :-1].ravel(), idx[1:, :-1].ravel(), idx[1:, 1:].ravel(), idx[:-1, 1:].ravel()])
    tris = np.vstack([quads[:, [0, 1, 2]], quads[:, [0, 2, 3]]])
    xy = np.column_stack([gx.ravel(), gy.ravel()])
    radius = np.linalg.norm(xy[tris].mean(axis=1), axis=1)
    tris = tris[(radius >= R_IN) & (radius <= R_OUT)]
    z = face["z_axis_mm"] - (n[0] * xy[:, 0] + n[1] * xy[:, 1]) / n[2]
    v = np.column_stack([xy, z]) + rng.normal(0, NOISE_MM, (len(xy), 1)) * n
    return v, tris


def triangle_samples(v, f):
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    cross = np.cross(b - a, c - a)
    area = 0.5 * np.linalg.norm(cross, axis=1)
    keep = area > 1e-9
    return (a + b + c)[keep] / 3, unit(cross[keep]), area[keep]


def build(rng):
    faces = truth_faces(rng)
    cen, nrm, area, label = [], [], [], []
    for i, face in enumerate(faces):
        c, n, a = triangle_samples(*face_mesh(face, rng))
        flip = np.sign(n @ face["normal"])  # consistent outward orientation
        cen.append(c), nrm.append(n * flip[:, None]), area.append(a), label.append(np.full(len(c), i))
    return faces, np.vstack(cen), np.vstack(nrm), np.concatenate(area), np.concatenate(label)


def z_level_histogram(cen, nrm, area, res=0.02, min_area=150.0):
    """The 935 twin's level detector, reproduced as a negative control."""
    sel = np.abs(nrm[:, 2]) > 0.98
    z, a = cen[sel, 2], area[sel]
    edges = np.arange(z.min() - res, z.max() + 2 * res, res)
    h, _ = np.histogram(z, bins=edges, weights=a)
    out, i = [], 1
    while i < len(h) - 1:
        if h[i] >= h[i - 1] and h[i] > h[i + 1]:
            lo, hi = max(0, i - 2), min(len(h), i + 3)
            if h[lo:hi].sum() >= min_area:
                c = 0.5 * (edges[lo:hi] + edges[lo + 1:hi + 1])
                out.append(float((c * h[lo:hi]).sum() / h[lo:hi].sum()))
            i = hi
        else:
            i += 1
    # A level is a horizontal plane; report it with an upward or downward normal.
    return [{"normal": np.array([0.0, 0.0, s]), "z_axis_mm": z0} for z0 in out for s in (-1.0, 1.0)]


def open3d_patches(cen, nrm):
    import open3d as o3d

    pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(cen))
    pcd.normals = o3d.utility.Vector3dVector(nrm)
    boxes = pcd.detect_planar_patches(normal_variance_threshold_deg=60, coplanarity_deg=75,
                                      outlier_ratio=0.75, min_plane_edge_length=0, min_num_points=0,
                                      search_param=o3d.geometry.KDTreeSearchParamKNN(knn=30))
    found = []
    for box in boxes:
        n = np.asarray(box.R)[:, 2]
        centre = np.asarray(box.center)
        if abs(n[2]) < 0.5:
            continue
        # Refit each patch by least squares on the points it contains, so the
        # reported plane is the patch's own fit, not the box orientation.
        idx = box.get_point_indices_within_bounding_box(pcd.points)
        p = cen[idx]
        q = p - p.mean(axis=0)
        normal = np.linalg.svd(q, full_matrices=False)[2][2]
        if normal @ nrm[idx].mean(axis=0) < 0:
            normal = -normal
        z_axis = p.mean(axis=0) @ normal / normal[2]
        found.append({"normal": normal, "z_axis_mm": float(z_axis), "points": len(idx),
                      "box_centre_mm": centre.tolist()})
    return found


def open3d_sequential_ransac(cen, nrm):
    """Open3D segment_plane repeatedly, keeping only inliers whose normals agree."""
    import open3d as o3d

    o3d.utility.random.seed(SEED)
    remaining = np.arange(len(cen))
    found = []
    while len(remaining) >= RANSAC_MIN_POINTS:
        pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(cen[remaining]))
        (a, b, c, d), inliers = pcd.segment_plane(RANSAC_DISTANCE_MM, 3, RANSAC_ITERATIONS)
        inliers = remaining[np.asarray(inliers)]
        normal = np.array([a, b, c])
        if normal @ nrm[inliers].mean(axis=0) < 0:
            normal = -normal
        agree = nrm[inliers] @ normal >= math.cos(math.radians(RANSAC_NORMAL_DEG))
        members = inliers[agree]
        remaining = np.setdiff1d(remaining, inliers if len(members) < RANSAC_MIN_POINTS else members)
        if len(members) < RANSAC_MIN_POINTS:
            continue
        p = cen[members]
        normal = np.linalg.svd(p - p.mean(axis=0), full_matrices=False)[2][2]
        if normal @ nrm[members].mean(axis=0) < 0:
            normal = -normal
        if abs(normal[2]) < 0.5:
            continue
        found.append({"normal": normal, "z_axis_mm": float(p.mean(axis=0) @ normal / normal[2]),
                      "points": int(len(members))})
    return found


def score(faces, found):
    rows, claimed = [], set()
    for t in faces:
        best = None
        for j, d in enumerate(found):
            ang = math.degrees(math.acos(np.clip(t["normal"] @ d["normal"], -1, 1)))
            off = abs(d["z_axis_mm"] - t["z_axis_mm"])
            if ang <= MATCH_ANGLE_DEG and off <= MATCH_OFFSET_MM and (best is None or off < best[2]):
                best = (j, ang, off)
        if best:
            claimed.add(best[0])
        rows.append({"fin": t["fin"], "side": t["side"], "draft_deg": t["draft_deg"],
                     "found": best is not None,
                     "tilt_error_deg": None if best is None else round(best[1], 4),
                     "offset_error_mm": None if best is None else round(best[2], 4)})
    hits = [r for r in rows if r["found"]]
    recall = len(hits) / len(rows)
    within = [r for r in hits if r["tilt_error_deg"] <= MAX_TILT_ERROR_DEG and r["offset_error_mm"] <= MAX_OFFSET_ERROR_MM]
    by_draft = {}
    for r in rows:
        key = f"{r['draft_deg']:.1f}"
        by_draft.setdefault(key, [0, 0])
        by_draft[key][0] += r["found"]
        by_draft[key][1] += 1
    return {
        "faces": len(rows), "found": len(hits), "recall": round(recall, 4),
        "found_within_acceptance": len(within),
        "found_by_draft_deg": {k: f"{a}/{b}" for k, (a, b) in sorted(by_draft.items())},
        "max_tilt_error_deg": max((r["tilt_error_deg"] for r in hits), default=None),
        "max_offset_error_mm": max((r["offset_error_mm"] for r in hits), default=None),
        "unmatched_detections": len(found) - len(claimed),
        "rows": rows,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    import open3d as o3d

    rng = np.random.default_rng(SEED)
    faces, cen, nrm, area, _ = build(rng)
    level = score(faces, z_level_histogram(cen, nrm, area))
    patches = score(faces, open3d_patches(cen, nrm))
    ransac = score(faces, open3d_sequential_ransac(cen, nrm))

    def passed(r):
        return r["found_within_acceptance"] / r["faces"] >= REQUIRED_RECALL and r["unmatched_detections"] == 0
    report = {
        "schema": "scan-primitive-fitting-witness/1",
        "witness": "synthetic drafted fin stack, ground truth generated independently of any detector",
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "lock_sha256": hashlib.sha256((Path(__file__).parent / "requirements.lock.txt").read_bytes()).hexdigest(),
        "open3d": o3d.__version__,
        "numpy": np.__version__,
        "geometry": {"seed": SEED, "fins": FINS, "faces": len(faces), "r_mm": [R_IN, R_OUT],
                     "pitch_mm": PITCH, "thickness_mm": THICKNESS, "drafts_deg": list(DRAFTS_DEG),
                     "triangle_mm": GRID_MM, "noise_mm": NOISE_MM, "samples": int(len(cen))},
        "acceptance": {"recall_min": REQUIRED_RECALL, "tilt_error_max_deg": MAX_TILT_ERROR_DEG,
                       "offset_error_max_mm": MAX_OFFSET_ERROR_MM,
                       "match_window": {"angle_deg": MATCH_ANGLE_DEG, "offset_mm": MATCH_OFFSET_MM}},
        "ransac_parameters": {"distance_mm": RANSAC_DISTANCE_MM, "normal_agreement_deg": RANSAC_NORMAL_DEG,
                              "min_points": RANSAC_MIN_POINTS, "iterations": RANSAC_ITERATIONS},
        "detectors": {"open3d_sequential_ransac": ransac, "open3d_patches_library_defaults": patches,
                      "z_level_histogram_negative_control": level},
        "passed": {name: passed(r) for name, r in (("open3d_sequential_ransac", ransac),
                                                   ("open3d_patches_library_defaults", patches),
                                                   ("z_level_histogram_negative_control", level))},
        "claims": "software witness for drafted planar faces only; no real part, scan or fit is qualified",
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    for name, r in report["detectors"].items():
        print(name, r["found_within_acceptance"], "/", r["faces"], r["found_by_draft_deg"], "tilt",
              r["max_tilt_error_deg"], "offset", r["max_offset_error_mm"], "spurious", r["unmatched_detections"])
    print(json.dumps(report["passed"]))


if __name__ == "__main__":
    main()
