"""Independent oriented-cell reconstruction of native wall-normal bisection."""
import json,re,sys
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
from scipy.spatial import cKDTree
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from audit_diagnostic import ascii_list
from run_case import ascii_faces
from frame_balance_batches import geometry
from uniform_interface_projection import metrics
w=Path(__file__).parent;root=Path('work/bionic-airflow-20261012')
def mesh(c):
 m=c/'constant/polyMesh';return ascii_list((m/'points').read_text(),True),[np.array(x,int) for x in ascii_faces((m/'faces').read_text())],ascii_list((m/'owner').read_text()).astype(int),ascii_list((m/'neighbour').read_text()).astype(int)
def cycle(f):
 f=tuple(map(int,f));return min(f[i:]+f[:i] for i in range(len(f)))
def cells(f,o,n):
 out=[[] for _ in range(int(max(o.max(),n.max())+1))]
 for i,c in enumerate(o):out[c].append(list(f[i]))
 for i,c in enumerate(n):out[c].append(list(f[i][::-1]))
 return out
def signature(fs):return tuple(sorted(cycle(x) for x in fs))
for name in ('radial-selective-snap-081','outer-wall-patch-085','outer-wall-bisect-086'):
 c=root/name;r=json.loads((c/'report.json').read_text());assert r['native_exit_code']==0 and r['mesh_gate_passed'] and not r['container_state']['OOMKilled'];assert all(sha(c/n)==h for n,h in r['output_sha256'].items())
 if name!='radial-selective-snap-081':
  man=json.loads((c/'manifest.json').read_text());assert all(sha(w/(name+'-inputs')/n)==h for n,h in man['file_sha256'].items())
a=root/'outer-wall-patch-085';b=root/'outer-wall-bisect-086';p,f,o,n=mesh(a);q,g,own,nei=mesh(b);p0,f0,o0,n0=mesh(root/'radial-selective-snap-081');assert np.array_equal(p,p0)
parent=cells(f,o,n);assert Counter(signature(x) for x in parent)==Counter(signature(x) for x in cells(f0,o0,n0))
block=re.search(r'outerWall\s*\{(.*?)\}',(a/'constant/polyMesh/boundary').read_text(),re.S)[1];start=int(re.search(r'startFace\s+(\d+)',block)[1]);count=int(re.search(r'nFaces\s+(\d+)',block)[1]);assert count==6784
outer_ids=range(start,start+count);outerpoints=set(np.concatenate([f[i] for i in outer_ids]));selected=set(o[list(outer_ids)]);assert len(selected)==6784
edges=set()
for face in f:
 for x,y in zip(face,np.roll(face,-1)):
  if (x in outerpoints)!=(y in outerpoints):edges.add(tuple(sorted((int(x),int(y)))))
assert len(edges)==6912
edge_to_mid={edge:len(p)+i for i,edge in enumerate(sorted(edges))};expected=np.concatenate([p,np.array([(p[x]+p[y])/2 for x,y in sorted(edges)])]);assert len(expected)==27648
expected_cells=[];ancestry=[]
for c,faces in enumerate(parent):
 if c not in selected:expected_cells.append(faces);ancestry.append(c);continue
 inner=[];outer=[];wall=None
 for face in faces:
  state=[x in outerpoints for x in face]
  if all(state):outer.append(face);wall=face
  elif not any(state):inner.append(face)
  else:
   expanded=[]
   for x,y in zip(face,face[1:]+face[:1]):
    expanded.append((x,1 if x in outerpoints else 0))
    if (x in outerpoints)!=(y in outerpoints):expanded.append((edge_to_mid[tuple(sorted((x,y)))],2))
   inner.append([x for x,s in expanded if s!=1]);outer.append([x for x,s in expanded if s!=0])
 assert wall is not None
 mids=[]
 for x in wall:
  hits=[mid for edge,mid in edge_to_mid.items() if x in edge];assert len(hits)==1;mids.append(hits[0])
 inner.append(mids);outer.append(mids[::-1]);assert len(inner)==len(outer)==6 and all(len(x)==4 for x in inner+outer)
 expected_cells.extend((inner,outer));ancestry.extend((c,c))
assert len(expected_cells)==20352
# Match every point and each fully oriented cell; derive own neighbour proof from incidence.
distance,pm=cKDTree(expected).query(q);assert distance.max()<1e-16 and len(set(pm))==len(q)==len(expected)
reverse=np.empty(len(expected),int);reverse[pm]=np.arange(len(pm));assert np.array_equal(q[reverse[:len(p)]],p)
lookup={signature(fs):i for i,fs in enumerate(expected_cells)};assert len(lookup)==20352
actual=cells([pm[x] for x in g],own,nei);cm=np.array([lookup[signature(fs)] for fs in actual]);assert len(set(cm))==20352
incidence=defaultdict(list)
for c,fs in enumerate(expected_cells):
 for face in fs:incidence[tuple(sorted(face))].append((c,cycle(face)))
assert len(incidence)==len(g)==68224
for i,face in enumerate(g):
 mapped=pm[face];items=incidence[tuple(sorted(mapped))];assert (int(cm[own[i]]),cycle(mapped)) in items
 if i<len(nei):assert len(items)==2 and (int(cm[nei[i]]),cycle(mapped[::-1])) in items
 else:assert len(items)==1
