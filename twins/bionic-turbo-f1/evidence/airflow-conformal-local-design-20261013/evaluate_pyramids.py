"""Evaluate one fixed local face-pyramid proposal; never write a native mesh."""
import json,sys,hashlib
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from audit_diagnostic import ascii_list
from run_case import ascii_faces
from frame_balance_batches import geometry
w=Path(__file__).parent;case=Path('work/bionic-airflow-20261012/regional-castellation-fixed-091');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((case/'report.json').read_text());assert all(sha(case/k)==h for k,h in r['output_sha256'].items()) and not r['container_state']['OOMKilled']
m=case/'2.6e-06/polyMesh';p=ascii_list((m/'points').read_text(),True);f=[np.array(v,int) for v in ascii_faces((m/'faces').read_text())];o=ascii_list((m/'owner').read_text()).astype(int);n=ascii_list((m/'neighbour').read_text()).astype(int);nc=int(max(o.max(),n.max())+1)
cf=np.empty((len(f),3));sf=cf.copy()
for size in sorted(set(map(len,f))):
 ids=np.array([i for i,v in enumerate(f) if len(v)==size]);cf[ids],sf[ids],_=geometry(p[np.array([f[i] for i in ids])])
inc=[[] for _ in range(nc)]
for i,c in enumerate(o):inc[c].append((i,1))
for i,c in enumerate(n):inc[c].append((i,-1))
est=np.zeros((nc,3));np.add.at(est,o,cf);np.add.at(est,n,cf[:len(n)]);est/=np.array(list(map(len,inc)))[:,None];vol3=np.zeros(nc);cc=np.zeros((nc,3))
for labels,centres,areas,sgn in ((o,cf,sf,1),(n,cf[:len(n)],sf[:len(n)],-1)):
 v=sgn*np.einsum('ij,ij->i',areas,centres-est[labels]);np.add.at(vol3,labels,v);np.add.at(cc,labels,v[:,None]*(.75*centres+.25*est[labels]))
cc/=vol3[:,None]
audit=json.loads(Path('twins/bionic-turbo-f1/evidence/airflow-castellation-transition-audit-20261013/readback.json').read_text())['reports'][-1];seeds=[audit['worst_concavity_tuple'][0],audit['worst_face']['owner']];assert seeds==[825,20005]
level=ascii_list((m/'cellLevel').read_text()).astype(int);assert all(level[c]==0 for c in seeds)
reports=[]
for parent in seeds:
 apex=len(p);coords=np.vstack([p,cc[parent]]);children=[];triangles=defaultdict(list)
 for child,(face,sign) in enumerate(inc[parent]):
  base=f[face][::sign].tolist();sides=[[int(y),int(x),apex] for x,y in zip(base,base[1:]+base[:1])];polys=[base]+sides;edges=Counter()
  for poly in polys:
   for x,y in zip(poly,poly[1:]+poly[:1]):edges[x,y]+=1
  assert all(v==1 and edges[y,x]==1 for (x,y),v in edges.items())
  centres=[];areas=[]
  for poly in polys:
   c,a,_=geometry(coords[np.array(poly)][None,:,:]);centres.append(c[0]);areas.append(a[0])
  centres=np.array(centres);areas=np.array(areas);estimate=centres.mean(axis=0);pv=np.einsum('ij,ij->i',areas,centres-estimate);volume=pv.sum()/3;centre=(pv[:,None]*(.75*centres+.25*estimate)).sum(axis=0)/pv.sum()
  lens=np.linalg.norm(areas,axis=1);normals=areas/lens[:,None];delta=centres[None,:,:]-centres[:,None,:];score=np.einsum('ijk,ik->ij',delta,normals)/np.maximum(np.linalg.norm(delta,axis=2),1e-300);np.fill_diagonal(score,-1)
  # Base is internal only when the inherited source face was internal; all side triangles are internal.
  ia=areas if face<len(n) else areas[1:];mean=np.linalg.norm(ia,axis=1).mean();det=abs(np.linalg.det(ia.T@ia/mean**2))/8
  record=dict(child=child,base_source_face=int(face),base_outward_sign=int(sign),faces=polys,centre_m=centre.tolist(),volume_m3=float(volume),determinant=float(det),max_plane_score=float(score.max()))
  children.append(record)
  for poly in sides:triangles[tuple(sorted(poly))].append((child,poly))
 assert all(len(v)==2 for v in triangles.values())
 angles=[]
 for key,pair in triangles.items():
  (i,poly),(j,other)=pair;assert set(zip(poly,poly[1:]+poly[:1]))=={(y,x) for x,y in zip(other,other[1:]+other[:1])}
  _,a,_=geometry(coords[np.array(poly)][None,:,:]);a=a[0];d=np.array(children[j]['centre_m'])-children[i]['centre_m'];angle=np.degrees(np.arccos(np.clip(np.dot(d,a)/np.linalg.norm(d)/np.linalg.norm(a),-1,1)));angles.append(dict(kind='new_internal',children=[i,j],vertices=poly,angle_deg=float(angle)))
 for child in children:
  face=child['base_source_face'];sign=child['base_outward_sign']
  if face<len(n):
   other=int(n[face] if sign==1 else o[face]);assert other not in seeds
   d=cc[other]-child['centre_m'];a=sf[face]*sign;angle=np.degrees(np.arccos(np.clip(np.dot(d,a)/np.linalg.norm(d)/np.linalg.norm(a),-1,1)));angles.append(dict(kind='inherited_base',child=child['child'],source_face=face,unchanged_neighbour=other,angle_deg=float(angle)))
 volume=sum(c['volume_m3'] for c in children);minimum=min(c['determinant'] for c in children);maximum=max(a['angle_deg'] for a in angles);badplanes=sum(c['max_plane_score']>-1e-6 for c in children)
 bundle=dict(parent=parent,source_mesh=str(m),apex_source='native_formula_volume_centroid',apex_label=apex,apex_xyz_m=cc[parent].tolist(),original_points=[dict(label=int(i),xyz_m=p[i].tolist()) for i in sorted({v for c in children for poly in c['faces'] for v in poly if v!=apex})],children=children,angles=angles,source_volume_m3=float(vol3[parent]/3),sum_child_volumes_m3=volume,all_cell_edges_cancel=True,internal_triangles_paired_opposite=True,original_base_faces_preserved=True)
 (w/f'parent-{parent}-candidate.json').write_text(json.dumps(bundle,indent=2)+'\n')
 reports.append(dict(parent=parent,children=len(children),new_internal_triangles=len(triangles),minimum_volume_m3=min(c['volume_m3'] for c in children),relative_volume_difference=float((volume-vol3[parent]/3)/(vol3[parent]/3)),minimum_determinant=minimum,bad_determinants=sum(c['determinant']<.001 for c in children),flagged_plane_cells=badplanes,maximum_angle_deg=maximum,faces_over_70=sum(a['angle_deg']>70 for a in angles),preflight_pass=bool(minimum>=.001 and maximum<=70 and badplanes==0 and all(c['volume_m3']>0 for c in children))))
(w/'readback.json').write_text(json.dumps(dict(source_receipt_sha256=sha(case/'report.json'),reader_sha256=sha(Path(__file__)),all_source_payloads_verified=True,native_execution=False,thresholds_unchanged=True,candidates=reports),indent=2)+'\n');print(json.dumps(reports))
