"""Verify coupled mesh against original topology and the two actual input regions."""
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
from uniform_interface_projection import metrics
w=Path(__file__).parent;root=Path('work/bionic-airflow-20261012')
def verify(c):
 r=json.loads((c/'report.json').read_text());assert r['native_exit_code']==0 and not r['container_state']['OOMKilled'];assert all(sha(c/n)==h for n,h in r['output_sha256'].items());return r
def mesh(path):
 return (ascii_list((path/'points').read_text(),True),[np.array(x,int) for x in ascii_faces((path/'faces').read_text())],ascii_list((path/'owner').read_text()).astype(int),ascii_list((path/'neighbour').read_text()).astype(int))
def cycle(f):
 f=tuple(map(int,f));return min(f[i:]+f[:i] for i in range(len(f)))
def cells(f,o,n):
 out=[[] for _ in range(int(max(o.max(),n.max())+1))]
 for i,c in enumerate(o):out[c].append(cycle(f[i]))
 for i,c in enumerate(n):out[c].append(cycle(f[i][::-1]))
 return [tuple(sorted(x)) for x in out]
def records(f,o,n,pm,cm):
 out=[]
 for i,face in enumerate(f):
  a=int(cm[o[i]]);b=int(cm[n[i]]) if i<len(n) else -1;v=pm[face]
  if b>=0 and a>b:a,b=b,a;v=v[::-1]
  out.append((cycle(v),a,b))
 return Counter(out)
def zone(path):
 s=(path/'cellZones').read_text();return np.fromstring(re.search(r'rotorZone\s*\{.*?cellLabels\s+List<label>\s*\d+\s*\((.*?)\)',s,re.S)[1],sep=' ',dtype=int)
for name in ('radial-full-077','radial-split-078','radial-selective-snap-081','post-snap-patches-082','post-snap-stitch-083'):verify(root/name)
for name in ('post-snap-patches-082','post-snap-stitch-083'):
 c=root/name;man=json.loads((c/'manifest.json').read_text());initial=w/(name+'-inputs');assert all(sha(initial/n)==h for n,h in man['file_sha256'].items());assert not list((initial/'constant/polyMesh').glob('*RegionAddressing'))
# Repatching can renumber faces, but must preserve oriented cells, faces and coordinates.
p,f,o,n=mesh(root/'radial-selective-snap-081/constant/polyMesh');q,g,a,b=mesh(root/'post-snap-patches-082/constant/polyMesh')
assert np.array_equal(p,q);orig=cells(f,o,n);lookup={x:i for i,x in enumerate(orig)};mapped=cells(g,a,b);cm=np.array([lookup[x] for x in mapped]);assert len(set(cm))==len(orig)
assert records(f,o,n,np.arange(len(p)),np.arange(len(orig)))==records(g,a,b,np.arange(len(p)),cm)
source=root/'radial-split-078/constant/domain1/polyMesh';boundary=(source/'boundary').read_text();block=re.search(r'domain1_to_rotorZone\s*\{(.*?)\}',boundary,re.S)[1];start=int(re.search(r'startFace\s+(\d+)',block)[1]);count=int(re.search(r'nFaces\s+(\d+)',block)[1])
block=re.search(r'domain1_to_rotorZone\s*\{(.*?)\}',(root/'post-snap-patches-082/constant/polyMesh/boundary').read_text(),re.S)[1];newstart=int(re.search(r'startFace\s+(\d+)',block)[1]);newcount=int(re.search(r'nFaces\s+(\d+)',block)[1]);assert count==newcount==6784
assert Counter(cycle(x) for x in f[start:start+count])==Counter(cycle(x) for x in g[newstart:newstart+newcount])
# Revalidate both native split mappings against 077, including orientation and cell ownership.
base=root/'radial-full-077/constant/polyMesh';bp,bf,bo,bn=mesh(base);original=cells(bf,bo,bn);assert len(set(original))==33920
covered=[];seen=Counter();expected=bp.copy();rotor_points=None
for region in ('rotorZone','domain1'):
 path=root/'radial-split-078/constant'/region/'polyMesh';rp,rf,ro,rn=mesh(path);pm=ascii_list((path/'pointRegionAddressing').read_text()).astype(int);fm=ascii_list((path/'faceRegionAddressing').read_text()).astype(int);cm=ascii_list((path/'cellRegionAddressing').read_text()).astype(int)
 assert np.array_equal(rp,bp[pm]);assert len(pm)==len(rp) and len(fm)==len(rf) and len(cm)==len(cells(rf,ro,rn))
 for face,label in zip(rf,fm):
  assert label!=0 and cycle(pm[face])==cycle(bf[abs(label)-1][::1 if label>0 else -1]);seen[abs(label)-1]+=1
 rc=cells([pm[x] for x in rf],ro,rn);assert all(rc[i]==original[c] for i,c in enumerate(cm));covered.extend(cm.tolist())
 if region=='rotorZone':rotor_points=pm
 else:
  assert len(p)==len(rp) and all(np.array_equal(x,y) for x,y in zip(f,rf));assert np.array_equal(o,ro) and np.array_equal(n,rn);expected[pm]=p
