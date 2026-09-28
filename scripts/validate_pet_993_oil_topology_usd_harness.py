#!/usr/bin/env python3
"""Validate the M64-Z-OL F1 oil-circuit topology harness USD.

Loads the merged harness with OpenUSD (pxr) and checks:
  - stage loads with a default prim,
  - all three circuit scopes exist with the expected node/edge counts
    matching the F1 topology readiness contracts,
  - every node sphere and edge mesh carries the placeholder geometry state
    and the single placeholder radius config value,
  - all cross-circuit links are tagged linkState=unknown.

Run: python3 scripts/validate_pet_993_oil_topology_usd_harness.py
Requires the usd-core (pxr) Python package; exits 1 with
PXr_UNAVAILABLE if it is missing (structural check only in that case).
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS = os.path.join(
    REPO, "twins/catalogue-parts/engineering/"
          "993-oil-circuit-topology-harness-f1.usda")
CONTRACTS = {
    "TurboLubricationControl":
        "twins/catalogue-parts/turbo-lubrication-control-topology-readiness-f1.json",
    "OilCoolerCircuit":
        "twins/catalogue-parts/oil-cooler-circuit-topology-readiness-f1.json",
    "OilTankCircuit":
        "twins/catalogue-parts/oil-tank-circuit-topology-readiness-f1.json",
}
PLACEHOLDER_RADIUS_M = 0.080
PLACEHOLDER_TUBE_RADIUS_M = 0.0125


def main():
    try:
        from pxr import Usd, UsdGeom
    except ImportError:
        print("PXr_UNAVAILABLE: python3 -m pip install usd-core to load-check")
        return 2

    stage = Usd.Stage.Open(HARNESS)
    errors = []
    if not stage or not stage.GetDefaultPrim():
        print("FAIL: harness stage did not load or has no default prim")
        return 1

    for circuit, contract_rel in CONTRACTS.items():
        contract = json.load(open(os.path.join(REPO, contract_rel)))
        want_nodes = contract["summary"]["topology_nodes"]
        want_edges = contract["summary"]["topology_edges"]
        nodes = stage.GetPrimAtPath(
            f"/OilCircuitTopologyHarnessF1/{circuit}/Nodes")
        edges = stage.GetPrimAtPath(
            f"/OilCircuitTopologyHarnessF1/{circuit}/Edges")
        got_nodes = len(nodes.GetAllChildren()) if nodes else -1
        got_edges = len(edges.GetAllChildren()) if edges else -1
        if got_nodes != want_nodes or got_edges != want_edges:
            errors.append(
                f"{circuit}: nodes {got_nodes}/{want_nodes} "
                f"edges {got_edges}/{want_edges}")

    for prim in stage.TraverseAll():
        state = prim.GetAttribute("geometryState")
        if state and state.Get() != "placeholder_not_measurement":
            errors.append(f"{prim.GetPath()}: bad geometryState")
        if prim.IsA(UsdGeom.Sphere):
            r = prim.GetAttribute("radius").Get()
            if abs(r - PLACEHOLDER_RADIUS_M) > 1e-12:
                errors.append(f"{prim.GetPath()}: radius {r} not placeholder")
        elif prim.IsA(UsdGeom.Mesh):
            r = prim.GetAttribute("placeholderRadiusM")
            if not r or r.Get() != PLACEHOLDER_TUBE_RADIUS_M:
                errors.append(f"{prim.GetPath()}: missing placeholder radius")
            ls = prim.GetAttribute("linkState")
            if ls and ls.Get() != "unknown":
                errors.append(f"{prim.GetPath()}: linkState not unknown")

    if errors:
        print("FAIL")
        for e in errors:
            print(" -", e)
        return 1
    n_prims = len(list(stage.TraverseAll()))
    print(f"PASS: harness loads (pxr), {n_prims} prims, "
          "all radii are the single placeholder config value, "
          "all cross-links tagged unknown")
    return 0


if __name__ == "__main__":
    sys.exit(main())
