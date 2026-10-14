"""Scalar independent readback of candidate topology, source ancestry and quality."""
import json,sys,hashlib,math
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from audit_diagnostic import ascii_list
from run_case import ascii_faces
w=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();m=Path('work/bionic-airflow-20261012/regional-castellation-fixed-091/2.6e-06/polyMesh');p=ascii_list((m/'points').read_text(),True);f=list(ascii_faces((m/'faces').read_text()));o=ascii_list((m/'owner').read_text()).astype(int);n=ascii_list((m/'neighbour').read_text()).astype(int)
inc=defaultdict(list)
for i,c in enumerate(o):inc[int(c)].append((i,1))
for i,c in enumerate(n):inc[int(c)].append((i,-1))
def polygon(x):
 if len(x)==3:return np.mean(x,axis=0),np.cross(x[1]-x[0],x[2]-x[0])/2
 seed=np.mean(x,axis=0);area=np.zeros(3);weighted=np.zeros(3);weight=0.
 for a,b in zip(x,x[1:]+x[:1]):
  cross=np.cross(b-a,seed-a);mag=float(np.linalg.norm(cross));area+=cross/2;weighted+=mag*(a+b+seed)/3;weight+=mag
 return weighted/weight,area

def metrics(polys):
 ca=[polygon(x) for x in polys];seed=sum(c for c,a in ca)/len(ca);v=[];moment=[]
 for c,a in ca:
  pv=float(np.dot(a,c-seed))/3;v.append(pv);moment.append(pv*(3*c+seed)/4)
 volume=math.fsum(v);return sum(moment)/volume,volume,ca
# Analytic unit cube and one face pyramid.
cube=[np.array(x,float) for x in [(0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1)]]
cycles=[[0,3,2,1],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]]
c,v,_=metrics([[cube[i] for i in poly] for poly in cycles]);assert abs(v-1)<1e-15 and np.max(abs(c-.5))<1e-15
apex=np.array([.5,.5,.5]);base=cycles[0];polys=[[cube[i] for i in base]]+[[cube[b],cube[a],apex] for a,b in zip(base,base[1:]+base[:1])];c,v,_=metrics(polys);assert abs(v-1/6)<1e-15 and np.max(abs(c-[.5,.5,.125]))<1e-15
cache={}
def source_cell(c):
 if c not in cache:cache[c]=metrics([[p[v] for v in f[i][::s]] for i,s in inc[c]])
 return cache[c]
reports=[]
for parent in (825,20005):
 path=w/f'parent-{parent}-candidate.json';b=json.loads(path.read_text());xyz={r['label']:np.array(r['xyz_m']) for r in b['original_points']};apex=b['apex_label'];xyz[apex]=np.array(b['apex_xyz_m']);sc,sv,_=source_cell(parent);assert np.allclose(sc,xyz[apex],rtol=0,atol=1e-17)
 assert len(b['children'])==len(inc[parent]);assert {r['base_source_face'] for r in b['children']}=={i for i,s in inc[parent]}
 old={v for i,s in inc[parent] for v in f[i]};assert set(xyz)-{apex}==old and all(np.array_equal(xyz[v],p[v]) for v in old)
 tri=defaultdict(list);children={};dets=[];scores=[];volumes=[]
 for child in b['children']:
  i=child['child'];face=child['base_source_face'];sign=dict(inc[parent])[face];base=list(f[face][::sign]);assert child['faces'][0]==base and child['base_outward_sign']==sign
  expected=[[int(y),int(x),apex] for x,y in zip(base,base[1:]+base[:1])];assert child['faces'][1:]==expected
  edge=Counter()
  for poly in child['faces']:
   for a,z in zip(poly,poly[1:]+poly[:1]):edge[a,z]+=1
  assert all(v==1 and edge[z,a]==1 for (a,z),v in edge.items())
  cc,volume,ca=metrics([[xyz[v] for v in poly] for poly in child['faces']]);assert np.allclose(cc,child['centre_m'],rtol=0,atol=1e-16);assert math.isclose(volume,child['volume_m3'],rel_tol=1e-12)
  areas=[a for c,a in ca][0 if face<len(n) else 1:];avg=math.fsum(float(np.linalg.norm(a)) for a in areas)/len(areas);tensor=sum(np.outer(a,a) for a in areas)/avg**2;det=abs(float(np.dot(tensor[0],np.cross(tensor[1],tensor[2]))))/8
  score=max(float(np.dot(d-c,a)/np.linalg.norm(d-c)/np.linalg.norm(a)) for k,(c,a) in enumerate(ca) for j,(d,_) in enumerate(ca) if k!=j)
  assert math.isclose(det,child['determinant'],rel_tol=1e-9,abs_tol=1e-14);assert abs(score-child['max_plane_score'])<1e-10
  children[i]=(cc,ca,child);dets.append(det);scores.append(score);volumes.append(volume)
  for poly in expected:tri[tuple(sorted(poly))].append((i,poly))
 assert all(len(v)==2 for v in tri.values())
 for pair in tri.values():
  a=pair[0][1];z=pair[1][1];assert set(zip(a,a[1:]+a[:1]))=={(v,u) for u,v in zip(z,z[1:]+z[:1])}
 angles=[]
 for row in b['angles']:
  if row['kind']=='new_internal':
   i,j=row['children'];assert {i,j}=={t[0] for t in tri[tuple(sorted(row['vertices']))]};d=children[j][0]-children[i][0];_,area=polygon([xyz[v] for v in row['vertices']])
  else:
   i=row['child'];child=children[i][2];face=child['base_source_face'];sign=child['base_outward_sign'];other=int(n[face] if sign==1 else o[face]);assert other==row['unchanged_neighbour'];d=source_cell(other)[0]-children[i][0];area=children[i][1][0][1]
  angle=math.degrees(math.acos(max(-1,min(1,float(np.dot(d,area)/np.linalg.norm(d)/np.linalg.norm(area))))));assert abs(angle-row['angle_deg'])<1e-8;angles.append(angle)
 assert len(angles)==len(tri)+sum(r['base_source_face']<len(n) for r in b['children'])
 reports.append(dict(parent=parent,candidate_sha256=sha(path),apex_matches_source_centroid=True,base_faces_and_original_points_exact=True,side_triangles_and_edges_verified=True,quality_values_independently_reproduced=True,minimum_determinant=min(dets),bad_determinants=sum(d<.001 for d in dets),flagged_plane_cells=sum(s>-1e-6 for s in scores),maximum_angle_deg=max(angles),faces_over_70=sum(a>70 for a in angles),relative_volume_difference=(math.fsum(volumes)-sv)/sv))
(w/'independent-readback.json').write_text(json.dumps(dict(reader_sha256=sha(Path(__file__)),analytic_cube_and_pyramid_checks=True,reports=reports,native_execution=False,accepted=False),indent=2)+'\n');print(json.dumps(reports))
