#!/usr/bin/env python3
"""Conservative full-revolution radial separation bounds on unchanged STL facets."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import struct

import numpy as np

MARGIN_MM = 1e-8
INSPECT_PATH = Path(__file__).resolve().parents[1] / "bionic-turbo-f0/inspect_mesh.py"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checked_triangles(values):
    triangles = np.asarray(values, dtype=np.float64)
    if triangles.ndim != 3 or triangles.shape[1:] != (3, 3) or not len(triangles):
        raise ValueError("nonempty_triangle_array_required")
    if not np.isfinite(triangles).all() or np.abs(triangles).max() > 1e6:
        raise ValueError("finite_bounded_coordinates_required")
    return triangles


def projected_min_radius(triangles):
    """Distance from the origin to each ENTIRE XY-projected triangle."""
    xy = checked_triangles(triangles)[:, :, :2]
    ends = np.roll(xy, -1, axis=1)
    edges = ends - xy
    lengths2 = np.einsum("nij,nij->ni", edges, edges)
    numerators = -np.einsum("nij,nij->ni", xy, edges)
    fractions = np.divide(numerators, lengths2, out=np.zeros_like(lengths2), where=lengths2 > 0)
    closest = xy + np.clip(fractions, 0, 1)[:, :, None] * edges
    distances = np.sqrt(np.einsum("nij,nij->ni", closest, closest).min(axis=1))
    cross = xy[:, :, 0] * ends[:, :, 1] - xy[:, :, 1] * ends[:, :, 0]
    area2 = ((xy[:, 1, 0] - xy[:, 0, 0]) * (xy[:, 2, 1] - xy[:, 0, 1])
             - (xy[:, 1, 1] - xy[:, 0, 1]) * (xy[:, 2, 0] - xy[:, 0, 0]))
    scale2 = np.maximum(1, np.square(xy).sum(axis=2).max(axis=1))
    tolerance = 64 * np.finfo(float).eps * scale2
    inside = (area2 != 0) & ((cross >= -tolerance[:, None]).all(axis=1)
                              | (cross <= tolerance[:, None]).all(axis=1))
    distances[inside] = 0
    return np.maximum(0, distances - MARGIN_MM)


def solid_winding_number(triangles, point):
    """Solid-angle containment check, without rays, angular samples or rtree."""
    vectors = checked_triangles(triangles) - np.asarray(point, dtype=float)
    lengths = np.linalg.norm(vectors, axis=2)
    if (lengths <= MARGIN_MM).any():
        raise ValueError("containment_point_on_surface_vertex")
    a, b, c = (vectors[:, i] for i in range(3))
    determinant = np.einsum("ij,ij->i", a, np.cross(b, c))
    denominator = (lengths.prod(axis=1)
                   + np.einsum("ij,ij->i", a, b) * lengths[:, 2]
                   + np.einsum("ij,ij->i", b, c) * lengths[:, 0]
                   + np.einsum("ij,ij->i", c, a) * lengths[:, 1])
    return float(np.sum(2 * np.arctan2(determinant, denominator)) / (4 * np.pi))


def radial_profile(rotor, housing, band_mm=0.1):
    rotor, housing = checked_triangles(rotor), checked_triangles(housing)
    if not np.isfinite(band_mm) or not 0.01 <= band_mm <= 1:
        raise ValueError("band_mm_must_be_finite_in_0.01_to_1")
    rz0, rz1 = rotor[:, :, 2].min(axis=1), rotor[:, :, 2].max(axis=1)
    hz0, hz1 = housing[:, :, 2].min(axis=1), housing[:, :, 2].max(axis=1)
    first, last = int(np.floor(rz0.min() / band_mm)), int(np.ceil(rz1.max() / band_mm))
    if not 0 < last - first <= 10000:
        raise ValueError("invalid_axial_band_count")
    upper = np.linalg.norm(rotor[:, :, :2], axis=2).max(axis=1) + MARGIN_MM
    lower = projected_min_radius(housing)
    rows = []
    for index in range(first, last):
        z0, z1 = index * band_mm, (index + 1) * band_mm
        selected_r = (rz0 <= z1 + MARGIN_MM) & (rz1 >= z0 - MARGIN_MM)
        selected_h = (hz0 <= z1 + MARGIN_MM) & (hz1 >= z0 - MARGIN_MM)
        rmax = float(upper[selected_r].max()) if selected_r.any() else None
        hmin = float(lower[selected_h].min()) if selected_h.any() else None
        gap = hmin - rmax if hmin is not None and rmax is not None else None
        rows.append({"z_low_mm": z0, "z_high_mm": z1,
                     "rotor_max_radius_upper_mm": rmax, "housing_min_radius_lower_mm": hmin,
                     "radial_gap_lower_mm": gap, "rotor_triangles": int(selected_r.sum()),
                     "housing_triangles": int(selected_h.sum())})
    finite_gaps = [row["radial_gap_lower_mm"] for row in rows if row["radial_gap_lower_mm"] is not None]
    gaps_positive = len(finite_gaps) == len(rows) and all(gap > 0 for gap in finite_gaps)
    axis_point = [0, 0, (float(rz0.min()) + float(rz1.max())) / 2]
    winding = solid_winding_number(housing, axis_point)
    axis_outside = abs(winding) < 1e-6
    stations = []
    for z in (21, 12, 4.5):
        indices = [i for i, row in enumerate(rows)
                   if row["z_low_mm"] - MARGIN_MM <= z <= row["z_high_mm"] + MARGIN_MM]
        values = [rows[i]["radial_gap_lower_mm"] for i in indices]
        stations.append({"z_mm": z, "band_indices": indices,
                         "radial_gap_lower_mm": min(values) if values and all(v is not None for v in values) else None})
    return {"gate": "positive" if gaps_positive and axis_outside else "indeterminate",
            "minimum_radial_gap_lower_mm": min(finite_gaps) if finite_gaps else None,
            "all_axial_bands_resolved": len(finite_gaps) == len(rows),
            "all_radial_bounds_positive": gaps_positive, "axis_reference_point_mm": axis_point,
            "axis_solid_winding_number": winding, "axis_outside_material": axis_outside,
            "station_rule": "All closed bands touching each station; take their minimum lower bound.",
            "stations": stations, "bands": rows}


def read_mesh(path, manifest_path, report, label, inspector):
    path, manifest_path = Path(path), Path(manifest_path)
    report["sources"][str(path)] = sha256(path)
    report["sources"][str(manifest_path)] = sha256(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("units") != "mm" or manifest.get("status") not in (
            "concept_geometry_generated", "concept_assembly_generated"):
        raise ValueError(f"{label}: invalid_generation_header")
    matches = [item for item in manifest.get("files", []) if item.get("file") == path.name]
    if len(matches) != 1 or matches[0].get("sha256") != report["sources"][str(path)]:
        raise ValueError(f"{label}: generation_hash_mismatch")
    payload = path.read_bytes()
    if len(payload) < 84:
        raise ValueError(f"{label}: binary_stl_header_required")
    count = struct.unpack_from("<I", payload, 80)[0]
    if not count or len(payload) != 84 + 50 * count or matches[0].get("triangles") != count:
        raise ValueError(f"{label}: binary_stl_count_mismatch")
    dtype = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")])
    triangles = np.frombuffer(payload, dtype=dtype, count=count, offset=84)["vertices"].astype(np.float64)
    summary, _ = inspector.inspect_triangles(triangles)
    report["meshes"][label] = summary
    report["generation_metadata"][label] = {key: manifest.get(key) for key in ("parameters", "study", "voxel_mm", "regularization", "kernel", "grid_phase_mm")}
    if not summary["passed"]:
        raise ValueError(f"{label}: mesh_gate_failed: {','.join(summary['failures'])}")
    return triangles


def require_matched_conditions(baseline, candidate):
    allowed = {"volute_law", "chamber_profile"}
    a, b = baseline.get("parameters"), candidate.get("parameters")
    if not isinstance(a, dict) or not isinstance(b, dict):
        raise ValueError("paired_parameter_objects_required")
    if {k: v for k, v in a.items() if k not in allowed} != {k: v for k, v in b.items() if k not in allowed}:
        raise ValueError("paired_parameters_differ_beyond_law_or_profile")
    if not isinstance(baseline.get("regularization"), dict) or baseline["regularization"] != candidate.get("regularization"):
        raise ValueError("paired_regularization_mismatch")
    if baseline.get("kernel") != candidate.get("kernel"):
        raise ValueError("paired_kernel_mismatch")
    if baseline.get("grid_phase_mm") != candidate.get("grid_phase_mm"):
        raise ValueError("paired_grid_phase_mismatch")


def compare(baseline, candidate, wheel, wheel_report, wheel_report_sha256, band_mm=0.1):
    report = {"schema_version": 1, "status": "indeterminate", "gate": "indeterminate",
              "geometry_only": True, "engineering_validated": False, "manufacturing_authorized": False,
              "performance_validated": False, "thermal_clearance_validated": False, "mesh_modified": False,
              "angular_samples": 0, "axis": "global Z", "units": "mm_assumed_from_STL_generators",
              "band_mm": band_mm, "numerical_margin_mm": MARGIN_MM, "sources": {}, "meshes": {},
              "generation_metadata": {}, "profiles": {}, "errors": [],
              "comparator_sha256": sha256(__file__), "mesh_inspector_sha256": sha256(INSPECT_PATH),
              "method": "Each closed Z band uses every overlapping triangle in full. Rotor maximum is the largest vertex radius; housing minimum is distance to the entire XY-projected triangle, including its interior. No angular sampling.",
              "interpretation": "A positive bound establishes radial separation of these triangulated meshes for every rotation about Z. An indeterminate bound is not collision evidence. These are bandwise radial bounds, not minimum Euclidean, thermal or manufactured clearances."}
    try:
        if sha256(wheel_report) != wheel_report_sha256:
            raise ValueError("wheel_report_sha256_mismatch")
        spec = importlib.util.spec_from_file_location("f1_strict_mesh_inspector", INSPECT_PATH)
        inspector = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(inspector)
        rotor = read_mesh(wheel, wheel_report, report, "wheel", inspector)
        housings = {}
        for label, directory in (("baseline", Path(baseline)), ("candidate", Path(candidate))):
            if (directory / "FAILED.json").exists():
                raise ValueError(f"{label}: failed_generation_marker")
            inspection_path = directory / "inspection.json"
            report["sources"][str(inspection_path)] = sha256(inspection_path)
            inspection = json.loads(inspection_path.read_text())
            if inspection.get("geometry_passed") is not True or inspection.get("status") != "passed":
                raise ValueError(f"{label}: prior_inspection_not_passed")
            for name in ("housing.stl", "report.json"):
                if inspection.get("sources", {}).get(name) != sha256(directory / name):
                    raise ValueError(f"{label}: prior_inspection_hash_mismatch")
            housings[label] = read_mesh(directory / "housing.stl", directory / "report.json", report, label, inspector)
        require_matched_conditions(report["generation_metadata"]["baseline"], report["generation_metadata"]["candidate"])
        report["paired_conditions_match"] = True
        for label, housing in housings.items():
            report["profiles"][label] = radial_profile(rotor, housing, band_mm)
        if all(profile["gate"] == "positive" for profile in report["profiles"].values()):
            report["status"] = report["gate"] = "positive"
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        report["errors"].append(str(error))
    for path, expected in report["sources"].items():
        if not Path(path).is_file() or sha256(path) != expected:
            report["errors"].append(f"changed_during_comparison: {path}")
            report["status"] = report["gate"] = "indeterminate"
    return report


def write_outputs(report, output):
    for label, profile in report["profiles"].items():
        with (output / f"{label}-profile.csv").open("x", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=profile["bands"][0].keys())
            writer.writeheader()
            writer.writerows(profile["bands"])
    if report["profiles"]:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
            for label, profile in report["profiles"].items():
                rows = profile["bands"]
                z = [(row["z_low_mm"] + row["z_high_mm"]) / 2 for row in rows]
                axes[0].plot(z, [row["housing_min_radius_lower_mm"] for row in rows], label=f"{label}: housing lower bound")
                axes[1].plot(z, [row["radial_gap_lower_mm"] for row in rows], label=label)
            axes[0].plot(z, [row["rotor_max_radius_upper_mm"] for row in rows], "k--", label="rotor upper bound")
            axes[0].set_ylabel("Radius bound [mm]")
            axes[1].set_ylabel("Radial gap lower bound [mm]")
            axes[1].set_xlabel("Global Z [mm]")
            axes[1].axhline(0, color="black", linewidth=1)
            for axis in axes:
                axis.legend(); axis.grid(alpha=.25)
            fig.suptitle("Full-revolution geometric bounds — no thermal or performance validation")
            fig.tight_layout(); fig.savefig(output / "profiles.png", dpi=170); plt.close(fig)
            report["plot"] = "profiles.png"
        except ImportError:
            report["plot"] = "matplotlib_unavailable_csv_only"
    report["outputs_sha256"] = {path.name: sha256(path) for path in output.iterdir() if path.is_file()}
    (output / "comparison.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline", "candidate", "wheel", "wheel_report", "output"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--wheel-report-sha256", required=True)
    parser.add_argument("--band-mm", type=float, default=.1)
    args = parser.parse_args()
    if not np.isfinite(args.band_mm) or not .01 <= args.band_mm <= 1:
        parser.error("band-mm must be finite in [0.01, 1]")
    if args.output.exists():
        parser.error("output exists; refusing to overwrite")
    args.output.mkdir(parents=True, exist_ok=False)
    report = compare(args.baseline, args.candidate, args.wheel, args.wheel_report, args.wheel_report_sha256, args.band_mm)
    write_outputs(report, args.output)
    print(json.dumps({"gate": report["gate"], "errors": report["errors"], "report": str(args.output / "comparison.json")}))
    return 0 if report["gate"] == "positive" else 1


if __name__ == "__main__":
    raise SystemExit(main())
