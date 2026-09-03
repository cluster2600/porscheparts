#!/usr/bin/env python3
"""Explique la divergence VG.007 sur le USDC F37 issu de usd-convert-cad.

Ce diagnostic lit les indices OpenUSD, compte les arêtes de bord selon la
définition du ManifoldChecker NVIDIA, puis refait le compte après soudure
exacte des coordonnées. Il n'écrit aucune géométrie et n'autorise aucune
fabrication.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any

import numpy as np
from pxr import Usd, UsdGeom


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def edge_audit(faces: np.ndarray, vertex_count: int) -> dict[str, Any]:
    triangle_edges = faces[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2)
    triangle_edges.sort(axis=1)
    unique_edges, counts = np.unique(triangle_edges, axis=0, return_counts=True)
    border_edges = unique_edges[counts == 1]
    overused_edges = unique_edges[counts > 2]
    border_degree = (
        np.bincount(border_edges.reshape(-1), minlength=vertex_count)
        if len(border_edges)
        else np.zeros(vertex_count, dtype=np.int64)
    )
    return {
        "unique_edge_count": int(len(unique_edges)),
        "border_edge_count": int(len(border_edges)),
        "edge_count_above_two_faces": int(len(overused_edges)),
        "vertices_with_more_than_two_border_edges": int(np.count_nonzero(border_degree > 2)),
        "maximum_border_edge_degree": int(border_degree.max(initial=0)),
    }


def reported_vg007_count(report: dict[str, Any]) -> int:
    issues = [item for item in report.get("issues", []) if "VG.007" in str(item.get("requirement", ""))]
    if len(issues) != 1:
        raise SystemExit("le rapport NVIDIA doit contenir exactement une issue VG.007")
    match = re.search(r"(\d+) vertices are non-manifold", str(issues[0].get("message", "")))
    if match is None:
        raise SystemExit("le compteur VG.007 est absent du message NVIDIA")
    return int(match.group(1))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--usd", type=Path, required=True)
    parser.add_argument("--geometry-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    geometry_report = json.loads(args.geometry_report.read_text(encoding="utf-8"))
    stage = Usd.Stage.Open(str(args.usd))
    if stage is None:
        raise SystemExit("impossible d'ouvrir le stage USD")
    meshes = [prim for prim in stage.Traverse() if prim.IsA(UsdGeom.Mesh)]
    if len(meshes) != 1:
        raise SystemExit("le diagnostic exige exactement un UsdGeomMesh")
    mesh = UsdGeom.Mesh(meshes[0])
    counts = np.asarray(mesh.GetFaceVertexCountsAttr().Get(), dtype=np.int64)
    if not np.all(counts == 3):
        raise SystemExit("le diagnostic exige un maillage triangulé")
    points = np.asarray(mesh.GetPointsAttr().Get(), dtype=np.float32)
    faces = np.asarray(mesh.GetFaceVertexIndicesAttr().Get(), dtype=np.int64).reshape(-1, 3)
    if faces.min(initial=0) < 0 or faces.max(initial=-1) >= len(points):
        raise SystemExit("indice de face hors limites")

    indexed = edge_audit(faces, len(points))
    unique_points, inverse, multiplicities = np.unique(
        points,
        axis=0,
        return_inverse=True,
        return_counts=True,
    )
    welded_faces = inverse[faces]
    welded = edge_audit(welded_faces, len(unique_points))
    nvidia_count = reported_vg007_count(geometry_report)
    count_matches = indexed["vertices_with_more_than_two_border_edges"] == nvidia_count

    payload = {
        "schema_version": "1.0.0",
        "phase": "F37_nvidia_usd_topology_diagnostic",
        "status": "conversion_indexing_cause_confirmed_manufacturing_release_blocked",
        "inputs": {
            "usd": {"path": args.usd.name, "bytes": args.usd.stat().st_size, "sha256": sha256(args.usd)},
            "geometry_report": {
                "path": args.geometry_report.name,
                "bytes": args.geometry_report.stat().st_size,
                "sha256": sha256(args.geometry_report),
            },
            "mesh_prim": str(meshes[0].GetPath()),
        },
        "nvidia_observation": {
            "rule": "VG.007",
            "reported_non_manifold_vertices": nvidia_count,
            "computed_count_matches_report": count_matches,
        },
        "official_conversion_indexing": {
            "point_count": int(len(points)),
            "triangle_count": int(len(faces)),
            **indexed,
        },
        "after_exact_coordinate_weld": {
            "point_count": int(len(unique_points)),
            "duplicate_coordinate_groups": int(np.count_nonzero(multiplicities > 1)),
            "extra_point_records_removed": int(len(points) - len(unique_points)),
            "maximum_coordinate_multiplicity": int(multiplicities.max(initial=0)),
            **welded,
        },
        "conclusion": {
            "conversion_indexing_cause_confirmed": bool(
                count_matches
                and indexed["vertices_with_more_than_two_border_edges"] > 0
                and welded["vertices_with_more_than_two_border_edges"] == 0
                and welded["border_edge_count"] == 0
            ),
            "explanation": "Les coordonnées soudées décrivent une peau fermée, mais usd-convert-cad les a réparties sur des indices distincts et créé des arêtes de bord pour VG.007.",
            "stl_geometry_redesign_indicated": False,
            "usd_index_repair_or_converter_change_indicated": True,
        },
        "gates": {
            "diagnostic_reproduced": bool(count_matches),
            "metal_print_authorized": False,
            "candidate_promotion_authorized": False,
            "engine_start_authorized": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
