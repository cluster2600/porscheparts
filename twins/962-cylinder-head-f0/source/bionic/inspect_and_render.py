"""Screen the ribbed head and retain actual VDB exchange evidence."""
import argparse
import json
from pathlib import Path

import importlib.util

FAMILY = Path(__file__).resolve().parents[2]
ROOT = FAMILY.parent.parent
s = importlib.util.spec_from_file_location("architecture_inspection", FAMILY / "source/architecture/inspect_and_render.py")
base = importlib.util.module_from_spec(s); s.loader.exec_module(base)


def inspect(native, binary, lattice_root, parent_meshes, output):
    reference = json.loads(Path(__file__).with_name("references.json").read_text())
    actual = {str(p.relative_to(lattice_root)): base.sha(p) for p in lattice_root.glob("LatticeLibrary/**/*.cs")}
    if actual != reference["source_hashes"] or base.sha(lattice_root / "LICENSE") != reference["license_sha256"]:
        raise ValueError("LatticeLibrary differs from the recorded build input")
    if output.exists(): raise ValueError("Output must be new")
    parent = json.loads((FAMILY / "derived/architecture-report.json").read_text())
    for name in ("coolant", "dry-passages"):
        if base.sha(native / (name + ".stl")) != parent["mesh_metrics"][name]["raw_sha256"] or \
            base.sha(parent_meshes / (name + ".stl")) != parent["mesh_metrics"][name]["sha256"]:
            raise ValueError("Passage geometry changed; new independent passage inspection needed")
    if base.sha(parent_meshes / "solid.stl") != parent["mesh_metrics"]["solid"]["sha256"]:
        raise ValueError("Parent solid changed")
    fields_path = native / "native-fields-report.json"
    fields = json.loads(fields_path.read_text())
    if fields.get("vdb_domains_equal") is not True or fields.get("all_active_values_checked_bidirectionally") is not True or \
        fields.get("fluid_solver_executed") is not False or fields.get("manufacturing_authorized") is not False:
        raise ValueError("VDB exchange evidence incomplete")
    import numpy as np
    import trimesh
    import vtk
    output.mkdir(parents=True)
    old = base.load("old_head_inspection", FAMILY / "source/inspect_study.py")
    render = base.load("head_render", FAMILY / "source/enclosed/render_enclosed.py")
    boundary = base.load("head_boundaries", FAMILY / "source/audit_coolant_boundaries.py")
    solid = output / "solid.stl"
    removed = old.mesh_tools.remove_degenerate_faces(native / "solid.stl", solid)
    mesh = trimesh.load_mesh(solid, process=True)
    if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0 or not np.isfinite(mesh.vertices).all():
        raise ValueError("Invalid ribbed head mesh")
    polys, distances = {}, {}
    for name, path in (("solid", solid), ("coolant", parent_meshes / "coolant.stl"), ("dry-passages", parent_meshes / "dry-passages.stl")):
        reader = vtk.vtkSTLReader(); reader.SetFileName(str(path)); reader.Update(); polys[name] = reader.GetOutput()
        d = vtk.vtkImplicitPolyDataDistance(); d.SetInput(polys[name]); distances[name] = d
    c = vtk.vtkPolyDataConnectivityFilter(); c.SetInputData(polys["solid"])
    c.SetExtractionModeToAllRegions(); c.Update()
    if c.GetNumberOfExtractedRegions() != 1: raise ValueError("Ribs are disconnected or closed cavities remain")
    parent_reader = vtk.vtkSTLReader(); parent_reader.SetFileName(str(parent_meshes / "solid.stl")); parent_reader.Update()
    parent_distance = vtk.vtkImplicitPolyDataDistance(); parent_distance.SetInput(parent_reader.GetOutput())
    anchors = [(x, y, z) for x in (-50, 50) for y in range(-42, 43, 14) for z in range(30, 73, 14)]
    anchor_distances = [parent_distance.EvaluateFunction(p) for p in anchors]
    if any(d >= 0 for d in anchor_distances): raise ValueError("An inner cell corner misses the parent skin")
    for p in parent["dry_opening_probes_mm"]:
        if distances["solid"].EvaluateFunction(p) <= 0: raise ValueError("Ribs block a dry opening")
    water = trimesh.load_mesh(parent_meshes / "coolant.stl", process=True)
    rows, _, excluded = boundary.probes(water.triangles_center, water.face_normals,
        distances["solid"].EvaluateFunction, distances["coolant"].EvaluateFunction, (-64, 64))
    render.render(polys, output / "views")
    sources = [Path(__file__), Path(__file__).with_name("references.json"), Path(__file__).with_name("Engine.csproj"),
               Path(__file__).with_name("HeadBionicRunner.cs"), FAMILY / "derived/architecture-report.json",
               FAMILY / "source/architecture/Head962ArchitectureStudy.cs", FAMILY / "source/architecture/inspect_and_render.py"]
    report = dict(status="external_bcc_rib_study_with_verified_geometric_vdb_exchange",
        manufacturing_authorized=False, is_fitment_validated=False, material_qualified=False,
        strength_validated=False, wall_thickness_qualified=False, hydraulic_performance_validated=False,
        thermal_improvement_validated=False, structural_optimisation_executed=False,
        solid=dict(raw_sha256=base.sha(native / "solid.stl"), sha256=base.sha(solid), triangles=len(mesh.faces),
                   volume_mm3=float(mesh.volume), bounds_mm=mesh.bounds.tolist(), watertight=True,
                   consistent_winding=True, surface_components=1, removed_zero_area_faces=removed),
        passage_raw_hashes={n: base.sha(native / (n + ".stl")) for n in ("coolant", "dry-passages")},
        vdb_sha256=base.sha(native / "head-fields.vdb"), native_fields_report_sha256=base.sha(fields_path),
        native_fields_report=fields, boundary_probes=rows, excluded_terminal_samples=excluded,
        assumed_cell_anchor_points_mm=anchors, anchor_signed_distances_mm=anchor_distances,
        source_hashes={str(p.relative_to(ROOT)): base.sha(p) for p in sources},
        binary_hashes={p.name: base.sha(p) for p in (binary / "Engine.dll", binary / "PicoGK.dll", binary / "picogk.26.2.dylib")},
        images={n:dict(sha256=base.sha(output / "views" / (n + ".png")), width=1600, height=1200)
                for n in ("exterior", "cutaway", "coolant")})
    (output / "bionic-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(volume_cm3=mesh.volume / 1000, fields=fields, boundary_probes=rows), indent=2))
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for n in ("native_dir", "binary_dir", "lattice_root", "parent_meshes", "output_dir"): p.add_argument(n, type=Path)
    a = p.parse_args()
    inspect(a.native_dir.resolve(), a.binary_dir.resolve(), a.lattice_root.resolve(), a.parent_meshes.resolve(), a.output_dir.resolve())
