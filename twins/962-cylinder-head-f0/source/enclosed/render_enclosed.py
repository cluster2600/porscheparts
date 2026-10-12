"""Inspect and render the continuous stock-envelope study; no fit or strength claim."""
import argparse
import importlib.util
import json
from pathlib import Path

FAMILY = Path(__file__).resolve().parents[2]
ROOT = FAMILY.parent.parent
spec = importlib.util.spec_from_file_location("head_views", FAMILY / "source/refine_and_render.py")
views = importlib.util.module_from_spec(spec); spec.loader.exec_module(views)


def cut_left(poly):
    import vtk
    plane = vtk.vtkPlane(); plane.SetOrigin(.25, 0, 0); plane.SetNormal(-1, 0, 0)
    planes = vtk.vtkPlaneCollection(); planes.AddItem(plane)
    clip = vtk.vtkClipClosedSurface(); clip.SetInputData(poly); clip.SetClippingPlanes(planes); clip.Update()
    result = clip.GetOutput()
    if not result.GetNumberOfCells() or result.GetBounds()[1] > .25001:
        raise ValueError("Incorrect virtual cut side")
    edges = vtk.vtkFeatureEdges(); edges.SetInputData(result)
    edges.BoundaryEdgesOn(); edges.NonManifoldEdgesOn(); edges.FeatureEdgesOff(); edges.ManifoldEdgesOff(); edges.Update()
    if edges.GetOutput().GetNumberOfCells(): raise ValueError("Virtual cut is not closed")
    return result


def render(polys, output):
    import vtk
    output.mkdir()
    scenes = (
        ("exterior", "ENVELOPPE CONTINUE", [("solid", (.72, .75, .78), 1)]),
        ("cutaway", "COUPE DE L'ENVELOPPE", [("solid", (.72, .75, .78), 1),
            ("coolant", (.08, .55, .95), 1), ("dry-passages", (.95, .48, .14), .8)]),
        ("coolant", "EAU DANS L'ENVELOPPE", [("solid", (.65, .70, .75), .12), ("coolant", (.08, .55, .95), 1)]))
    for name, title, components in scenes:
        window = vtk.vtkRenderWindow(); window.SetOffScreenRendering(1); window.SetSize(1600, 1200)
        renderer = vtk.vtkRenderer(); renderer.SetBackground(.035, .05, .075)
        renderer.SetBackground2(.10, .14, .19); renderer.GradientBackgroundOn(); window.AddRenderer(renderer)
        for part, colour, opacity in components:
            data = polys[part]
            if name == "cutaway" and part == "solid": data = cut_left(data)
            if part == "dry-passages":
                plane = vtk.vtkPlane(); plane.SetOrigin(0, 0, 0); plane.SetNormal(0, 0, 1)
                clip = vtk.vtkClipPolyData(); clip.SetInputData(data); clip.SetClipFunction(plane); clip.Update(); data = clip.GetOutput()
            normals = vtk.vtkPolyDataNormals(); normals.SetInputData(data); normals.SetFeatureAngle(45)
            mapper = vtk.vtkPolyDataMapper(); mapper.SetInputConnection(normals.GetOutputPort()); mapper.ScalarVisibilityOff()
            actor = vtk.vtkActor(); actor.SetMapper(mapper)
            prop = actor.GetProperty(); prop.SetColor(*colour); prop.SetOpacity(opacity)
            prop.SetInterpolationToPhong(); prop.SetSpecular(.35); prop.SetSpecularPower(30); renderer.AddActor(actor)
        label = vtk.vtkTextActor(); label.SetInput(title + "\nETUDE F0 / VOXEL 0.5 mm\nEnveloppe hypothetique - interfaces non mesurees")
        label.SetPosition(40, 35); label.GetTextProperty().SetFontSize(24)
        label.GetTextProperty().SetColor(.90, .94, .98); renderer.AddViewProp(label)
        camera = renderer.GetActiveCamera(); camera.SetPosition(235, -270, 220); camera.SetFocalPoint(0, 0, 38)
        camera.SetViewUp(0, 0, 1); camera.ParallelProjectionOn(); renderer.ResetCamera(); camera.SetParallelScale(125)
        renderer.ResetCameraClippingRange(); window.Render()
        capture = vtk.vtkWindowToImageFilter(); capture.SetInput(window); capture.Update()
        writer = vtk.vtkPNGWriter(); writer.SetFileName(str(output / (name + ".png")))
        writer.SetInputConnection(capture.GetOutputPort()); writer.Write(); window.Finalize()


