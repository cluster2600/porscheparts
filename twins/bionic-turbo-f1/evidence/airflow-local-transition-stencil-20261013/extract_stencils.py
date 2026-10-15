"""Extract exact labelled cell complexes for two diagnosed transitions, not CFD cases."""
import hashlib,json,re,sys,tarfile
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
from scipy.spatial import cKDTree
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from audit_diagnostic import ascii_list
from run_case import ascii_faces
w=Path(__file__).parent;root=Path('work/bionic-airflow-20261012');coarse=root/'outer-wall-bisect-086';fine=root/'regional-castellation-fixed-091'
for c in (coarse,fine):
 r=json.loads((c/'report.json').read_text());assert all(sha(c/n)==v for n,v in r['output_sha256'].items()) and not r['container_state']['OOMKilled']
def load(m):
 p=ascii_list((m/'points').read_text(),True);f=[np.array(v,int) for v in ascii_faces((m/'faces').read_text())];o=ascii_list((m/'owner').read_text()).astype(int);n=ascii_list((m/'neighbour').read_text()).astype(int);cells=[[] for _ in range(int(max(o.max(),n.max())+1))]
 for i,c in enumerate(o):cells[c].append((i,1))
 for i,c in enumerate(n):cells[c].append((i,-1))
 return p,f,o,n,cells
p,f,o,n,pc=load(coarse/'constant/polyMesh');q,g,a,b,gc=load(fine/'2.6e-06/polyMesh');level=ascii_list((fine/'2.6e-06/polyMesh/cellLevel').read_text()).astype(int)
d,ix=cKDTree(q).query(p);assert np.all(d==0) and len(set(ix))==len(p);orig=np.full(len(q),-1,int);orig[ix]=np.arange(len(p));pv=[tuple(sorted(set(np.concatenate([f[i] for i,_ in cell])))) for cell in pc];lookup={v:i for i,v in enumerate(pv)};assert len(lookup)==len(pc)
gv=[np.unique(np.concatenate([g[i] for i,_ in cell])) for cell in gc];anchors=[set(orig[v][orig[v]>=0]) for v in gv];ancestry=np.full(len(gc),-1,int);children=defaultdict(list)
for c,v in enumerate(gv):
 if level[c]==0:ancestry[c]=lookup[tuple(sorted(anchors[c]))]
 else:
  assert len(anchors[c])==1
  for point in v:children[int(point)].append(c)
centres={}
for point,cs in children.items():
 if orig[point]>=0 or len(cs)!=8:continue
 key=tuple(sorted(set().union(*(anchors[c] for c in cs))))
 if len(key)==8 and key in lookup:
  parent=lookup[key];assert parent not in centres;centres[parent]=point
  for c in cs:assert ancestry[c]==-1;ancestry[c]=parent
