"""Render retained head meshes in English without rewriting sealed evidence."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

FAMILY = Path(__file__).resolve().parents[1]
ROOT = FAMILY.parents[1]
DELIVERY = FAMILY / "derived/family/delivery-report.json"
NAMES = ("solid", "coolant", "dry-passages")


def checked(path, expected):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != expected:
        raise ValueError("Input differs from retained evidence: " + str(path))
    return digest


def render(model, output):
    if output.exists():
        raise ValueError("Output must be new; preserve earlier views")
    report_path = ROOT / model["report_path"]
    checked(report_path, model["report_sha256"])
    report = json.loads(report_path.read_text())
    bore = model["bore_mm"]
    if report["config"]["geometry"]["bore_mm"] != bore or any(report["qualification"].values()):
        raise ValueError("Expected a matching unqualified geometry study")
    directory = ROOT / model["inspection_directory"]
    paths = {name: directory / (name + ".stl") for name in NAMES}
    hashes = {name: checked(path, report["mesh_metrics"][name]["sha256"])
              for name, path in paths.items()}
    import numpy as np
    import vtk
    from vtk.util.numpy_support import vtk_to_numpy
    cut_path = FAMILY / "source/enclosed/render_enclosed.py"
    spec = importlib.util.spec_from_file_location("retained_head_cut", cut_path)
    cut = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cut)
    polys = {}
    for name, path in paths.items():
        reader = vtk.vtkSTLReader(); reader.SetFileName(str(path)); reader.Update()
        polys[name] = reader.GetOutput()
    output.mkdir(parents=True)
    scenes = {
        "exterior": [("solid", (.72, .75, .78), 1)],
        "cutaway": [("solid", (.72, .75, .78), 1), ("coolant", (.08, .55, .95), 1),
                    ("dry-passages", (.95, .48, .14), .45)],
        "coolant": [("solid", (.65, .70, .75), .10), ("coolant", (.08, .55, .95), 1)],
        "chamber": [("solid", (.72, .75, .78), 1)],
    }
    images = {}
    for name, components in scenes.items():
        window = vtk.vtkRenderWindow(); window.SetOffScreenRendering(1); window.SetSize(1400, 1050)
        renderer = vtk.vtkRenderer(); renderer.SetBackground(.035, .05, .075)
        renderer.SetBackground2(.10, .14, .19); renderer.GradientBackgroundOn(); window.AddRenderer(renderer)
        for part, colour, opacity in components:
            poly = cut.cut_left(polys[part]) if name == "cutaway" and part == "solid" else polys[part]
            normals = vtk.vtkPolyDataNormals(); normals.SetInputData(poly); normals.SetFeatureAngle(45)
            mapper = vtk.vtkPolyDataMapper(); mapper.SetInputConnection(normals.GetOutputPort()); mapper.ScalarVisibilityOff()
            actor = vtk.vtkActor(); actor.SetMapper(mapper)
            actor.GetProperty().SetColor(*colour); actor.GetProperty().SetOpacity(opacity)
            actor.GetProperty().SetInterpolationToPhong(); renderer.AddActor(actor)
        label = vtk.vtkTextActor()
        label.SetInput(f"962 C / BIONIC DERIVATIVE / BORE {bore:g} mm\n"
                       f"{name.upper()} / GEOMETRY STUDY / 0.5 mm VOXELS\n"
                       "Published dimensions + design assumptions / unmeasured interfaces")
        label.SetPosition(30, 30); label.GetTextProperty().SetFontSize(20)
        label.GetTextProperty().SetColor(.90, .94, .98); renderer.AddViewProp(label)
        camera = renderer.GetActiveCamera()
        camera.SetPosition(*((180, -210, -210) if name == "chamber" else (235, -270, 220)))
        camera.SetFocalPoint(0, 0, 30); camera.SetViewUp(0, 0, 1); camera.ParallelProjectionOn()
        renderer.ResetCamera(); camera.SetParallelScale(125); renderer.ResetCameraClippingRange(); window.Render()
        capture = vtk.vtkWindowToImageFilter(); capture.SetInput(window); capture.Update()
        pixels = vtk_to_numpy(capture.GetOutput().GetPointData().GetScalars())
        if not np.isfinite(pixels).all() or np.ptp(pixels) < 30:
            raise ValueError("Non-finite or uniform render: " + name)
        path = output / (name + ".png")
        writer = vtk.vtkPNGWriter(); writer.SetFileName(str(path))
        writer.SetInputConnection(capture.GetOutputPort()); writer.Write(); window.Finalize()
        images[name] = dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(), width=1400, height=1050)
    receipt = dict(status="english_views_of_retained_geometry_not_physics", bore_mm=bore,
                   source_report_sha256=model["report_sha256"], input_mesh_sha256=hashes,
                   renderer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   cut_helper_sha256=hashlib.sha256(cut_path.read_bytes()).hexdigest(), images=images,
                   geometry_regenerated=False, manufacturing_authorized=False)
    (output / "render-report.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bore", type=int, choices=(95, 98, 100, 102), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    model = next(m for m in json.loads(DELIVERY.read_text())["models"] if m["bore_mm"] == args.bore)
    result = render(model, args.output)
    print(json.dumps(dict(bore_mm=args.bore, images=len(result["images"]), output=str(args.output))))
