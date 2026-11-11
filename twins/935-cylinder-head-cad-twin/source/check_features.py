#!/usr/bin/env python3
"""Measure the fitted features, and the CAD body, with CloudCompare.

A fit must not supply its own inspection evidence. ``fit_features.py`` fits
half of the scan vertices of each window; this script takes the other half and
has CloudCompare 2.13.2 measure their distance to the fitted primitive, built
here as a triangle mesh over the stations the fit covers. CloudCompare runs in
the repository's assigned image through its wrapper
(``benchmarks/free-tools/cloudcompare.py``), with no network.

Acceptance, fixed before the first run:

* the check set of a feature is the held-out vertices CloudCompare finds within
  ``BAND_MM`` of the primitive;
* a feature is **confirmed** when that set holds at least ``MIN_VERTICES`` and
  at least ``MIN_SHARE`` of it lies within the twin tolerance ``TOLERANCE_MM``.

``--body`` measures a sample of acquired scan facets against a closed twin
body instead, for comparison with the Warp scorecard.

The distances are to the scan, whose scale is an owner instruction. A
confirmed feature is a primitive that describes the acquired surface within
the tolerance. It is not a dimension of the specimen.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
from pathlib import Path

import numpy as np

from twin_common import sha256_file, write_json

SCHEMA = "935-cad-twin-feature-check/1"
BAND_MM = 0.5
TOLERANCE_MM = 0.2
MIN_SHARE = 0.90
MIN_VERTICES = 100
SEGMENTS = 720


def frame(a: np.ndarray):
    e1 = np.cross(a, np.eye(3)[np.argmin(np.abs(a))])
    e1 /= np.linalg.norm(e1)
    return e1, np.cross(a, e1)


def primitive_mesh(fit: dict, plane_half_size: float = 40.0):
    """Vertices and triangles of a fitted primitive over the extent the fit covers."""

    if fit["type"] == "plane":
        n = np.asarray(fit["normal"], dtype=float)
        e1, e2 = frame(n / np.linalg.norm(n))
        c = np.asarray(fit["point"], dtype=float)
        s = plane_half_size
        v = np.array([c - s * e1 - s * e2, c + s * e1 - s * e2, c + s * e1 + s * e2, c - s * e1 + s * e2])
        return v, np.array([[0, 1, 2], [0, 2, 3]])
    a = np.asarray(fit["axis_direction"], dtype=float)
    a /= np.linalg.norm(a)
    e1, e2 = frame(a)
    c = np.asarray(fit["axis_point"], dtype=float)
    k = math.tan(math.radians(fit.get("half_angle_deg", 0.0)))
    angle = np.linspace(0.0, 2.0 * math.pi, SEGMENTS, endpoint=False)
    rings = []
    for t in fit["station_range_mm"]:
        r = 0.5 * fit["diameter_mm"] + k * t
        rings.append(c + t * a + r * (np.outer(np.cos(angle), e1) + np.outer(np.sin(angle), e2)))
    i = np.arange(SEGMENTS)
    j = (i + 1) % SEGMENTS
    faces = np.concatenate([np.column_stack([i, j, j + SEGMENTS]), np.column_stack([i, j + SEGMENTS, i + SEGMENTS])])
    return np.concatenate(rings), faces


def write_obj(path: Path, v: np.ndarray, f: np.ndarray) -> None:
    with open(path, "w") as out:
        out.writelines(f"v {x:.9f} {y:.9f} {z:.9f}\n" for x, y, z in v)
        out.writelines(f"f {a + 1} {b + 1} {c + 1}\n" for a, b, c in f)


def cloudcompare(image: str, work: Path, name: str, points: np.ndarray, v: np.ndarray, f: np.ndarray,
                 memory: str = "4g", timeout: int = 900) -> np.ndarray:
    """Unsigned distance of each point to the mesh, as CloudCompare reports it."""

    case = work / name
    case.mkdir(parents=True)
    np.savetxt(case / "cloud.xyz", points, fmt="%.9f")
    write_obj(case / "mesh.obj", v, f)
    (case / "configuration.json").write_text(json.dumps({
        "units": "mm",
        "cloud_to_reference": [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
    }))
    subprocess.run([
        "docker", "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges", "--cpus", "2", "--memory", memory, "--memory-swap", memory,
        "--pids-limit", "256", "--tmpfs", "/tmp:rw,nosuid,size=1g", "--user", f"{os.getuid()}:{os.getgid()}",
        "--mount", f"type=bind,src={case.resolve()},dst=/work", image,
        "compare", "--cloud", "/work/cloud.xyz", "--mesh", "/work/mesh.obj",
        "--configuration", "/work/configuration.json", "--output", "/work/result",
    ], check=True, timeout=timeout, capture_output=True)
    receipt = json.loads((case / "result/receipt.json").read_text())
    if receipt["status"] != "diagnostic_completed":
        raise SystemExit(f"{name}: CloudCompare wrapper returned {receipt['status']}")
    distance = np.loadtxt(case / "result/distances.asc", comments=("#", "//"))[:, 3]
    if len(distance) != len(points):
        raise SystemExit(f"{name}: {len(distance)} distances for {len(points)} points")
    return np.abs(distance)


def verdict(distance: np.ndarray) -> dict:
    """The acceptance of one feature from CloudCompare's distances of its held-out vertices."""

    near = distance[distance < BAND_MM]
    out = {"held_out_vertices_in_window": int(len(distance)), "check_vertices": int(len(near))}
    if len(near) < MIN_VERTICES:
        return {**out, "confirmed": False, "reason": f"fewer than {MIN_VERTICES} held-out vertices near the primitive"}
    share = float((near < TOLERANCE_MM).mean())
    return {**out,
            "share_within_tolerance": round(share, 4),
            "median_mm": round(float(np.median(near)), 4),
            "p95_mm": round(float(np.percentile(near, 95)), 4),
            "confirmed": bool(share >= MIN_SHARE)}


