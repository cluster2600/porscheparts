"""Read final native mesh, exact join and topological child ancestry, no rerun."""
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
def mesh(m):return ascii_list((m/'points').read_text(),True),[np.array(x,int) for x in ascii_faces((m/'faces').read_text())],ascii_list((m/'owner').read_text()).astype(int),ascii_list((m/'neighbour').read_text()).astype(int)
def cyc(f):
 f=tuple(map(int,f));return min(f[i:]+f[:i] for i in range(len(f)))
def cellfaces(f,o,n):
 result=[[] for _ in range(int(max(o.max(),n.max())+1))]
 for i,c in enumerate(o):result[c].append((i,1))
 for i,c in enumerate(n):result[c].append((i,-1))
 return result
for name in ('outer-wall-bisect-086','castellation-target-089','regional-castellation-090','regional-castellation-fixed-091'):
 c=root/name;r=json.loads((c/'report.json').read_text());assert not r['container_state']['OOMKilled'];assert all(sha(c/n)==h for n,h in r['output_sha256'].items())
 if name!='outer-wall-bisect-086':
  man=json.loads((c/'manifest.json').read_text());assert all(sha(w/(name+'-inputs')/n)==h for n,h in man['file_sha256'].items())
parent=root/'outer-wall-bisect-086/constant/polyMesh';case=root/'regional-castellation-fixed-091';final=case/'2.6e-06/polyMesh';p,f,o,n=mesh(parent);q,g,a,b=mesh(final)
assert len(q)==76049 and len(g)==162880 and len(b)==137648
parents=cellfaces(f,o,n);actual=cellfaces(g,a,b);assert len(parents)==20352 and len(actual)==44992
level=ascii_list((final/'cellLevel').read_text()).astype(int);assert Counter(level)==Counter({0:16832,1:28160})
d,ix=cKDTree(q).query(p);assert np.all(d==0) and len(set(ix))==len(p);original=np.full(len(q),-1,int);original[ix]=np.arange(len(p))
pvertices=[tuple(sorted(set(np.concatenate([f[i] for i,_ in fs])))) for fs in parents];plook={v:i for i,v in enumerate(pvertices)};assert len(plook)==len(parents) and all(len(v)==8 for v in pvertices)
vertices=[np.unique(np.concatenate([g[i] for i,_ in fs])) for fs in actual];anchors=[set(original[v][original[v]>=0]) for v in vertices];ancestry=np.full(len(actual),-1,int)
point_children=defaultdict(list)
for c,v in enumerate(vertices):
 if level[c]==0:assert len(anchors[c])==8;ancestry[c]=plook[tuple(sorted(anchors[c]))]
 else:
  assert len(anchors[c])==1
  for x in v:point_children[int(x)].append(c)
centres={}
for x,cs in point_children.items():
 if original[x]>=0 or len(cs)!=8:continue
 key=tuple(sorted(set().union(*(anchors[c] for c in cs))))
 if len(key)==8 and key in plook:
  par=plook[key];assert par not in centres;centres[par]=x
  for c in cs:assert ancestry[c]==-1;ancestry[c]=par
assert len(centres)==3520 and np.all(ancestry>=0)
counts=np.bincount(ancestry,minlength=len(parents));assert Counter(counts)==Counter({1:16832,8:3520});assert set(np.flatnonzero(counts==8))==set(centres)
# Full oriented edge closure for every final cell, including transition polyhedra.
for fs in actual:
 ed=Counter()
 for i,sign in fs:
  face=g[i][::sign]
  for x,y in zip(face,np.roll(face,-1)):ed[int(x),int(y)]+=1
 assert all(v==1 and ed[y,x]==1 for (x,y),v in ed.items())
