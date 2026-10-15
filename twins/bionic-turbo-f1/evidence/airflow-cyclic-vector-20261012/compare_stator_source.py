"""Conservative nearest-source-facet search for the worst rejected-mesh wall face."""
import json,sys
from pathlib import Path
import numpy as np
import trimesh
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from audit_interface_corridor import read_patches
case=Path('work/bionic-airflow-20261012/baseline-gap-033');manifest=json.loads((case/'case-manifest.json').read_text());report=json.loads(Path(__file__).with_name('stator-frame-exploration.json').read_text());point=np.array(report['worst_faces'][0]['native_formula_face_centre_mm'])
test=np.array([[[0.,0,0],[1,0,0],[0,1,0]]]);np.testing.assert_allclose(trimesh.triangles.closest_point(test,np.array([[.2,.2,.5]])),[[.2,.2,0]])
tri=read_patches(case/'constant/triSurface/domain.stl',manifest['surface'])['stator'];lo=tri.min(axis=1);hi=tri.max(axis=1);lower=np.linalg.norm(np.maximum(np.maximum(lo-point,point-hi),0),axis=1)
first=int(lower.argmin());initial=trimesh.triangles.closest_point(tri[first:first+1],point[None])[0];upper=float(np.linalg.norm(initial-point));ids=np.flatnonzero(lower<=upper+1e-12)
closest=trimesh.triangles.closest_point(tri[ids],np.tile(point,(len(ids),1)));distance=np.linalg.norm(closest-point,axis=1);minimum=float(distance.min());ties=np.flatnonzero(distance<=minimum+1e-9);records=[]
for j in ties:
 i=int(ids[j]);v=tri[i];normal=np.cross(v[1]-v[0],v[2]-v[0]);normal/=np.linalg.norm(normal);q=closest[j]
 records.append(dict(stator_triangle=i,vertices_mm=v.tolist(),closest_point_mm=q.tolist(),distance_mm=float(distance[j]),unit_normal=normal.tolist(),normal_rotation_at_closest_point_m_s=float(np.dot(np.cross([0,0,10471.975511966],q/1000),normal))))
result=dict(source_sha256=sha(Path(__file__)),surface_sha256=manifest['surface']['sha256'],mesh_face=report['worst_faces'][0],candidate_triangles=len(ids),total_stator_triangles=len(tri),nearest_distance_mm=minimum,nearest_ties=records,bounding_box_pruning_proven=True,trimesh_version=trimesh.__version__,scope='Nearest facet to one mesh face centre only. Not a surface-wide deviation bound, wall fit qualification, thermal clearance, or flow result.')
with Path(__file__).with_name('stator-source-comparison.json').open('x') as out:json.dump(result,out,indent=2)
print(json.dumps(result))
