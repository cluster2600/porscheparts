#!/usr/bin/env python3
"""Screen head/cylinder/piston intersections and generate compact 4V packing envelopes."""
import argparse
import importlib.util
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ASSEMBLY = HERE.parent / "assembly"
sys.path.insert(0, str(ASSEMBLY))
from engine_layout import beam
from reconstruct import check_output, save, sha256
spec = importlib.util.spec_from_file_location("clearance_assembly", ASSEMBLY / "run.py")
assembly = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assembly)
from build_f37_printable_head_mesh import intersection_volume
from kinematics_f2_math import slider_delta_mm


def recipe(plan):
    if (plan["classification"] != "compact_4v_packing_envelopes_not_valve_or_head_manufacturing_geometry"
            or plan["manufacturing_authorized"] is not False or plan["engine_start_authorized"] is not False
            or plan["base_bore_mm"] != 85 or plan["hypothetical_mm_per_scan_unit"] != 1
            or plan["actual_alloy"] is not None or plan["measured_interfaces"] is not None):
        raise ValueError("Wrong variant or physical promotion")
    c = plan["candidate"]
    if any(isinstance(v, bool) or not math.isfinite(v) or v <= 0 for v in c.values()):
        raise ValueError("Invalid candidate dimension")
    if c["stem_diameter_mm"] >= min(c["intake_head_diameter_mm"], c["exhaust_head_diameter_mm"]):
        raise ValueError("Stem must fit inside the disc")
    parts, axes = [], {}
    for role, sign in (("intake", 1), ("exhaust", -1)):
        axis = [0, sign * math.sin(math.radians(c["axis_inclination_deg"])), math.cos(math.radians(c["axis_inclination_deg"]))]
        for side in (-1, 1):
            name = f"candidate_{role}_{'left' if side < 0 else 'right'}"
            center = [side * c["pair_half_pitch_mm"], sign * c["row_offset_mm"], c["disc_center_z_mm"]]
            point = lambda distance: [x + distance * a for x, a in zip(center, axis)]
            parts.append({"id": name, "add": [
                beam(point(-c["disc_thickness_mm"] / 2), point(c["disc_thickness_mm"] / 2), c[role + "_head_diameter_mm"] / 2),
                beam(center, point(c["stem_length_mm"]), c["stem_diameter_mm"] / 2)], "subtract": [], "intersect": []})
            axes[name] = axis
    return {"classification": "hypothetical_engine_components_not_manufacturing_geometry", "parts": parts}, axes


def common_volume(first, second):
    volume, method, witness = intersection_volume(first, second)
    if not math.isfinite(volume) or volume < 0:
        raise ValueError("Intersection failed: " + method)
    return {"volume_mm3_hypothesis": volume, "positive_volume_contact": volume > 0, "witness": witness}


