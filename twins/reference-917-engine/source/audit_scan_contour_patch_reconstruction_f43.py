#!/usr/bin/env python3
"""Audit exact/local F43 d'un STEP et, facultativement, d'un maillage Gmsh.

Le rapport produit par ce script reste local lorsqu'il contient des coordonnées
ou des indices issus de la géométrie privée. La synthèse publique est construite
à partir des seuls compteurs, empreintes et quantiles.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import gmsh
import numpy as np

from audit_brep_f42 import brepcheck, read_step, shape_properties, topology
from repair_topology_f42_1 import full_bop_map, pcurve_faults


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def mesh_quality(mesh_path: Path) -> dict:
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.open(str(mesh_path))
        types, tag_groups, _ = gmsh.model.mesh.getElements(3)
        tags = [int(tag) for group in tag_groups for tag in group]
        quality = np.sort(np.asarray(gmsh.model.mesh.getElementQualities(tags, "minSICN"), dtype=float))
    finally:
        gmsh.finalize()

    def quantile(value: float) -> float | None:
        return float(np.quantile(quality, value)) if len(quality) else None

    return {
        "sha256": sha256(mesh_path),
        "bytes": mesh_path.stat().st_size,
        "element_types_3d": [int(value) for value in types],
        "tetrahedra": int(len(quality)),
        "minimum_minSICN": float(quality[0]) if len(quality) else None,
        "p001_minSICN": quantile(0.001),
        "p01_minSICN": quantile(0.01),
        "p05_minSICN": quantile(0.05),
        "count_minSICN_le_0": int(np.sum(quality <= 0.0)),
        "count_minSICN_lt_0_1": int(np.sum(quality < 0.1)),
    }


def audit(step_path: Path, mesh_path: Path | None) -> dict:
    shape, transferred = read_step(step_path)
    check = brepcheck(shape)
    topological = topology(shape)
    pcurves = pcurve_faults(shape)
    bop = full_bop_map(shape)
    report = {
        "schema": "porsche-917-f43-private-audit/v1",
        "phase": "F43",
        "step": {
            "sha256": sha256(step_path),
            "bytes": step_path.stat().st_size,
            "transferred_roots": transferred,
            "repository_policy": "private_local_only_scan_derived_geometry",
        },
        "properties": shape_properties(shape),
        "brepcheck": check,
        "topology": topological,
        "pcurves": pcurves,
        "BOPAlgo": bop,
        "mesh": mesh_quality(mesh_path) if mesh_path is not None else None,
    }
    mesh = report["mesh"]
    report["gates"] = {
        "BRepCheck_exact_valid": bool(check["shape_valid"]),
        "one_solid_one_shell": bool(
            topological["unique_subshape_counts"]["solid"] == 1
            and topological["unique_subshape_counts"]["shell"] == 1
        ),
        "zero_free_or_nonmanifold_edges": bool(
            topological["edge_classification"]["free_edges"] == 0
            and topological["edge_classification"]["nonmanifold_edges"] == 0
        ),
        "zero_pcurve_faults": bool(pcurves["result_count"] == 0),
        "zero_BOPAlgo_faults": bool(not bop["has_faulty"]),
        "mesh_has_no_inverted_tetrahedra": bool(mesh and mesh["count_minSICN_le_0"] == 0),
        "all_tetrahedra_minSICN_at_least_0_1": bool(mesh and mesh["count_minSICN_lt_0_1"] == 0),
        "functional_internal_geometry_complete": False,
        "manufacturing_authorized": False,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--step", type=Path, required=True)
    parser.add_argument("--mesh", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.step, args.mesh)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report["gates"], sort_keys=True))
    return 0 if all(report["gates"].values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