# Named source086 outer patch; source078 join matched by exact coordinates and cycles.
bl=re.search(r'outerWall\s*\{(.*?)\}',(parent/'boundary').read_text(),re.S)[1];st=int(re.search(r'startFace\s+(\d+)',bl)[1]);ct=int(re.search(r'nFaces\s+(\d+)',bl)[1]);outerparents=set(o[st:st+ct])
s=root/'radial-split-078/constant/domain1/polyMesh';sp,sf,so,sn=mesh(s);bl=re.search(r'domain1_to_rotorZone\s*\{(.*?)\}',(s/'boundary').read_text(),re.S)[1];st=int(re.search(r'startFace\s+(\d+)',bl)[1]);ct=int(re.search(r'nFaces\s+(\d+)',bl)[1]);jp=np.unique(np.concatenate(sf[st:st+ct]));dd,jm=cKDTree(q).query(sp[jp]);assert np.all(dd==0);mp=dict(zip(jp,jm));expected={cyc([mp[x] for x in face]) for face in sf[st:st+ct]}
join=[i for i in range(len(b),len(g)) if cyc(g[i]) in expected];assert len(join)==6784 and {cyc(g[i]) for i in join}==expected
joinparents=set(ancestry[a[join]])
# All debug meshes are retained. Compare decoded topology/points/levels at every written stage.
snapshots=[]
for dpath in sorted((d for d in case.iterdir() if d.is_dir() and (d/'polyMesh/points').exists()),key=lambda x:float(x.name)):
 pp,ff,oo,nn=mesh(dpath/'polyMesh');ll=ascii_list((dpath/'polyMesh/cellLevel').read_text()).astype(int)
 snapshots.append(dict(directory=dpath.name,points=len(pp),faces=len(ff),cells=len(ll),same_as_final_geometry_topology=(np.array_equal(pp,q) and len(ff)==len(g) and all(np.array_equal(x,y) for x,y in zip(ff,g)) and np.array_equal(oo,a) and np.array_equal(nn,b)),same_levels=np.array_equal(ll,level)))
# Evaluate all final faces by polygon width, retain warped fixed faces.
cf=np.empty((len(g),3));sfv=cf.copy();warp=np.empty(len(g))
for width in sorted(set(map(len,g))):
 ids=np.array([i for i,x in enumerate(g) if len(x)==width]);cf[ids],sfv[ids],warp[ids]=geometry(q[np.array([g[i] for i in ids])])
vf=np.einsum('ij,ij->i',cf,sfv)/3;vol=np.bincount(a,weights=vf,minlength=len(actual))-np.bincount(b,weights=vf[:len(b)],minlength=len(actual));assert vol.min()>0
bad=ascii_list((final/'sets/concaveCells').read_text()).astype(int);nonorth=ascii_list((final/'sets/nonOrthoFaces').read_text()).astype(int);assert len(set(bad))==6700 and len(set(nonorth))==14080
mi=metrics(q,[g[i] for i in join],10471.975511966)
checks=re.findall(r'Time = ([^\n]+).*?(Failed \d+ mesh checks\.|Mesh OK\.)',(case/'log.checkMesh').read_text(),re.S)
res=dict(reader_sha256=sha(Path(__file__)),all_payloads_and_initial_inputs_verified=True,all_original_coordinates_exact=True,all_cell_edges_cancel=True,topological_ancestry_by_original_anchors_and_shared_eight_child_centre=True,refined_parents=len(centres),children_per_refined_parent=8,unrefined_parents=16832,refined_parents_touching_outer=len(set(centres)&outerparents),refined_parents_touching_join=len(set(centres)&joinparents),cells=len(actual),points=len(q),faces=len(g),internal_faces=len(b),join_quads_exact=len(join),join_metrics=mi,volume_m3=float(vol.sum()),minimum_cell_volume_m3=float(vol.min()),maximum_face_warp_m=float(warp.max()),concave_cells=len(bad),concave_by_level={str(k):v for k,v in Counter(level[bad]).items()},concave_parents_touching_join=len(set(ancestry[bad])&joinparents),severely_nonorthogonal_faces=len(nonorth),debug_snapshots=snapshots,native_check_results=checks,debug_directory_labels_are_not_flow_time=True,native_mesh_admitted=False,flow_solver_launched=False)
(w/'readback.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res))
