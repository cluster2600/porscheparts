"""Read labelled complexes independently against complete archived mesh arrays."""
import json,sys,hashlib
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from audit_diagnostic import ascii_list
from run_case import ascii_faces
w=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
roots={'source086':Path('work/bionic-airflow-20261012/outer-wall-bisect-086/constant/polyMesh'),'source091':Path('work/bionic-airflow-20261012/regional-castellation-fixed-091/2.6e-06/polyMesh')}
meshes={}
for key,path in roots.items():
 p=ascii_list((path/'points').read_text(),True);f=list(ascii_faces((path/'faces').read_text()));o=ascii_list((path/'owner').read_text()).astype(int);n=ascii_list((path/'neighbour').read_text()).astype(int)
 incidence=defaultdict(list)
 for face,c in enumerate(o):incidence[int(c)].append([face,1])
 for face,c in enumerate(n):incidence[int(c)].append([face,-1])
 meshes[key]=(p,f,o,n,incidence)
reports=[]
for filename in ('face_planes-complex.json','nonorthogonality-complex.json'):
 bundle=json.loads((w/filename).read_text());pointsets={};cellvertices={}
 for key in roots:
  data=bundle[key];p,f,o,n,incidence=meshes[key];selected={x['source_cell'] for x in data['cells']};assert len(selected)==len(data['cells'])
  expectedfaces={face for c in selected for face,_ in incidence[c]};expectedpoints={v for face in expectedfaces for v in f[face]}
  assert {x['source_point'] for x in data['points']}==expectedpoints and len(data['points'])==len(expectedpoints)
  for x in data['points']:assert np.array_equal(p[x['source_point']],x['xyz_m'])
  records=data['internal_faces']+data['boundary_faces'];assert len(records)==len(expectedfaces) and {x['source_face'] for x in records}==expectedfaces
  for c in data['cells']:assert c['oriented_faces']==incidence[c['source_cell']]
  for r in records:
   i=r['source_face'];neighbour=int(n[i]) if i<len(n) else None
   assert r['vertices']==list(f[i]) and r['source_owner']==o[i] and r['source_neighbour']==neighbour
   internal=int(o[i]) in selected and neighbour in selected
   assert ('outward_sign' not in r)==internal
   if not internal:assert r['outward_sign']==(1 if int(o[i]) in selected else -1) and r['source_kind']==('original_boundary' if neighbour is None else 'synthetic_cut')
  cellvertices[key]={c:{v for i,_ in incidence[c] for v in f[i]} for c in selected}
  pointsets[key]={tuple(p[i]) for i in expectedpoints}
 assert set(bundle['parent_cells'])==set(cellvertices['source086'])
 assert set(bundle['one_face_ring_cells'])<=set(cellvertices['source091'])
 byparent=defaultdict(list)
 for r in bundle['ancestry']:byparent[r['parent']].append(r)
 assert set(byparent)==set(bundle['parent_cells']) and len(bundle['ancestry'])==len(cellvertices['source091']) and {r['cell'] for r in bundle['ancestry']}==set(cellvertices['source091'])
 p=meshes['source086'][0];q=meshes['source091'][0];oldcoords={tuple(v) for v in p}
 for parent,children in byparent.items():
  expected={tuple(p[i]) for i in cellvertices['source086'][parent]};assert len(expected)==8
  actual=[{tuple(q[i]) for i in cellvertices['source091'][r['cell']]} for r in children]
  anchors=[s&oldcoords for s in actual]
  if len(children)==1:assert children[0]['level']==0 and anchors[0]==expected
  else:
   assert len(children)==8 and all(r['level']==1 for r in children) and all(len(s)==1 for s in anchors) and set.union(*anchors)==expected
   assert len(set.intersection(*actual))==1
 reports.append(dict(file=filename,sha256=sha(w/filename),exact_source_points_faces_incidence=True,cut_classification_verified=True,complete_ancestry_verified=True,parents=len(byparent),cells=len(bundle['ancestry'])))
(w/'independent-readback.json').write_text(json.dumps(dict(reader_sha256=sha(Path(__file__)),reports=reports,native_admission=False,corrective_stencil=False),indent=2)+'\n')
print(json.dumps(reports))
