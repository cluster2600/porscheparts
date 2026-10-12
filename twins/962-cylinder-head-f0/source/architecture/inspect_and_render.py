"""Independently inspect photo-informed study exports and render the actual meshes."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

FAMILY = Path(__file__).resolve().parents[2]
ROOT = FAMILY.parent.parent


def load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def inspect(native, binary, shape_root, output):
    library = json.loads(Path(__file__).with_name("references.json").read_text())["library"]
    actual = {str(p.relative_to(shape_root)): sha(p) for p in shape_root.glob("ShapeKernel/**/*.cs")}
    if actual != library["source_hashes"] or sha(shape_root / "LICENSE") != library["license_sha256"]:
        raise ValueError("Installed ShapeKernel source differs from the recorded build input")
    import numpy as np
    import trimesh
    import vtk
    if output.exists(): raise ValueError("Output must be new")
    output.mkdir(parents=True)
    old = load("old_head_inspector", FAMILY / "source/inspect_study.py")
    rendering = load("closed_head_views", FAMILY / "source/enclosed/render_enclosed.py")
    boundary = load("head_boundary", FAMILY / "source/audit_coolant_boundaries.py")
    polys, meshes, distances, metrics = {}, {}, {}, {}
    for name in ("solid", "coolant", "dry-passages"):
        raw = native / ("962-ARCHITECTURE-" + name.upper() + ".stl")
        cleaned = output / (name + ".stl")
        removed = old.mesh_tools.remove_degenerate_faces(raw, cleaned)
        mesh = trimesh.load_mesh(cleaned, process=True)
        if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0 or not np.isfinite(mesh.vertices).all():
            raise ValueError("Invalid mesh: " + name)
        reader = vtk.vtkSTLReader(); reader.SetFileName(str(cleaned)); reader.Update()
        poly = reader.GetOutput()
        connectivity = vtk.vtkPolyDataConnectivityFilter(); connectivity.SetInputData(poly)
        connectivity.SetExtractionModeToAllRegions(); connectivity.Update()
        components = connectivity.GetNumberOfExtractedRegions()
        metrics[name] = dict(raw_sha256=sha(raw), sha256=sha(cleaned), triangles=len(mesh.faces),
                             volume_mm3=float(mesh.volume), bounds_mm=mesh.bounds.tolist(),
                             watertight=True, consistent_winding=True, surface_components=components,
                             removed_zero_area_faces=removed)
        meshes[name], polys[name] = mesh, poly
        d = vtk.vtkImplicitPolyDataDistance(); d.SetInput(poly); distances[name] = d
    # A connected coolant surface and two open terminals screen against isolated jackets.
    if any(m["surface_components"] != 1 for m in metrics.values()):
        raise ValueError("Study contains disconnected surfaces or sealed cavities")
    water = meshes["coolant"]
    samples = np.vstack((water.vertices, water.triangles_center))
    clearance = old.water_dry_clearance(samples, polys["dry-passages"])
    openings = [(x, side * (25 + 14 * 33 / 75), 58) for side in (-1, 1) for x in (-18, 18)]
    openings += [(-9, 0, 88), (9, 0, 88), (0, -74, 43), (0, 74, 43)]
    for p in openings:
        if distances["dry-passages"].EvaluateFunction(p) >= 0 or distances["solid"].EvaluateFunction(p) <= 0:
            raise ValueError("Blocked dry opening: " + str(p))
    ports = [boundary.section(polys["coolant"], x)[1] for x in (-63.5, 63.5)]
    rotation = vtk.vtkTransform(); rotation.RotateZ(90)
    rotated = vtk.vtkTransformPolyDataFilter(); rotated.SetInputData(polys["dry-passages"])
    rotated.SetTransform(rotation); rotated.Update()
    gas_ports = [boundary.section(rotated.GetOutput(), x)[1] for x in (-74, 74)]
    expected = float(np.pi * 24.25 * 13.625)
    if any(abs(p["area_mm2"] / expected - 1) > .02 for p in gas_ports):
        raise ValueError("Native oval loft differs from the independent ellipse-area check")
    rows, _, excluded = boundary.probes(water.triangles_center, water.face_normals,
        distances["solid"].EvaluateFunction, distances["coolant"].EvaluateFunction, (-64, 64))
    rendering.render(polys, output / "views")
    sources = [Path(__file__), *Path(__file__).parent.glob("*.cs"), *Path(__file__).parent.glob("*.json"),
               Path(__file__).with_name("Engine.csproj"), ROOT / "parts/picogk-catalog/common/Sdf.cs",
               ROOT / "parts/picogk-catalog/common/Params.cs", ROOT / "parts/picogk-catalog/common/Runner.cs",
               FAMILY / "source/inspect_study.py", FAMILY / "source/enclosed/render_enclosed.py",
               FAMILY / "source/refine_and_render.py", FAMILY / "source/audit_coolant_boundaries.py",
               *sorted((FAMILY / "derived/qwen-assistance").glob("**/*.*"))]
    report = dict(status="photo_informed_architecture_study_not_a_dimensionally_reconstructed_962_head",
        manufacturing_authorized=False, is_fitment_validated=False, material_qualified=False,
        hydraulic_performance_validated=False, thermal_improvement_validated=False, strength_validated=False,
        wall_thickness_qualified=False, interface_conformity_validated=False,
        mesh_metrics=metrics, sampled_water_dry_clearance_mm=clearance, clearance_samples=len(samples),
        dry_opening_probes_mm=openings, coolant_terminal_sections=ports,
        gas_port_sections_rotated_z_90deg=gas_ports, analytic_gas_port_area_mm2=expected,
        boundary_probes=rows, excluded_terminal_samples=excluded,
        source_hashes={str(p.relative_to(ROOT)): sha(p) for p in sources},
        binary_hashes={p.name: sha(p) for p in (binary / "Engine.dll", binary / "PicoGK.dll", binary / "picogk.26.2.dylib")},
        executed_dotnet_version="9.0.317", runtime=dict(vtk=vtk.vtkVersion.GetVTKVersion(), trimesh=trimesh.__version__),
        native_reports={n: json.loads((native / ("962-ARCHITECTURE-" + n.upper() + ".report.json")).read_text()) for n in metrics},
        images={n:dict(sha256=sha(output / "views" / (n + ".png")), width=1600, height=1200)
                for n in ("exterior", "cutaway", "coolant")})
    (output / "architecture-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(mesh_metrics=metrics, clearance_mm=clearance, boundary_probes=rows), indent=2))
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for n in ("native_dir", "binary_dir", "shape_kernel_root", "output_dir"): p.add_argument(n, type=Path)
    a = p.parse_args()
    inspect(a.native_dir.resolve(), a.binary_dir.resolve(), a.shape_kernel_root.resolve(), a.output_dir.resolve())
