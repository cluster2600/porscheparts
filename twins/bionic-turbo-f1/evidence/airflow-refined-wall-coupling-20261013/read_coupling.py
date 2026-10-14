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
from collections import defaultdict
for name in ('radial-full-077','radial-split-078','outer-wall-bisect-086','refined-wall-patches-087','refined-wall-stitch-088'):verify(root/name)
for name in ('refined-wall-patches-087','refined-wall-stitch-088'):
 c=root/name;man=json.loads((c/'manifest.json').read_text());initial=w/(name+'-inputs');assert all(sha(initial/n)==h for n,h in man['file_sha256'].items());assert not list(initial.rglob('*RegionAddressing'))
# Independently revalidate native source maps, including every signed face and cell.
base=root/'radial-full-077/constant/polyMesh';bp,bf,bo,bn=mesh(base);original=cells(bf,bo,bn);covered=[];seen=Counter()
for region in ('rotorZone','domain1'):
 path=root/'radial-split-078/constant'/region/'polyMesh';rp,rf,ro,rn=mesh(path);pm=ascii_list((path/'pointRegionAddressing').read_text()).astype(int);fm=ascii_list((path/'faceRegionAddressing').read_text()).astype(int);cm=ascii_list((path/'cellRegionAddressing').read_text()).astype(int)
 assert np.array_equal(rp,bp[pm]);assert len(pm)==len(rp) and len(fm)==len(rf) and len(cm)==len(cells(rf,ro,rn))
 for face,label in zip(rf,fm):
  assert label!=0 and cycle(pm[face])==cycle(bf[abs(label)-1][::1 if label>0 else -1]);seen[abs(label)-1]+=1
 rc=cells([pm[x] for x in rf],ro,rn);assert all(rc[i]==original[c] for i,c in enumerate(cm));covered.extend(cm.tolist())
assert sorted(covered)==list(range(33920));assert Counter(seen.values())==Counter({1:95616,2:6784}) and set(seen)==set(range(102400))
# Repatching changes boundary numbering only, not cell geometry or adjacency.
p,f,o,n=mesh(root/'outer-wall-bisect-086/constant/polyMesh');q,g,a,b=mesh(root/'refined-wall-patches-087/constant/polyMesh');assert np.array_equal(p,q)
orig=cells(f,o,n);lookup={x:i for i,x in enumerate(orig)};cm=np.array([lookup[x] for x in cells(g,a,b)]);assert len(set(cm))==len(orig)==20352
assert records(f,o,n,np.arange(len(p)),np.arange(len(orig)))==records(g,a,b,np.arange(len(p)),cm)
# Build expected composite from the actual immutable rotor region and refined fixed region.
expected=[];point_lookup={};expected_cells=[];rotor_points=[];incidence=defaultdict(list);source_boundary=Counter()
for index,path in enumerate((root/'radial-split-078/constant/rotorZone/polyMesh',root/'outer-wall-bisect-086/constant/polyMesh')):
 rp,rf,ro,rn=mesh(path);pm=[]
 for xyz in rp:
  key=tuple(xyz)
  if key not in point_lookup:point_lookup[key]=len(expected);expected.append(xyz)
  pm.append(point_lookup[key])
 pm=np.array(pm);offset=len(expected_cells);local=cells([pm[x] for x in rf],ro,rn);expected_cells.extend(local)
 if index==0:rotor_points=pm
 for i,face in enumerate(rf):
  v=pm[face];items=incidence[tuple(sorted(v))];items.append((offset+int(ro[i]),cycle(v)))
  if i<len(rn):items.append((offset+int(rn[i]),cycle(v[::-1])))
  else:source_boundary[cycle(v)]+=1
expected=np.array(expected);assert len(expected)==41472 and len(expected_cells)==40704 and len(incidence)==122880
assert all(len(v) in (1,2) for v in incidence.values())
for items in incidence.values():
 if len(items)==2:assert items[0][0]!=items[1][0] and items[0][1]==cycle(items[1][1][::-1])
# Exactly the join faces disappear from the union of source boundaries.
paired=sum(1 for v in source_boundary if source_boundary[cycle(v[::-1])]);assert paired==2*6784
case=root/'refined-wall-stitch-088';final=case/'constant/polyMesh';q,g,a,b=mesh(final);dist,pm=cKDTree(expected).query(q)
assert np.all(dist==0) and len(set(pm))==len(q)==41472
lookup={x:i for i,x in enumerate(expected_cells)};assert len(lookup)==40704
cm=np.array([lookup[x] for x in cells([pm[x] for x in g],a,b)]);assert len(set(cm))==40704
assert len(g)==122880 and len(b)==100992
for i,face in enumerate(g):
 v=pm[face];items=incidence[tuple(sorted(v))];assert (int(cm[a[i]]),cycle(v)) in items
 if i<len(b):assert len(items)==2 and (int(cm[b[i]]),cycle(v[::-1])) in items
 else:assert len(items)==1
