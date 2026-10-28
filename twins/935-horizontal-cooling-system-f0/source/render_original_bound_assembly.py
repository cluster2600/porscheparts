#!/usr/bin/env python3
"""Render a reviewed 935 assembly with VTK 9.7 without editing frozen reviewers."""

import argparse
import json
from pathlib import Path

from review_refreshed_assembly import COLORS, fresh, save, sha


def render(native, exports, output):
    import vtk

    native, exports = Path(native), Path(exports)
    report = json.loads((exports / "report.json").read_text())
    receipt = json.loads((native / "receipt.json").read_text())
    if (report["native_receipt_sha256"] != sha(native / "receipt.json")
            or report["native_concatenation_coordinates_and_order_exact"] is not True):
        raise ValueError("Independent triangle transport audit required")
    out = fresh(output)
    actors, counts = {}, {}
    for row in receipt["components"]:
        path = native / row["file"]
        if sha(path) != row["sha256"]:
            raise ValueError("Native component changed")
        reader = vtk.vtkSTLReader()
        reader.SetFileName(str(path))
        reader.MergingOff()
        reader.Update()
        data = reader.GetOutput()
        if data.GetNumberOfPolys() != row["triangles"]:
            raise ValueError("Render lost triangles")
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(data)
        mapper.ScalarVisibilityOff()
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        prop = actor.GetProperty()
        prop.SetColor(*COLORS[row["id"]])
        prop.SetOpacity(1)
        prop.SetAmbient(.25)
        prop.SetDiffuse(.75)
        actors[row["id"]] = actor
        counts[row["id"]] = data.GetNumberOfPolys()

    window = vtk.vtkRenderWindow()
    window.SetSize(2400, 1600)
    window.SetOffScreenRendering(1)
    views = [
        ("935 horizontal cooling assembly - packaging study", set(actors), (1, -1.7, 1.2)),
        ("Two banks of three cylinders - shroud hidden", set(actors) - {"provisional_shroud"}, (0, -.01, 2)),
        ("Corrected scan-based rotor and observed drive", {"rotor_candidate", "drive_observed"}, (-1, -1.5, 1.2)),
        ("Rotor, admission and distribution envelope", set(actors) - {"engine_context"}, (1, -1.5, 1.3)),
    ]
    for index, (title, names, direction) in enumerate(views):
        renderer = vtk.vtkRenderer()
        x = (index % 2) * .5
        y = .5 if index < 2 else 0
        renderer.SetViewport(x, y, x + .5, y + .5)
        renderer.SetBackground(.035, .065, .085)
        for name in names:
            renderer.AddActor(actors[name])
        for label, pos, size in [
            (title, (20, 755), 21),
            ("Uncalibrated scale; unresolved interfaces; inspection only", (20, 18), 16),
        ]:
            text = vtk.vtkTextActor()
            text.SetInput(label)
            text.SetPosition(*pos)
            text.GetTextProperty().SetFontSize(size)
            text.GetTextProperty().SetColor(.95, .96, .98)
            renderer.AddViewProp(text)
        camera = renderer.GetActiveCamera()
        camera.SetPosition(*direction)
        camera.SetFocalPoint(0, 0, 0)
        camera.SetViewUp(*((0, 1, 0) if index == 1 else (0, 0, 1)))
        camera.ParallelProjectionOn()
        renderer.ResetCamera()
        renderer.ResetCameraClippingRange()
        window.AddRenderer(renderer)
    path = out / "935-assembly-review.png"
    try:
        window.Render()
        capture = vtk.vtkWindowToImageFilter()
        capture.SetInput(window)
        capture.ReadFrontBufferOff()
        capture.Update()
        writer = vtk.vtkPNGWriter()
        writer.SetFileName(str(path))
        writer.SetInputConnection(capture.GetOutputPort())
        writer.Write()
    finally:
        window.Finalize()
    if not path.is_file() or not path.stat().st_size:
        raise ValueError("Missing rendered image")
    if any(sha(native / row["file"]) != row["sha256"] for row in receipt["components"]):
        raise ValueError("Rendering changed geometry")
    save(out / "report.json", dict(
        target="935", engine_cylinders=6, geometry_triangles=counts,
        native_receipt_sha256=sha(native / "receipt.json"),
        export_report_sha256=sha(exports / "report.json"),
        image_sha256=sha(path), vtk_version=vtk.vtkVersion.GetVTKVersion(),
        decimation=False, opacity=1, exact_historical_engine_reconstructed=False,
        physical_validation=False, manufacturing_authorized=False,
    ))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native", type=Path)
    parser.add_argument("exports", type=Path)
    parser.add_argument("new_output", type=Path)
    args = parser.parse_args()
    render(args.native, args.exports, args.new_output)
