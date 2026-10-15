"""Independently decode the saved STL and compare oriented native boundary triangles."""
import json,re,sys
from pathlib import Path
from collections import Counter
import numpy as np
from scipy.spatial import cKDTree
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from audit_diagnostic import ascii_list
from run_case import ascii_faces
from frame_balance_batches import geometry
w=Path(__file__).parent;root=Path('work/bionic-airflow-20261012');m=root/'outer-wall-bisect-086/constant/polyMesh'
p=ascii_list((m/'points').read_text(),True);faces=[np.array(v,int) for v in ascii_faces((m/'faces').read_text())];n=len(ascii_list((m/'neighbour').read_text()))
surface=root/'castellation-target-089/constant/triSurface/collar.stl';text=surface.read_text();groups={}
for name,body in re.findall(r'^solid (\w+)\n(.*?)^endsolid \1$',text,re.M|re.S):
 xyz=np.array([[float(x) for x in row.split()] for row in re.findall(r'^\s*vertex (.*)$',body,re.M)]).reshape(-1,3,3);d,labels=cKDTree(p).query(xyz.reshape(-1,3));assert np.all(d==0);groups[name]=labels.reshape(-1,3)
assert {k:len(v) for k,v in groups.items()}==dict(join=13568,rear=768,front=768,outer=13568)
b=re.search(r'outerWall\s*\{(.*?)\}',(m/'boundary').read_text(),re.S)[1];st=int(re.search(r'startFace\s+(\d+)',b)[1]);count=int(re.search(r'nFaces\s+(\d+)',b)[1])
def cycle(v):
 v=tuple(map(int,v));return min(v[i:]+v[:i] for i in range(len(v)))
expected={k:[] for k in groups};bounds=[]
for i in range(n,len(faces)):
 v=faces[i];x=p[v];name='outer' if st<=i<st+count else 'rear' if np.all(x[:,2]==p[:,2].min()) else 'front' if np.all(x[:,2]==p[:,2].max()) else 'join'
 expected[name]+=[cycle(v[[0,1,2]]),cycle(v[[0,2,3]])]
 normal=np.cross(x[1]-x[0],x[2]-x[0]);uv=np.delete(x,np.argmax(abs(normal)),axis=1);e=np.roll(uv,-1,axis=0)-uv;cross=e[:,0]*np.roll(e[:,1],-1)-e[:,1]*np.roll(e[:,0],-1);assert np.all(cross>0) or np.all(cross<0)
 bounds.append(float(np.linalg.norm(x.mean(axis=0)-(x[0]+x[2])/2)))
for name,v in groups.items():assert Counter(map(cycle,v))==Counter(expected[name])
tri=np.concatenate(list(groups.values()));edges=Counter((int(a),int(b)) for v in tri for a,b in zip(v,np.roll(v,-1)));assert all(c==1 and edges[b,a]==1 for (a,b),c in edges.items())
x=p[tri];tv=float(np.einsum('ij,ij->i',x[:,0],np.cross(x[:,1],x[:,2])).sum()/6)
cf,sf,warp=geometry(p[np.array(faces[n:])]);native=float(np.einsum('ij,ij->i',cf,sf).sum()/3)
prep=json.loads((w/'target-preparation.json').read_text());assert max(bounds)==prep['paired_fan_hausdorff_upper_bound_m']
a=w/'regional-castellation-090-inputs';b=w/'regional-castellation-fixed-091-inputs';pa={str(q.relative_to(a)):q for q in a.rglob('*') if q.is_file()};pb={str(q.relative_to(b)):q for q in b.rglob('*') if q.is_file()};assert pa.keys()==pb.keys();diff=[k for k in pa if pa[k].read_bytes()!=pb[k].read_bytes()];assert diff==['system/snappyHexMeshDict']
old=pa[diff[0]].read_text();new=pb[diff[0]].read_text();assert len(new)==len(old)+1 and new.replace('outer { level (1 1); }}}}', 'outer { level (1 1); }}}',1)==old
result=dict(reader_sha256=sha(Path(__file__)),surface_sha256=sha(surface),triangles=len(tri),regions={k:len(v) for k,v in groups.items()},all_vertex_coordinates_exact=True,oriented_triangles_and_edges_verified=True,projected_quad_convexity_verified=True,paired_fan_bound_m=max(bounds),bound_scope=prep['bound_scope'],diagonal_triangle_signed_volume_m3=tv,native_polygon_boundary_volume_m3=native,volume_difference_m3=tv-native,syntax_pair_changed_files=diff,syntax_change='one added closing brace; all other initial payloads identical',physical_geometry_changed=False)
(w/'target-readback.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
