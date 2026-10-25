"""Show all analysis triangles and localized cycle paths; no geometry correction."""
import json
import signal
import sys
import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray
from run_reconstruction import ROOT, sha, save

signal.alarm(180)
sys.path.insert(0, str(ROOT/'twins/reference-917-engine/source'))
from render_scan_contour_patch_reconstruction_f43 import text_actor

out = ROOT/'work/935-snap-resume-20261025/surface-cycles-001'
proof = json.loads((out/'assessment.json').read_text())
source = ROOT/'work/935-local-relocation-20261022/candidate-002/candidate.npz'
assert sha(source) == proof['input_sha256'] and sha(out/'cycles.npz') == proof['cycles_npz_sha256']
with np.load(source, allow_pickle=False) as data:
    vertices, faces = data['vertices'].astype(float), data['faces'].astype(np.int64)
with np.load(out/'cycles.npz', allow_pickle=False) as data:
    cycles = [data[f'cycle_{i:02d}'].copy() for i in range(12)]
points = vtk.vtkPoints(); points.SetData(numpy_to_vtk(vertices, deep=True))
cells = vtk.vtkCellArray(); cells.SetCells(len(faces), numpy_to_vtkIdTypeArray(np.column_stack((np.full(len(faces), 3), faces)).ravel(), deep=True))
surface = vtk.vtkPolyData(); surface.SetPoints(points); surface.SetPolys(cells)
mapper = vtk.vtkPolyDataMapper(); mapper.SetInputData(surface); mapper.ScalarVisibilityOff()
actor = vtk.vtkActor(); actor.SetMapper(mapper); actor.GetProperty().SetColor(.27, .61, .76); actor.GetProperty().SetAmbient(.35)
paths = []
for cycle in cycles:
    poly = vtk.vtkPolyData(); poly.SetPoints(points)
    lines = vtk.vtkCellArray(); lines.InsertNextCell(len(cycle))
    for vertex in cycle: lines.InsertCellPoint(int(vertex))
    poly.SetLines(lines); mapping = vtk.vtkPolyDataMapper(); mapping.SetInputData(poly)
    line = vtk.vtkActor(); line.SetMapper(mapping); line.GetProperty().SetColor(1, .52, .08)
    line.GetProperty().SetLineWidth(4); line.GetProperty().RenderLinesAsTubesOn(); paths.append(line)

centre = (vertices.min(axis=0)+vertices.max(axis=0))/2
views = [('Top: all twelve basis cycles', centre, np.array([0., 0, 1.]), 160., list(range(12))),
         ('Underside: full surface', centre, np.array([0., 0, -1.]), 160., list(range(12))),
         ('Oblique: full surface', centre, np.array([1., -1.5, 1.]), 160., list(range(12)))]
for index in [1, 3, 5, 8, 11]:
    focus = vertices[cycles[index][:-1]].mean(axis=0)
    direction = np.r_[focus[:2]/np.linalg.norm(focus[:2]), -.7]
    views.append((f'Passage detail: cycle {index+1:02d}', focus, direction, 5., [index]))
window = vtk.vtkRenderWindow(); window.SetSize(3000, 2400); window.SetOffScreenRendering(1)
for index, (title, focus, direction, scale, shown) in enumerate(views):
    col, row = index%3, index//3
    renderer = vtk.vtkRenderer(); renderer.SetViewport(col/3, (2-row)/3, (col+1)/3, (3-row)/3)
    renderer.SetBackground(.035, .065, .085); renderer.AddActor(actor)
    for cycle in shown: renderer.AddActor(paths[cycle])
    renderer.AddViewProp(text_actor(title, 20, 745, 23))
    renderer.AddViewProp(text_actor('Complete source triangles; uncalibrated geometry', 20, 25, 18))
    camera = renderer.GetActiveCamera(); camera.SetFocalPoint(*focus); camera.SetPosition(*(focus+direction*500))
    camera.SetViewUp(*((0, 1, 0) if index < 2 else (0, 0, 1))); camera.ParallelProjectionOn(); camera.SetParallelScale(scale)
    renderer.ResetCameraClippingRange(); window.AddRenderer(renderer)
image = out/'935-surface-passages-001.png'
assert not image.exists() and surface.GetNumberOfPolys() == 873288
try:
    window.Render(); capture = vtk.vtkWindowToImageFilter(); capture.SetInput(window); capture.ReadFrontBufferOff(); capture.Update()
    writer = vtk.vtkPNGWriter(); writer.SetFileName(str(image)); writer.SetInputConnection(capture.GetOutputPort()); writer.Write()
finally:
    window.Finalize()
assert image.is_file() and sha(source) == proof['input_sha256']
save(out/'visual-receipt.json', dict(source_sha256=sha(__file__), input_sha256=sha(source),
     topology_assessment_sha256=sha(out/'assessment.json'), image_sha256=sha(image),
     triangles=surface.GetNumberOfPolys(), decimation=False, views=len(views),
     surface_modified=False, physical_feature_identity_verified=False, CFD_accepted=False))
print(image, flush=True)
