#!/usr/bin/env python3
"""Validate F4 fluid/electrical routing counts and fail-closed metadata."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pxr import Usd, UsdGeom


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    stage = Usd.Stage.Open(str(args.stage.resolve()), load=Usd.Stage.LoadAll)
    world = stage.GetPrimAtPath("/World") if stage else None
    fluid = stage.GetPrimAtPath("/World/Simulation/Fluids") if stage else None
    electrical = stage.GetPrimAtPath("/World/Simulation/Electrical") if stage else None
    variants = world.GetVariantSets().GetVariantSet("engineVariant") if world else None
    previous_variant = variants.GetVariantSelection() if variants else ""
    if variants:
        variants.SetVariantSelection("917_30_turbo")
    fluid_curves = [prim for prim in Usd.PrimRange(fluid) if prim.IsA(UsdGeom.BasisCurves)] if fluid else []
    electrical_curves = [prim for prim in Usd.PrimRange(electrical) if prim.IsA(UsdGeom.BasisCurves)] if electrical else []
    if variants:
        variants.SetVariantSelection(previous_variant or "type_912_4_5_na")
    checks = {
        "stage_opens": bool(stage),
        "simulation_is_fail_closed": bool(world) and world.GetCustomDataByKey("3dprinting993:systemsSimulationReady") is False,
        "fluid_route_count": len(fluid_curves) == config["acceptance"]["fluid_route_instance_count"],
        "electrical_route_count": len(electrical_curves) == config["acceptance"]["electrical_route_instance_count"],
        "all_routes_provisional": all(prim.GetCustomDataByKey("3dprinting993:simulationReady") is False for prim in fluid_curves + electrical_curves),
        "timeline_preserved": stage.GetEndTimeCode() > stage.GetStartTimeCode(),
    }
    report = {"schema_version": "1.0.0", "status": "passed" if all(checks.values()) else "failed", "checks": checks}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
