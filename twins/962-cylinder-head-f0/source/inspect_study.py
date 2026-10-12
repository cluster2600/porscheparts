"""Inspect actual native meshes; publish a study receipt and an inspectable preview."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FAMILY = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("mount_mesh", ROOT / "twins/993-engine-mount-system-f0/source/build_study.py")
mesh_tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mesh_tools)
NAMES = ("solid", "coolant", "dry-passages")


def water_dry_clearance(samples, dry):
    import vtk
    distance = vtk.vtkImplicitPolyDataDistance()
    distance.SetInput(dry)
    clearance = min(distance.EvaluateFunction(tuple(p)) for p in samples)
    if clearance <= 1:
        raise ValueError("Water intersects or approaches dry passages: " + str(clearance))
    return clearance


def inspect(native, output):
    import numpy as np
    import trimesh
    import vtk

    if output.exists():
        raise ValueError("Output directory must be new")
    output.mkdir(parents=True)
    meshes, polys, metrics = {}, {}, {}
    for name in NAMES:
        src = native / ("962-HEAD-STUDY-" + name.upper() + ".stl")
        dst = output / (name + ".stl")
        removed = mesh_tools.remove_degenerate_faces(src, dst)
        mesh = trimesh.load_mesh(dst, process=True)
        if not np.isfinite(mesh.vertices).all() or not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0:
            raise ValueError("Invalid study mesh: " + name)
        reader = vtk.vtkSTLReader()
        reader.SetFileName(str(dst)); reader.Update()
        poly = reader.GetOutput()
        connectivity = vtk.vtkPolyDataConnectivityFilter()
        connectivity.SetInputData(poly); connectivity.SetExtractionModeToAllRegions(); connectivity.Update()
        if connectivity.GetNumberOfExtractedRegions() != 1:
            raise ValueError("Disconnected study volume: " + name)
        meshes[name], polys[name] = mesh, poly
        metrics[name] = dict(triangles=len(mesh.faces), connected_components=1,
                             watertight=True, consistent_winding=True, volume_mm3=float(mesh.volume),
                             bounds_mm=mesh.bounds.tolist(), removed_zero_area_faces=removed,
                             sha256=hashlib.sha256(dst.read_bytes()).hexdigest())
    samples = np.vstack((meshes["coolant"].vertices, meshes["coolant"].triangles_center))
    clearance = water_dry_clearance(samples, polys["dry-passages"])
    probes = []
    spec = json.loads((FAMILY / "source/solid.json").read_text())
    z = spec["parameters"]["height_mm"]["value"] - 2
    dry_distance, solid_distance = vtk.vtkImplicitPolyDataDistance(), vtk.vtkImplicitPolyDataDistance()
    dry_distance.SetInput(polys["dry-passages"]); solid_distance.SetInput(polys["solid"])
    for x, y in [(-22, -32), (-22, 32), (22, -32), (22, 32), (-9, 0), (9, 0)]:
        point = (x, y, z)
        if dry_distance.EvaluateFunction(point) >= 0 or solid_distance.EvaluateFunction(point) <= 0:
            raise ValueError("Missing dry guide or spark opening: " + str(point))
        probes.append(point)
    report = dict(status="shape_study_only_unmeasured_interfaces_no_manufacturing",
                  manufacturing_authorized=False, is_fitment_validated=False,
                  thermal_improvement_validated=False, material_qualified=False,
                  mesh_metrics=metrics, sampled_water_dry_clearance_mm=clearance,
                  clearance_samples=len(samples), wall_thickness_qualified=False,
                  dry_opening_probes_mm=probes, valve_passage_count=4, spark_passage_count=2,
                  source_hashes={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in [ROOT / "parts/picogk-catalog/engine/Head962Study.cs", Path(__file__),
                                FAMILY / "interface-contract.json", FAMILY / "research.json",
                                *[FAMILY / "source" / (n + ".json") for n in NAMES]]},
                  runtime=dict(trimesh=trimesh.__version__, vtk=vtk.vtkVersion.GetVTKVersion()),
                  native_reports={n: json.loads((native / ("962-HEAD-STUDY-" + n.upper() + ".report.json")).read_text()) for n in NAMES})
    window = vtk.vtkRenderWindow(); window.SetOffScreenRendering(1); window.SetSize(1500, 650)
    for i in range(3):
        renderer = vtk.vtkRenderer(); renderer.SetViewport(i / 3, 0, (i + 1) / 3, 1)
        renderer.SetBackground(.055, .075, .105); window.AddRenderer(renderer)
        for name, colour in (("solid", (.7, .72, .76)), ("coolant", (.12, .65, 1)), ("dry-passages", (1, .6, .18))):
            if i == 0 and name != "solid" or i == 1 and name != "coolant":
                continue
            data = polys[name]
            if i == 2 and name == "solid":
                plane = vtk.vtkPlane(); plane.SetOrigin(0, 0, 0); plane.SetNormal(1, 0, 0)
                clip = vtk.vtkClipPolyData(); clip.SetInputData(data); clip.SetClipFunction(plane); clip.Update()
                data = clip.GetOutput()
            if i == 2 and name == "dry-passages":
                plane = vtk.vtkPlane(); plane.SetOrigin(0, 0, 0); plane.SetNormal(0, 0, 1)
                clip = vtk.vtkClipPolyData(); clip.SetInputData(data); clip.SetClipFunction(plane); clip.Update()
                data = clip.GetOutput()
            mapper = vtk.vtkPolyDataMapper(); mapper.SetInputData(data); mapper.ScalarVisibilityOff()
            actor = vtk.vtkActor(); actor.SetMapper(mapper); actor.GetProperty().SetColor(*colour)
            if i == 2 and name == "solid": actor.GetProperty().SetOpacity(.25)
            renderer.AddActor(actor)
        label = vtk.vtkTextActor()
        label.SetInput(("SOLID / F0", "WATER / F0", "SECTION / 4V + 2 PLUGS")[i] + "\nUNMEASURED STUDY - NO MANUFACTURING")
        label.GetTextProperty().SetFontSize(16); label.GetTextProperty().SetColor(.9, .93, .98)
        label.SetPosition(12, 22); renderer.AddViewProp(label)
        camera = renderer.GetActiveCamera(); camera.SetPosition(230, -270, 220); camera.SetFocalPoint(0, 0, 28)
        camera.SetViewUp(0, 0, 1); camera.ParallelProjectionOn(); renderer.ResetCamera()
        camera.SetParallelScale(160); renderer.ResetCameraClippingRange()
    window.Render()
    capture = vtk.vtkWindowToImageFilter(); capture.SetInput(window); capture.Update()
    writer = vtk.vtkPNGWriter(); writer.SetFileName(str(output / "preview.png")); writer.SetInputConnection(capture.GetOutputPort()); writer.Write()
    report["preview_sha256"] = hashlib.sha256((output / "preview.png").read_bytes()).hexdigest()
    (output / "study-report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect(args.native_dir.resolve(), args.output_dir.resolve()), indent=2))
