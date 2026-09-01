#!/usr/bin/env python3
"""Validate the fail-closed 917 Omniverse test-bench layer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pxr import Usd, UsdPhysics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", type=Path)
    parser.add_argument("--bench", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    bench = json.loads(args.bench.read_text(encoding="utf-8"))
    stage = Usd.Stage.Open(str(args.stage.resolve()), load=Usd.Stage.LoadAll)
    world = stage.GetPrimAtPath("/World") if stage else None
    required = ["Bedplate", "Dynamometer", "DynoCoupling", "Battery", "OilReservoir", "FuelSupply", "EmergencyStop"]
    checks = {
        "stage_opens": bool(stage),
        "world_preserved": bool(world),
        "fired_run_disabled": bool(world) and world.GetCustomDataByKey("3dprinting993:firedRunAuthorized") is False,
        "required_bench_components": all(stage.GetPrimAtPath(f"/World/TestBench/{name}") for name in required),
        "four_mount_proxies": all(stage.GetPrimAtPath(f"/World/TestBench/EngineMount_{index:02d}") for index in range(1, 5)),
        "coupling_kinematic": UsdPhysics.RigidBodyAPI(stage.GetPrimAtPath("/World/TestBench/DynoCoupling")).GetKinematicEnabledAttr().Get() is True,
        "timeline_preserved": stage.GetEndTimeCode() > stage.GetStartTimeCode(),
    }
    report = {
        "schema_version": "1.0.0",
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "maximum_authorized_stage": bench["acceptance"]["maximum_authorized_stage"],
        "critical_blockers": bench["critical_blockers"],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
