#!/usr/bin/env python3
"""Construit les B-rep solveur F33 2V/4V; aucune géométrie de fabrication."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import gmsh


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def build_variant(contract: dict, design: dict, output: Path) -> dict:
    cfg = contract["functional_solver_cad"]
    architecture = design["architecture"]
    output.mkdir(parents=True, exist_ok=True)
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 1)
    gmsh.model.add(f"f33_head_{architecture}")
    occ = gmsh.model.occ
    outer = occ.addCylinder(0.0, 0.0, 0.0, 0.0, 0.0, cfg["head_height_mm"], cfg["outer_radius_mm"])
    tools = []
    chamber_radius = 52.0
    chamber_center_z = -(chamber_radius - cfg["chamber_depth_mm"])
    tools.append((3, occ.addSphere(0.0, 0.0, chamber_center_z, chamber_radius)))

    for kind in ("intake", "exhaust"):
        diameter = design[f"{kind}_diameter_mm"]
        port_diameter = 0.72 * diameter
        direction = 1.0 if kind == "intake" else -1.0
        port_length = cfg[f"{kind}_port_length_mm"]
        axis_z = 35.0 if kind == "intake" else 30.0
        for x, y in design["valve_positions_xy_mm"][kind]:
            tools.append((3, occ.addCylinder(x, y, -1.0, 0.0, 0.0, 46.0, 0.43 * diameter)))
            tools.append((3, occ.addCylinder(x, y, 14.0, 0.0, 0.0, 59.0, 3.5)))
            tools.append((3, occ.addCylinder(x, y, -0.5, 0.0, 0.0, 7.0, 0.50 * diameter)))
            tools.append(
                (
                    3,
                    occ.addCylinder(
                        x,
                        y,
                        axis_z,
                        0.0,
                        direction * port_length,
                        0.0,
                        0.5 * port_diameter,
                    ),
                )
            )

    tools.append((3, occ.addCylinder(0.0, 0.0, -1.0, 0.0, 0.0, cfg["head_height_mm"] + 2.0, cfg["spark_plug_bore_mm"] / 2.0)))
    for x in (-43.0, 43.0):
        for y in (-43.0, 43.0):
            tools.append((3, occ.addCylinder(x, y, -1.0, 0.0, 0.0, cfg["head_height_mm"] + 2.0, cfg["fastener_bore_mm"] / 2.0)))

    jacket_outer = occ.addCylinder(0.0, 0.0, 18.0, 0.0, 0.0, cfg["cooling_jacket_height_mm"], cfg["cooling_jacket_radius_mm"])
    jacket_inner = occ.addCylinder(0.0, 0.0, 17.5, 0.0, 0.0, cfg["cooling_jacket_height_mm"] + 1.0, cfg["cooling_jacket_radius_mm"] - 7.0)
    jacket, _ = occ.cut([(3, jacket_outer)], [(3, jacket_inner)], removeObject=True, removeTool=True)
    tools.extend(jacket)
    tools.append((3, occ.addCylinder(-cfg["outer_radius_mm"] - 2.0, 0.0, 55.0, 2.0 * cfg["outer_radius_mm"] + 4.0, 0.0, 0.0, 2.5)))
    result, _ = occ.cut([(3, outer)], tools, removeObject=True, removeTool=True)
    occ.removeAllDuplicates()
    occ.synchronize()
    volumes = gmsh.model.getEntities(3)
    if not result or not volumes:
        gmsh.finalize()
        raise RuntimeError(f"aucun volume F33 pour {architecture}")
    volume_mm3 = sum(occ.getMass(dim, tag) for dim, tag in volumes)
    step_path = output / f"917-head-functional-solver-{architecture}.step"
    stl_path = output / f"917-head-functional-solver-{architecture}.stl"
    gmsh.write(str(step_path))
    gmsh.option.setNumber("Mesh.MeshSizeMax", 5.0)
    gmsh.option.setNumber("Mesh.MeshSizeMin", 2.5)
    gmsh.model.mesh.generate(2)
    gmsh.write(str(stl_path))
    surface_nodes = len(gmsh.model.mesh.getNodes()[0])
    surface_elements = sum(len(tags) for tags in gmsh.model.mesh.getElements(2)[1])
    gmsh.finalize()
    return {
        "architecture": architecture,
        "classification": cfg["classification"],
        "volume_count": len(volumes),
        "volume_mm3": volume_mm3,
        "surface_node_count": surface_nodes,
        "surface_element_count": surface_elements,
        "step": {"path": step_path.name, "sha256": sha256(step_path), "bytes": step_path.stat().st_size},
        "stl": {"path": stl_path.name, "sha256": sha256(stl_path), "bytes": stl_path.stat().st_size},
        "included_features": cfg["included_features"],
        "excluded_features": cfg["excluded_features"],
        "manufacturing_cad_complete": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--design-study", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    contract = load_json(args.contract)
    study = load_json(args.design_study)
    variants = [
        item for item in study["variants"]
        if item["scenario_id"] == "917_30_1973_turbo_5374"
    ]
    if {item["architecture"] for item in variants} != {"2v", "4v"}:
        raise SystemExit("les deux architectures turbo F29 sont requises")
    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"output already exists: {output}")
    output.mkdir(parents=True)
    reports = [build_variant(contract, design, output) for design in variants]
    manifest = {
        "schema_version": "1.0.0",
        "phase": "F33",
        "status": "functional_solver_cad_generated_not_manufacturing_cad",
        "variants": reports,
        "release_gates": contract["release_gates"],
    }
    manifest_path = output / "geometry-report.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "variants": len(reports)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
