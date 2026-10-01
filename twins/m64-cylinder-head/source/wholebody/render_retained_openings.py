#!/usr/bin/env python3
"""Actual retained boundary views; no generative image or geometry repair."""
import argparse
from pathlib import Path
import signal

import numpy as np
from run_parallel_cad_trials import native

PIN = '285d0271e6e9cc4db1f80f8e7bdb54c88578c63c55ffe1ef3e442baa1cac3424'


def run(args):
    import gmsh
    import vtk
    from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray
    if (args.output.exists() or args.output.is_symlink() or args.output.with_suffix('.json').exists()
            or args.mesh.is_symlink() or native.sha256(args.mesh) != PIN):
        raise ValueError('fresh_output_and_retained_mesh_required')
    gmsh.initialize(['retained-views', '-nopopup'], readConfigFiles=False, run=False)
    gmsh.option.setNumber('General.Terminal', 0)
    try:
        gmsh.open(str(args.mesh)); tags, xyz, _ = gmsh.model.mesh.getNodes()
        order = np.argsort(tags); tags = tags[order]; points = np.array(xyz).reshape(-1, 3)[order]
        types, _, nodes = gmsh.model.mesh.getElements(2)
        if list(types) != [2]: raise ValueError('linear_retained_boundary_required')
        indices = np.searchsorted(tags, nodes[0])
        if indices.max() >= len(tags) or not np.array_equal(tags[indices], nodes[0]):
            raise ValueError('boundary_node_binding_required')
        faces = indices.reshape(-1, 3)
    finally: gmsh.finalize()
    if not np.isfinite(points).all() or not 0 < len(faces) < 2000000:
        raise ValueError('bounded_finite_surface_required')
    before = (points.tobytes(), faces.tobytes())
    cloud = vtk.vtkPoints(); cloud.SetData(numpy_to_vtk(points, deep=True))
    cells = vtk.vtkCellArray()
    cells.ImportLegacyFormat(numpy_to_vtkIdTypeArray(np.column_stack((np.full(len(faces), 3), faces)).ravel().astype(np.int64), deep=True))
    poly = vtk.vtkPolyData(); poly.SetPoints(cloud); poly.SetPolys(cells)
    mapper = vtk.vtkPolyDataMapper(); mapper.SetInputData(poly)
    window = vtk.vtkRenderWindow(); window.SetOffScreenRendering(1); window.SetSize(2400, 800 if args.detail else 1600)
    lo, hi = points.min(0), points.max(0); centre = (lo+hi)/2; span = max(hi-lo)
    directions = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    labels = ['X+', 'X-', 'Y+', 'Y-', 'Z+', 'Z-']
    if args.detail:
        directions = [(0, 1, 0), (0, -1, 0), (0, 0, -1)]
        labels = ['Ouverture laterale - Y+', 'Ouverture laterale - Y-', 'Quatre logements - Z-']
    for i, direction in enumerate(directions):
        renderer = vtk.vtkRenderer(); window.AddRenderer(renderer)
        col, row = i % 3, i // 3
        rows = 1 if args.detail else 2
        renderer.SetViewport(col/3, 1-(row+1)/rows, (col+1)/3, 1-row/rows)
        renderer.SetBackground(.065, .105, .145)
        actor = vtk.vtkActor(); actor.SetMapper(mapper)
        actor.GetProperty().SetColor(.72, .78, .82); actor.GetProperty().SetAmbient(.3)
        actor.GetProperty().SetDiffuse(.7); actor.GetProperty().SetInterpolationToFlat()
        renderer.AddActor(actor)
        focus = centre + (np.array([0, -.15*span, 0]) if args.detail and direction[2] else 0)
        camera = renderer.GetActiveCamera(); camera.SetPosition(*(focus+span*2*np.array(direction)))
        camera.SetFocalPoint(*focus); camera.SetViewUp(*( (0, 1, 0) if direction[2] else (0, 0, 1)))
        camera.ParallelProjectionOn(); camera.SetParallelScale(span*(.30 if args.detail else .65)); renderer.ResetCameraClippingRange()
        text = vtk.vtkTextActor(); text.SetInput(labels[i]+' | CAO')
        text.SetPosition(22, 760); text.GetTextProperty().SetFontSize(24); text.GetTextProperty().SetColor(.9,.95,1)
        text.GetTextProperty().SetBackgroundColor(.065,.105,.145); text.GetTextProperty().SetBackgroundOpacity(.95)
        renderer.AddViewProp(text)
        note = vtk.vtkTextActor(); note.SetInput('Corps seul, sans soupapes | Vue du maillage retenu\nScan 935 : interfaces M64 et fabrication non validees')
        note.SetPosition(22, 20); note.GetTextProperty().SetFontSize(16); note.GetTextProperty().SetColor(1,.72,.6)
        note.GetTextProperty().SetBackgroundColor(.065,.105,.145); note.GetTextProperty().SetBackgroundOpacity(.95)
        renderer.AddViewProp(note)
    window.Render()
    capture = vtk.vtkWindowToImageFilter(); capture.SetInput(window); capture.ReadFrontBufferOff(); capture.Update()
    writer = vtk.vtkPNGWriter(); writer.SetFileName(str(args.output)); writer.SetInputConnection(capture.GetOutputPort()); writer.Write()
    window.Finalize()
    if not args.output.is_file() or not args.output.stat().st_size or before != (points.tobytes(), faces.tobytes()) or native.sha256(args.mesh) != PIN:
        raise ValueError('render_or_unchanged_input_check_failed')
    args.output.chmod(0o600)
    native.save(args.output.with_suffix('.json'), dict(schema='m64-retained-openings-render/v1',
        mesh_sha256=PIN, source_sha256=native.sha256(__file__), image_sha256=native.sha256(args.output),
        triangles=len(faces), detail=args.detail, generative_image=False, smoothing=False, geometry_modified=False,
        inputs_unchanged=True, manufacturing_authorized=False))
    print(args.output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('mesh', 'output'): parser.add_argument('--'+key, type=Path, required=True)
    parser.add_argument('--detail', action='store_true', help='Zoom the two lateral openings and the four visible recesses.')
    signal.alarm(120); run(parser.parse_args())
