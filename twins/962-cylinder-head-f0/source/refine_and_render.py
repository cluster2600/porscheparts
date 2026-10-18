"""Refine the unchanged F0 to 0.5 mm and render its actual inspected meshes."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

FAMILY = Path(__file__).resolve().parents[1]
ROOT = FAMILY.parent.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def refined_spec(source):
    data = json.loads(source.read_text())
    if data["voxel_mm"] != .75 or data["status"] != "shape_study_only_unmeasured_interfaces_no_manufacturing":
        raise ValueError("Expected retained 0.75 mm F0 inputs")
    data["voxel_mm"] = .5
    return data


def render(polys, output):
    import vtk
    output.mkdir()
    scenes = (
        ("exterior", "EXTERIEUR", [("solid", (.72, .75, .78), 1)]),
        ("cutaway", "COUPE / EAU + PASSAGES", [("solid", (.72, .75, .78), 1),
            ("coolant", (.08, .55, .95), 1), ("dry-passages", (.95, .48, .14), .8)]),
        ("coolant", "CIRCUIT D'EAU", [("solid", (.65, .70, .75), .12), ("coolant", (.08, .55, .95), 1)]))
    for name, title, components in scenes:
        window = vtk.vtkRenderWindow(); window.SetOffScreenRendering(1); window.SetSize(1600, 1200)
        renderer = vtk.vtkRenderer(); renderer.SetBackground(.035, .05, .075)
        renderer.SetBackground2(.10, .14, .19); renderer.GradientBackgroundOn(); window.AddRenderer(renderer)
        for part, colour, opacity in components:
            data = polys[part]
            clips = []
            if name == "cutaway" and part == "solid": clips.append(((0, 0, 0), (1, 0, 0)))
            if part == "dry-passages": clips.append(((0, 0, 0), (0, 0, 1)))
            for origin, normal in clips:
                plane = vtk.vtkPlane(); plane.SetOrigin(*origin); plane.SetNormal(*normal)
                clip = vtk.vtkClipPolyData(); clip.SetInputData(data); clip.SetClipFunction(plane); clip.Update()
                data = clip.GetOutput()
            normals = vtk.vtkPolyDataNormals(); normals.SetInputData(data); normals.SetFeatureAngle(45)
            mapper = vtk.vtkPolyDataMapper(); mapper.SetInputConnection(normals.GetOutputPort()); mapper.ScalarVisibilityOff()
            actor = vtk.vtkActor(); actor.SetMapper(mapper)
            prop = actor.GetProperty(); prop.SetColor(*colour); prop.SetOpacity(opacity)
            prop.SetInterpolationToPhong(); prop.SetSpecular(.35); prop.SetSpecularPower(30)
            renderer.AddActor(actor)
        label = vtk.vtkTextActor(); label.SetInput(title + "\nMODELE F0 / VOXEL 0.5 mm\nInterfaces non mesurees - aucune qualification physique")
        label.SetPosition(40, 35); label.GetTextProperty().SetFontSize(24)
        label.GetTextProperty().SetColor(.90, .94, .98); renderer.AddViewProp(label)
        camera = renderer.GetActiveCamera(); camera.SetPosition(235, -270, 220); camera.SetFocalPoint(0, 0, 38)
        camera.SetViewUp(0, 0, 1); camera.ParallelProjectionOn(); renderer.ResetCamera()
        camera.SetParallelScale(125); renderer.ResetCameraClippingRange()
        window.Render()
        capture = vtk.vtkWindowToImageFilter(); capture.SetInput(window); capture.Update()
        writer = vtk.vtkPNGWriter(); writer.SetFileName(str(output / (name + ".png")))
        writer.SetInputConnection(capture.GetOutputPort()); writer.Write(); window.Finalize()


def run(engine, output):
    if engine.name != "Engine.dll": raise ValueError("Expected the pinned Engine.dll executable")
    original_path = FAMILY / "derived/study-report.json"
    original = json.loads(original_path.read_text())
    for relative, digest in original["source_hashes"].items():
        if sha(ROOT / relative) != digest:
            raise ValueError("Retained F0 source changed: " + relative)
    provenance = json.loads((FAMILY / "derived/runtime-provenance.json").read_text())
    for name, digest in provenance["artifacts"].items():
        if sha(engine.parent / name) != digest:
            raise ValueError("Native/managed runtime changed: " + name)
    if output.exists(): raise ValueError("Output directory must be new")
    output.mkdir(parents=True)
    inputs = output / "inputs"; inputs.mkdir()
    inspector = load("head_inspection", FAMILY / "source/inspect_study.py")
    lock = load("native_lock", ROOT / "parts/picogk-catalog/tools/run_part.py")
    execution = {}
    for name in inspector.NAMES:
        reference = FAMILY / "source" / (name + ".json")
        path = inputs / (name + ".json")
        path.write_text(json.dumps(refined_spec(reference), indent=2) + "\n")
        execution[name] = dict(reference=str(reference.relative_to(ROOT)), reference_sha256=sha(reference),
                               input_sha256=sha(path), changed_fields={"voxel_mm": .5})
    print("Waiting for the shared PicoGK lock", flush=True)
    lock.acquire(timeout_s=60)
    try:
        for name in inspector.NAMES:
            print("Native 0.5 mm export: " + name, flush=True)
            subprocess.run([lock.DOTNET, str(engine), str(inputs / (name + ".json")), str(output / "native")],
                           check=True, timeout=600)
    finally:
        lock.LOCK.unlink(missing_ok=True)
    version = subprocess.check_output([lock.DOTNET, "--version"], text=True).strip()
    return inspect_and_render(output, execution, provenance, original_path, version)


def inspect_and_render(output, execution, provenance, original_path, dotnet_version):
    inspector = load("head_inspection", FAMILY / "source/inspect_study.py")
    boundary = load("head_boundaries", FAMILY / "source/audit_coolant_boundaries.py")
    for name, item in execution.items():
        if sha(output / "inputs" / (name + ".json")) != item["input_sha256"]:
            raise ValueError("Execution input changed: " + name)
    print("Independent mesh inspection", flush=True)
    inspected = inspector.inspect(output / "native", output / "inspected")
    # The reused inspector hashes geometric reference templates; execution inputs are recorded separately.
    for native in inspected["native_reports"].values():
        if native["voxel_mm"] != .5: raise ValueError("Native export resolution differs")
    import vtk
    import trimesh
    readers, distances = {}, {}
    for name in inspector.NAMES:
        reader = vtk.vtkSTLReader(); reader.SetFileName(str(output / "inspected" / (name + ".stl"))); reader.Update()
        readers[name] = reader
        distance = vtk.vtkImplicitPolyDataDistance(); distance.SetInput(reader.GetOutput()); distances[name] = distance
    water = trimesh.load_mesh(output / "inspected/coolant.stl", process=True)
    rows, _, excluded = boundary.probes(water.triangles_center, water.face_normals,
        distances["solid"].EvaluateFunction, distances["coolant"].EvaluateFunction, (-80, 80))
    ports = {n: boundary.section(readers["coolant"].GetOutput(), x)[1]
             for n, x in (("inlet", -80), ("outlet", 80))}
    print("Rendering exterior, cutaway and coolant views", flush=True)
    render({n: r.GetOutput() for n, r in readers.items()}, output / "views")
    report = dict(status="same_geometry_refinement_and_views_not_physical_qualification",
        manufacturing_authorized=False, is_fitment_validated=False, hydraulic_performance_validated=False,
        thermal_improvement_validated=False, interface_conformity_validated=False, wall_thickness_qualified=False,
        reference_voxel_mm=.75, refined_voxel_mm=.5, execution_inputs=execution,
        geometry_reference_source_hashes=inspected["source_hashes"],
        source_hashes={str(p.relative_to(ROOT)): sha(p) for p in (Path(__file__), original_path,
            FAMILY / "source/audit_coolant_boundaries.py", FAMILY / "derived/runtime-provenance.json",
            ROOT / "parts/picogk-catalog/tools/run_part.py")},
        reference_runtime_provenance=provenance, executed_dotnet_version=dotnet_version,
        native_reports=inspected["native_reports"], mesh_metrics=inspected["mesh_metrics"],
        sampled_water_dry_clearance_mm=inspected["sampled_water_dry_clearance_mm"],
        clearance_samples=inspected["clearance_samples"], dry_opening_probes_mm=inspected["dry_opening_probes_mm"],
        boundary_probes=rows, excluded_terminal_face_samples=excluded, ports=ports,
        images={name: dict(sha256=sha(output / "views" / (name + ".png")), width=1600, height=1200)
                for name in ("exterior", "cutaway", "coolant")})
    (output / "refinement-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "boundary_probes": rows, "output": str(output)}, indent=2), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine_dll", type=Path); parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    run(args.engine_dll.resolve(), args.output_dir.resolve())
