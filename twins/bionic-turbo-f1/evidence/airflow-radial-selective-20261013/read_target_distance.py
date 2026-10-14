"""Exact vertex-to-triangle search and conservative one-sided parent-face bound."""
import json,sys
from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial import cKDTree
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from audit_diagnostic import ascii_list
from run_case import ascii_faces
from frame_balance_batches import geometry
w=Path(__file__).parent;root=Path('work/bionic-airflow-20261012');parent=root/'radial-isolated-079';case=root/'radial-selective-snap-081'
for c in (parent,case):
 report=json.loads((c/'report.json').read_text());assert all(sha(c/k)==v for k,v in report['output_sha256'].items())
m=parent/'constant/polyMesh';p=ascii_list((m/'points').read_text(),True);f=[np.array(x,int) for x in ascii_faces((m/'faces').read_text())];internal=len(ascii_list((m/'neighbour').read_text()));boundary=np.array(f[internal:]);q=ascii_list((case/'constant/polyMesh/points').read_text(),True)
manifest=json.loads((w/'radial-selective-snap-081-inputs/manifest.json').read_text());moving=np.array(manifest['moving_point_labels']);initial=ascii_list((w/'radial-selective-snap-081-inputs/constant/polyMesh/points').read_text(),True)
tri=p[boundary[:,[[0,1,2],[0,2,3]]]].reshape(-1,3,3)
lo=tri.min(axis=1);hi=tri.max(axis=1);tree=cKDTree(tri.mean(axis=1))
# Analytic closest point, vertex and edge witnesses verify the projection primitive.
test=np.tile(np.array([[[0.,0,0],[1,0,0],[0,1,0]]]),(3,1,1));queries=np.array([[.2,.2,.5],[2,0,0],[.7,.7,.1]])
np.testing.assert_allclose(trimesh.triangles.closest_point(test,queries),[[.2,.2,0],[1,0,0],[.5,.5,0]],atol=1e-15)
def nearest(points):
 _,seeds=tree.query(points);out=[]
 for pt,seed in zip(points,seeds):
  first=trimesh.triangles.closest_point(tri[seed:seed+1],pt[None])[0];upper=np.linalg.norm(first-pt)
  lower=np.linalg.norm(np.maximum(np.maximum(lo-pt,pt-hi),0),axis=1);ids=np.flatnonzero(lower<=upper+1e-14)
  closest=trimesh.triangles.closest_point(tri[ids],np.tile(pt,(len(ids),1)));dist=np.linalg.norm(closest-pt,axis=1);j=int(dist.argmin())
  out.append((float(dist[j]),int(ids[j]),closest[j].tolist(),len(ids)))
 return out
before=nearest(initial[moving]);after=nearest(q[moving]);dist=np.array([r[0] for r in after]);old=np.array([r[0] for r in before])
# Independent exhaustive comparisons, without bounding-box pruning, at extrema and spaced labels.
check=sorted(set([int(dist.argmax()),int(old.argmax()),*np.linspace(0,len(moving)-1,10).astype(int).tolist()]))
for i in check:
 all_near=trimesh.triangles.closest_point(tri,np.tile(q[moving[i]],(len(tri),1)))
 assert abs(np.linalg.norm(all_near-q[moving[i]],axis=1).min()-dist[i])<1e-15
# Each planar convex parent quad lies entirely in the target STL. Distance to this
# convex quad is convex, so max vertex distance bounds every point in the convex
# hull of the final quad, including either triangular faceting of a warped quad.
cp,area,warp=geometry(p[boundary]);assert warp.max()<1e-12
v=p[boundary];cross=np.cross(np.roll(v,-1,axis=1)-v,np.roll(v,-2,axis=1)-np.roll(v,-1,axis=1));assert np.all(np.einsum('ijk,ik->ij',cross,area)>0)
repeated=np.repeat(tri.reshape(-1,2,3,3)[:,None,:,:,:],4,axis=1).reshape(-1,3,3)
queries=np.repeat(q[boundary][:,:,None,:],2,axis=2).reshape(-1,3)
closest=trimesh.triangles.closest_point(repeated,queries)
parent_distance=np.linalg.norm(closest-queries,axis=1).reshape(-1,4,2).min(axis=2)
bound=parent_distance.max(axis=1);worst=int(bound.argmax());source_error=np.linalg.norm(q[moving]-p[moving],axis=1)
res=dict(reader_sha256=sha(Path(__file__)),trimesh_version=trimesh.__version__,all_payloads_verified=True,target_triangles=len(tri),points_examined=len(moving),all_target_triangles_bounded_before_pruning=True,pruning_guard_m=1e-14,brute_force_cross_checks=len(check),initial_target_distance_max_m=float(old.max()),final_target_distance_max_m=float(dist.max()),final_target_distance_min_m=float(dist.min()),final_source_vertex_error_max_m=float(source_error.max()),target_distance_reduced_at_all_examined_points=bool(np.all(dist<old)),maximum_one_sided_parent_quad_bound_m=float(bound.max()),worst_bound_face=internal+worst,worst_bound_vertex_distances_m=parent_distance[worst].tolist(),parent_quads_planar_and_convex=True,scope='Distances are to synthetic target triangles. Per-face bound is one-sided to the matching parent convex quad, covering any triangular faceting of the final quad. Not a symmetric Hausdorff distance, exact surface restoration, Euclidean physical clearance, or flow performance.')
(w/'target-point-distances.json').write_text(json.dumps(dict(point_labels=moving.tolist(),before=before,after=after),indent=2)+'\n')
(w/'target-distance-summary.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2))
