"""Independent mesh, passage and flow-section screens for the 4 L flow variant."""
import argparse
import importlib.util
import json
from pathlib import Path

SOURCE = Path(__file__).resolve().parent
FAMILY = SOURCE.parents[1]
ROOT = FAMILY.parents[1]
spec = importlib.util.spec_from_file_location("head_inspection_helpers", SOURCE.parent / "architecture/inspect_and_render.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def render(polys, output):
    import vtk
    closed = base.load("closed_section_method", SOURCE.parent / "enclosed/render_enclosed.py")
    output.mkdir()
    scenes = (
        ("exterior", "ENVELOPPE / PORTS D'EAU 22 mm", [("solid", (.72, .75, .78), 1)]),
        ("cutaway", "COUPE / EAU BLEUE / VOLUMES SECS ORANGE", [
            ("solid", (.72, .75, .78), 1), ("coolant", (.08, .55, .95), 1),
            ("dry-passages", (.95, .48, .14), .45)]),
        ("coolant", "RESEAU D'EAU / RESERVATIONS DE DEUX ALLUMAGES", [
            ("solid", (.65, .70, .75), .10), ("coolant", (.08, .55, .95), 1)]),
        ("chamber", "CHAMBRE / 4 PASSAGES DE SOUPAPES / 2 PUITS D'ALLUMAGE", [
            ("solid", (.72, .75, .78), 1)]))
    for name, title, components in scenes:
        window = vtk.vtkRenderWindow(); window.SetOffScreenRendering(1); window.SetSize(1600, 1200)
        renderer = vtk.vtkRenderer(); renderer.SetBackground(.035, .05, .075)
        renderer.SetBackground2(.10, .14, .19); renderer.GradientBackgroundOn(); window.AddRenderer(renderer)
        for part, colour, opacity in components:
            poly = polys[part]
            if name == "cutaway" and part == "solid":
                poly = closed.cut_left(poly)
            normals = vtk.vtkPolyDataNormals(); normals.SetInputData(poly); normals.SetFeatureAngle(45)
            mapper = vtk.vtkPolyDataMapper(); mapper.SetInputConnection(normals.GetOutputPort()); mapper.ScalarVisibilityOff()
            actor = vtk.vtkActor(); actor.SetMapper(mapper)
            prop = actor.GetProperty(); prop.SetColor(*colour); prop.SetOpacity(opacity)
            prop.SetInterpolationToPhong(); prop.SetSpecular(.35); prop.SetSpecularPower(30); renderer.AddActor(actor)
        label = vtk.vtkTextActor()
        label.SetInput(title + "\nMEZGER 4 L BITURBO / SP95 / ETUDE 0.5 mm\nInterfaces non mesurees - aucune autorisation de fabrication")
        label.SetPosition(35, 35); label.GetTextProperty().SetFontSize(22)
        label.GetTextProperty().SetColor(.90, .94, .98); renderer.AddViewProp(label)
        camera = renderer.GetActiveCamera()
        camera.SetPosition(*( (180, -210, -210) if name == "chamber" else (235, -270, 220)))
        camera.SetFocalPoint(0, 0, 30); camera.SetViewUp(0, 0, 1)
        camera.ParallelProjectionOn(); renderer.ResetCamera(); camera.SetParallelScale(125)
        renderer.ResetCameraClippingRange(); window.Render()
        capture = vtk.vtkWindowToImageFilter(); capture.SetInput(window); capture.Update()
        writer = vtk.vtkPNGWriter(); writer.SetFileName(str(output / (name + ".png")))
        writer.SetInputConnection(capture.GetOutputPort()); writer.Write(); window.Finalize()


def inspect(native, binary, shape_root, output):
    import numpy as np
    import trimesh
    import vtk
    if output.exists():
        raise ValueError("Output must be new; retain rejected runs")
    for folder, reference in (
        (shape_root, json.loads((SOURCE.parent / "architecture/references.json").read_text())["library"]),
        (shape_root.parent / "LEAP71_LatticeLibrary", json.loads((SOURCE.parent / "bionic/references.json").read_text())),
    ):
        pattern = "ShapeKernel/**/*.cs" if "ShapeKernel" in folder.name else "LatticeLibrary/**/*.cs"
        if {str(p.relative_to(folder)): base.sha(p) for p in folder.glob(pattern)} != reference["source_hashes"]:
            raise ValueError("Library source changed")
        if base.sha(folder / "LICENSE") != reference["license_sha256"]:
            raise ValueError("Library licence changed")
    output.mkdir(parents=True)
    old = base.load("retained_head_mesh_checks", SOURCE.parent / "inspect_study.py")
    boundary = base.load("retained_boundary_probes", SOURCE.parent / "audit_coolant_boundaries.py")
    polys, distances, metrics, meshes = {}, {}, {}, {}
    for name in ("solid", "coolant", "dry-passages"):
        raw, cleaned = native / (name + ".stl"), output / (name + ".stl")
        removed = old.mesh_tools.remove_degenerate_faces(raw, cleaned)
        mesh = trimesh.load_mesh(cleaned, process=True)
        if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0 or not np.isfinite(mesh.vertices).all():
            raise ValueError("Invalid mesh: " + name)
        reader = vtk.vtkSTLReader(); reader.SetFileName(str(cleaned)); reader.Update()
        polys[name], meshes[name] = reader.GetOutput(), mesh
        connectivity = vtk.vtkPolyDataConnectivityFilter(); connectivity.SetInputData(polys[name])
        connectivity.SetExtractionModeToAllRegions(); connectivity.Update()
        metrics[name] = dict(raw_sha256=base.sha(raw), sha256=base.sha(cleaned), triangles=len(mesh.faces),
                             volume_mm3=float(mesh.volume), bounds_mm=mesh.bounds.tolist(),
                             watertight=True, consistent_winding=True,
                             surface_components=connectivity.GetNumberOfExtractedRegions(),
                             removed_zero_area_faces=removed)
        distance = vtk.vtkImplicitPolyDataDistance(); distance.SetInput(polys[name]); distances[name] = distance
    if any(m["surface_components"] != 1 for m in metrics.values()):
        (output / "rejected-components.json").write_text(json.dumps(metrics, indent=2) + "\n")
        raise ValueError("Disconnected surface or sealed cavity; retain this rejected run")
    water = meshes["coolant"]
    samples = np.vstack((water.vertices, water.triangles_center))
    clearance = old.water_dry_clearance(samples, polys["dry-passages"])
    if clearance < 4:
        raise ValueError("Sampled dry/wet separation below the unchanged 4 mm screen")
    openings = [(x, side * (25 + 14 * 33 / 75), 58) for side in (-1, 1) for x in (-20, 20)]
    openings += [(0, 0, 58), (38, 0, 58), (0, -74, 43), (0, 74, 43)]
    for p in openings:
        if distances["dry-passages"].EvaluateFunction(p) >= 0 or distances["solid"].EvaluateFunction(p) <= 0:
            raise ValueError("Blocked dry opening: " + str(p))
    budget_path = FAMILY / "derived/mezger-sp95-budget.json"
    budget = json.loads(budget_path.read_text())
    q = budget["nominal"]["results"]["water_each_head_l_min"] / 60000
    ports = [boundary.section(polys["coolant"], x)[1] for x in (-75.5, 75.5)]
    for port in ports:
        port["mean_speed_at_budget_flow_m_s"] = q / (port["area_mm2"] * 1e-6)
        if port["mean_speed_at_budget_flow_m_s"] > 3:
            raise ValueError("Port section misses the recorded 3 m/s design target")
    rows, _, excluded = boundary.probes(water.triangles_center, water.face_normals,
        distances["solid"].EvaluateFunction, distances["coolant"].EvaluateFunction, (-76, 76))
    fields = json.loads((native / "native-fields-report.json").read_text())
    if fields["vdb_domains_equal"] is not True or fields["all_active_values_checked_bidirectionally"] is not True:
        raise ValueError("Native VDB roundtrip failed")
    render(polys, output / "views")
    sources = [p for p in SOURCE.iterdir() if p.is_file()]
    sources += [budget_path, SOURCE.parent / "inspect_study.py", SOURCE.parent / "audit_coolant_boundaries.py",
                SOURCE.parent / "enclosed/render_enclosed.py", SOURCE.parent / "architecture/inspect_and_render.py",
                SOURCE.parent / "architecture/references.json", SOURCE.parent / "bionic/references.json"]
    report = dict(status="flow_sized_4l_sp95_geometry_study", mesh_metrics=metrics,
        sampled_water_dry_clearance_mm=clearance, clearance_samples=len(samples),
        dry_opening_probes_mm=openings, coolant_terminal_sections=ports,
        assumed_flow_each_head_l_min=q * 60000, boundary_probes=rows, excluded_terminal_samples=excluded,
        native_fields_report=fields, vdb_sha256=base.sha(native / "head-fields.vdb"),
        grid_hashes={p.name: base.sha(p) for p in native.glob("coolant-cells-*.json")},
        source_hashes={str(p.relative_to(ROOT)): base.sha(p) for p in sources},
        binary_hashes={p.name: base.sha(p) for p in binary.iterdir() if p.suffix in (".dll", ".dylib")},
        qualification=dict(is_fitment_validated=False, material_qualified=False, strength_validated=False,
            wall_thickness_qualified=False, hydraulic_performance_validated=False,
            thermal_improvement_validated=False, interface_conformity_validated=False, manufacturing_authorized=False),
        images={p.name: dict(sha256=base.sha(p), width=1600, height=1200) for p in (output / "views").glob("*.png")})
    (output / "study-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(mesh_metrics=metrics, clearance_mm=clearance, ports=ports, boundary_probes=rows), indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("native", "binary", "shape_root", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    inspect(*(p.resolve() for p in (args.native, args.binary, args.shape_root, args.output)))
