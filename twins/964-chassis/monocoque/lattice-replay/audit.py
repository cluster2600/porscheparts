"""Independently screen raw replay meshes; preserve all faces, including rejects."""
import argparse
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
HELPER = ROOT / "twins/m64-cylinder-head/source/picogk-local-junction/audit_surface_topology.py"
spec = importlib.util.spec_from_file_location("replay_surface_audit", HELPER)
surface = importlib.util.module_from_spec(spec)
spec.loader.exec_module(surface)
# Resource ceilings only: the 0.25 mm replay has 328k faces; predicates are unchanged.
surface.MAX_FACES, surface.MAX_VERTICES = 400_000, 1_200_000
CASES = ("global-050", "local-050", "global-025", "local-025")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stable_volume(triangles):
    """Signed tetrahedral integration in float64 about the bounding-box centre."""
    a = np.asarray(triangles, dtype=float)
    if a.ndim != 3 or a.shape[1:] != (3, 3) or not len(a) or not np.isfinite(a).all():
        raise ValueError("Finite nonempty triangles required")
    origin = (a.min(axis=(0, 1)) + a.max(axis=(0, 1))) / 2
    local = a - origin
    terms = np.einsum("ij,ij->i", local[:, 0], np.cross(local[:, 1], local[:, 2])) / 6
    return math.fsum(map(float, terms))


def zero_mask(triangles):
    vertices, inverse = np.unique(triangles.reshape(-1, 3), axis=0, return_inverse=True)
    return surface.exact_zero_area_mask(vertices, inverse.reshape(-1, 3))


def survey_state(path):
    with Path(path).open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows or len({r["datum_id"] for r in rows}) != len(rows):
        raise ValueError("Missing or duplicated survey identities")
    if any(r["xyz_validated"] not in ("True", "False") for r in rows):
        raise ValueError("Unknown validation flag")
    return {"register_points": len(rows),
            "validated_xyz": sum(r["xyz_validated"] == "True" for r in rows),
            "missing_z": [r["datum_id"] for r in rows if not r["z_mm"].strip()],
            "source_sha256": sha(path), "complete_body_interface_inventory": False}


def run(directory, output):
    directory, output = Path(directory), Path(output)
    if output.exists():
        raise FileExistsError(output)
    old = HERE.parent / "field-lattice/evidence"
    archived, _ = surface.load_binary_stl(old / "graded_probe.stl")
    expected = sha(old / "report.json")
    results, meshes = {}, {}
    for label in CASES:
        folder = directory / label
        native = json.loads((folder / "native.json").read_text())
        if (native["input_report_sha256"] != expected or native["case_id"] != label
                or native["mesh_repaired"] is not False or native["original_design_parameters_changed"] is not False):
            raise ValueError("Unexpected native input or geometry change")
        triangles, digest = surface.load_binary_stl(folder / "raw.stl")
        if len(triangles) != native["triangles"]:
            raise ValueError("Native triangle count mismatch")
        vertices, inverse = np.unique(triangles.reshape(-1, 3), axis=0, return_inverse=True)
        topology = surface.audit_arrays(vertices, inverse.reshape(-1, 3))
        mask = zero_mask(triangles)
        if int(mask.sum()) != topology["exact_zero_area_faces"]:
            raise ValueError("Zero-area predicate disagrees")
        origin = np.array(native["local_to_F0_translation_mm"], float)
        global_triangles = triangles + origin
        centroid_volume = stable_volume(triangles)
        global_float32 = global_triangles.astype(np.float32).astype(float)
        zero_global32 = int(zero_mask(global_float32).sum())
        closed = topology["closed_oriented_combinatorial_surface_screen_pass"]
        results[label] = {"native": native, "raw_stl_sha256": digest,
            "raw_vdb_sha256": sha(folder / "raw.vdb"), "native_receipt_sha256": sha(folder / "native.json"),
            "topology": topology, "centred_float64_signed_volume_mm3": centroid_volume,
            "volume_is_conditional_on_embedded_closed_surface": True,
            "native_volume_relative_difference": abs(native["volume_mm3"]-centroid_volume)/abs(centroid_volume),
            "float32_globalization_zero_area_faces": zero_global32,
            "zero_face_indices": np.flatnonzero(mask).tolist(),
            "zero_face_global_bounds_mm": [global_triangles[mask].min(axis=(0,1)).tolist(),
                                            global_triangles[mask].max(axis=(0,1)).tolist()] if mask.any() else None,
            "numerical_mesh_candidate": bool(closed and topology["edge_connected_face_components"] == 1),
            "solver_ready": False, "manufacturing_authorized": False}
        meshes[label] = global_triangles
        print(label, "zero faces:", int(mask.sum()), "closed:", closed,
              "centred volume:", centroid_volume, flush=True)
    baseline_equal = np.array_equal(meshes["global-050"], archived)
    if not baseline_equal:
        raise ValueError("Baseline does not reproduce the archived raw triangle coordinates")
    comparisons = {}
    for resolution in ("050", "025"):
        a, b = meshes["global-"+resolution], meshes["local-"+resolution]
        if a.shape != b.shape:
            raise ValueError("Cannot compare corresponding triangles after topology count changes")
        comparisons[resolution] = {"maximum_corresponding_vertex_delta_mm": float(np.abs(a-b).max()),
            "centred_volume_relative_delta": abs(stable_volume(a)-stable_volume(b))/abs(stable_volume(b))}
    survey = ROOT / "twins/964-chassis/derived/interface-measurements-20261008.csv"
    report = {"schema": "964-lattice-frame-resolution-replay/v1", "input_report_sha256": expected,
        "archived_raw_triangle_coordinates_reproduced": baseline_equal,
        "resource_limits": {"faces": surface.MAX_FACES, "vertices": surface.MAX_VERTICES},
        "surface_criteria_modified": False, "cases": results, "same_resolution_frame_comparison": comparisons,
        "local_refinement_volume_relative_change": abs(results["local-025"]["centred_float64_signed_volume_mm3"]-
            results["local-050"]["centred_float64_signed_volume_mm3"])/abs(results["local-025"]["centred_float64_signed_volume_mm3"]),
        "interface_survey": survey_state(survey),
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in (Path(__file__), HERE/"Program.cs", HERE/"Replay.csproj", HELPER)},
        "geometric_self_intersections": "untested", "structural_analysis_executed": False,
        "product_strength_validated": False, "manufacturing_authorized": False}
    with output.open("x") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    run(args.directory, args.output)
