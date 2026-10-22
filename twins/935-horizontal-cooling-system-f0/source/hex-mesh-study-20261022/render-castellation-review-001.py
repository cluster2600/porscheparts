"""Show the actual pre-snap air boundary and its vertex-sampled geometric gaps."""
import json,signal,sys
from pathlib import Path
import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk,numpy_to_vtkIdTypeArray,vtk_to_numpy
from run_reconstruction import ROOT,sha

signal.alarm(240)
sys.path.insert(0,str(ROOT/'twins/reference-917-engine/source'))
from render_scan_contour_patch_reconstruction_f43 import text_actor

def poly(vertices,faces):
 points=vtk.vtkPoints();points.SetData(numpy_to_vtk(vertices,deep=True))
 cells=vtk.vtkCellArray();cells.SetCells(len(faces),numpy_to_vtkIdTypeArray(np.column_stack([np.full(len(faces),3),faces]).ravel(),deep=True))
 result=vtk.vtkPolyData();result.SetPoints(points);result.SetPolys(cells);return result

def distances(surface,reference):
 query=vtk.vtkDistancePolyDataFilter();query.SetInputData(0,surface);query.SetInputData(1,reference);query.SignedDistanceOff();query.ComputeSecondDistanceOff();query.ComputeCellCenterDistanceOff();query.Update()
 result=vtk.vtkPolyData();result.DeepCopy(query.GetOutput());return result

triangle=np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]])
control=distances(poly(triangle+[0,0,.125],np.array([[0,1,2]])),poly(triangle,np.array([[0,1,2]])))
assert np.allclose(vtk_to_numpy(control.GetPointData().GetArray('Distance')),.125,rtol=0,atol=1e-12)
phase=ROOT/'work/935-local-relocation-20261022';source=phase/'castellation-review-001/VTK/rotor/rotor_0.vtk'
proof=json.loads(source.with_name('rotor-vtk-manifest-001.json').read_text());assert proof['stage']=='unsnapped_castellated_boundary' and sha(source)==proof['sha256']
reference_file=phase/'candidate-002/candidate.npz';assert sha(reference_file)=='0642cc25734981859c8c6d7bdf2e69d756d4ece0de422c78831067c4a8e164c6'
with np.load(reference_file) as bundle:vertices=bundle['vertices'].astype(float)*.001;faces=bundle['faces'].astype(np.int64)
reference=poly(vertices,faces)
reader=vtk.vtkPolyDataReader();reader.SetFileName(str(source));reader.Update();boundary=reader.GetOutput()
assert boundary.GetNumberOfPolys()>1_000_000 and boundary.GetNumberOfPoints()>1_000_000
mesh=distances(boundary,reference);values=vtk_to_numpy(mesh.GetPointData().GetArray('Distance'));assert len(values)==boundary.GetNumberOfPoints() and np.isfinite(values).all() and np.all(values>=0)
field=numpy_to_vtk(values*1000,deep=True);field.SetName('sampled_gap_mm_assumed');mesh.GetPointData().SetScalars(field)
colours=vtk.vtkColorTransferFunction()
for value,colour in [(0,(.12,.45,.8)),(.15,(.25,.78,.67)),(.3,(1,.8,.2)),(.5,(.9,.18,.1))]:colours.AddRGBPoint(value,*colour)
mapper=vtk.vtkPolyDataMapper();mapper.SetInputData(mesh);mapper.SetLookupTable(colours);mapper.SetScalarRange(0,.5)
actor=vtk.vtkActor();actor.SetMapper(mapper);actor.GetProperty().SetAmbient(.35)
wire_mapper=vtk.vtkPolyDataMapper();wire_mapper.SetInputData(mesh);wire_mapper.ScalarVisibilityOff()
wire=vtk.vtkActor();wire.SetMapper(wire_mapper);wire.GetProperty().SetRepresentationToWireframe();wire.GetProperty().SetColor(.95,.6,.15);wire.GetProperty().SetOpacity(.65)
ref_mapper=vtk.vtkPolyDataMapper();ref_mapper.SetInputData(reference);ref_mapper.ScalarVisibilityOff()
ref_actor=vtk.vtkActor();ref_actor.SetMapper(ref_mapper);ref_actor.GetProperty().SetColor(.35,.62,.78);ref_actor.GetProperty().SetAmbient(.35)
window=vtk.vtkRenderWindow();window.SetSize(2400,1200);window.SetOffScreenRendering(1)
centre=(vertices.min(axis=0)+vertices.max(axis=0))/2
target=vertices[np.argmin(np.linalg.norm(vertices-np.array([.132,-.045,0]),axis=1))]
for index,title in enumerate(['935: air-mesh boundary before snapping','Blade-tip detail: air mesh over the reference rotor']):
 renderer=vtk.vtkRenderer();renderer.SetViewport(index/2,0,(index+1)/2,1);renderer.SetBackground(.035,.065,.085)
 renderer.AddActor(actor if index==0 else ref_actor)
 if index:renderer.AddActor(wire)
 renderer.AddViewProp(text_actor(title,25,1140,23))
 renderer.AddViewProp(text_actor('Diagnostic geometry only; no pressure, airflow or stress field',25,28,18))
 renderer.AddViewProp(text_actor('Uncalibrated scale: 1 source unit assumed to be 1 mm',25,59,18))
 camera=renderer.GetActiveCamera();focus=target if index else centre;camera.SetFocalPoint(*focus);camera.SetPosition(*(focus+np.array([1,-1.5,1.1])*.3));camera.SetViewUp(0,0,1);camera.ParallelProjectionOn()
 if index:camera.SetParallelScale(.024)
 else:
  renderer.ResetCamera()
  legend=vtk.vtkScalarBarActor();legend.SetLookupTable(colours);legend.SetTitle('Vertex-sampled gap [mm, assumed scale]');legend.SetNumberOfLabels(4);legend.SetOrientationToHorizontal();legend.SetPosition(.17,.11);legend.SetWidth(.67);legend.SetHeight(.1);renderer.AddActor2D(legend)
 renderer.ResetCameraClippingRange();window.AddRenderer(renderer)
image=phase/'935-castellation-review-001.png';assert not image.exists()
try:
 window.Render();capture=vtk.vtkWindowToImageFilter();capture.SetInput(window);capture.ReadFrontBufferOff();capture.Update();writer=vtk.vtkPNGWriter();writer.SetFileName(str(image));writer.SetInputConnection(capture.GetOutputPort());writer.Write()
finally:window.Finalize()
assert image.is_file() and image.stat().st_size>0 and sha(source)==proof['sha256']
receipt={'source_sha256':sha(__file__),'native_VTK_sha256':sha(source),'reference_sha256':sha(reference_file),'image_sha256':sha(image),'native_boundary_polygons':boundary.GetNumberOfPolys(),'native_boundary_vertices':len(values),'distance_control_parallel_triangles_passed':True,'all_boundary_vertices_queried':True,'maximum_sampled_gap_m_assumed':float(values.max()),'p95_sampled_gap_m_assumed':float(np.quantile(values,.95)),'median_sampled_gap_m_assumed':float(np.median(values)),'decimation':False,'complete_bidirectional_surface_bound':False,'VTK_coordinates_are_display_precision_only':True,'stage':'pre_snap_castellation','scale_verified':False,'CFD_accepted':False,'manufacturing_authorized':False}
with (phase/'castellation-visual-receipt-001.json').open('x') as stream:json.dump(receipt,stream,indent=2)
print(json.dumps(receipt),flush=True)