def run(previous, dotnet, output):
    import numpy as np
    import trimesh
    output = check_output(output)
    plan = json.loads((HERE / "plan.json").read_text())
    candidate_recipe, candidate_axes = recipe(plan)
    prior = json.loads((previous / "livraison/report.json").read_text())
    execution = json.loads((ASSEMBLY / "execution-20261011.json").read_text())
    if sha256(previous / "livraison/report.json") != execution["private_report_sha256"]:
        raise ValueError("Prior geometry report changed")
    lock = json.loads((ASSEMBLY / "imports.json").read_text())
    meshes, axes, source_hashes = {}, {}, {}
    for index in (1, 4, 7, 10):
        for component in (index, index + 2):
            item = next(row for row in lock["head"]["files"] if row["id"] == f"head_component_{component:02d}")
            path = ROOT / item["source"]
            if sha256(path) != item["sha256"]:
                raise ValueError("Inherited valve or guide changed")
            source_hashes[str(path.relative_to(ROOT))] = sha256(path)
            mesh = trimesh.load_mesh(path, process=True)
            if not mesh.is_volume:
                raise ValueError("Invalid inherited mesh")
            meshes[item["id"]] = mesh
        guide = meshes[f"head_component_{index+2:02d}"]
        _, vectors = np.linalg.eigh(np.cov((guide.vertices - guide.center_mass).T))
        axis = vectors[:, -1]
        if axis[2] < 0:
            axis = -axis
        axes[f"head_component_{index:02d}"] = axis
    output.mkdir(parents=True, mode=0o700)
    save(output / "recipe.json", candidate_recipe)
    shutil.copy2(HERE / "plan.json", output / "plan.json")
    with (output / "build.log").open("x") as log:
        subprocess.run([dotnet, "build", str(ASSEMBLY / "Engine.csproj"), "-c", "Release", "-o", str(output / "app"),
                        "-p:BaseIntermediateOutputPath=" + str(output / "obj") + "/"], check=True, stdout=log, stderr=subprocess.STDOUT)
    records, audits = [], []
    for grid in (1, .5):
        native = output / f"native-{grid:g}"
        with (output / f"native-{grid:g}.log").open("x") as log:
            subprocess.run([dotnet, str(output / "app/Engine.dll"), str(output / "recipe.json"), sha256(output / "recipe.json"), str(grid), str(native)],
                           check=True, stdout=log, stderr=subprocess.STDOUT)
        candidates = {}
        for name in candidate_axes:
            candidate, audit = assembly.inspect(native / (name + ".stl"), allow_exact_zero=True)
            if not audit["passed"]:
                raise ValueError("Candidate envelope topology rejected")
            audit.update({"grid_mm": grid, "id": name})
            audits.append(audit)
            candidate.export(native / (name + "-screened.stl"))
            candidates[name] = candidate
        selected = {}
        for name, group, directory in (("cylinder", "core", "core"), ("piston", "engine", "engine")):
            path = previous / "run-003" / f"{directory}-{grid:g}" / (name + "-exact-zero-only.stl")
            audit = next(a for a in prior["geometry_audits"] if a["voxel_mm"] == grid and a["group"] == group)["meshes"][name]
            if sha256(path) != audit["candidate_sha256"]:
                raise ValueError("Prior native mesh changed")
            source_hashes[str(path.relative_to(ROOT))] = sha256(path)
            selected[name] = trimesh.load_mesh(path, process=True)
            if not selected[name].is_volume:
                raise ValueError("Invalid prior native mesh")
        matrix = np.eye(4)
        matrix[:3, :3] = [[-1, 0, 0], [0, 0, 1], [0, 1, 0]]
        matrix[:3, 3] = [0, 0, -plan["cylinder_length_mm"]]
        selected["cylinder"].apply_transform(matrix)
        matrix[:3, 3] = [0, 0, plan["rod_length_mm"] + plan["stroke_mm"] / 2 - plan["head_deck_mm"]]
        selected["piston"].apply_transform(matrix)
        for variant, valves, directions in (("inherited", {n: meshes[n] for n in axes}, axes), ("compact_candidate", candidates, candidate_axes)):
            for name, valve in valves.items():
                for lift in plan["lift_cases_mm"]:
                    moving = valve.copy()
                    moving.apply_translation(-np.asarray(directions[name]) * lift)
                    cylinder_contact = common_volume(moving, selected["cylinder"])
                    for angle in plan["crank_angle_cases_deg_from_positive_bank_tdc"]:
                        piston = selected["piston"].copy()
                        piston.apply_translation([0, 0, slider_delta_mm(angle, plan["stroke_mm"] / 2, plan["rod_length_mm"])])
                        records.append({"grid_mm": grid, "variant": variant, "valve": name, "lift_mm": lift, "crank_angle_deg": angle,
                                        "valve_cylinder": cylinder_contact, "valve_piston": common_volume(moving, piston)})
        if grid == .5:
            scene = trimesh.Scene()
            for variant, valves, directions, offset in (("inherited", {n: meshes[n] for n in axes}, axes, -90), ("compact_candidate", candidates, candidate_axes, 90)):
                for name, mesh in {**selected, **valves}.items():
                    display = mesh.copy()
                    if name in directions:
                        display.apply_translation(-np.asarray(directions[name]) * 2)
                    display.apply_translation([offset, 0, 0])
                    display.apply_scale(.001)
                    display.visual.face_colors = [175, 115, 65, 255] if variant == "inherited" else [50, 150, 175, 255]
                    scene.add_geometry(display, geom_name=variant + "_" + name, node_name=variant + "_" + name)
            scene.export(output / "head-interface-comparison.glb")
    paths = [HERE / "check_clearance.py", HERE / "plan.json", ASSEMBLY / "Program.cs", ASSEMBLY / "Engine.csproj", ASSEMBLY / "run.py",
             ASSEMBLY / "engine_layout.py", ROOT / "parts/picogk-catalog/common/Sdf.cs", ROOT / "twins/reference-917-engine/source/build_f37_printable_head_mesh.py",
             ROOT / "twins/reference-917-engine/source/kinematics_f2_math.py"]
    report = {"classification": "sampled_mesh_contact_screen_with_compact_4v_packing_envelopes_no_release", "records": records,
              "native_candidate_audits": audits, "source_sha256": {str(p.relative_to(ROOT)): sha256(p) for p in paths},
              "private_input_sha256": source_hashes, "previous_geometry_report_sha256": sha256(previous / "livraison/report.json"),
              "geometry_changed_in_previous_delivery": False, "collision_method": "Manifold_triangle_mesh_boolean_not_exact_BRep_or_metrology",
              "sampled_poses_not_continuous_sweep": True, "cam_law_validated": False, "positive_clearance_validated": False,
              "new_head_body_seats_guides_ports_required": True, "manufacturing_authorized": False, "functional_assembly_accepted": False}
    save(output / "contact-report.json", report)
    print(json.dumps({"poses": len(records), "candidate_audits": len(audits), "output": str(output)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous", type=Path, required=True)
    parser.add_argument("--dotnet", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.previous.resolve(), args.dotnet, args.output)
