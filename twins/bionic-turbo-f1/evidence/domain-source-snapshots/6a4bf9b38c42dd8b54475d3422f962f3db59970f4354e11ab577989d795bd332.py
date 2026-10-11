#!/usr/bin/env python3
"""Inspect a sealed concept fluid volume and label its exact exported facets."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct

import numpy as np
import pyvista as pv
import trimesh

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("bionic_mesh_inspector", ROOT / "twins/bionic-turbo-f0/inspect_mesh.py")
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)
REGIONS = ("inlet", "outlet", "rotor", "stator")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inspect_fluid(triangles):
    report, mesh = BASE.inspect_triangles(triangles)
    # Closed internal rotor islands have negative signed boundary volumes.
    allowed = {"not_one_connected_surface", "nonpositive_component_volume"}
    errors = [x for x in report["failures"] if x not in allowed]
    volumes = report["component_signed_volumes_mm3"]
    if sum(v > 0 for v in volumes) != 1 or any(v == 0 for v in volumes) or mesh.volume <= 0:
        errors.append("expected_one_positive_outer_boundary_and_negative_obstacles")
    report.update(passed=not errors, failures=errors, enclosed_obstacles_allowed=True,
                  containment_and_self_intersection_verified=False)
    return report, mesh


def distances(points, mesh):
    faces = np.column_stack((np.full(len(mesh.faces), 3), mesh.faces)).ravel()
    surface = pv.PolyData(mesh.vertices, faces)
    return np.abs(pv.PolyData(points).compute_implicit_distance(surface)["implicit_distance"])


def label_faces(mesh, rotor_distance, housing_distance, tolerance_mm=0.65, rear_radius_mm=34):
    triangles = mesh.triangles
    centers = mesh.triangles_center
    inlet = np.max(np.abs(triangles[:, :, 2] - 44.0), axis=1) < 0.001
    outlet = np.max(np.abs(triangles[:, :, 1] - 80.0), axis=1) < 0.001
    rotor = (~inlet & ~outlet & (rotor_distance <= tolerance_mm)
             & (rotor_distance < housing_distance))
    labels = np.full(len(triangles), "stator", dtype="U6")
    labels[rotor] = "rotor"
    labels[inlet] = "inlet"
    labels[outlet] = "outlet"
    radii = np.linalg.norm(centers[:, :2], axis=1)
    rear = ((radii <= rear_radius_mm + tolerance_mm) & (centers[:, 2] <= -3.75 + tolerance_mm)
            & ((np.abs(centers[:, 2] + 3.75) <= tolerance_mm)
               | (np.abs(radii - rear_radius_mm) <= tolerance_mm)))
    extension = ((centers[:, 1] >= 42.25 - tolerance_mm)
                 & (np.hypot(centers[:, 0] - 49, centers[:, 2]) <= 14 + tolerance_mm))
    # shortcut: voxel cut creates an inlet bevel; qualify its sensitivity before performance ranking.
    cap_vertices = np.abs(triangles[:, :, 2] - 44) < 0.001
    vertex_radii = np.linalg.norm(triangles[:, :, :2], axis=2)
    off_cap_radii = np.sum(np.where(cap_vertices, 0, vertex_radii), axis=1)
    longest_edge = np.max(np.linalg.norm(triangles - np.roll(triangles, 1, axis=1), axis=2), axis=1)
    inlet_trim = ((labels == "stator") & (np.sum(cap_vertices, axis=1) == 2)
                  & np.all((triangles[:, :, 2] >= 43.5) & (triangles[:, :, 2] <= 44.001), axis=1)
                  & np.all(vertex_radii <= 22.5, axis=1) & (off_cap_radii >= 21)
                  & (longest_edge <= 1.5) & (housing_distance <= 0.75))
    unexplained = ((labels == "stator") & (housing_distance > tolerance_mm) & ~rear & ~extension & ~inlet_trim)
    counts = {name: int(np.count_nonzero(labels == name)) for name in REGIONS}
    errors = []
    if any(count == 0 for count in counts.values()):
        errors.append("all_four_boundary_regions_required")
    if np.any(unexplained):
        errors.append("unexplained_stator_faces_or_nominal_mask_clipping")
    return labels, {"passed": not errors, "errors": errors, "face_counts": counts,
                    "unexplained_stator_faces": int(np.count_nonzero(unexplained)),
                    "unexplained_face_examples_mm": centers[unexplained][:10].tolist(),
                    "classification_tolerance_mm": tolerance_mm,
                    "maximum_rotor_distance_mm": float(np.max(rotor_distance[rotor])) if np.any(rotor) else None,
                    "rear_idealization_faces": int(np.count_nonzero((labels == "stator") & rear)),
                    "extension_idealization_faces": int(np.count_nonzero((labels == "stator") & extension)),
                    "inlet_trim_idealization": {
                        "faces": int(np.count_nonzero(inlet_trim)),
                        "faces_exceeding_wall_tolerance": int(np.count_nonzero(inlet_trim & (housing_distance > tolerance_mm))),
                        "area_mm2": float(np.sum(mesh.area_faces[inlet_trim])),
                        "maximum_centroid_distance_mm": float(np.max(housing_distance[inlet_trim])) if np.any(inlet_trim) else None,
                        "maximum_edge_mm": float(np.max(longest_edge[inlet_trim])) if np.any(inlet_trim) else None,
                        "rule": "Two vertices on z44; third in z43.5..44 and r21..22.5; all vertices r<=22.5; edges<=1.5; centroid housing distance<=0.75 mm",
                        "sensitivity_validated": False},
                    "method": "centroid proximity to exact imported material surfaces; explicit cap and seal exceptions"}


def write_surface(path, mesh, labels):
    # All source facets retained; the only coordinate change is mm -> m.
    with path.open("x", encoding="ascii") as stream:
        for name in REGIONS:
            stream.write(f"solid {name}\n")
            for index in np.flatnonzero(labels == name):
                n = mesh.face_normals[index]
                stream.write("facet normal %.12g %.12g %.12g\nouter loop\n" % tuple(n))
                for point in mesh.triangles[index] / 1000:
                    stream.write("vertex %.12g %.12g %.12g\n" % tuple(point))
                stream.write("endloop\nendfacet\n")
            stream.write(f"endsolid {name}\n")


def load_declared(directory, report, name):
    declared = [item for item in report["files"] if item["file"] == name]
    path = directory / name
    if len(declared) != 1 or declared[0]["sha256"] != sha(path):
        raise ValueError(f"source_hash_mismatch:{name}")
    header = path.read_bytes()[:84]
    if len(header) != 84:
        raise ValueError("binary_stl_required")
    count = struct.unpack_from("<I", header, 80)[0]
    if path.stat().st_size != 84 + count * 50 or count != declared[0]["triangles"]:
        raise ValueError(f"facet_count_mismatch:{name}")
    return trimesh.load_mesh(path, process=False)


def prepare(directory, output):
    output.mkdir(parents=True, exist_ok=False)
    receipt = {"status": "failed", "performance_validated": False,
               "real_assembly_fluid_domain": False, "manufacturing_authorized": False,
               "source_report_sha256": sha(directory / "report.json"), "sources": {},
               "preparer_sha256": sha(Path(__file__))}
    try:
        if (directory / "FAILED.json").exists():
            raise ValueError("failed_generation_marker")
        report = json.loads((directory / "report.json").read_text())
        if report.get("status") != "ideal_fluid_geometry_generated_pending_qa" or report.get("units") != "mm":
            raise ValueError("unsupported_generation_report")
        construction = report["construction"]
        if (construction["inlet_cap_z_mm"] != 44 or construction["outlet_cap_y_mm"] != 80
                or construction["rear_seal_radius_mm"] not in (34, 35.5)
                or construction["rear_seal_top_z_mm"] != -3.75):
            raise ValueError("unsupported_ideal_closure")
        receipt["construction"] = construction
        fluid_raw = load_declared(directory, report, "fluid.stl")
        rotor = load_declared(directory, report, "rotor-union.stl")
        housing = load_declared(directory, report, "housing-final.stl")
        receipt["sources"] = {n: sha(directory / n) for n in ("fluid.stl", "rotor-union.stl", "housing-final.stl")}
        inspection, fluid = inspect_fluid(fluid_raw.triangles)
        receipt["mesh"] = inspection
        if not inspection["passed"]:
            raise ValueError("fluid_mesh_failed")
        points = fluid.triangles_center
        labels, classification = label_faces(fluid, distances(points, rotor), distances(points, housing),
                                             rear_radius_mm=construction["rear_seal_radius_mm"])
        receipt["classification"] = classification
        if not classification["passed"]:
            raise ValueError("boundary_classification_failed")
        if any(sha(directory / name) != expected for name, expected in receipt["sources"].items()):
            raise ValueError("source_changed_during_inspection")
        surface = output / "fluid-regions.stl"
        write_surface(surface, fluid, labels)
        receipt.update(status="surface_prepared_pending_volume_mesh", surface_sha256=sha(surface),
                       units="m", bounds_m=(fluid.bounds / 1000).tolist(),
                       all_facets_retained=True, source_facet_count=len(fluid.faces),
                       source_voxel_mm=0.5, geometry_uncertainty_quantified=False, native_seed_mm=[15, 0, 40])
    except Exception as error:
        receipt["error"] = str(error)
        (output / "FAILED.json").write_text(json.dumps(receipt, indent=2) + "\n")
        raise
    finally:
        (output / "surface-report.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = prepare(args.input, args.output)
    print(result["status"])
