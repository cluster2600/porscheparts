"""Compare complete native, OBJ and VTK readbacks of the analytic unit cube."""
from fractions import Fraction
import json,re,sys
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
import vtk
from vtk.util.numpy_support import vtk_to_numpy
from import_conforming_volume import helper,integer_points,determinant
from prepare_conforming_surface import sha

p=Path(sys.argv[1]);output=p/'export-readback.json';assert not output.exists()
parser=Path('work/935-surface-facet-repair-20261022/export-fluid-plc-005.py')
assert sha(parser)=='f50f4cd315c757d9d2c291640f49bfd1a6107a1de851685f8c407e47c33883cb'
ascii=helper(parser,'hex_review_cube_ascii');proof=json.loads((p/'geometry-readback.json').read_text())
assert proof['native_full_quality_passed'] and proof['cells']==216 and proof['vertices']==343
mesh=p/'constant/polyMesh'
for name,digest in proof['native_mesh_sha256'].items():assert sha(mesh/name)==digest
count,body=ascii.foam_list(mesh/'points');native=np.fromstring(body.replace('(',' ').replace(')',' '),sep=' ').reshape(-1,3)
assert native.shape==(count,3) and count==343 and np.isfinite(native).all()
count,body=ascii.foam_list(mesh/'faces');rows=list(re.finditer(r'(\d+)\s*\(([^()]*)\)',body))
assert len(rows)==count==756 and not re.sub(r'\d+\s*\([^()]*\)','',body).strip()
faces=[np.fromstring(row[2],sep=' ',dtype=np.int64) for row in rows]
assert all(len(f)==int(row[1]) and len(f)==4 and f.min()>=0 and f.max()<len(native) for row,f in zip(rows,faces))
expected=native[np.unique(np.concatenate(faces[540:]))]
lines=(p/'boundary.obj').read_text().splitlines()
vertices=np.asarray([[float(x) for x in line.split()[1:]] for line in lines if line.startswith('v ')])
triangles=np.asarray([[int(x)-1 for x in line.split()[1:]] for line in lines if line.startswith('f ')],dtype=np.int32)
assert vertices.shape==(218,3) and triangles.shape==(432,3) and np.isfinite(vertices).all()
assert triangles.min()==0 and triangles.max()==len(vertices)-1
assert np.array_equal(np.unique(vertices,axis=0),np.unique(expected,axis=0))
edges=triangles[:,[[0,1],[1,2],[2,0]]].reshape(-1,2)
unique,inverse,counts=np.unique(np.sort(edges,axis=1),axis=0,return_inverse=True,return_counts=True)
balance=np.bincount(inverse,weights=np.where(edges[:,0]<edges[:,1],1.,-1.))
assert np.all(counts==2) and np.all(balance==0) and len(vertices)-len(unique)+len(triangles)==2
integers,scale=integer_points(vertices)
volume=Fraction(sum(determinant((0,0,0),*(integers[int(i)] for i in f)) for f in triangles),6*scale**3)
assert abs(volume-1)<Fraction(1,10**12)
files=sorted((p/'VTK').glob('*/*.vtk'));assert len(files)==4
display_maximum=0.;patches=[]
for file in files:
 reader=vtk.vtkPolyDataReader();reader.SetFileName(str(file));reader.Update();poly=reader.GetOutput()
 v=vtk_to_numpy(poly.GetPoints().GetData());distances,_=cKDTree(expected).query(v)
 display_maximum=max(display_maximum,float(distances.max()))
 assert poly.GetNumberOfCells()=={'inlet':36,'outlet':36,'duct':108,'rotor':36}[file.parent.name]
 patches.append({'name':file.parent.name,'faces':poly.GetNumberOfCells(),'coordinate_dtype':str(v.dtype),'maximum_distance_to_native_vertices':float(distances.max()),'sha256':sha(file)})
assert 0<display_maximum<1e-6
foam=p/'case.foam'
if not foam.exists():foam.touch(exist_ok=False)
reader=vtk.vtkOpenFOAMReader();reader.SetFileName(str(foam));reader.Use64BitFloatsOn();reader.CreateCellToPointOff();reader.Update();internal=reader.GetOutput().GetBlock(0)
assert internal.GetNumberOfPoints()==343 and internal.GetNumberOfCells()==216
read_vertices=vtk_to_numpy(internal.GetPoints().GetData());reader_error=float(np.linalg.norm(read_vertices-native,axis=1).max())
assert 0<reader_error<1e-6
result={'source_sha256':sha(__file__),'parent_native_readback_sha256':sha(p/'geometry-readback.json'),'OBJ_sha256':sha(p/'boundary.obj'),'OBJ_vertices':len(vertices),'OBJ_triangles':len(triangles),'OBJ_coordinates_exact_native_boundary_subset':True,'OBJ_boundary_closed_oriented_Euler_2':True,'OBJ_exact_serialized_volume':str(volume),'OBJ_volume_absolute_error_from_analytic_unit_cube':float(abs(volume-1)),'VTK_patch_exports':patches,'VTK_maximum_coordinate_distance_to_native':display_maximum,'VTK_native_reader_64_bit_input_requested':True,'VTK_native_reader_output_dtype':str(read_vertices.dtype),'VTK_native_reader_maximum_coordinate_error':reader_error,'VTK_views_are_not_exact_coordinate_evidence':True,'synthetic_control_only':True,'actual_rotor_mesh_export_verified':False,'CFD_accepted':False,'manufacturing_authorized':False}
output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
