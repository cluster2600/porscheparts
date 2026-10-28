"""Show the complete bounded analysis surface and locate its remaining poor facets."""
import json
import signal
import sys
from pathlib import Path

import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray
from run_reconstruction import ROOT, sha

signal.alarm(180)
sys.path.insert(0, str(ROOT / 'twins/reference-917-engine/source'))
from render_scan_contour_patch_reconstruction_f43 import text_actor

phase = ROOT / 'work/935-local-relocation-20261022'
proof = json.loads((phase / 'geometry-assessment-002.json').read_text())
source = phase / 'candidate-002/candidate.npz'
assert proof['complete_surface_bound_established'] and sha(source) == proof['output_sha256']['candidate.npz']
with np.load(source) as data:
    vertices, faces = data['vertices'].astype(float), data['faces'].astype(np.int64)
t = vertices[faces]
quality = 2 * np.sqrt(3) * np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1) / np.sum((t[:, [1, 2, 0]] - t) ** 2, axis=(1, 2))
poor = quality < .05
assert len(faces) == proof['triangles'] and int(poor.sum()) == proof['poor_triangles_below_0_05'] == 0
points = vtk.vtkPoints(); points.SetData(numpy_to_vtk(vertices, deep=True))
cells = vtk.vtkCellArray(); cells.SetCells(len(faces), numpy_to_vtkIdTypeArray(np.column_stack([np.full(len(faces), 3), faces]).ravel(), deep=True))
mesh = vtk.vtkPolyData(); mesh.SetPoints(points); mesh.SetPolys(cells)
assert mesh.GetNumberOfPolys() == len(faces)
mapper = vtk.vtkPolyDataMapper(); mapper.SetInputData(mesh); mapper.ScalarVisibilityOff()
surface = vtk.vtkActor(); surface.SetMapper(mapper); surface.GetProperty().SetColor(.23, .59, .78); surface.GetProperty().SetAmbient(.3)
locations = t[poor].mean(axis=1)
mark_points = vtk.vtkPoints(); mark_points.SetData(numpy_to_vtk(locations, deep=True))
mark_mesh = vtk.vtkPolyData(); mark_mesh.SetPoints(mark_points)
mark_mesh.SetVerts(vtk.vtkCellArray())
for index in range(len(locations)):
    mark_mesh.GetVerts().InsertNextCell(1); mark_mesh.GetVerts().InsertCellPoint(index)
mark_mapper = vtk.vtkPolyDataMapper(); mark_mapper.SetInputData(mark_mesh)
marks = vtk.vtkActor(); marks.SetMapper(mark_mapper); marks.GetProperty().SetColor(1, .28, .18); marks.GetProperty().SetPointSize(8); marks.GetProperty().RenderPointsAsSpheresOn()
window = vtk.vtkRenderWindow(); window.SetSize(2400, 1200); window.SetOffScreenRendering(1)
centre = (vertices.min(axis=0) + vertices.max(axis=0)) / 2
views = [('935 rotor: complete relocated analysis surface', (1, -1.5, 1.1)), ('Top view: no triangle below quality 0.05', (0, -.001, 2))]
for index, (title, direction) in enumerate(views):
    renderer = vtk.vtkRenderer(); renderer.SetViewport(index / 2, 0, (index + 1) / 2, 1); renderer.SetBackground(.035, .065, .085)
    renderer.AddActor(surface)
    if index and len(locations): renderer.AddActor(marks)
    renderer.AddViewProp(text_actor(title, 25, 1140, 24))
    renderer.AddViewProp(text_actor('873,288 triangles; no display decimation', 25, 65, 21))
    renderer.AddViewProp(text_actor('Source-coordinate inspection; scale and CFD unqualified', 25, 28, 19))
    camera = renderer.GetActiveCamera(); camera.SetFocalPoint(*centre); camera.SetPosition(*(centre + np.array(direction) * np.ptp(vertices, axis=0).max())); camera.SetViewUp(*((0, 1, 0) if index else (0, 0, 1))); camera.ParallelProjectionOn()
    renderer.ResetCamera(); renderer.ResetCameraClippingRange(); window.AddRenderer(renderer)
image = phase / '935-relocated-rotor-002.png'
assert not image.exists() and not image.is_symlink()
try:
    window.Render(); capture = vtk.vtkWindowToImageFilter(); capture.SetInput(window); capture.ReadFrontBufferOff(); capture.Update()
    writer = vtk.vtkPNGWriter(); writer.SetFileName(str(image)); writer.SetInputConnection(capture.GetOutputPort()); writer.Write()
finally:
    window.Finalize()
assert image.is_file() and image.stat().st_size > 0 and sha(source) == proof['output_sha256']['candidate.npz']
receipt = {'source_sha256': sha(__file__), 'input_sha256': sha(source), 'assessment_sha256': sha(phase / 'geometry-assessment-002.json'), 'image_sha256': sha(image), 'triangles': len(faces), 'poor_triangle_locations': int(poor.sum()), 'decimation': False, 'display_kind': 'actual analysis triangles; red points mark poor-face centroids, not flow or stress', 'scale_verified': False, 'CFD_accepted': False, 'manufacturing_authorized': False}
with (phase / 'rotor-visual-receipt-003.json').open('x') as stream:
    json.dump(receipt, stream, indent=2)
print(json.dumps(receipt), flush=True)