rz=zone(final);assert set(cm[rz])==set(range(20352)) and len(rz)==20352
reverse=np.empty(len(expected),int);reverse[pm]=np.arange(len(pm));assert np.array_equal(q[reverse[rotor_points]],expected[rotor_points]);assert not list(final.glob('*RegionAddressing'))
u,v,c,d=mesh(case/'stitched-polyMesh');assert np.array_equal(q,u) and np.array_equal(a,c) and np.array_equal(b,d) and all(np.array_equal(x,y) for x,y in zip(g,v));assert np.array_equal(rz,zone(case/'stitched-polyMesh'))
bs=(final/'boundary').read_text();assert 'mappedWall' not in bs and not re.search(r'nFaces\s+0;',bs)
cf=np.empty((len(g),3));sf=cf.copy();warp=np.empty(len(g))
for width in sorted(set(map(len,g))):
 ids=np.array([i for i,x in enumerate(g) if len(x)==width]);cf[ids],sf[ids],warp[ids]=geometry(q[np.array([g[i] for i in ids])])
cellfaces=[[] for _ in range(40704)]
for i,c in enumerate(a):cellfaces[c].append((i,1))
for i,c in enumerate(b):cellfaces[c].append((i,-1))
active=np.zeros(40704,bool);active[rz]=True
for c,items in enumerate(cellfaces):
 edges=Counter()
 for i,sign in items:
  face=list(g[i][::sign])
  for x,y in zip(face,face[1:]+face[:1]):edges[x,y]+=1
 assert all(v==1 and edges[y,x]==1 for (x,y),v in edges.items())
 assert sorted(len(g[i]) for i,_ in items)==([3,3,4,4,4] if active[c] else [4]*6)
vf=np.einsum('ij,ij->i',cf,sf)/3;vol=np.bincount(a,weights=vf,minlength=40704)-np.bincount(b,weights=vf[:len(b)],minlength=40704);assert vol.min()>0
flux=np.einsum('ij,ij->i',np.cross([0,0,10471.975511966],cf),sf);net=np.bincount(a,weights=flux,minlength=40704)-np.bincount(b,weights=flux[:len(b)],minlength=40704)
interface=np.flatnonzero(active[a[:len(b)]]!=active[b]);assert len(interface)==6784 and all(len(g[i])==4 for i in interface)
mi=metrics(q,[g[i] for i in interface],10471.975511966);assert mi['max_normal_frame_speed_m_s']<1e-8 and abs(net[rz]).max()<1e-16
# Match each final MRF face to the named rotor source boundary, with opposite fixed-side orientation.
rpath=root/'radial-split-078/constant/rotorZone/polyMesh';rp,rf,ro,rn=mesh(rpath);bl=re.search(r'rotorZone_to_domain1\s*\{(.*?)\}',(rpath/'boundary').read_text(),re.S)[1];st=int(re.search(r'startFace\s+(\d+)',bl)[1]);ct=int(re.search(r'nFaces\s+(\d+)',bl)[1]);assert ct==6784
assert {tuple(sorted(pm[g[i]])) for i in interface}=={tuple(sorted(rotor_points[x])) for x in rf[st:st+ct]}
res=dict(reader_sha256=sha(Path(__file__)),all_payloads_and_initial_inputs_verified=True,split_maps_reverified=True,repatch_preserves_geometry_and_adjacency=True,exact_composite_points=True,all_oriented_faces_and_owner_neighbour_bijective=True,all_cell_edges_cancel=True,all_rotor_points_and_cells_unchanged=True,rotor_zone_exact=True,all_join_quads_preserved=True,cleanup_geometry_unchanged=True,obsolete_addressing_absent=True,cells=40704,rotating_prisms=20352,fixed_hexahedra=20352,points=len(q),faces=len(g),internal_faces=len(b),boundary_faces=len(g)-len(b),volume_m3=float(vol.sum()),minimum_cell_volume_m3=float(vol.min()),maximum_face_warp_m=float(warp.max()),interface=mi,max_rotating_geometric_frame_balance_m3_s=float(abs(net[rz]).max()),max_all_geometric_frame_balance_m3_s=float(abs(net).max()),native_mesh_admitted=verify(case)['mesh_gate_passed'],flow_solver_launched=False,physical_turbo_present=False,rest_qualified=False)
with (w/'readback.json').open('x') as stream:json.dump(res,stream,indent=2)
print(json.dumps(res))
