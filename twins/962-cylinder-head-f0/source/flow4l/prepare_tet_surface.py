"""Derive a bounded-error, closed coolant surface for tetrahedral meshing."""
import argparse
import hashlib
import json
from pathlib import Path


def prepare(source, output):
    import numpy as np
    import trimesh
    import vtk
    from vtk.util.numpy_support import vtk_to_numpy
    if output.exists():
        raise ValueError("Output must be new")
    reader = vtk.vtkSTLReader(); reader.SetFileName(str(source)); reader.Update()
    original = reader.GetOutput()
    decimation = vtk.vtkDecimatePro(); decimation.SetInputData(original)
    decimation.SetTargetReduction(.9); decimation.PreserveTopologyOn(); decimation.BoundaryVertexDeletionOff()
    decimation.SetErrorIsAbsolute(True); decimation.SetAbsoluteError(.1); decimation.AccumulateErrorOn(); decimation.Update()
    surface = decimation.GetOutput()
    deviations = []
    for a, b in ((original, surface), (surface, original)):
        distance = vtk.vtkImplicitPolyDataDistance(); distance.SetInput(b)
        deviations.append(max(abs(distance.EvaluateFunction(a.GetPoint(i))) for i in range(a.GetNumberOfPoints())))
    if max(deviations) > .25:
        raise ValueError("Derived surface exceeds the fixed 0.25 mm sampled deviation limit")
    output.mkdir(parents=True)
    path = output / "coolant-surface.stl"
    writer = vtk.vtkSTLWriter(); writer.SetInputData(surface); writer.SetFileTypeToBinary(); writer.SetFileName(str(path)); writer.Write()
    old, mesh = trimesh.load_mesh(source, process=True), trimesh.load_mesh(path, process=True)
    if not mesh.is_watertight or not mesh.is_winding_consistent or abs(mesh.volume / old.volume - 1) > .02:
        raise ValueError("Surface closure or volume-deviation screen failed")
    points = vtk_to_numpy(surface.GetPoints().GetData())
    triangles = vtk_to_numpy(surface.GetPolys().GetData()).reshape(-1, 4)[:, 1:]
    np.savez_compressed(output / "surface.npz", points_mm=points, triangles=triangles)
    report = dict(status="bounded_surface_derivative_not_a_new_master", original_triangles=original.GetNumberOfCells(),
        triangles=surface.GetNumberOfCells(), sampled_vertex_deviation_each_direction_mm=deviations,
        volume_mm3=mesh.volume, relative_volume_change=mesh.volume / old.volume - 1,
        watertight=True, consistent_winding=True,
        hashes={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (
            Path(__file__), source, path, output / "surface.npz")}, manufacturing_authorized=False)
    (output / "surface-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("source", type=Path); parser.add_argument("output", type=Path)
    args = parser.parse_args(); prepare(args.source.resolve(), args.output.resolve())
