"""Map every refined synthetic wall face to one unchanged parent facet."""
import json,sys
from collections import Counter
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from uniform_interface_projection import read_mesh
from audit_frame_interface import face_geometry
w=Path(__file__).parent;root=Path('work/bionic-airflow-20261012');parent=root/'reconstructed-interface-038';case=root/'protected-axial-056'
for c in (parent,case):
 r=json.loads((c/'report.json').read_text());assert all(sha(c/n)==h for n,h in r['output_sha256'].items())
p,oldfaces,_,ni=read_mesh(parent);q,faces,_,nj=read_mesh(case)
edges=np.array(sorted({tuple(sorted((int(f[i]),int(f[(i+1)%len(f)])))) for f in oldfaces for i in range(len(f))}))
midpoints=p[edges].mean(axis=1);distance,index=cKDTree(midpoints).query(q[len(p):],k=2)
assert distance[:,0].max()<1e-17 and distance[:,1].min()>1e-12
support=[set() for _ in p]
for face_id in range(ni,len(oldfaces)):
 for v in oldfaces[face_id]:support[v].add(face_id)
for edge in edges[index[:,0]]:support.append(support[edge[0]] & support[edge[1]])
assert len(support)==len(q)
midpoint_ids={tuple(map(int,edge)):len(p)+i for i,edge in enumerate(edges[index[:,0]])}
edge_chains={i:Counter() for i in range(ni,len(oldfaces))}
def add_edge(chain,a,b):
    a,b=int(a),int(b);assert a!=b
    chain[tuple(sorted((a,b)))]+=1 if a<b else -1
assert len(midpoint_ids)==len(q)-len(p)
accum={i:np.zeros(3) for i in range(ni,len(oldfaces))};counts={i:0 for i in accum};max_plane=0.;minimum_side=1.
for face in faces[nj:]:
 candidates=set.intersection(*(support[v] for v in face));assert len(candidates)==1
 parent_id=candidates.pop();old=p[oldfaces[parent_id]];c,s=face_geometry(old);unit=s/np.linalg.norm(s)
 v=q[face];error=float(abs((v-c)@unit).max());assert error<1e-16;max_plane=max(max_plane,error)
 # Convex parent-facet containment, using signed distances to each edge plane.
 for start,end in zip(old,np.roll(old,-1,axis=0)):
  edge=end-start;side=np.cross(edge,v-start)@unit/np.linalg.norm(edge);minimum_side=min(minimum_side,float(side.min()));assert side.min()>-1e-16
 _,area=face_geometry(v);assert np.dot(area,s)>0
 accum[parent_id]+=area;counts[parent_id]+=1
 for a,b in zip(face,np.roll(face,-1)):add_edge(edge_chains[parent_id],a,b)
for i,actual in edge_chains.items():
 expected=Counter();face=oldfaces[i]
 for a,b in zip(face,np.roll(face,-1)):
  midpoint=midpoint_ids.get(tuple(sorted((int(a),int(b)))))
  if midpoint is None:add_edge(expected,a,b)
  else:add_edge(expected,a,midpoint);add_edge(expected,midpoint,b)
 assert {e:n for e,n in actual.items() if n}=={e:n for e,n in expected.items() if n}
relative=[]
for i,area in accum.items():
 _,original=face_geometry(p[oldfaces[i]]);assert counts[i]>0
 relative.append(float(np.linalg.norm(area-original)/np.linalg.norm(original)))
assert max(relative)<1e-12
result=dict(source_sha256=sha(Path(__file__)),all_payloads_verified=True,old_wall_faces=len(oldfaces)-ni,new_wall_faces=len(faces)-nj,all_new_points_match_unique_parent_edge_midpoints=True,max_new_point_midpoint_distance_m=float(distance[:,0].max()),all_wall_faces_map_to_one_parent=True,all_parent_facets_covered=True,oriented_interior_edges_cancel_and_parent_boundary_is_exact=True,max_wall_plane_distance_m=max_plane,minimum_edge_signed_distance_m=minimum_side,max_parent_area_vector_relative_error=max(relative),wall_subdivision_counts={str(n):list(counts.values()).count(n) for n in sorted(set(counts.values()))},physical_turbo_geometry_present=False,mesh_admitted=False)
with (w/'boundary-readback-v2.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