def image_id(image: str) -> str:
    return subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}}", image], check=True,
                          capture_output=True, text=True).stdout.strip()


def check_features(args) -> None:
    fits = json.loads(args.fits.read_text())
    split = np.load(args.split)
    v = np.load(args.bare_scan)["v"]
    rows = []
    for region in fits["regions"]:
        fit = region["fit"]
        if fit is None:
            rows.append({"id": region["id"], "confirmed": False, "reason": "no fit"})
            continue
        held = v[split[region["id"] + "__held"]]
        mesh_v, mesh_f = primitive_mesh(fit)
        row = {"id": region["id"], "type": fit["type"], "determined_by_the_fit": fit["determined"],
               **verdict(cloudcompare(args.image, args.work, region["id"], held, mesh_v, mesh_f))}
        rows.append(row)
        print(region["id"], {k: row[k] for k in row if k not in ("id", "type")}, flush=True)
    write_json(args.out, {
        "schema": SCHEMA,
        "fits_sha256": sha256_file(args.fits),
        "tool": {"name": "CloudCompare 2.13.2, C2M_DIST, unsigned", "image": args.image, "image_id": image_id(args.image),
                 "wrapper": "benchmarks/free-tools/cloudcompare.py"},
        "acceptance": {"fixed_before_first_run": True, "band_mm": BAND_MM, "tolerance_mm": TOLERANCE_MM,
                       "min_share": MIN_SHARE, "min_vertices": MIN_VERTICES},
        "claims": "held-out scan vertices against the fitted primitive; a confirmed feature describes the acquired "
                  "surface within the tolerance and establishes no dimension of the specimen",
        "confirmed": sum(r["confirmed"] for r in rows),
        "regions_checked": len(rows),
        "regions": rows,
    })


def check_body(args) -> None:
    d = np.load(args.bare_scan)
    v, f = d["v"], d["f"]
    tri = v[f]
    area = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    rng = np.random.default_rng(args.seed)
    pick = rng.choice(len(f), size=args.samples, replace=True, p=area / area.sum())
    body = np.load(args.body)
    distance = cloudcompare(args.image, args.work, "body", tri[pick].mean(axis=1), body["v"], body["f"],
                            memory="8g", timeout=3600)
    scorecard = json.loads(args.scorecard.read_text())
    write_json(args.out, {
        "schema": "935-cad-twin-body-cloudcompare/1",
        "tool": {"name": "CloudCompare 2.13.2, C2M_DIST, unsigned", "image": args.image, "image_id": image_id(args.image)},
        "sample": {"facets": args.samples, "rule": "centroids of acquired bare-scan facets drawn with probability "
                   "proportional to area, with replacement", "seed": args.seed},
        "body_triangles": int(len(body["f"])),
        "cloudcompare": {
            "p50_mm": round(float(np.median(distance)), 4),
            "p95_mm": round(float(np.percentile(distance, 95)), 4),
            "share_within_0p1_mm": round(float((distance < 0.1).mean()), 4),
            "share_within_0p2_mm": round(float((distance < 0.2).mean()), 4),
            "share_within_0p5_mm": round(float((distance < 0.5).mean()), 4),
        },
        "scorecard_sha256": sha256_file(args.scorecard),
        "scorecard_scan_to_twin": {
            "checker": scorecard["checker"],
            "p50_mm": scorecard["scan_to_twin"]["p50"],
            "p95_mm": scorecard["scan_to_twin"]["p95"],
            "share_within_0p1_mm": scorecard["scan_to_twin"]["area_share_within_mm"]["0.1"],
            "share_within_0p2_mm": scorecard["scan_to_twin"]["area_share_within_mm"]["0.2"],
            "share_within_0p5_mm": scorecard["scan_to_twin"]["area_share_within_mm"]["0.5"],
        },
        "claims": "a second distance tool on a sample; it checks the scorecard's arithmetic, not the scan",
    })


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--bare-scan", type=Path, required=True)
    ap.add_argument("--image", required=True, help="local CloudCompare image built from containers/free-tools-cloudcompare.Dockerfile")
    ap.add_argument("--work", type=Path, required=True, help="new private directory for clouds, meshes and receipts")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--fits", type=Path)
    ap.add_argument("--split", type=Path, help="private NPZ written by fit_features.py")
    ap.add_argument("--body", type=Path, help="private NPZ (v, f) of a closed twin body: measure the scan against it instead")
    ap.add_argument("--scorecard", type=Path)
    ap.add_argument("--samples", type=int, default=200000)
    ap.add_argument("--seed", type=int, default=20261111)
    args = ap.parse_args()
    if args.work.exists():
        raise SystemExit(f"{args.work} exists: give a new directory")
    args.work.mkdir(parents=True)
    if args.body:
        check_body(args)
    else:
        check_features(args)


if __name__ == "__main__":
    main()
