"""Compare original and locally repaired native surfaces; orange marks changed triangles."""
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

out = ROOT/'work/935-snap-resume-20261025/field-root-audit-002'
proof = json.loads((out/'assessment.json').read_text())
native = json.loads((out/'native-intersection-assessment.json').read_text())
assert native['full_surface_self_intersections_passed'] and native['candidate_sha256'] == proof['variants'][1]['input_sha256']
meshes = []; old_keys = None; changed_count = None
for index, name in enumerate(['rotor-0.npz', 'rotor-0p6.npz']):
    path = out/name; assert sha(path) == proof['variants'][index]['indexed_npz_sha256']
    with np.load(path, allow_pickle=False) as data: vertices, faces = data['vertices'].copy(), data['faces'].copy()
    tri = vertices[faces]; order = np.lexsort((tri[:, :, 2], tri[:, :, 1], tri[:, :, 0]), axis=1)
    rows = np.ascontiguousarray(tri[np.arange(len(tri))[:, None], order].reshape(-1, 9))
    keys = rows.view(np.dtype((np.void, rows.dtype.itemsize*9))).ravel()
    if old_keys is None: old_keys = keys; changed = np.zeros(len(faces), dtype=bool)
    else: changed = ~np.isin(keys, old_keys, assume_unique=True); changed_count = int(changed.sum())
    points = vtk.vtkPoints(); points.SetData(numpy_to_vtk(vertices, deep=True))
    cells = vtk.vtkCellArray(); cells.SetCells(len(faces), numpy_to_vtkIdTypeArray(np.column_stack((np.full(len(faces), 3), faces)).ravel(), deep=True))
    mesh = vtk.vtkPolyData(); mesh.SetPoints(points); mesh.SetPolys(cells)
    colours = np.tile(np.array([66, 155, 197], dtype=np.uint8), (len(faces), 1)); colours[changed] = [255, 139, 37]
    mesh.GetCellData().SetScalars(numpy_to_vtk(colours, deep=True, array_type=vtk.VTK_UNSIGNED_CHAR))
    mapper = vtk.vtkPolyDataMapper(); mapper.SetInputData(mesh); mapper.SetScalarModeToUseCellData(); mapper.SetColorModeToDirectScalars()
    actor = vtk.vtkActor(); actor.SetMapper(mapper); actor.GetProperty().SetAmbient(.35); meshes.append(actor)

window = vtk.vtkRenderWindow(); window.SetSize(2400, 1600); window.SetOffScreenRendering(1)
for row in range(2):
    for col in range(2):
        renderer = vtk.vtkRenderer(); renderer.SetViewport(col/2, (1-row)/2, (col+1)/2, (2-row)/2)
        renderer.SetBackground(.035, .065, .085); renderer.AddActor(meshes[col])
        title = ['Original PicoGK master: five root passages', 'Local 0.6-source-unit root correction'][col]
        renderer.AddViewProp(text_actor(title, 25, 745, 25))
        renderer.AddViewProp(text_actor('Geometry inspection; scale, fit and operating strength remain unqualified', 25, 25, 18))
        renderer.AddViewProp(text_actor('Full surface; orange = changed triangles' if col else 'Full original surface; no display decimation', 25, 58, 18))
        focus = np.array([72.0, -52.3, -20.3]) if row else np.array([0., 0, 0])
        direction = np.r_[focus[:2]/np.linalg.norm(focus[:2]), -.7] if row else np.array([1., -1.5, 1.1])
        camera = renderer.GetActiveCamera(); camera.SetFocalPoint(*focus); camera.SetPosition(*(focus+direction*500)); camera.SetViewUp(0, 0, 1)
        camera.ParallelProjectionOn(); camera.SetParallelScale(5 if row else 165)
        renderer.ResetCameraClippingRange(); window.AddRenderer(renderer)
image = out/'935-local-root-repair-001.png'; assert not image.exists()
try:
    window.Render(); capture = vtk.vtkWindowToImageFilter(); capture.SetInput(window); capture.ReadFrontBufferOff(); capture.Update()
    writer = vtk.vtkPNGWriter(); writer.SetFileName(str(image)); writer.SetInputConnection(capture.GetOutputPort()); writer.Write()
finally:
    window.Finalize()
assert image.is_file() and changed_count > 0
save(out/'visual-receipt.json', dict(source_sha256=sha(__file__), audit_sha256=sha(out/'assessment.json'),
     image_sha256=sha(image), original_faces=1322970, candidate_faces=1320006, changed_candidate_faces=changed_count,
     decimation=False, colours_show_triangle_identity_only=True, scale_verified=False, CFD_accepted=False))
print(image, flush=True)
