#!/usr/bin/env python3
"""Audit every contracted assembly mesh; export geometry-only views to a new directory."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import struct

import numpy as np
import trimesh

BASE_PATH = Path(__file__).resolve().parents[1] / "inspect_mesh.py"
SPEC = importlib.util.spec_from_file_location("bionic_mesh_inspector", BASE_PATH)
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)
CONTRACT = Path(__file__).with_name("component-contract.json")
COLORS = {"compressor": "#b4c6d5", "turbine": "#c58d67", "rotor": "#d8ae62",
          "bearing_system": "#debc77", "lubrication": "#66b79d",
          "wastegate": "#be899e", "retention": "#8896a4"}


def inspect_outputs(directory, contract_path=CONTRACT):
    report = {"schema_version": 1, "status": "failed", "geometry_passed": False,
              "geometry_only": True, "engineering_validated": False, "manufacturing_authorized": False,
              "assembly_clearances_checked": False, "self_intersections_checked": False,
              "native_intersection_screen_recomputed": False, "minimum_clearance_measured": False,
              "measured_interfaces_verified": False, "mesh_modified": False,
              "inspector_sha256": BASE.sha256(Path(__file__)),
              "shared_mesh_inspector_sha256": BASE.sha256(BASE_PATH),
              "sources": {}, "meshes": {}, "errors": []}
    meshes, files = {}, []
    try:
        if (directory / "FAILED.json").exists():
            raise ValueError("generation_failed_marker_present")
        report["component_contract_sha256"] = BASE.sha256(contract_path)
        contract = json.loads(contract_path.read_text())
        expected = {item["id"]: item for item in contract["components"]}
        if len(expected) != len(contract["components"]) or not expected:
            raise ValueError("invalid_component_contract")
        path = directory / "report.json"
        manifest_bytes = path.read_bytes()
        report["sources"][path.name] = hashlib.sha256(manifest_bytes).hexdigest()
        manifest = json.loads(manifest_bytes)
        if manifest["schema_version"] != 1 or manifest["status"] != "concept_assembly_generated" or manifest["units"] != "mm":
            raise ValueError("invalid_manifest_header")
        if manifest["contract_sha256"] != report["component_contract_sha256"]:
            raise ValueError("generation_contract_sha256_mismatch")
        voxel = manifest["voxel_mm"]
        if type(voxel) not in (int, float) or not math.isfinite(voxel) or voxel <= 0 or voxel != contract["voxel_mm"]:
            raise ValueError("invalid_voxel_mm")
        files = manifest["files"]
        if not isinstance(files, list) or not all(isinstance(item, dict) for item in files):
            raise ValueError("invalid_file_records")
        ids = [item["id"] for item in files]
        if len(set(ids)) != len(ids) or set(ids) != set(expected):
            raise ValueError("component_set_mismatch")
        for item in files:
            component = expected[item["id"]]
            if item["file"] != item["id"] + ".stl" or Path(item["file"]).name != item["file"]:
                raise ValueError("component_filename_mismatch")
            if item["label"] != component["label"] or item["group"] != component["group"]:
                raise ValueError("component_description_mismatch")
            offsets = item["explode_offset_mm"]
            if not isinstance(offsets, list) or len(offsets) != 3 or not all(
                type(v) in (int, float) and math.isfinite(v) for v in offsets
            ):
                raise ValueError("invalid_explode_offset")
            if type(item["triangles"]) is not int or item["triangles"] <= 0:
                raise ValueError("invalid_triangle_count")
        if {p.name for p in directory.glob("*.stl")} != {item["file"] for item in files}:
            raise ValueError("stl_file_set_mismatch")
        required_pairs = {tuple(pair) for pair in contract["noninterference_pairs"]}
        screen = manifest["selected_voxel_intersections"]
        if not isinstance(screen, list) or not all(isinstance(item, dict) for item in screen):
            raise ValueError("invalid_native_intersection_screen")
        pairs = [(item["a"], item["b"]) for item in screen]
        if len(set(pairs)) != len(pairs) or set(pairs) != required_pairs:
            raise ValueError("native_intersection_pair_set_mismatch")
        for item in screen:
            volume = item["voxel_intersection_mm3"]
            if item["passed"] is not True or type(volume) not in (int, float) or not math.isfinite(volume) or volume != 0:
                raise ValueError("native_intersection_screen_failed")
        report["generator_selected_voxel_screen_passed"] = True
        report["generator_selected_voxel_screen_pair_count"] = len(pairs)
        report["contract_component_count"] = len(expected)
        report["voxel_mm"] = voxel
        report["display_components"] = [{k: item[k] for k in ("id", "label", "group", "explode_offset_mm")} for item in files]
    except (OSError, ValueError, KeyError, TypeError) as error:
        report["errors"].append(f"manifest: {error}")
        return report, meshes, files
    for item in files:
        try:
            path = directory / item["file"]
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            report["sources"][path.name] = digest
            if digest != item["sha256"]:
                raise ValueError("generation_sha256_mismatch")
            if item["id"] == "compressor-housing" and digest != contract["compressor_housing_sha256"]:
                raise ValueError("independent_compressor_housing_sha256_mismatch")
            if len(data) < 84:
                raise ValueError("binary_stl_header_required")
            count = struct.unpack_from("<I", data, 80)[0]
            if len(data) != 84 + 50 * count or count != item["triangles"]:
                raise ValueError("binary_stl_facet_count_mismatch")
            raw = trimesh.load_mesh(io.BytesIO(data), file_type="stl", process=False)
            if not isinstance(raw, trimesh.Trimesh) or len(raw.faces) != count:
                raise ValueError("raw_triangle_count_mismatch")
            summary, mesh = BASE.inspect_triangles(raw.triangles)
            report["meshes"][item["id"]] = summary
            meshes[item["id"]] = mesh
            if not summary["passed"] or not summary["all_input_triangles_retained"]:
                report["errors"].append(f"{item['id']}: {', '.join(summary['failures'])}")
        except (OSError, ValueError, KeyError, IndexError) as error:
            report["errors"].append(f"{item['id']}: {error}")
    try:
        for filename, expected_hash in report["sources"].items():
            if BASE.sha256(directory / filename) != expected_hash:
                raise ValueError(f"{filename}: changed_during_inspection")
        if BASE.sha256(contract_path) != report["component_contract_sha256"]:
            raise ValueError("contract_changed_during_inspection")
        if (directory / "FAILED.json").exists():
            raise ValueError("generation_failed_marker_present")
    except (OSError, ValueError) as error:
        report["errors"].append(str(error))
    report["geometry_passed"] = not report["errors"] and len(meshes) == len(expected)
    report["status"] = "passed" if report["geometry_passed"] else "failed"
    return report, meshes, files


def export_views(meshes, files, output):
    import pyvista as pv

    def surface(item, exploded=False):
        mesh = meshes[item["id"]]
        faces = np.column_stack((np.full(len(mesh.faces), 3), mesh.faces)).ravel()
        vertices = mesh.vertices + (np.asarray(item["explode_offset_mm"]) if exploded else 0)
        return pv.PolyData(vertices, faces)

    def add(plot, item, exploded=False, section=False):
        model = surface(item, exploded)
        if section and "housing" in item["id"]:
            model = model.clip(normal=(1, 0, 0), origin=(0, 0, 0), invert=False)
        plot.add_mesh(model, color=COLORS.get(item["group"], "#a6b4c2"),
                      smooth_shading=True, ambient=0.25, diffuse=0.8, specular=0.35)

    def frame(plot, title, footer):
        plot.set_background("#101820")
        plot.add_text(title, position="upper_left", font_size=16, color="#f1ebe2")
        plot.add_text(footer, position="lower_left", font_size=9, color="#afbbc5")
        plot.enable_parallel_projection()
        plot.view_vector((-3, 2, 1.8), viewup=(0, 0, 1))

    plot = pv.Plotter(shape=(1, 2), off_screen=True, window_size=(2000, 1100), border=False)
    for column, exploded, title in ((0, False, "BIONIC TURBO / ASSEMBLED DISPLAY CUT"),
                                    (1, True, "EXPLODED / CONCEPT COMPONENTS")):
        plot.subplot(0, column)
        for item in files:
            add(plot, item, exploded=exploded, section=not exploded)
        frame(plot, title, "Geometry concept | display colors only\nNo clearance, CFD, strength or mechanical validation")
    plot.screenshot(str(output / "assembly-preview.png"))
    plot.close()
    rows, columns = math.ceil(len(files) / 4), 4
    atlas = pv.Plotter(shape=(rows, columns), off_screen=True,
                       window_size=(2000, 380 * rows), border=False)
    for index, item in enumerate(files):
        atlas.subplot(index // columns, index % columns)
        add(atlas, item)
        frame(atlas, item["label"], f"{item['id']}\nIndependent display scale | concept only")
    atlas.screenshot(str(output / "component-atlas.png"))
    atlas.close()
    for exploded, name in ((False, "assembled.glb"), (True, "exploded.glb")):
        scene = trimesh.Scene()
        for item in files:
            mesh = meshes[item["id"]].copy()
            mesh.visual.face_colors = trimesh.visual.color.hex_to_rgba(COLORS.get(item["group"], "#a6b4c2"))
            transform = np.eye(4)
            transform[:3, :3] *= .001
            if exploded:
                transform[:3, 3] = np.asarray(item["explode_offset_mm"]) * .001
            scene.add_geometry(mesh, node_name=item["id"], geom_name=item["id"], transform=transform)
        scene.export(output / name, file_type="glb")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    report, meshes, files = inspect_outputs(args.directory)
    report_path = args.output / "inspection.json"
    report["status"] = "inspection_in_progress" if report["geometry_passed"] else "failed"
    report_path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    if report["geometry_passed"]:
        try:
            export_views(meshes, files, args.output)
            report["exports"] = {name: BASE.sha256(args.output / name) for name in (
                "assembly-preview.png", "component-atlas.png", "assembled.glb", "exploded.glb")}
            report["display_cut_only"] = True
            report["gltf_mm_to_m_scale"] = .001
            report["status"] = "passed"
        except Exception as error:
            report["status"] = "failed"
            report["errors"].append(f"views: {type(error).__name__}: {error}")
    report_path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": report["status"], "report": str(report_path), "errors": report["errors"]}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
