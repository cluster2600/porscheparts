#!/usr/bin/env python3
"""Validate the fail-closed F5 917 starter, dyno and oil-prime support layer."""

from __future__ import annotations

import argparse
import json
from collections import Counter
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
    root = stage.GetPrimAtPath("/World/TestBench/StartSupportF5") if stage else None
    prims = list(Usd.PrimRange(root)) if root else []
    counts = Counter(prim.GetCustomDataByKey("3dprinting993:supportId") for prim in prims)
    counts.pop(None, None)
    expected = {item["id"]: item["count"] for item in config["support_components"]}
    routes = [prim for prim in prims if prim.IsA(UsdGeom.BasisCurves)]
    checks = {
        "stage_opens": bool(stage),
        "f4_bench_preserved": bool(stage) and bool(stage.GetPrimAtPath("/World/TestBench/Dynamometer")),
        "f4_systems_preserved": bool(stage) and bool(stage.GetPrimAtPath("/World/Simulation/Fluids")),
        "support_counts": dict(counts) == expected,
        "four_support_routes": len(routes) == 4,
        "oil_prime_topology_complete": bool(world) and world.GetCustomDataByKey("3dprinting993:oilPrimeTopologyComplete") is True,
        "oil_prime_solver_blocked": bool(world) and world.GetCustomDataByKey("3dprinting993:oilPrimeSolverReady") is False,
        "starter_torque_blocked": bool(world) and world.GetCustomDataByKey("3dprinting993:starterTorqueSimulationReady") is False,
        "all_support_provisional": all(prim.GetCustomDataByKey("3dprinting993:simulationReady") is False for prim in prims if prim.GetCustomDataByKey("3dprinting993:supportId")),
        "timeline_preserved": bool(stage) and stage.GetEndTimeCode() > stage.GetStartTimeCode(),
    }
    report = {
        "schema_version": "1.0.0",
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "support_counts": dict(sorted(counts.items())),
        "remaining_release_inputs": config["remaining_release_inputs"],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
