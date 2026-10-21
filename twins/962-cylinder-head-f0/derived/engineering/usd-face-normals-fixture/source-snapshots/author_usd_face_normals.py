"""Fresh face-normal-only USD derivative; native validation remains separate."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import platform

import numpy as np


# Conservative IEEE binary32 rounding bounds for a normalized vector. Each
# component in [-1, 1] rounds by at most 2**-25; use unit roundoff (2**-24),
# twice that bound, also leaving room for binary64 reference arithmetic.
COMPONENT_BOUND = 2.0 ** -24
VECTOR_BOUND = math.sqrt(3.0) * COMPONENT_BOUND
ANGLE_BOUND_RAD = math.asin(VECTOR_BOUND / (1.0 - VECTOR_BOUND))
MESH = "/Head/Solid"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fresh(path):
    if Path(path).exists() or Path(path).is_symlink():
        raise FileExistsError("Output must be new; preserve previous evidence")


def triangles(points, counts, indices):
    p, c, i = np.asarray(points), np.asarray(counts), np.asarray(indices)
    if (p.dtype != np.dtype("float32") or p.ndim != 2 or p.shape[1] != 3
            or not len(p) or not np.isfinite(p).all()):
        raise ValueError("Finite binary32 points required")
    if (c.ndim != 1 or i.ndim != 1 or c.dtype.kind not in "iu"
            or i.dtype.kind not in "iu" or not len(c) or not (c == 3).all()
            or len(i) != 3 * len(c) or (i < 0).any() or (i >= len(p)).any()):
        raise ValueError("Nonempty triangular in-range ordered topology required")
    return p, i.reshape(-1, 3)


def face_normals(points, counts, indices):
    p, faces = triangles(points, counts, indices)
    t = p[faces].astype(np.float64)
    cross = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    length = np.linalg.norm(cross, axis=1)
    if not np.isfinite(cross).all() or not np.isfinite(length).all() or (length <= 0).any():
        raise ValueError("Nonfinite or degenerate face; no geometry repair permitted")
    return (cross / length[:, None]).astype(np.float32)


def assess_normals(points, counts, indices, normals):
    p, faces = triangles(points, counts, indices)
    n = np.asarray(normals)
    if n.dtype != np.dtype("float32") or n.shape != (len(faces), 3) or not np.isfinite(n).all():
        raise ValueError("One finite binary32 normal per face required")
    # Recompute from readback geometry with explicit determinants, independently
    # of the author's np.cross call. No sampling or vertex-normal averaging.
    t = p[faces].astype(np.float64)
    a, b = t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]
    cross = np.column_stack((a[:, 1] * b[:, 2] - a[:, 2] * b[:, 1],
                             a[:, 2] * b[:, 0] - a[:, 0] * b[:, 2],
                             a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]))
    length = np.sqrt(np.sum(cross * cross, axis=1))
    if not np.isfinite(length).all() or (length <= 0).any():
        raise ValueError("Nonfinite or degenerate readback face")
    reference = cross / length[:, None]
    if n.tobytes() != reference.astype(np.float32).tobytes():
        raise ValueError("Normal bytes differ from independently rounded face reference")
    stored = n.astype(np.float64)
    dot = np.sum(reference * stored, axis=1)
    unit_error = np.abs(np.sqrt(np.sum(stored * stored, axis=1)) - 1.0)
    angle = np.arctan2(np.linalg.norm(np.cross(reference, stored), axis=1), dot)
    component_error = np.abs(stored - reference)
    if ((dot <= 0).any() or (component_error > COMPONENT_BOUND).any()
            or (unit_error > VECTOR_BOUND).any() or (angle > ANGLE_BOUND_RAD).any()):
        raise ValueError("Normal winding or predeclared quantization bound failed")
    return {"faces_checked": len(faces), "max_component_error": float(component_error.max()),
            "max_unit_length_error": float(unit_error.max()),
            "max_angle_radians": float(angle.max()),
            "component_bound": COMPONENT_BOUND, "unit_length_bound": VECTOR_BOUND,
            "angle_bound_radians": ANGLE_BOUND_RAD,
            "reference_binary32_bytes_equal": True}


def open_source(path, expected):
    if sha(path) != expected:
        raise ValueError("Source hash drift before output creation")
    from pxr import Usd, UsdGeom
    if Usd.GetVersion() != (0, 25, 5):
        raise ValueError("Recorded OpenUSD 25.5 runtime required")
    stage = Usd.Stage.Open(str(path), Usd.Stage.LoadAll)
    if not stage:
        raise ValueError("Source USD did not open")
    root = stage.GetRootLayer()
    single_layer(stage)
    mesh = UsdGeom.Mesh(stage.GetPrimAtPath(MESH))
    if (not mesh or str(stage.GetDefaultPrim().GetPath()) != "/Head"
            or [str(p.GetPath()) for p in stage.Traverse()] != ["/Head", MESH]
            or UsdGeom.GetStageUpAxis(stage) != "Z"
            or UsdGeom.GetStageMetersPerUnit(stage) != 0.001
            or mesh.GetSubdivisionSchemeAttr().Get() != "none"
            or mesh.GetOrientationAttr().Get() != "rightHanded"):
        raise ValueError("Expected original Z/mm unsubdivided rightHanded head stage")
    if (root.GetAttributeAtPath(MESH + ".normals")
            or any(prim.HasProperty("primvars:normals") for prim in stage.Traverse())
            or any(attr.GetNumTimeSamples() for prim in stage.Traverse()
                   for attr in prim.GetAttributes())):
        raise ValueError("Existing normals, overriding primvar or time samples refused")
    if not np.array_equal(np.asarray(UsdGeom.XformCache().GetLocalToWorldTransform(
            mesh.GetPrim())), np.eye(4)):
        raise ValueError("Identity world frame required")
    return stage, mesh


def single_layer(stage):
    if (stage.GetRootLayer().subLayerPaths or not stage.GetSessionLayer().empty
            or len([v for v in stage.GetUsedLayers()
                    if v != stage.GetSessionLayer()]) != 1):
        raise ValueError("Single root layer and empty session required")


def geometry(mesh):
    return (np.asarray(mesh.GetPointsAttr().Get()),
            np.asarray(mesh.GetFaceVertexCountsAttr().Get()),
            np.asarray(mesh.GetFaceVertexIndicesAttr().Get()))


def author(source, output, source_sha256):
    source, output = Path(source), Path(output)
    fresh(output)
    stage, mesh = open_source(source, source_sha256)
    from pxr import Sdf, Usd, UsdGeom, Vt
    normals = face_normals(*geometry(mesh))
    layer = Sdf.Layer.CreateAnonymous("face-normals.usda")
    layer.TransferContent(stage.GetRootLayer())
    derivative = Usd.Stage.Open(layer)
    target = UsdGeom.Mesh(derivative.GetPrimAtPath(MESH))
    if (not target.CreateNormalsAttr().Set(Vt.Vec3fArray.FromNumpy(normals))
            or not target.SetNormalsInterpolation(UsdGeom.Tokens.uniform)):
        raise ValueError("Explicit face normals/interpolation authoring failed")
    if sha(source) != source_sha256:
        raise ValueError("Source hash drift before export")
    with output.open("xb"):
        pass
    if not layer.Export(str(output), args={"format": "usdc"}):
        raise ValueError("Fresh native USDC export failed")
    if sha(source) != source_sha256:
        raise ValueError("Source changed during derivative export")
    return {"status": "face_normals_authored_independent_check_and_validation_required",
            "source_sha256": source_sha256, "source_unchanged": True,
            "output_sha256": sha(output), "output_bytes": output.stat().st_size,
            "normal_count": len(normals), "interpolation": "uniform",
            "writer_sha256": sha(__file__), "OpenUSD_version": Usd.GetVersion(),
            "python_version": platform.python_version(),
            "property_assignment_intent": "skip", "manufacturing_authorized": False}


def check(source, output, source_sha256, output_sha256):
    source, output = Path(source), Path(output)
    original, mesh = open_source(source, source_sha256)
    from pxr import Sdf, Usd, UsdGeom, Vt
    if sha(output) != output_sha256:
        raise ValueError("Derivative hash drift")
    stage = Usd.Stage.Open(str(output), Usd.Stage.LoadAll)
    if not stage:
        raise ValueError("Derivative USD did not open")
    single_layer(stage)
    result = UsdGeom.Mesh(stage.GetPrimAtPath(MESH))
    if not result or result.GetNormalsInterpolation() != "uniform":
        raise ValueError("Uniform mesh normals required")
    before, after = geometry(mesh), geometry(result)
    if any(a.dtype != b.dtype or a.shape != b.shape or a.tobytes() != b.tobytes()
           for a, b in zip(before, after)):
        raise ValueError("Ordered geometry bytes changed")
    assessment = assess_normals(*after, np.asarray(result.GetNormalsAttr().Get()))
    # Compare the full canonical Sdf content against an original-layer copy
    # with precisely the checked normals/interpolation added. Extra metadata,
    # connections or samples on the normals property are therefore refused too.
    layer = Sdf.Layer.CreateAnonymous("independent-property-check.usda")
    layer.TransferContent(original.GetRootLayer())
    # Keep this stage alive while editing its prim.
    expected_stage = Usd.Stage.Open(layer)
    expected = UsdGeom.Mesh(expected_stage.GetPrimAtPath(MESH))
    if (not expected.CreateNormalsAttr().Set(Vt.Vec3fArray.FromNumpy(
            np.asarray(result.GetNormalsAttr().Get())))
            or not expected.SetNormalsInterpolation(UsdGeom.Tokens.uniform)
            or layer.ExportToString() != stage.GetRootLayer().ExportToString()):
        raise ValueError("Authored properties changed beyond normals/interpolation")
    if sha(source) != source_sha256 or sha(output) != output_sha256:
        raise ValueError("Source or derivative changed during read-only check")
    return {"status": "full_ordered_geometry_properties_and_face_normals_pass",
            "source_sha256": source_sha256, "output_sha256": output_sha256,
            "ordered_geometry_bytes_equal": True, "all_other_authored_content_equal": True,
            "normals": assessment, "checker_sha256": sha(__file__),
            "source_unchanged": True, "output_unchanged": True,
            "minimum_or_full_validator_executed": False,
            "property_assignment_intent": "skip", "manufacturing_authorized": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["author", "check"])
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--output-sha256")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    fresh(args.report)
    if args.mode == "check" and not args.output_sha256:
        parser.error("check requires --output-sha256")
    result = (author(args.source, args.output, args.source_sha256)
              if args.mode == "author" else check(args.source, args.output,
                                                 args.source_sha256, args.output_sha256))
    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    with args.report.open("x", encoding="utf-8") as stream:
        stream.write(text)
    print(text, end="")


if __name__ == "__main__":
    main()
