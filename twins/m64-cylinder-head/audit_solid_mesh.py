#!/usr/bin/env python3
"""Read-only, hash-bound audit of an existing private first-order tetra mesh.

No remeshing, unit conversion, boundary assignment or solver is performed.
Only aggregate metrics leave the private mesh; this is not CAD conformity proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def signed_tetra_volumes(points: np.ndarray, cells: np.ndarray) -> np.ndarray:
    """det(b-a,c-a,d-a)/6; connectivity is zero-based, not Gmsh node tags."""
    points = np.asarray(points, dtype=float)
    cells = np.asarray(cells)
    if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
        raise ValueError("finite_3d_points_required")
    if cells.ndim != 2 or cells.shape[1] != 4 or not np.issubdtype(cells.dtype, np.integer):
        raise ValueError("linear_tetra_connectivity_required")
    if len(cells) == 0 or cells.min() < 0 or cells.max() >= len(points):
        raise ValueError("valid_nonempty_connectivity_required")
    values = np.empty(len(cells))
    for start in range(0, len(cells), 100000):
        xyz = points[cells[start:start + 100000]]
        edges = xyz[:, 1:] - xyz[:, :1]
        values[start:start + len(xyz)] = np.einsum(
            "ij,ij->i", edges[:, 0], np.cross(edges[:, 1], edges[:, 2])) / 6.0
    return values


def boundary_summary(cells: np.ndarray, surface_triangles: np.ndarray) -> dict:
    """Compare tetra boundary connectivity with stored triangles, no positions."""
    cells = np.asarray(cells)
    surface_triangles = np.asarray(surface_triangles)
    faces = np.concatenate([cells[:, ids] for ids in (
        [0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3])])
    faces.sort(axis=1)
    unique, multiplicity = np.unique(faces, axis=0, return_counts=True)
    boundary = unique[multiplicity == 1]
    surface = np.sort(surface_triangles, axis=1)
    stored, counts = np.unique(surface, axis=0, return_counts=True)
    common = np.unique(np.concatenate([boundary, stored]), axis=0)
    intersection = len(boundary) + len(stored) - len(common)
    return {
        "tetra_boundary_triangles": len(boundary),
        "internal_triangle_faces": int((multiplicity == 2).sum()),
        "nonmanifold_triangle_faces": int((multiplicity > 2).sum()),
        "stored_surface_triangles": len(surface_triangles),
        "duplicate_stored_triangles": int((counts - 1).sum()),
        "tetra_boundary_triangles_missing_from_surface": len(boundary) - intersection,
        "stored_triangles_not_on_tetra_boundary": len(stored) - intersection,
        "boundary_connectivity_matches_stored_surface": bool(
            len(boundary) == intersection == len(stored)
            and np.all(counts == 1) and np.all(multiplicity <= 2)),
    }


def quality_summary(values: np.ndarray) -> dict:
    values = np.asarray(values, dtype=float)
    if not len(values) or not np.isfinite(values).all():
        raise ValueError("finite_nonempty_qualities_required")
    return {
        "minimum_minSICN": float(values.min()),
        "p01_minSICN": float(np.quantile(values, .01)),
        "p05_minSICN": float(np.quantile(values, .05)),
        "count_le_zero": int((values <= 0).sum()),
        "count_lt_0p1": int((values < .1).sum()),
        "project_quality_threshold": .1,
        "project_quality_gate_passed": bool(np.all(values >= .1)),
    }


def audit(args) -> dict:
    source_hash = sha256(args.input)
    if source_hash != args.sha256:
        raise ValueError("mesh_hash_mismatch")
    if args.output.exists():
        raise FileExistsError(args.output)
    import gmsh

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.option.setNumber("General.NumThreads", 1)
        gmsh.open(str(args.input))
        types, tag_groups, node_groups = gmsh.model.mesh.getElements(3)
        if list(map(int, types)) != [4]:
            raise ValueError("only_first_order_tetrahedra_supported")
        surface_types, _, surface_nodes = gmsh.model.mesh.getElements(2)
        if list(map(int, surface_types)) != [2]:
            raise ValueError("only_first_order_surface_triangles_supported")
        node_tags, coordinates, _ = gmsh.model.mesh.getNodes()
        node_tags = np.asarray(node_tags)
        order = np.argsort(node_tags)
        if len(np.unique(node_tags)) != len(node_tags):
            raise ValueError("duplicate_node_tags")
        sorted_tags = node_tags[order]
        points = np.asarray(coordinates).reshape(-1, 3)[order]
        tetra_tags = np.asarray(node_groups[0]).reshape(-1, 4)
        cells = np.searchsorted(sorted_tags, tetra_tags)
        if cells.max() >= len(sorted_tags) or not np.array_equal(sorted_tags[cells], tetra_tags):
            raise ValueError("element_references_unknown_node")
        surface = np.asarray(surface_nodes[0]).reshape(-1, 3)
        boundary = boundary_summary(tetra_tags, surface)
        volumes = signed_tetra_volumes(points, cells)
        qualities = quality_summary(gmsh.model.mesh.getElementQualities(tag_groups[0], "minSICN"))
        surface_entities = gmsh.model.getEntities(2)
        grouped_surfaces = set()
        named_surface_groups = 0
        for dim, tag in gmsh.model.getPhysicalGroups(2):
            grouped_surfaces.update(map(int, gmsh.model.getEntitiesForPhysicalGroup(dim, tag)))
            named_surface_groups += bool(gmsh.model.getPhysicalName(dim, tag))
        surface_entity_tags = {tag for _, tag in surface_entities}
        report = {
            "schema": "m64-private-solid-mesh-audit/v1",
            "mesh_sha256": source_hash,
            "mesh_bytes": args.input.stat().st_size,
            "audit_source_sha256": sha256(Path(__file__)),
            "gmsh_version": gmsh.__version__,
            "nodes": len(node_tags),
            "tetrahedra": len(cells),
            "element_type": "Gmsh_4_first_order_tetrahedron",
            "volume_entities": len(gmsh.model.getEntities(3)),
            "surface_entities": len(surface_entities),
            "physical_surface_groups": len(gmsh.model.getPhysicalGroups(2)),
            "named_physical_surface_groups": named_surface_groups,
            "physical_volume_groups": len(gmsh.model.getPhysicalGroups(3)),
            "surfaces_in_physical_groups": len(grouped_surfaces & surface_entity_tags),
            "surface_group_coverage_fraction": len(grouped_surfaces & surface_entity_tags) / len(surface_entities),
            "quality": qualities,
            "signed_volume": {
                "sum_scan_units_cubed": float(volumes.sum()),
                "absolute_sum_scan_units_cubed": float(np.abs(volumes).sum()),
                "minimum_scan_units_cubed": float(volumes.min()),
                "count_negative": int((volumes < 0).sum()),
                "count_zero": int((volumes == 0).sum()),
                "count_nonfinite": int((~np.isfinite(volumes)).sum()),
            },
            "boundary": boundary,
            "repeated_node_tetrahedra": int((np.diff(np.sort(tetra_tags, axis=1), axis=1) == 0).any(axis=1).sum()),
            "absolute_scale_certified": False,
            "unit_conversion_applied": False,
            "mesh_modified": False,
            "physical_boundary_conditions_assigned": False,
            "boundary_mapping_to_exact_STEP_verified": False,
            "grid_convergence_verified": False,
            "ready_for_head_CHT_or_structural_validation": False,
            "manufacturing_authorized": False,
        }
    finally:
        gmsh.finalize()
    if sha256(args.input) != source_hash:
        raise ValueError("input_changed_during_read_only_audit")
    report["mesh_hash_unchanged_after_audit"] = True
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report, allow_nan=False), flush=True)
    return 0 if report["quality"]["project_quality_gate_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
