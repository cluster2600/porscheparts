#!/usr/bin/env python3
"""Compose the existing unmeasured reference, then check units and export round-trip."""
import argparse
import hashlib
import json
from pathlib import Path

from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade, UsdUtils, UsdValidation


def build(output):
    source = output.parent.parent / "results/reference/reference.usdz"
    reference = Usd.Stage.Open(str(source))
    if not reference or UsdGeom.GetStageMetersPerUnit(reference) != 1 or UsdGeom.GetStageUpAxis(reference) != "Z":
        raise ValueError("Reference must already use metres and Z up")
    if output.exists():
        raise FileExistsError(output)
    stage = Usd.Stage.CreateNew(str(output))
    root = UsdGeom.Xform.Define(stage, "/FanProgram").GetPrim()
    stage.SetDefaultPrim(root)
    UsdGeom.SetStageMetersPerUnit(stage, 1.)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    stage.SetTimeCodesPerSecond(1.)
    stage.SetFramesPerSecond(24.)
    root.SetCustomData({"status": "unmeasured_parametric_reference_only", "programRecord": "program.json",
        "scanIncluded": False, "manufacturingAuthorized": False, "digitalTwinValidated": False,
        "sourceReferenceSHA256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "geometryUnitsBeforeOriginalExport": "mm", "sourceExportScale": 0.001,
        "axis": "geometric_model_positive_Z_not_a_measured_vehicle_datum",
        "timeUnit": "seconds", "rotationAnimated": False, "rpmToRadPerSecond": "rpm*pi/30",
        "rpmToUsdPhysicsDegreesPerSecond": "rpm*6", "cfdStatus": "PR105_final_2000_iterations_rejected_convergence"})
    prim = UsdGeom.Xform.Define(stage, "/FanProgram/Reference").GetPrim()
    prim.GetReferences().AddReference("../results/reference/reference.usdz")
    material = UsdShade.Material.Define(stage, "/FanProgram/Materials/AlSi10MgCandidate")
    material.GetPrim().SetCustomData({"qualification": "unqualified_candidate_visual_shader_only"})
    shader = UsdShade.Shader.Define(stage, material.GetPath().AppendChild("Surface"))
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(.64, .68, .73))
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(1.)
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(.4)
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    UsdShade.MaterialBindingAPI.Apply(stage.GetPrimAtPath("/FanProgram/Reference/Rotor")).Bind(material)
    UsdGeom.Scope.Define(stage, "/FanProgram/Results")
    stage.GetPrimAtPath("/FanProgram/Results").SetCustomData({"record": "../results/program-20261003/",
        "fieldsAttached": False, "reason": "no historical field transferred to another geometry"})
    stage.GetRootLayer().Save()
    output.write_text(output.read_text().rstrip() + "\n")
    expected = json.loads((source.parent / "validation.json").read_text())["geometry_checks"]["rotor"]["bounds_mm"]
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_])
    box = cache.ComputeWorldBound(stage.GetPrimAtPath("/FanProgram/Reference/Rotor")).ComputeAlignedRange()
    bounds = [list(box.GetMin()), list(box.GetMax())]
    errors = [abs(bounds[i][j] - expected[i][j] * .001) for i in range(2) for j in range(3)]
    # Reduction changes extrema slightly. This checks factor/axes against the stored model, not a real part.
    if max(errors) > 1e-5:
        raise ValueError("Unexpected reference scale or transformed bounds")
    layers, assets, unresolved = UsdUtils.ComputeAllDependencies(str(output))
    if unresolved:
        raise ValueError(f"Unresolved dependencies: {unresolved}")
    findings = UsdValidation.ValidationContext(UsdValidation.ValidationRegistry().GetOrLoadAllValidators()).Validate(stage)
    if findings:
        raise ValueError([v.GetMessage() for v in findings])
    reopened = Usd.Stage.Open(str(output))
    if not reopened or UsdGeom.GetStageMetersPerUnit(reopened) != 1:
        raise ValueError("Export round-trip failed")
    return {"status": "passed_usd_composition_units_and_model_roundtrip", "usd_version": list(Usd.GetVersion()),
        "source_reference_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "asset_sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "meters_per_unit": 1,
        "up_axis": "Z", "time_codes_per_second": 1, "rotor_bounds_m": bounds,
        "maximum_roundtrip_model_bound_error_m": max(errors), "model_bound_tolerance_m": 1e-5,
        "unresolved_dependencies": [], "openusd_validator_findings": [], "scan_included": False,
        "physical_accuracy_verified": False, "simready_profile_validated": False,
        "new_rtx_render_executed": False, "digital_twin_validated": False}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("output", type=Path)
    ap.add_argument("report", type=Path)
    args = ap.parse_args()
    result = build(args.output)
    with args.report.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(result["status"])
