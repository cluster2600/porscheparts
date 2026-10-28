"""Add an inspection-only 935 rotor revolution to the hash-pinned USD assembly.

The Z axis, scale, drive connection, and stationary environment are provisional.
No physical joint or operating speed is defined by this animation.
"""

import json
import math
from pathlib import Path
import shutil
import sys

import numpy as np

from compose_flange_witness_usd import digest


COMPOSED_SHA256 = "5f330f4cf071e790b7c026a0ba1bb359c8c5dc19eef8003dfe12c94224bcbac9"
BASE_SHA256 = "22fa354baa2d69d22e21b4677625023259cd529e22708b25aeba0affe87f10ce"
SWEEP_SHA256 = "656c15ff50002192f9df19d2ba2c2888e9666f2471ffd6b5bc5c9f85aab60146"
RECEIPT_SHA256 = "b63b4830d028c3455e7e40e25180f62463057794148b380661483a02f8069a2b"


def run(composed_dir: Path, sweep_path: Path, output: Path) -> None:
    from pxr import Gf, Usd, UsdGeom

    composed_dir, sweep_path, output = (path.resolve() for path in
                                         (composed_dir, sweep_path, output))
    if output.exists() or not output.is_relative_to((Path.cwd() / "work").resolve()):
        raise ValueError("Use a new private work/ output directory")
    composed_path = composed_dir / "assembly-with-flange-witness.usdc"
    base_path = composed_dir / "base-assembly.usdc"
    report_path = composed_dir / "composition-report.json"
    report = json.loads(report_path.read_text())
    if (digest(composed_path) != COMPOSED_SHA256 or digest(base_path) != BASE_SHA256
            or report["composed_usd_sha256"] != COMPOSED_SHA256
            or report["base_usd_sha256"] != BASE_SHA256
            or report["base_component_count"] != 4
            or report["witness_component_count"] != 8
            or report["source_unit_to_mm_verified"] is not False
            or report["manufacturing_authorized"] is not False):
        raise ValueError("Pinned unqualified 935 inspection USD required")
    if digest(sweep_path) != SWEEP_SHA256:
        raise ValueError("Pinned rigid rotor sweep changed")
    sweep = json.loads(sweep_path.read_text())
    if (sweep["schema"] != "935-rigid-rotor-sweep-v1"
            or sweep["native_receipt_sha256"] != RECEIPT_SHA256
            or sweep["samples_per_revolution"] != 240
            or sweep["axis"] != {"origin_native_units": [0, 0, 0],
                                  "direction": [0, 0, 1]}
            or sweep["source_coordinate_unit"] != "uncalibrated_scan_unit"
            or any(sweep[key] is not False for key in
                   ("scale_verified", "axis_verified_on_historical_935",
                    "rotor_drive_mount_defined", "solid_containment_checked",
                    "thermal_or_elastic_changes_checked", "manufacturing_authorized"))):
        raise ValueError("Unqualified Z-axis sweep required")
    for name in ("drive_observed", "provisional_shroud"):
        if (len(sweep["phases"][name]) != 240
                or sweep["summary"][name]["sampled_collision_count"] != 0
                or sweep["summary"][name]["rigid_surface_sweep_separated"] is not True
                or sweep["summary"][name]["lower_bound_distance_native_units"] <= 0):
            raise ValueError("Positive 240-phase rigid surface sweep required")
        for index, phase in enumerate(sweep["phases"][name]):
            if phase["phase_index"] != index or abs(phase["angle_deg"] - 1.5 * index) > 1e-10:
                raise ValueError("Unexpected sweep phase angles")

    output.mkdir(parents=True, mode=0o700)
    copied_base = output / "base-assembly.usdc"
    copied_composed = output / "composed-inspection.usdc"
    shutil.copyfile(base_path, copied_base)
    shutil.copyfile(composed_path, copied_composed)
    if digest(copied_base) != BASE_SHA256 or digest(copied_composed) != COMPOSED_SHA256:
        raise ValueError("USD layer copy changed")
    stage_path = output / "kinematic-inspection.usdc"
    stage = Usd.Stage.CreateNew(str(stage_path))
    stage.GetRootLayer().subLayerPaths = ["composed-inspection.usdc"]
    UsdGeom.SetStageMetersPerUnit(stage, 1)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    stage.SetStartTimeCode(0)
    stage.SetEndTimeCode(240)
    stage.SetTimeCodesPerSecond(60)
    stage.SetFramesPerSecond(60)
    world = stage.GetPrimAtPath("/World")
    rotor = stage.GetPrimAtPath("/World/rotor_candidate")
    if not world.IsValid() or not rotor.IsValid() or not rotor.IsA(UsdGeom.Mesh):
        raise ValueError("Original assembly did not compose")
    stage.SetDefaultPrim(world)
    rotor_override = stage.OverridePrim("/World/rotor_candidate")
    rotor_override.SetCustomData({"classification": "kinematic_inspection_only",
                                  "rigid_sweep_sha256": SWEEP_SHA256,
                                  "axis_verified_on_historical_935": False,
                                  "rotor_drive_mount_defined": False,
                                  "physical_validation": False,
                                  "manufacturing_authorized": False})
    spin = UsdGeom.Xformable(rotor_override).AddRotateZOp(precision=UsdGeom.XformOp.PrecisionDouble)
    for index in range(241):
        spin.Set(1.5 * index, Usd.TimeCode(index))
    stage.GetRootLayer().Save()

    reopened = Usd.Stage.Open(str(stage_path), load=Usd.Stage.LoadNone)
    if (UsdGeom.GetStageMetersPerUnit(reopened) != 1
            or UsdGeom.GetStageUpAxis(reopened) != UsdGeom.Tokens.z
            or reopened.GetStartTimeCode() != 0 or reopened.GetEndTimeCode() != 240
            or reopened.GetTimeCodesPerSecond() != 60
            or reopened.GetDefaultPrim().GetPath().pathString != "/World"):
        raise ValueError("Kinematic USD metadata changed")
    children = {p.GetName() for p in reopened.GetPrimAtPath("/World").GetChildren()}
    if children != {"engine_context", "drive_observed", "rotor_candidate",
                    "provisional_shroud", "inspection"}:
        raise ValueError("Base assembly identities changed")
    if {p.GetName() for p in reopened.GetPrimAtPath("/World/inspection").GetChildren()} != {
            f"flange_opening_{i:02}" for i in range(8)}:
        raise ValueError("PicoGK flange witnesses lost")
    mesh = UsdGeom.Mesh(reopened.GetPrimAtPath("/World/rotor_candidate"))
    points = np.asarray(mesh.GetPointsAttr().Get(), dtype=np.float64)
    candidate = points[np.argmax(np.sum(points[:, :2] ** 2, axis=1))]
    spin_readback = UsdGeom.Xformable(mesh.GetPrim()).GetOrderedXformOps()
    if len(spin_readback) != 1 or spin_readback[0].GetTimeSamples() != list(range(241)):
        raise ValueError("Rotor rotation time samples changed")
    maximum_error = 0.
    for index in range(241):
        angle = math.radians(1.5 * index)
        c, s = math.cos(angle), math.sin(angle)
        expected = np.array([c * candidate[0] - s * candidate[1],
                             s * candidate[0] + c * candidate[1], candidate[2]])
        transform = UsdGeom.XformCache(Usd.TimeCode(index)).GetLocalToWorldTransform(mesh.GetPrim())
        observed = np.asarray(transform.Transform(Gf.Vec3d(*map(float, candidate))))
        maximum_error = max(maximum_error, float(np.linalg.norm(observed - expected)))
    if maximum_error > 1e-8 or digest(copied_base) != BASE_SHA256 or digest(copied_composed) != COMPOSED_SHA256:
        raise ValueError("Rotor time-sample transform or source layer changed")
    result = {"status": "kinematic_inspection_only",
              "base_usd_sha256": BASE_SHA256, "composed_usd_sha256": COMPOSED_SHA256,
              "rigid_sweep_sha256": SWEEP_SHA256, "kinematic_usd_sha256": digest(stage_path),
              "rotor_time_samples": 241, "frames_per_second_for_preview_only": 60,
              "angle_per_frame_deg": 1.5, "maximum_transform_fixture_error_m": maximum_error,
              "sweep_lower_bounds_source_units": {
                  name: sweep["summary"][name]["lower_bound_distance_native_units"]
                  for name in ("drive_observed", "provisional_shroud")},
              "source_unit_to_stage_metre_factor_assumed": .001,
              "source_unit_to_mm_verified": False, "axis_verified_on_historical_935": False,
              "rotor_drive_mount_defined": False, "operating_speed_defined": False,
              "physics_joint_defined": False, "physical_validation": False,
              "manufacturing_authorized": False}
    (output / "kinematic-report.json").write_text(json.dumps(result, indent=2) + "\n")
    for file in output.iterdir():
        file.chmod(0o600)
    print(json.dumps({"status": result["status"], "kinematic_usd_sha256": result["kinematic_usd_sha256"],
                      "maximum_transform_fixture_error_m": maximum_error}))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: compose_kinematic_usd.py COMPOSED_USD_DIR RIGID_SWEEP_REPORT NEW_PRIVATE_OUTPUT")
    run(*(Path(arg) for arg in sys.argv[1:]))