assert np.all(ancestry>=0) and Counter(np.bincount(ancestry,minlength=len(pc)))==Counter({1:16832,8:3520})
# Seed values come from the published audit, not assumed numbering after mapping.
audit=Path('twins/bionic-turbo-f1/evidence/airflow-castellation-transition-audit-20261013/readback.json');rr=json.loads(audit.read_text())['reports'][-1];worst=rr['worst_face'];seeds={'face_planes':[rr['worst_concavity_tuple'][0]],'nonorthogonality':[worst['owner'],worst['neighbour']]}
assert a[worst['label']]==worst['owner'] and b[worst['label']]==worst['neighbour']
def cell_complex(points,faces,owner,nei,cells,selected):
 selected=set(map(int,selected));ids=sorted(set(i for c in selected for i,_ in cells[c]));vertices=sorted(set(np.concatenate([faces[i] for i in ids])));internal=[];boundary=[];edges=Counter()
 for i in ids:
  left=int(owner[i]);right=int(nei[i]) if i<len(nei) else None;record=dict(source_face=i,vertices=faces[i].tolist(),source_owner=left,source_neighbour=right)
  if left in selected and right in selected:internal.append(record)
  else:
   sign=1 if left in selected else -1;record.update(outward_sign=sign,source_kind='original_boundary' if right is None else 'synthetic_cut');boundary.append(record)
   face=faces[i][::sign]
   for x,y in zip(face,np.roll(face,-1)):edges[int(x),int(y)]+=1
 for c in selected:
  ce=Counter()
  for i,s in cells[c]:
   face=faces[i][::s]
   for x,y in zip(face,np.roll(face,-1)):ce[int(x),int(y)]+=1
  assert all(v==1 and ce[y,x]==1 for (x,y),v in ce.items())
 assert all(v==edges[y,x] for (x,y),v in edges.items())
 adjacency={c:set() for c in selected}
 for r in internal:adjacency[r['source_owner']].add(r['source_neighbour']);adjacency[r['source_neighbour']].add(r['source_owner'])
 reached={min(selected)};queue=list(reached)
 while queue:
  c=queue.pop()
  for other in adjacency[c]-reached:reached.add(other);queue.append(other)
 assert reached==selected
 return dict(points=[dict(source_point=int(i),xyz_m=points[i].tolist()) for i in vertices],cells=[dict(source_cell=c,oriented_faces=[[int(i),int(s)] for i,s in cells[c]]) for c in sorted(selected)],internal_faces=internal,boundary_faces=boundary,all_cell_edges_cancel=True,union_boundary_edges_cancel=True,face_connected=True)
summaries=[]
for name,seed in seeds.items():
 ring=set(seed)
 for c in seed:
  for i,_ in gc[c]:
   ring.add(int(a[i]))
   if i<len(b):ring.add(int(b[i]))
 parents=sorted(set(ancestry[list(ring)]));selected=np.flatnonzero(np.isin(ancestry,parents));current=cell_complex(q,g,a,b,gc,selected);source=cell_complex(p,f,o,n,pc,parents)
 bundle=dict(scope='Exact read-only complexes, not standalone admitted CFD domains; cuts are synthetic. No corrective stencil applied.',seed_cells=seed,one_face_ring_cells=sorted(ring),complete_parent_families=True,parent_cells=parents,source086=source,source091=current,ancestry=[dict(cell=int(c),parent=int(ancestry[c]),level=int(level[c])) for c in selected])
 (w/(name+'-complex.json')).write_text(json.dumps(bundle,indent=2)+'\n');summaries.append(dict(name=name,seeds=seed,parents=len(parents),cells=len(selected),points=len(current['points']),internal_faces=len(current['internal_faces']),boundary_faces=len(current['boundary_faces']),synthetic_cuts=sum(r['source_kind']=='synthetic_cut' for r in current['boundary_faces']),original_boundary_faces=sum(r['source_kind']=='original_boundary' for r in current['boundary_faces']),levels=dict(Counter(map(int,level[selected])))))
archive=Path('work/bionic-native-diagnostics-20261012/OpenFOAM-v2406.tgz');assert sha(archive)=='8d1450fb89eec1e7cecc55c3bb7bc486ccbf63d069379d1d5d7518fa16a4686a';members=['OpenFOAM-v2406/applications/utilities/mesh/advanced/splitCells/splitCells.C','OpenFOAM-v2406/applications/utilities/mesh/manipulation/subsetMesh/subsetMesh.C']
with tarfile.open(archive) as t:refs=[dict(member=m,sha256=hashlib.sha256(t.extractfile(m).read()).hexdigest()) for m in members]
(w/'readback.json').write_text(json.dumps(dict(reader_sha256=sha(Path(__file__)),audit_sha256=sha(audit),source_receipts={str(c):sha(c/'report.json') for c in (coarse,fine)},all_source_payloads_verified=True,native_rerun=False,source_members=refs,source_url='https://dl.openfoam.com/source/v2406/OpenFOAM-v2406.tgz',archive_sha256=sha(archive),complexes=summaries),indent=2)+'\n');print(json.dumps(summaries))
