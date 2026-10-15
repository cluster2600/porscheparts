"""Independent native-cell correspondence for one radial block subdivision."""
import json,re,sys
from collections import Counter
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from audit_diagnostic import ascii_list
from run_case import ascii_faces
from uniform_interface_projection import read_mesh,metrics
from frame_balance_batches import geometry
w=Path(__file__).parent;root=Path('work/bionic-airflow-20261012');base=root/'full-collar-063';case=root/'radial-full-077'
for c in (base,case):
 r=json.loads((c/'report.json').read_text());assert r['mesh_gate_passed'] and r['native_exit_code']==0
 assert all(sha(c/k)==v for k,v in r['output_sha256'].items())
p,f,interface,internal=read_mesh(case);bp,bf,bi,bint=read_mesh(base)
m=case/'constant/polyMesh';o=ascii_list((m/'owner').read_text()).astype(int);n=ascii_list((m/'neighbour').read_text()).astype(int)
count=int(max(o.max(),n.max())+1);assert count==33920 and len(p)==34560
spec=json.loads((base/'construction.json').read_text());source=np.array(spec['vertices']);stride=512
# Expected grid: retain the three original rings, add only radial midpoints.
midpoints=np.array([(source[k*stride+256+i]+source[k*stride+384+i])/2 for k in range(54) for i in range(128)])
expected=np.vstack((source,midpoints));distance,mapping=cKDTree(p).query(expected)
assert distance.max()<1e-16 and len(set(mapping))==len(expected)==len(p)
old=mapping[:len(source)];mid=mapping[len(source):].reshape(54,128)
cellkeys=[];expected_boundary=Counter();expected_faces=Counter();expected_rotating=[]
def cycle(face):
 face=tuple(map(int,face));return min(face[k:]+face[:k] for k in range(len(face)))
def add(poly0,poly1,rotating):
 faces=[poly0[::-1],poly1]+[[a,b,poly1[(j+1)%len(poly0)],poly1[j]] for j,(a,b) in enumerate(zip(poly0,poly0[1:]+poly0[:1]))]
 key=tuple(sorted(poly0+poly1));cellkeys.append(key)
 if rotating:expected_rotating.append(key)
 for face in faces:expected_faces[cycle(face)]+=1
for k in range(53):
 for i in range(128):
  j=(i+1)%128;a=256+i;b=256+j;d=2*i;t=d+1;c=(2*i+2)%256
  for poly in ([a,b,t],[a,t,d],[b,c,t]):add(old[np.array(poly)+k*stride].tolist(),old[np.array(poly)+(k+1)*stride].tolist(),True)
  for left,right in ((old[k*stride+256:k*stride+384],mid[k]),(mid[k],old[k*stride+384:(k+1)*stride])):
   # Upper plane uses exactly the same radial addressing.
   inner=np.array_equal(left,old[k*stride+256:k*stride+384])
   upperleft=old[(k+1)*stride+256:(k+1)*stride+384] if inner else mid[k+1]
   upperright=mid[k+1] if inner else old[(k+1)*stride+384:(k+2)*stride]
   add([left[i],right[i],right[j],left[j]],[upperleft[i],upperright[i],upperright[j],upperleft[j]],False)
assert all(v==1 for v in expected_faces.values())
for face in expected_faces:
 if not expected_faces[cycle(face[::-1])]:expected_boundary[face]=1
actualkeys=[];cellfaces=[[] for _ in range(count)]
for i,c in enumerate(o):cellfaces[c].append((i,1))
for i,c in enumerate(n):cellfaces[c].append((i,-1))
for items in cellfaces:
 edges=Counter();vertices=set()
 for i,sign in items:
  face=list(f[i][::sign]);vertices.update(face)
  for a,b in zip(face,face[1:]+face[:1]):edges[a,b]+=1
 assert all(v==1 and edges[b,a]==1 for (a,b),v in edges.items())
 actualkeys.append(tuple(sorted(vertices)))
assert Counter(actualkeys)==Counter(cellkeys) and len(set(actualkeys))==count
actualfaces=Counter(cycle(face) for face in f)
for i in range(internal):actualfaces[cycle(f[i][::-1])]+=1
assert actualfaces==expected_faces
assert Counter(cycle(face) for face in f[internal:])==expected_boundary
zone=np.fromstring(re.search(r'rotorZone\s*\{.*?cellLabels\s+List<label>\s*\d+\s*\((.*?)\)',(m/'cellZones').read_text(),re.S)[1],sep=' ',dtype=int)
assert Counter(actualkeys[c] for c in zone)==Counter(expected_rotating)
# Native old points and MRF polygons compared independently, without construction labels.
dist,bmap=cKDTree(p).query(bp);assert dist.max()<1e-16 and len(set(bmap))==len(bp)
key=lambda face:tuple(sorted(map(int,face)))
assert Counter(key(bmap[bf[i]]) for i in bi)==Counter(key(f[i]) for i in interface)
cf=np.empty((len(f),3));sf=cf.copy();warp=np.empty(len(f))
for size in sorted(set(map(len,f))):
 ids=np.array([i for i,x in enumerate(f) if len(x)==size]);cf[ids],sf[ids],warp[ids]=geometry(p[np.array([f[i] for i in ids])])
part=np.einsum('ij,ij->i',cf,sf)/3
volume=np.bincount(o,weights=part,minlength=count)-np.bincount(n,weights=part[:internal],minlength=count)
flux=np.einsum('ij,ij->i',np.cross([0,0,10471.975511966],cf),sf)
net=np.bincount(o,weights=flux,minlength=count)-np.bincount(n,weights=flux[:internal],minlength=count)
assert volume.min()>0 and abs(volume.sum()/4.611377236219329e-6-1)<1e-12 and warp.max()<1e-12
metric=metrics(p,[f[i] for i in interface],10471.975511966)
assert metric['max_normal_frame_speed_m_s']<1e-8 and abs(net).max()<1e-16
initial=w/'radial-full-077-inputs';manifest=json.loads((initial/'manifest.json').read_text())
assert all(sha(initial/k)==v for k,v in manifest['file_sha256'].items())
for name in ('controlDict','fvSchemes','fvSolution'):assert (initial/'system'/name).read_bytes()==(base/'system'/name).read_bytes()
new=(initial/'system/blockMeshDict').read_text();assert new.replace(') (2 1 1) simpleGrading',') (1 1 1) simpleGrading')==(base/'system/blockMeshDict').read_text()
result=dict(reader_sha256=sha(Path(__file__)),all_payloads_verified=True,only_fixed_radial_block_count_changed=True,cells=count,points=len(p),faces=len(f),internal_faces=internal,boundary_faces=len(f)-internal,rotating_cells=len(zone),fixed_cells=count-len(zone),original_point_max_rounding_m=float(dist.max()),all_expected_points_bijective=True,all_expected_cell_vertex_sets_bijective=True,all_oriented_faces_and_ownership_verified=True,all_cell_edges_cancel=True,oriented_boundary_matches_subdivision=True,interface_quads_match_parent=True,interface=metric,maximum_face_warp_m=float(warp.max()),minimum_cell_volume_m3=float(volume.min()),boundary_volume_m3=float(volume.sum()),max_rotating_cell_frame_flux_m3_s=float(abs(net[zone]).max()),max_all_cell_frame_flux_m3_s=float(abs(net).max()),mesh_admitted=True,physical_turbo_geometry_present=False,solver_launched=False)
(w/'full-readback.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
