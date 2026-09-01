#!/usr/bin/env python3
"""Validate the F0 composition contract without claiming SimReady conformance."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pxr import Usd, UsdGeom, UsdPhysics


def check_stage(path: Path, minimum_meshes: int) -> tuple[Usd.Stage, list[dict[str, object]]]:
    stage = Usd.Stage.Open(str(path), load=Usd.Stage.LoadAll)
    direct_meshes = [prim for prim in stage.TraverseAll() if prim.IsA(UsdGeom.Mesh)]
    prototype_meshes = [
        prim
        for prototype in stage.GetPrototypes()
        for prim in Usd.PrimRange(prototype)
        if prim.IsA(UsdGeom.Mesh)
    ]
    mesh_count = len(direct_meshes) + len(prototype_meshes)
    checks = [
        {"name": f"{path.stem}_opens", "passed": bool(stage)},
        {"name": f"{path.stem}_default_prim", "passed": bool(stage.GetDefaultPrim())},
        {"name": f"{path.stem}_z_up", "passed": UsdGeom.GetStageUpAxis(stage) == UsdGeom.Tokens.z},
        {"name": f"{path.stem}_millimetres", "passed": UsdGeom.GetStageMetersPerUnit(stage) == 0.001},
        {
            "name": f"{path.stem}_mesh_count",
            "passed": mesh_count >= minimum_meshes,
            "mesh_count": mesh_count,
            "direct_mesh_count": len(direct_meshes),
            "prototype_mesh_count": len(prototype_meshes),
        },
    ]
    return stage, checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stages", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    engine_path = args.stages / "917-engine-assembly-f0.usda"
    rig_path = args.stages / "993-935-valvetrain-test-rig-f0.usda"
    overview_path = args.stages / "engine-research-overview-f0.usda"
    engine, checks = check_stage(engine_path, 1)
    rig, rig_checks = check_stage(rig_path, 4)
    overview, overview_checks = check_stage(overview_path, 5)
    checks.extend(rig_checks)
    checks.extend(overview_checks)

    expected_lifts = {"lift_0_0mm", "lift_2_0mm", "lift_5_0mm", "lift_10_0mm"}
    valve_details = []
    for prim in rig.GetPrimAtPath("/World/Valves").GetChildren():
        variants = prim.GetVariantSets()
        lift = variants.GetVariantSet("liftStudy")
        material = variants.GetVariantSet("materialStudy")
        detail = {
            "path": str(prim.GetPath()),
            "lift_variants": lift.GetVariantNames(),
            "lift_selection": lift.GetVariantSelection(),
            "material_variants": material.GetVariantNames(),
            "material_selection": material.GetVariantSelection(),
            "instanceable": prim.IsInstanceable(),
        }
        valve_details.append(detail)
        checks.extend(
            [
                {
                    "name": f"{prim.GetName()}_lift_variants",
                    "passed": set(lift.GetVariantNames()) == expected_lifts,
                },
                {
                    "name": f"{prim.GetName()}_default_lift",
                    "passed": lift.GetVariantSelection() == "lift_0_0mm",
                },
                {
                    "name": f"{prim.GetName()}_material_variants",
                    "passed": bool(material.GetVariantNames() and material.GetVariantSelection()),
                },
                {"name": f"{prim.GetName()}_instanceable", "passed": prim.IsInstanceable()},
            ]
        )

    rigid_bodies = [
        str(prim.GetPath())
        for prim in overview.TraverseAll()
        if prim.HasAPI(UsdPhysics.RigidBodyAPI)
    ]
    checks.append(
        {
            "name": "f0_has_no_unreviewed_rigid_bodies",
            "passed": not rigid_bodies,
            "rigid_bodies": rigid_bodies,
        }
    )
    report = {
        "status": "passed" if all(item["passed"] for item in checks) else "failed",
        "classification": "F0_research_assembly_not_simready_conformance",
        "checks": checks,
        "valves": valve_details,
        "physics_assignment": "intentionally_absent",
        "next_step": "render on OVRTX, then segment and measure real component datums",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
