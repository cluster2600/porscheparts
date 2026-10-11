#!/usr/bin/env python3
"""Inspect exact PicoGK STL exports and render a geometry-only concept preview."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

import numpy as np
import trimesh


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_triangles(triangles):
    triangles = np.asarray(triangles, dtype=np.float64)
    if triangles.ndim != 3 or triangles.shape[1:] != (3, 3) or not len(triangles):
        raise ValueError("nonempty_triangles_required")
    if not np.isfinite(triangles).all():
        raise ValueError("finite_coordinates_required")
    # Index identical coordinates only: no tolerance, facet removal or repair.
    vertices, inverse = np.unique(triangles.reshape(-1, 3), axis=0, return_inverse=True)
    faces = inverse.reshape(-1, 3)
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False, validate=False)
    _, incidence = np.unique(mesh.edges_sorted, axis=0, return_counts=True)
    groups = trimesh.graph.connected_components(
        mesh.face_adjacency, nodes=np.arange(len(faces)), min_len=1, engine="scipy")
    centered = triangles - vertices.mean(axis=0)
    volumes = np.einsum("ij,ij->i", centered[:, 0],
                        np.cross(centered[:, 1], centered[:, 2])) / 6
    component_volumes = [float(volumes[group].sum()) for group in groups]
    degenerates = int(np.count_nonzero(mesh.area_faces == 0))
    duplicates = len(faces) - len(np.unique(np.sort(faces, axis=1), axis=0))
    boundary_edges = int(np.count_nonzero(incidence == 1))
    nonmanifold_edges = int(np.count_nonzero(incidence > 2))
    failures = []
    for failed, reason in (
        (bool(boundary_edges), "boundary_edges"),
        (bool(nonmanifold_edges), "nonmanifold_edges"),
        (bool(degenerates), "degenerate_triangles"),
        (bool(duplicates), "duplicate_triangles"),
        (not mesh.is_winding_consistent, "inconsistent_winding"),
        (len(groups) != 1, "not_one_connected_surface"),
        (any(v <= 0 or not np.isfinite(v) for v in component_volumes), "nonpositive_component_volume"),
    ):
        if failed:
            failures.append(reason)
    return {
        "passed": not failures,
        "failures": failures,
        "triangles": len(faces),
        "vertices": len(vertices),
        "unique_edges": len(incidence),
        "boundary_edges": boundary_edges,
        "nonmanifold_edges": nonmanifold_edges,
        "degenerate_triangles": degenerates,
        "duplicate_triangles": duplicates,
        "surface_components": len(groups),
        "component_triangle_counts": [len(group) for group in groups],
        "component_signed_volumes_mm3": component_volumes,
        "signed_volume_mm3": float(volumes.sum()),
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "bounds_mm": mesh.bounds.tolist(),
        "extents_mm": mesh.extents.tolist(),
        "all_input_triangles_retained": sum(map(len, groups)) == len(triangles),
    }, mesh


def inspect_outputs(directory):
    report = {
        "schema_version": 1,
        "status": "failed",
        "geometry_only": True,
        "engineering_validated": False,
        "manufacturing_authorized": False,
        "mesh_modified": False,
        "self_intersections_checked": False,
        "units": "mm_assumed_from_generator_not_measured",
        "inspector_sha256": sha256(Path(__file__)),
        "numpy_version": np.__version__,
        "trimesh_version": trimesh.__version__,
        "sources": {},
        "meshes": {},
        "errors": [],
    }
    meshes = {}
    declared = {}
    try:
        path = directory / "report.json"
        report["sources"][path.name] = sha256(path)
        generation = json.loads(path.read_text())
        if not isinstance(generation, dict):
            raise ValueError("generation_report_object_required")
        files = generation.get("files")
        if not isinstance(files, list) or not all(
            isinstance(item, dict) and isinstance(item.get("file"), str)
            and isinstance(item.get("sha256"), str) and isinstance(item.get("triangles"), int)
            for item in files
        ):
            raise ValueError("generation_file_records_required")
        declared = {item["file"]: item for item in files}
        if len(files) != 3 or set(declared) != {"housing.stl", "flow-domain.stl", "section.stl"}:
            raise ValueError("generation_file_set_mismatch")
    except (OSError, ValueError) as error:
        report["errors"].append(f"report.json: {error}")
    for name in ("housing", "flow-domain", "section"):
        path = directory / f"{name}.stl"
        try:
            report["sources"][path.name] = sha256(path)
            if declared.get(path.name, {}).get("sha256") != report["sources"][path.name]:
                report["errors"].append(f"{name}: generation_sha256_mismatch")
            # PicoGK writes binary STL; bind loader output to its raw facet count.
            with path.open("rb") as stream:
                header = stream.read(84)
            if len(header) != 84:
                raise ValueError("binary_stl_header_required")
            expected = struct.unpack_from("<I", header, 80)[0]
            if path.stat().st_size != 84 + 50 * expected:
                raise ValueError("binary_stl_length_mismatch")
            if declared.get(path.name, {}).get("triangles") != expected:
                report["errors"].append(f"{name}: generation_triangle_count_mismatch")
            raw = trimesh.load_mesh(path, file_type="stl", process=False)
            if not isinstance(raw, trimesh.Trimesh) or len(raw.faces) != expected:
                raise ValueError("raw_triangle_count_mismatch")
            summary, meshes[name] = inspect_triangles(raw.triangles)
            report["meshes"][name] = summary
            if not summary["passed"]:
                report["errors"].append(f"{name}: {', '.join(summary['failures'])}")
        except (OSError, ValueError, IndexError) as error:
            report["errors"].append(f"{name}: {error}")
    for filename, expected in report["sources"].items():
        if sha256(directory / filename) != expected:
            report["errors"].append(f"{filename}: changed_during_inspection")
    report["geometry_passed"] = not report["errors"]
    if report["geometry_passed"]:
        report["status"] = "passed"
    return report, meshes


def render_preview(meshes, output):
    import pyvista as pv

    plot = pv.Plotter(shape=(1, 2), off_screen=True, window_size=(1800, 1000), border=False)
    for column, name, color, title, direction in (
        (0, "housing", "#c68a5c", "BIONIC TURBO / F0", (2.5, 3, 1.9)),
        (1, "section", "#aebcc8", "GEOMETRIC SECTION", (-3, 2, 1.8)),
    ):
        plot.subplot(0, column)
        plot.set_background("#101820")
        mesh = meshes[name]
        faces = np.column_stack((np.full(len(mesh.faces), 3), mesh.faces)).ravel()
        surface = pv.PolyData(mesh.vertices, faces)
        plot.add_mesh(surface, color=color, smooth_shading=True, ambient=0.25,
                      diffuse=0.8, specular=0.35, specular_power=25)
        plot.add_text(title, position="upper_left", font_size=20, color="#f1ebe2")
        plot.add_text("PicoGK | original concept geometry\nNo fit, CFD or strength validation",
                      position="lower_left", font_size=11, color="#a6b5c1")
        plot.enable_parallel_projection()
        plot.view_vector(direction, viewup=(0, 0, 1))
        plot.camera.zoom(1.1)
    plot.screenshot(str(output))
    plot.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    report, meshes = inspect_outputs(args.directory)
    preview = args.directory / "preview.png"
    if report["geometry_passed"]:
        try:
            render_preview(meshes, preview)
            report["preview_sha256"] = sha256(preview)
        except Exception as error:
            report["status"] = "failed"
            report["errors"].append(f"preview: {type(error).__name__}: {error}")
    output = args.directory / "inspection.json"
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": report["status"], "report": str(output), "errors": report["errors"]}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