assert sorted(covered)==list(range(33920));assert set(seen)==set(range(102400)) and Counter(seen.values())==Counter({1:95616,2:6784})
assert np.array_equal(expected[rotor_points],bp[rotor_points])
# Final mesh has exactly the composite points; topology is independently matched by oriented cell faces.
case=root/'post-snap-stitch-083';final=case/'constant/polyMesh';q,g,a,b=mesh(final);dist,pm=cKDTree(expected).query(q)
assert dist.max()==0 and len(set(pm))==len(q)==len(expected)==34560
joined=cells([pm[x] for x in g],a,b);lookup={x:i for i,x in enumerate(original)};cm=np.array([lookup[x] for x in joined]);assert len(set(cm))==len(original)==33920
assert records(bf,bo,bn,np.arange(len(bp)),np.arange(33920))==records(g,a,b,pm,cm)
rz=zone(final);assert set(cm[rz])==set(zone(base));assert len(rz)==20352
assert not list(final.glob('*RegionAddressing'))
# Cleanup may reorder empty patches only; geometry/topology/zone remain exact.
u,v,c,d=mesh(case/'stitched-polyMesh');assert np.array_equal(q,u) and np.array_equal(a,c) and np.array_equal(b,d) and all(np.array_equal(x,y) for x,y in zip(g,v));assert np.array_equal(rz,zone(case/'stitched-polyMesh'))
bs=(final/'boundary').read_text();assert 'mappedWall' not in bs and 'nFaces          0;' not in bs
# Every cell is closed by paired oriented edges; no unshared or duplicate internal faces.
cf=np.empty((len(g),3));sf=cf.copy();warp=np.empty(len(g))
for width in sorted(set(map(len,g))):
 ids=np.array([i for i,x in enumerate(g) if len(x)==width]);cf[ids],sf[ids],warp[ids]=geometry(q[np.array([g[i] for i in ids])])
cellfaces=[[] for _ in range(33920)]
for i,c in enumerate(a):cellfaces[c].append((i,1))
for i,c in enumerate(b):cellfaces[c].append((i,-1))
active=np.zeros(33920,bool);active[rz]=True
for c,items in enumerate(cellfaces):
 edges=Counter()
 for i,sign in items:
  face=list(g[i][::sign])
  for x,y in zip(face,face[1:]+face[:1]):edges[x,y]+=1
 assert all(v==1 and edges[y,x]==1 for (x,y),v in edges.items())
 assert sorted(len(g[i]) for i,_ in items)==([3,3,4,4,4] if active[c] else [4]*6)
volface=np.einsum('ij,ij->i',cf,sf)/3;vol=np.bincount(a,weights=volface,minlength=33920)-np.bincount(b,weights=volface[:len(b)],minlength=33920);assert vol.min()>0
flux=np.einsum('ij,ij->i',np.cross([0,0,10471.975511966],cf),sf);net=np.bincount(a,weights=flux,minlength=33920)-np.bincount(b,weights=flux[:len(b)],minlength=33920)
interface=np.flatnonzero(active[a[:len(b)]]!=active[b]);assert len(interface)==6784 and all(len(g[i])==4 for i in interface)
mi=metrics(q,[g[i] for i in interface],10471.975511966);assert mi['max_normal_frame_speed_m_s']<1e-8 and abs(net[rz]).max()<1e-16
res=dict(reader_sha256=sha(Path(__file__)),all_payloads_and_initial_inputs_verified=True,split_maps_reverified=True,repatch_preserves_all_oriented_cells_faces_and_coordinates=True,final_cell_bijection=True,final_oriented_faces_owner_neighbour_bijection=True,exact_composite_point_coordinates=True,all_rotating_points_preserved=True,rotor_zone_preserved=True,obsolete_region_addressing_absent=True,cleanup_geometry_unchanged=True,all_cell_edges_cancel=True,cells=33920,rotating_cells=len(rz),points=len(q),faces=len(g),internal_faces=len(b),boundary_faces=len(g)-len(b),interface=mi,minimum_cell_volume_m3=float(vol.min()),volume_m3=float(vol.sum()),maximum_face_warp_m=float(warp.max()),max_rotating_geometric_frame_balance_m3_s=float(abs(net[rz]).max()),max_all_geometric_frame_balance_m3_s=float(abs(net).max()),native_mesh_admitted=verify(case)['mesh_gate_passed'],rest_test_performed=False,physical_turbo_present=False,performance_authorized=False)
with (w/'readback.json').open('x') as stream:json.dump(res,stream,indent=2)
print(json.dumps(res))
