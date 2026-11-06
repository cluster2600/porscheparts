#!/usr/bin/env python3
"""Exact private native-index transport to binary USD, with strict readback.

No repair, rescaling, simplification, normals, material or physics assignment is
performed. A successful transport is not geometry or engineering admission.
Run with the retained OpenUSD/NumPy runtime; all large outputs stay private.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

import numpy as np
from pxr import Usd, UsdGeom, UsdUtils, Vt


CHUNK = 250_000
PRIM = "/AssumedCell/NativeBoundary"
PRIMARY_REFERENCES = [
    "https://openusd.org/release/toolset.html",
    "https://openusd.org/release/api/class_usd_geom_mesh.html",
    "https://docs.omniverse.nvidia.com/dev-guide/latest/programmer_ref/usd/data-types/convert-vtarray-numpy.html",
]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(data)
    return digest.hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def read_inputs(args):
    paths = {name: Path(getattr(args, name)) for name in
             ("model", "native_report", "index_report", "vertices", "triangles")}
    hashes = {name: sha(path) for name, path in paths.items()}
    require(hashes["model"] == args.expected_model_sha256,
            "Model bytes differ from the explicitly selected revision")
    model, native, index = [json.loads(paths[name].read_text()) for name in
                            ("model", "native_report", "index_report")]
    require(model["units"] == "mm" and model["status"] == "assumed",
            "Only explicitly assumed millimetre geometry is in scope")
    require(native["geometry_sha256"] == hashes["model"],
            "Native report does not bind the selected canonical model")
    require(all(isinstance(native[key], str) and len(native[key]) == 64 and
                all(c in "0123456789abcdef" for c in native[key])
                for key in ("vdb_sha256", "stl_sha256")),
            "Native source hashes are missing or malformed")
    require(index["source_vdb_sha256"] == native["vdb_sha256"] and
            index["source_stl_sha256"] == native["stl_sha256"],
            "Native/indexed source hash chain differs")
    require(index["reextracted_stl_byte_identical"] is True and
            index["reextracted_stl_sha256"] == native["stl_sha256"],
            "Indexed report does not preserve the native extraction")
    require(hashes["vertices"] == index["vertices_f32_sha256"] and
            hashes["triangles"] == index["triangles_i32_sha256"],
            "Actual indexed arrays do not match their source report")
    nv, nt = index["vertex_count"], index["triangle_count"]
    require(type(nv) is int and type(nt) is int and nv > 0 and nt > 0,
            "Invalid indexed counts")
    require(native["native_output_triangles"] == nt,
            "Native and indexed triangle counts differ")
    require(paths["vertices"].stat().st_size == 12 * nv and
            paths["triangles"].stat().st_size == 12 * nt,
            "Binary array lengths differ from the declared format/counts")
    vertices = np.memmap(paths["vertices"], dtype="<f4", mode="r", shape=(nv, 3))
    triangles = np.memmap(paths["triangles"], dtype="<i4", mode="r", shape=(nt, 3))
    binding = {"actual_input_sha256": hashes,
               "canonical_model_sha256": hashes["model"],
               "referenced_native_VDB_sha256": native["vdb_sha256"],
               "referenced_native_STL_sha256": native["stl_sha256"],
               "raw_VDB_STL_rehashed_by_this_exporter": False,
               "source_probe_failures_retained": index.get("finite_occupancy_probe_failures"),
               "scope": "Report hash consistency and actual model/indexed-array bytes; no upstream physical admission"}
    return paths, hashes, binding, vertices, triangles


def inspect_arrays(vertices, triangles):
    """Visit every point/index/triangle, with bounded temporary storage."""
    result = {"vertices": len(vertices), "triangles": len(triangles),
              "nonfinite_vertices": 0, "out_of_range_triangles": 0,
              "zero_area_triangles": 0, "nonfinite_cross_product_triangles": 0,
              "cross_norm_at_most_1e_minus_8_mm2": 0,
              "zero_area_first_source_triangle_ids": [],
              "arithmetic": "float64 cross products of unchanged float32 source coordinates",
              "zero_area_rule": "All three computed cross-product components equal zero; no positive tolerance or repair",
              "source_triangle_ids": "Original zero-based row indices"}
    bounds = np.array([[np.inf] * 3, [-np.inf] * 3], dtype=np.float64)
    for start in range(0, len(vertices), CHUNK):
        points = np.asarray(vertices[start:start + CHUNK])
        finite = np.isfinite(points).all(axis=1)
        result["nonfinite_vertices"] += int((~finite).sum())
        if finite.any():
            bounds[0] = np.minimum(bounds[0], points[finite].min(axis=0))
            bounds[1] = np.maximum(bounds[1], points[finite].max(axis=0))
    for start in range(0, len(triangles), CHUNK):
        indices = np.asarray(triangles[start:start + CHUNK])
        valid = ((indices >= 0) & (indices < len(vertices))).all(axis=1)
        result["out_of_range_triangles"] += int((~valid).sum())
        ids = np.flatnonzero(valid)
        if not len(ids):
            continue
        points = np.asarray(vertices[indices[valid]], dtype=np.float64)
        cross = np.cross(points[:, 1] - points[:, 0], points[:, 2] - points[:, 0])
        finite = np.isfinite(cross).all(axis=1)
        zero = finite & (cross == 0).all(axis=1)
        result["nonfinite_cross_product_triangles"] += int((~finite).sum())
        result["zero_area_triangles"] += int(zero.sum())
        result["cross_norm_at_most_1e_minus_8_mm2"] += int(
            (finite & (np.einsum("ij,ij->i", cross, cross) <= 1e-16)).sum())
        remaining = 32 - len(result["zero_area_first_source_triangle_ids"])
        result["zero_area_first_source_triangle_ids"].extend(
            (start + ids[np.flatnonzero(zero)[:remaining]]).tolist())
    result["bounds_mm"] = bounds.tolist() if np.isfinite(bounds).all() else None
    result["passed"] = not any(result[key] for key in
        ("nonfinite_vertices", "out_of_range_triangles", "zero_area_triangles",
         "nonfinite_cross_product_triangles"))
    return result


def validate_raw_rejection(path, binding, checks):
    """Allow only a documented zero-area defect to be preserved, never fixed."""
    require(checks["zero_area_triangles"] > 0 and not any(checks[key] for key in
        ("nonfinite_vertices", "out_of_range_triangles", "nonfinite_cross_product_triangles")),
        "Raw diagnostic transport only permits finite, in-range zero-area faces")
    receipt = json.loads(Path(path).read_text())
    require(receipt["status"] == "rejected_native_triangle_quality_preserved_unmodified" and
            receipt["geometry_admitted"] is False and receipt["quality_admitted"] is False,
            "Raw diagnostic mode requires an explicit geometry-quality rejection")
    require(receipt["binding"]["actual_input_sha256"] == binding["actual_input_sha256"] and
            receipt["native_stl_sha256"] == binding["referenced_native_STL_sha256"] and
            receipt["binding"]["referenced_native_VDB_sha256"] == binding["referenced_native_VDB_sha256"],
            "Quality rejection does not bind these exact original inputs")
    require(receipt["zero_area_triangle_count"] == checks["zero_area_triangles"] and
            receipt["checked_vertex_count"] == checks["vertices"] and
            receipt["checked_triangle_count"] == checks["triangles"],
            "Quality rejection counts differ from the complete current array scan")
    return sha(path)


def author_stage(path, vertices, triangles, bounds, binding):
    stage = Usd.Stage.CreateNew(str(path))
    require(bool(stage), "USD stage creation failed")
    UsdGeom.SetStageMetersPerUnit(stage, 0.001)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    root = UsdGeom.Xform.Define(stage, "/AssumedCell")
    stage.SetDefaultPrim(root.GetPrim())
    raw = binding.get("raw_diagnostic_transport", False)
    root.GetPrim().SetCustomDataByKey("studyStatus", "unqualified_raw_native_diagnostic" if raw
                                    else "assumed_geometry_transport_only")
    root.GetPrim().SetCustomDataByKey("canonicalModelSHA256", binding["canonical_model_sha256"])
    if raw:
        root.GetPrim().SetCustomDataByKey("qualityAdmitted", False)
        root.GetPrim().SetCustomDataByKey("zeroAreaTriangleCount", binding["zero_area_triangles"])
        root.GetPrim().SetCustomDataByKey("qualityRejectionSHA256", binding["quality_rejection_sha256"])
    mesh = UsdGeom.Mesh.Define(stage, PRIM)
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mesh.CreateOrientationAttr(UsdGeom.Tokens.rightHanded)
    mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(vertices))
    mesh.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(triangles), 3, dtype=np.int32)))
    mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(triangles.reshape(-1)))
    mesh.CreateExtentAttr(Vt.Vec3fArray.FromNumpy(np.asarray(bounds, dtype=np.float32)))
    require(stage.GetRootLayer().Save(), "USD binary save failed")
    # Release the authored stage before full readback to avoid retaining two
    # separate copies of its large array values in the bounded runtime.
    mesh = root = stage = None
    gc.collect()


def compare_bytes(actual, expected, message):
    require(actual.shape == expected.shape and actual.dtype == expected.dtype,
            message + ": shape/type differs")
    a, b = actual.view(np.uint8).reshape(-1), expected.view(np.uint8).reshape(-1)
    block = CHUNK * 12
    for start in range(0, len(a), block):
        require(np.array_equal(a[start:start + block], b[start:start + block]), message)


def inspect_stage(path, vertices, triangles, bounds):
    stage = Usd.Stage.Open(str(path), Usd.Stage.LoadNone)
    require(bool(stage), "USD reopen failed")
    require(stage.GetRootLayer().GetFileFormat().formatId == "usdc", "Output is not binary USDC")
    require(stage.GetDefaultPrim().GetPath().pathString == "/AssumedCell", "Default prim differs")
    require(UsdGeom.GetStageMetersPerUnit(stage) == 0.001 and
            UsdGeom.GetStageUpAxis(stage) == UsdGeom.Tokens.z, "Stage units/up-axis differ")
    require([str(p.GetPath()) for p in stage.Traverse()] == ["/AssumedCell", PRIM],
            "Unexpected stage prims")
    for prim in stage.Traverse():
        require(not prim.GetAppliedSchemas(), "Unexpected applied schema/physics")
    mesh = UsdGeom.Mesh.Get(stage, PRIM)
    require(mesh.GetSubdivisionSchemeAttr().Get() == UsdGeom.Tokens.none,
            "Unexpected subdivision")
    require(not mesh.GetNormalsAttr().HasAuthoredValueOpinion(),
            "Unexpected authored normals; raw defects must not receive fake normals")
    require(all(not UsdGeom.Xformable(prim).GetOrderedXformOps() for prim in stage.Traverse()),
            "Unexpected coordinate transform")
    points_value, indices_value, counts_value = (mesh.GetPointsAttr().Get(),
        mesh.GetFaceVertexIndicesAttr().Get(), mesh.GetFaceVertexCountsAttr().Get())
    points, indices, counts = map(np.asarray, (points_value, indices_value, counts_value))
    compare_bytes(points, vertices, "USD point bits differ from the original arrays")
    compare_bytes(indices.reshape((-1, 3)), triangles, "USD index bits differ from original arrays")
    require(counts.shape == (len(triangles),) and counts.dtype == np.dtype("int32") and
            bool(np.all(counts == 3)), "USD face counts differ")
    expected_bounds = np.asarray(bounds, dtype=np.float32)
    computed = np.stack((points.min(axis=0), points.max(axis=0)))
    compare_bytes(computed, expected_bounds, "USD point bounds differ")
    compare_bytes(np.asarray(mesh.GetExtentAttr().Get()), expected_bounds, "USD authored extent differs")
    topology = UsdGeom.Mesh.ValidateTopology(indices_value, counts_value, len(points))
    require(bool(topology[0] if isinstance(topology, tuple) else topology), "Official USD topology check failed")
    return stage, {"point_bits_equal": True, "index_bits_equal": True,
                   "counts_equal": True, "bounds_equal": True,
                   "topology_index_range_and_counts_passed": True,
                   "binary_usdc": True, "no_applied_schemas": True,
                   "no_authored_normals": True, "no_coordinate_transform": True,
                   "metersPerUnit": 0.001, "upAxis": "Z", "defaultPrim": "/AssumedCell"}


def official_checker(path):
    checker = UsdUtils.ComplianceChecker(arkit=False, skipARKitRootLayerCheck=True)
    checker.CheckCompliance(str(path))
    result = {"implementation": "OpenUSD UsdUtils.ComplianceChecker",
              "errors": list(checker.GetErrors()),
              "failed_checks": list(checker.GetFailedChecks()),
              "warnings": list(checker.GetWarnings()),
              "scope": "Generic USD software checks only; not SimReady, Kit, GPU or engineering validation"}
    result["passed"] = not result["errors"] and not result["failed_checks"]
    return result


def export_checked(output, vertices, triangles, bounds, binding):
    path, flat = output / "native-cell.usdc", output / "native-cell-flattened.usdc"
    author_stage(path, vertices, triangles, bounds, binding)
    stage, readback = inspect_stage(path, vertices, triangles, bounds)
    # This is the official flatten operation used by usdcat --flatten, saving
    # directly as a crate rather than serializing millions of values to text.
    layer = stage.Flatten()
    require(layer.Export(str(flat)), "Flattened binary export failed")
    stage = layer = None
    gc.collect()
    stage, flattened_readback = inspect_stage(flat, vertices, triangles, bounds)
    stage = None
    gc.collect()
    checks = {"original": official_checker(path), "flattened": official_checker(flat)}
    return {"readback": readback, "flattened_readback": flattened_readback,
            "official_checker": checks,
            "artifacts": {p.name: {"sha256": sha(p), "bytes": p.stat().st_size}
                          for p in (path, flat)},
            "passed": all(c["passed"] for c in checks.values())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("model", "native-report", "index-report", "vertices", "triangles", "output",
                 "expected-model-sha256"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--raw-diagnostic-transport", action="store_true",
                        help="Preserve documented native zero-area faces; geometry quality remains rejected")
    parser.add_argument("--quality-rejection", help="Exact source-bound native-quality-rejection.json")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=False, exist_ok=False)
    started = time.monotonic()
    report = {"classification": "native_indexed_USDC_transport_not_engineering_validation",
              "generator_sha256": sha(__file__), "status": "running",
              "runtime": {"Python": platform.python_version(), "NumPy": np.__version__,
                          "OpenUSD": list(Usd.GetVersion()), "platform": platform.platform()},
              "primary_references": PRIMARY_REFERENCES,
              "physical_validation": False, "manufacturing_authorized": False,
              "Omniverse_Kit_or_GPU_executed": False, "geometry_repaired": False,
              "quality_admitted": False, "raw_diagnostic_transport": args.raw_diagnostic_transport}
    try:
        paths, hashes, binding, vertices, triangles = read_inputs(args)
        report["binding"] = binding
        report["array_preflight"] = inspect_arrays(vertices, triangles)
        write(output / "array-preflight.json", report["array_preflight"])
        require(bool(args.quality_rejection) == args.raw_diagnostic_transport,
                "Raw diagnostic flag and a bound quality-rejection receipt must be provided together")
        if args.raw_diagnostic_transport:
            rejection = Path(args.quality_rejection)
            rejection_sha = validate_raw_rejection(rejection, binding, report["array_preflight"])
            paths["quality_rejection"], hashes["quality_rejection"] = rejection, rejection_sha
            binding.update({"raw_diagnostic_transport": True,
                            "quality_rejection_sha256": rejection_sha,
                            "zero_area_triangles": report["array_preflight"]["zero_area_triangles"]})
            report["strict_array_quality_gate_still_failed"] = not report["array_preflight"]["passed"]
        else:
            require(report["array_preflight"]["passed"],
                    "Original arrays contain invalid values/indices or zero-area triangles; no USD authored and no repair")
        report["export"] = export_checked(output, vertices, triangles,
                                            report["array_preflight"]["bounds_mm"], binding)
        require(all(sha(path) == hashes[name] for name, path in paths.items()),
                "An input changed during transport/validation")
        report["inputs_unchanged"] = True
        report["status"] = (("passed_raw_diagnostic_transport_quality_rejected" if args.raw_diagnostic_transport
                             else "passed_transport_only") if report["export"]["passed"]
                            else "failed_official_checker")
    except Exception as error:
        report["status"] = "failed_closed"
        report["error"] = type(error).__name__ + ": " + str(error)
    report["elapsed_seconds"] = time.monotonic() - started
    write(output / "report.json", report)
    print(json.dumps({"status": report["status"], "elapsed_seconds": report["elapsed_seconds"]}))
    return 0 if report["status"] in ("passed_transport_only",
                                    "passed_raw_diagnostic_transport_quality_rejected") else 1


if __name__ == "__main__":
    sys.exit(main())