# Prove oriented closure for every final cell.
for fs in actual:
 ed=Counter()
 for face in fs:
  for x,y in zip(face,face[1:]+face[:1]):ed[x,y]+=1
 assert all(v==1 and ed[y,x]==1 for (x,y),v in ed.items())
# Exterior wall and join quads are unchanged; remaining end faces subdivide within convex planar parents.
boundary=[pm[x] for x in g[len(nei):]];final_cycles=Counter(cycle(x) for x in boundary)
for i in outer_ids:assert final_cycles[cycle(f[i])]==1
join=[];endparents=[];childends=[]
for i in range(len(n),len(f)):
 if i in outer_ids:continue
 face=f[i]
 if np.all(p[face,2]==p[:,2].min()) or np.all(p[face,2]==p[:,2].max()):endparents.append(i)
 else:join.append(i);assert final_cycles[cycle(face)]==1
assert len(join)==6784 and len(endparents)==512
# Boundary face ancestry follows the reconstructed cell surface. End planes remain exact.
new_boundary_edges=Counter();old_boundary_edges=Counter()
for face in boundary:
 if np.all(expected[face,2]==p[:,2].min()) or np.all(expected[face,2]==p[:,2].max()):childends.append(face)
assert len(childends)==768
for idx in endparents:
 face=f[idx];xy=p[face,:2];cross=np.cross(np.roll(xy,-1,axis=0)-xy,np.roll(xy,-2,axis=0)-np.roll(xy,-1,axis=0));assert np.all(cross>0) or np.all(cross<0)
 # Expand original boundary cycle by midpoint labels; children must cancel only their shared diagonal.
 exp=[]
 for x,y in zip(face,np.roll(face,-1)):
  exp.append(int(x));key=tuple(sorted((int(x),int(y))))
  if key in edge_to_mid:exp.append(edge_to_mid[key])
 allowed=set(exp);children=[v for v in childends if set(v)<=allowed];assert len(children)==(2 if o[idx] in selected else 1)
 ed=Counter()
 for v in children:
  for x,y in zip(v,np.roll(v,-1)):ed[int(x),int(y)]+=1
 net=Counter({e:v-ed[e[::-1]] for e,v in ed.items() if v>ed[e[::-1]]});want=Counter(zip(exp,exp[1:]+exp[:1]));assert net==want
# Geometric native-style readback, including fixed-domain warp and volume.
cf=np.empty((len(g),3));sf=cf.copy();warp=np.empty(len(g))
cf[:],sf[:],warp[:]=geometry(q[np.array(g)])
vf=np.einsum('ij,ij->i',cf,sf)/3;vol=np.bincount(own,weights=vf,minlength=20352)-np.bincount(nei,weights=vf[:len(nei)],minlength=20352);assert vol.min()>0
pc,ps,pw=geometry(p[np.array(f)]);pv=np.einsum('ij,ij->i',pc,ps)/3;parentvol=np.bincount(o,weights=pv,minlength=len(parent))-np.bincount(n,weights=pv[:len(n)],minlength=len(parent));assert abs(vol.sum()/parentvol.sum()-1)<1e-12
join_final=[g[len(nei)+i] for i,v in enumerate(boundary) if cycle(v) in {cycle(f[j]) for j in join}];mi=metrics(q,join_final,10471.975511966);assert mi['max_normal_frame_speed_m_s']<1e-8
zone=(b/'constant/polyMesh/pointZones').read_text();mt=re.search(r'frozenPoints\s*\{.*?pointLabels\s+List<label>\s*(\d+)\s*\((.*?)\)',zone,re.S);frozen=np.fromstring(mt[2],sep=' ',dtype=int);assert len(frozen)==int(mt[1])
new_endpoints=[i for i in range(len(p),len(expected)) if expected[i,2] in (p[:,2].min(),p[:,2].max())]
res=dict(reader_sha256=sha(Path(__file__)),all_payloads_initial_inputs_verified=True,repatch_preserves_oriented_cells=True,all_original_point_coordinates_exact=True,new_midpoints=len(edges),max_midpoint_serialization_error_m=float(distance.max()),all_cells_bijective_to_independent_bisection=True,oriented_faces_and_owner_neighbour_verified=True,children_per_selected_parent=2,unselected_parents_unchanged=True,all_cell_edges_cancel=True,outer_faces_unchanged=6784,join_faces_unchanged=6784,end_parent_faces=512,end_child_faces=768,end_coverage_oriented_edges_and_convexity_verified=True,cells=len(actual),points=len(q),faces=len(g),internal_faces=len(nei),minimum_cell_volume_m3=float(vol.min()),volume_m3=float(vol.sum()),parent_volume_m3=float(parentvol.sum()),maximum_face_warp_m=float(warp.max()),join=mi,frozen_zone_points=len(frozen),new_end_points=len(new_endpoints),new_end_points_in_frozen_zone=len(set(pm[frozen])&set(new_endpoints)),native_mesh_admitted=True,flow_solver_launched=False,physical_boundary_layers_qualified=False)
with (w/'readback.json').open('x') as out:json.dump(res,out,indent=2)
print(json.dumps(res))