def inspect_and_render(native, refined, binary_dir, output):
    import numpy as np
    import trimesh
    import vtk
    if output.exists(): raise ValueError("Output must be new")
    parent = json.loads((FAMILY / "derived/refinement-report.json").read_text())
    for name in ("coolant", "dry-passages"):
        if views.sha(refined / (name + ".stl")) != parent["mesh_metrics"][name]["sha256"]:
            raise ValueError("Refined passage source changed")
    output.mkdir(parents=True)
    inspector = views.load("inspection", FAMILY / "source/inspect_study.py")
    solid_path = output / "solid.stl"
    removed = inspector.mesh_tools.remove_degenerate_faces(native / "962-HEAD-ENCLOSED-STUDY.stl", solid_path)
    mesh = trimesh.load_mesh(solid_path, process=True)
    if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0 or not np.isfinite(mesh.vertices).all():
        raise ValueError("Invalid enclosed solid")
    polys, distances = {}, {}
    for name, path in (("solid", solid_path), ("coolant", refined / "coolant.stl"), ("dry-passages", refined / "dry-passages.stl")):
        reader = vtk.vtkSTLReader(); reader.SetFileName(str(path)); reader.Update(); polys[name] = reader.GetOutput()
        distance = vtk.vtkImplicitPolyDataDistance(); distance.SetInput(polys[name]); distances[name] = distance
    connectivity = vtk.vtkPolyDataConnectivityFilter(); connectivity.SetInputData(polys["solid"])
    connectivity.SetExtractionModeToAllRegions(); connectivity.Update()
    if connectivity.GetNumberOfExtractedRegions() != 1: raise ValueError("Enclosed solid is disconnected")
    probes = [(-78, 0, 45), (78, 0, 45), (0, -78, 45), (0, 78, 45), (0, 0, 88), (60, 60, 45), (-60, -60, 45)]
    signed = [distances["solid"].EvaluateFunction(p) for p in probes]
    if any(d >= 0 for d in signed): raise ValueError("Missing stock-envelope material")
    for p in parent["dry_opening_probes_mm"]:
        if distances["solid"].EvaluateFunction(tuple(p)) <= 0: raise ValueError("Blocked guide or plug opening")
    boundary = views.load("boundaries", FAMILY / "source/audit_coolant_boundaries.py")
    water = trimesh.load_mesh(refined / "coolant.stl", process=True)
    rows, _, excluded = boundary.probes(water.triangles_center, water.face_normals,
        distances["solid"].EvaluateFunction, distances["coolant"].EvaluateFunction, (-80, 80))
    render(polys, output / "views")
    source_paths = [Path(__file__), FAMILY / "source/enclosed/Engine.csproj", FAMILY / "source/enclosed-solid.json",
        ROOT / "parts/picogk-catalog/engine/Head962EnclosedStudy.cs", ROOT / "parts/picogk-catalog/engine/Head962Study.cs",
        ROOT / "parts/picogk-catalog/common/Sdf.cs", ROOT / "parts/picogk-catalog/common/Params.cs",
        ROOT / "parts/picogk-catalog/common/Runner.cs",
        FAMILY / "source/refine_and_render.py", FAMILY / "source/inspect_study.py", FAMILY / "source/audit_coolant_boundaries.py",
        FAMILY / "derived/refinement-report.json"]
    report = dict(status="continuous_stock_envelope_study_not_functional_head", manufacturing_authorized=False,
        is_fitment_validated=False, wall_thickness_qualified=False, hydraulic_performance_validated=False,
        thermal_improvement_validated=False, strength_validated=False, interface_conformity_validated=False,
        envelope_assumptions=dict(width_mm=160, depth_mm=160, height_mm=90, corner_radius_mm=8, basis="assumption"),
        mesh=dict(sha256=views.sha(solid_path), triangles=len(mesh.faces), volume_mm3=float(mesh.volume),
                  bounds_mm=mesh.bounds.tolist(), watertight=True, consistent_winding=True, connected_components=1,
                  removed_zero_area_faces=removed), material_probe_positions_mm=probes, material_probe_signed_distances_mm=signed,
        dry_opening_probes_mm=parent["dry_opening_probes_mm"], boundary_probes=rows, excluded_terminal_face_samples=excluded,
        passage_mesh_hashes={n: parent["mesh_metrics"][n]["sha256"] for n in ("coolant", "dry-passages")},
        native_report=json.loads((native / "962-HEAD-ENCLOSED-STUDY.report.json").read_text()),
        source_hashes={str(p.relative_to(ROOT)): views.sha(p) for p in source_paths},
        binary_hashes={p.name: views.sha(p) for p in (binary_dir / "Engine.dll", binary_dir / "PicoGK.dll", binary_dir / "picogk.26.2.dylib")},
        images={n: dict(sha256=views.sha(output / "views" / (n + ".png")), width=1600, height=1200) for n in ("exterior", "cutaway", "coolant")})
    (output / "enclosed-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"volume_cm3": mesh.volume / 1000, "boundary_probes": rows, "output": str(output)}, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("native_dir", "refined_dir", "binary_dir", "output_dir"): parser.add_argument(name, type=Path)
    args = parser.parse_args()
    inspect_and_render(args.native_dir.resolve(), args.refined_dir.resolve(), args.binary_dir.resolve(), args.output_dir.resolve())
