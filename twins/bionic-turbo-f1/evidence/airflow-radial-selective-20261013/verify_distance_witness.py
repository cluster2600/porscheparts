"""Preserve a scale-dependent first-reader refusal using the saved native mesh."""
import ast,hashlib,inspect,json,sys
from pathlib import Path
import numpy as np
import trimesh
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from audit_diagnostic import ascii_list
from run_case import ascii_faces
w=Path(__file__).parent;root=Path('work/bionic-airflow-20261012');a=root/'radial-isolated-079/constant/polyMesh';b=root/'radial-selective-snap-081/constant/polyMesh'
p=ascii_list((a/'points').read_text(),True);q=ascii_list((b/'points').read_text(),True);faces=list(ascii_faces((a/'faces').read_text()));face=faces[40607]
tri=p[np.array(face)[[[0,1,2],[0,2,3]]]];tri=np.repeat(tri[None],4,axis=0).reshape(-1,3,3);points=np.repeat(q[face],2,axis=0)
module=ast.parse((w/'read_target_distance_v2.py').read_text());node=next(x for x in module.body if isinstance(x,ast.FunctionDef) and x.name=='closest_point');namespace={'np':np};exec(compile(ast.Module(body=[node],type_ignores=[]),'<pinned-reader-function>','exec'),namespace)
formula=namespace['closest_point'];results={}
for scale in (1,1000):
 cp=trimesh.triangles.closest_point(tri*scale,points*scale)/scale;dist=np.linalg.norm(cp-points,axis=1).reshape(4,2).min(axis=1)
 results[str(scale)]=dict(distances_m=dist.tolist(),max_distance_m=float(dist.max()))
cp=formula(tri,points);dist=np.linalg.norm(cp-points,axis=1).reshape(4,2).min(axis=1);vertex=np.linalg.norm(q[face]-p[face],axis=1)
assert results['1']['max_distance_m']>float(vertex.max()) and np.all(dist<=vertex+1e-14)
assert np.max(abs(np.array(results['1000']['distances_m'])-dist))<1e-14
source=inspect.getsource(trimesh.triangles.closest_point);(w/'trimesh-closest-point-source.py').write_text(source)
report=dict(source_sha256=sha(Path(__file__)),trimesh_version=trimesh.__version__,trimesh_function_sha256=hashlib.sha256(source.encode()).hexdigest(),formula_reader_sha256=sha(w/'read_target_distance_v2.py'),native_face=40607,point_labels=list(map(int,face)),source_vertices_m=p[face].tolist(),final_vertices_m=q[face].tolist(),valid_vertex_upper_bounds_m=vertex.tolist(),trimesh_results_by_coordinate_scale=results,independent_formula_distances_m=dist.tolist(),scale_dependence_reproduced=True,no_native_replay=True,scope='Reader-library behaviour only. First distance reports rejected; neither solver nor mesh tolerances changed. Independent formula and analytic scale tests used in v2.')
(w/'distance-library-witness.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
