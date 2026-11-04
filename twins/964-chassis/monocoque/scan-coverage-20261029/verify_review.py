"""Independently compare reopened USD and section archives with admitted arrays.

This checks software/data fidelity, not semantic segmentation, physical datums,
interior coverage, a reconstructed part or engineering qualification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def expected_regions(vertices, faces, regions):
    tri = vertices[faces]
    low, high = tri.min(axis=1), tri.max(axis=1)
    owners = np.full(len(faces), -1, dtype=np.int16)
    for index, region in enumerate(regions):
        limits = np.array(region["bounds"]).reshape(3, 2)
        mask = (low >= limits[:, 0]).all(axis=1) & (high <= limits[:, 1]).all(axis=1)
        owners[(owners == -1) & mask] = index
    expected = {r["name"]: np.flatnonzero(owners == i) for i, r in enumerate(regions)}
    expected["Context"] = np.flatnonzero(owners == -1)
    return expected


def verify_stage(stage_path, vertices, faces, config):
    from pxr import Gf, Usd, UsdGeom
    stage = Usd.Stage.Open(str(stage_path))
    if stage is None or UsdGeom.GetStageMetersPerUnit(stage) != 0.001 or UsdGeom.GetStageUpAxis(stage) != "Z":
        raise ValueError("Wrong stage units or axis")
    if stage.GetRootLayer().subLayerPaths or len(stage.GetUsedLayers()) != 2:
        raise ValueError("Unexpected layer dependency")
    root = stage.GetDefaultPrim()
    if not root or str(root.GetPath()) != "/ScanReview":
        raise ValueError("Unexpected root")
    for flag in ("bodySegmentationValidated", "structuralDatumsRegistered", "fitmentValidated",
                 "manufacturingReleased", "interiorSurfacesReconstructed"):
        if root.GetAttribute("scan:" + flag).Get() is not False:
            raise ValueError("Unexpected qualification claim")
    expected = expected_regions(vertices, faces, config["regions"])
    found, counts = set(), {}
    transform = UsdGeom.XformCache()
    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Mesh):
            continue
        name = prim.GetName()
        if name not in expected or str(prim.GetPath()) != "/ScanReview/Observed/" + name or name in found:
            raise ValueError("Unexpected mesh")
        if transform.GetLocalToWorldTransform(prim) != Gf.Matrix4d(1):
            raise ValueError("Source-coordinate transform changed")
        if prim.GetAttribute("scan:componentIdentified").Get() is not False:
            raise ValueError("Unsupported part identification")
        mesh = UsdGeom.Mesh(prim)
        face_ids = np.array(prim.GetAttribute("scan:sourceFaceIds").Get())
        vertex_ids = np.array(prim.GetAttribute("scan:sourceVertexIds").Get())
        points = np.array(mesh.GetPointsAttr().Get())
        indices = np.array(mesh.GetFaceVertexIndicesAttr().Get())
        face_counts = np.array(mesh.GetFaceVertexCountsAttr().Get())
        if not np.array_equal(face_ids, expected[name]):
            raise ValueError("Source face selection differs from independent window evaluation")
        if len(face_counts) != len(face_ids) or not np.all(face_counts == 3) or len(indices) != 3 * len(face_ids):
            raise ValueError("Source topology changed")
        if vertex_ids.ndim != 1 or (vertex_ids < 0).any() or (vertex_ids >= len(vertices)).any():
            raise ValueError("Invalid source vertex IDs")
        if (indices < 0).any() or (indices >= len(vertex_ids)).any():
            raise ValueError("Invalid local face indices")
        if not np.array_equal(points, vertices[vertex_ids]):
            raise ValueError("Observed source coordinates changed")
        if not np.array_equal(vertex_ids[indices.reshape(-1, 3)], faces[face_ids]):
            raise ValueError("Original oriented triangles changed")
        if not np.array_equal(vertex_ids, np.unique(faces[face_ids])):
            raise ValueError("Unexpected unused or duplicated source vertices")
        found.add(name)
        counts[name] = len(face_ids)
    if found != set(expected) or sum(counts.values()) != len(faces):
        raise ValueError("Incomplete source-face partition")
    for name in config["unobserved_requirements"]:
        prim = stage.GetPrimAtPath("/ScanReview/RequiredUnobserved/" + name)
        if not prim or list(prim.GetChildren()) or prim.GetAttribute("scan:status").Get() != "required_surface_not_established_by_this_scan_review":
            raise ValueError("Missing or fabricated unobserved surface")
    return counts


def verify_sections(review, vertices, faces, config):
    scope = np.array(config["section_scope_bounds"]).reshape(3, 2)
    tri = vertices[faces].astype(np.float64)
    inside = ((tri >= scope[:, 0]) & (tri <= scope[:, 1])).all(axis=(1, 2))
    results = {}
    for entry in config["sections"]:
        axis, position = entry["axis"], entry["position_mm"]
        distance = tri[:, :, axis] - position
        numerical_touch = (np.abs(distance) <= 1e-6).any(axis=1)
        expected = np.flatnonzero(inside & ~numerical_touch & (distance.min(axis=1) < -1e-6) & (distance.max(axis=1) > 1e-6))
        with np.load(review / (entry["name"] + ".npz"), allow_pickle=False) as archive:
            ids, points = archive["source_face_ids"], archive["endpoints"]
        if not np.array_equal(ids, expected) or points.shape != (len(ids), 2, 3) or not np.isfinite(points).all():
            raise ValueError("Section selection differs from the original triangles")
        if not np.allclose(points[:, :, axis], position, rtol=0, atol=1e-9):
            raise ValueError("Section endpoints are off the selected plane")
        # Independent endpoint construction, one triangle at a time with edge clipping.
        for triangle, actual in zip(tri[ids], points):
            expected_points = []
            for i, j in ((0, 1), (1, 2), (2, 0)):
                a, b = triangle[i], triangle[j]
                if min(a[axis], b[axis]) < position < max(a[axis], b[axis]):
                    t = (position - a[axis]) / (b[axis] - a[axis])
                    expected_points.append((1 - t) * a + t * b)
            if len(expected_points) != 2 or not np.allclose(actual, expected_points, rtol=0, atol=1e-9):
                raise ValueError("Section endpoints differ from the source triangle edges")
        results[entry["name"]] = {"source_intersections_verified": len(ids), "touching_triangles_excluded": int((inside & numerical_touch).sum())}
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scan", type=Path, required=True)
    parser.add_argument("--vertices", type=Path, required=True)
    parser.add_argument("--faces", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    args = parser.parse_args()
    target = args.review / "verification.json"
    if target.exists():
        raise FileExistsError("Verification receipt already exists")
    registration_path = ROOT / "twins/964-chassis/derived/scan-recalage-20260925.json"
    registration = json.loads(registration_path.read_text())
    if sha(args.scan) != registration["source_sha256"]:
        raise ValueError("Original scan digest mismatch")
    for path, name in ((args.vertices, "verts_vehicle.npy"), (args.faces, "faces.npy")):
        if sha(path) != registration["outputs"][name]:
            raise ValueError("Original array digest mismatch")
    report = json.loads((args.review / "run.json").read_text())
    config = json.loads((HERE / "regions.json").read_text())
    stage_path = args.review / "observed-underbody.usdc"
    for path, expected in ((stage_path, report["stage_sha256"]), (HERE / "regions.json", report["regions_sha256"]),
                           (registration_path, report["registration_sha256"]), (HERE / "build_review.py", report["author_sha256"])):
        if sha(path) != expected:
            raise ValueError("Receipt input mismatch")
    vertices = np.load(args.vertices, allow_pickle=False)
    faces = np.load(args.faces, allow_pickle=False)
    counts = verify_stage(stage_path, vertices, faces, config)
    sections = verify_sections(args.review, vertices, faces, config)
    result = {"classification": "source_fidelity_verification_not_engineering_validation", "verified": True,
              "source_sha256": registration["source_sha256"], "run_sha256": sha(args.review / "run.json"),
              "verifier_sha256": sha(__file__), "stage_sha256": sha(stage_path),
              "source_triangles_accounted_once": sum(counts.values()), "groups": counts, "sections": sections,
              "coordinates_and_oriented_faces_exact": True, "no_missing_surface_inferred": True,
              "semantic_body_classification_validated": False, "fitment_validated": False, "manufacturing_released": False}
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
