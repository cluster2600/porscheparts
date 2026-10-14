"""Independent scalar readback of the outer-buffer proposal."""
import ast,json,hashlib,math,sys,csv
from pathlib import Path
from collections import defaultdict,Counter
import numpy as np
from scipy.spatial import cKDTree
w=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();helper=Path('twins/bionic-turbo-f1/evidence/airflow-conformal-local-design-20261013/verify_pyramids.py');assert sha(helper)=='673f80a53bd03dba18820fa060c51e4cea75c660a6e546a8cda6c1e394be6c2a'
module=ast.parse(helper.read_text());defs=ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in ('polygon','metrics')],type_ignores=[]);exec(compile(defs,str(helper),'exec'))
s=json.loads((w/'construction.json').read_text());source=Path('work/bionic-airflow-20261012/full-collar-063');parent=json.loads((source/'construction.json').read_text());assert sha(source/'construction.json')==s['source_construction_sha256']
for path,digest in s['source_receipts'].items():
 c=Path(path);assert sha(c/'report.json')==digest;r=json.loads((c/'report.json').read_text());assert all(sha(c/n)==h for n,h in r['output_sha256'].items())
p=np.array(s['vertices']);zi=s['source_interval_indices'];assert zi==[49,50,51];assert s['stations_m']==[parent['stations_m'][i] for i in [49,50,51,52]] and s['radii_m']==[parent['radii_m'][i] for i in [49,50,51,52]]
qi,_,qo=parent['radial_ratios'];assert s['radial_ratios']==[qi,1,(1+qo)/2,1+3*(qo-1)/4,qo]
expected=[]
for ring,(ratio,n) in enumerate(zip(s['radial_ratios'],(256,128,256,256,256))):
 pairs=list(zip(s['stations_m'],s['radii_m']))
 if ring>=3:pairs=sorted(pairs+[((a[0]+b[0])/2,(a[1]+b[1])/2) for a,b in zip(pairs,pairs[1:])])
 for z,r in pairs:
  expected.extend([(ratio*math.cos(2*math.pi*i/n)*r,ratio*math.sin(2*math.pi*i/n)*r,z) for i in range(n)])
d,mapping=cKDTree(p).query(expected);assert len(p)==len(expected)==len(set(mapping)) and d.max()<1e-16
reg=defaultdict(list);polys=[]
for cell,block in enumerate(s['blocks']):
 # These are collapsed hexahedra; reconstruct the two triangular ends and three lateral faces directly.
 if s['stages'][cell]=='buffer':
  assert len(set(block))==8;lo=block[:4];hi=block[4:];n=4
 else:
  lo=block[:3];hi=block[4:7];assert block[2]==block[3] and block[6]==block[7];n=3
 faces=[lo[::-1],hi]+[[lo[i],lo[(i+1)%n],hi[(i+1)%n],hi[i]] for i in range(n)];polys.append(faces);edge=Counter()
 for face in faces:
  reg[tuple(sorted(face))].append((cell,face))
  for a,b in zip(face,face[1:]+face[:1]):edge[a,b]+=1
 assert all(n==1 and edge[b,a]==1 for (a,b),n in edge.items())
assert all(len(v) in (1,2) for v in reg.values());centres=[];volumes=[];rows=[];all_dets=[];internal_counts=[];boundary=[];interfaces=[];stagejoins=[]
for key,pair in reg.items():
 if len(pair)==1:boundary.append(key)
 else:
  (a,x),(b,y)=pair;assert set(zip(x,x[1:]+x[:1]))=={(v,u) for u,v in zip(y,y[1:]+y[:1])}
  if s['rotating'][a]!=s['rotating'][b]:interfaces.append(key)
  if {s['stages'][a],s['stages'][b]}=={'angular','axial'}:stagejoins.append(key)
assert set(interfaces)=={tuple(sorted(f)) for f in s['mrf_faces']} and len(interfaces)==384
assert set(stagejoins)=={tuple(sorted(f)) for f in s['stage_join_faces']} and len(stagejoins)==768
collapse=lambda f:tuple(sorted(set(f)))
assert Counter(boundary)==Counter(collapse(f) for f in s['walls'])
# Compare MRF faces with precisely the three source intervals, using coordinate matching only.
oldp=np.array(parent['vertices']);dist,oldmap=cKDTree(oldp).query(p);assert all(dist[i]<1e-16 for face in s['mrf_faces'] for i in face)
sourcefaces=parent['expected_interface_faces'][49*128:52*128];assert {tuple(sorted(oldmap[f])) for f in s['mrf_faces']}=={tuple(sorted(f)) for f in sourcefaces}
for cell,faces in enumerate(polys):
 c,v,ca=metrics([[p[i] for i in f] for f in faces]);centres.append(c);volumes.append(v);internal=[a for face,(cf,a) in zip(faces,ca) if len(reg[tuple(sorted(face))])==2];avg=math.fsum(float(np.linalg.norm(a)) for a in internal)/len(internal);tensor=sum(np.outer(a,a) for a in internal)/avg**2;det=abs(float(np.dot(tensor[0],np.cross(tensor[1],tensor[2]))))/8
 score=max(float(np.dot(cj-ci,ai)/np.linalg.norm(cj-ci)/np.linalg.norm(ai)) for i,(ci,ai) in enumerate(ca) for j,(cj,aj) in enumerate(ca) if i!=j)
 all_dets.append(det);internal_counts.append(len(internal))
 if det<.001:rows.append(dict(cell=cell,stage=s['stages'][cell],interval=cell//2048,role=(cell%2048-768)%3 if s['stages'][cell]=='axial' else None,internal_faces=len(internal),determinant=det))
 assert score<=-1e-6 and v>0
cc=np.array(centres);angle_rows=[]
for pair in reg.values():
 if len(pair)!=2:continue
 (a,f),(b,_)=pair;_,sf=polygon([p[i] for i in f]);d=cc[b]-cc[a];angle=math.degrees(math.acos(max(-1,min(1,float(np.dot(d,sf)/np.linalg.norm(d)/np.linalg.norm(sf))))));angle_rows.append((a,b,angle))
with (w/'angles.csv').open('x') as out:
 writer=csv.writer(out);writer.writerow(['owner','neighbour','angle_deg','owner_stage','neighbour_stage']);writer.writerows((a,b,x,s['stages'][a],s['stages'][b]) for a,b,x in angle_rows)
n=256;radial=.5*n*math.sin(2*math.pi/n)*(qo*qo-qi*qi);expected_volume=radial*sum((z1-z0)*(r0*r0+r0*r1+r1*r1)/3 for z0,z1,r0,r1 in zip(s['stations_m'][:-1],s['stations_m'][1:],s['radii_m'][:-1],s['radii_m'][1:]));assert abs(sum(volumes)/expected_volume-1)<1e-12
quality=json.loads((w/'quality.json').read_text());assert len(rows)==quality['bad_determinants']==0 and abs(max(v[2] for v in angle_rows)-quality['maximum_angle_deg'])<1e-8
perstage={}
for a,b,angle in angle_rows:
 key='/'.join(sorted([s['stages'][a],s['stages'][b]]));perstage[key]=max(perstage.get(key,0),angle)
result=dict(reader_sha256=sha(Path(__file__)),scalar_helper_sha256=sha(helper),construction_sha256=sha(w/'construction.json'),all_source_payloads_verified=True,points_max_match_error_m=float(dist[[i for f in s['mrf_faces'] for i in f]].max()),shared_faces_and_cell_edges_verified=True,mrf_source_faces_matched=384,stage_join_faces_verified=768,minimum_volume_m3=min(volumes),volume_m3=sum(volumes),analytic_volume_m3=expected_volume,bad_cells=len(rows),bad_groups=dict(Counter(str((r['stage'],r['interval'],r['role'],r['internal_faces'])) for r in rows)),minimum_determinant=min(all_dets),faces_over_70=sum(x>70 for _,_,x in angle_rows),severe_stage_pairs=dict(Counter('/'.join(sorted([s['stages'][a],s['stages'][b]])) for a,b,x in angle_rows if x>70)),angle_maxima_by_stage_pair=perstage,native_executed=False,accepted=False)
# Exact topological roles from the archived failed candidate, not a field remap.
old=Path('work/bionic-staged-transition-20261013');manifest=json.loads(Path('work/bionic-airflow-delivery-20261013-staged-transition/file-manifest.json').read_text());assert all(sha(Path('work')/r['path'])==r['sha256'] for r in manifest['files'])
prior=list(csv.DictReader((old/'bad-determinants.csv').open()));mapped=[int(r['cell'])//1536*2048+int(r['cell'])%1536 for r in prior];assert len(mapped)==512 and all(s['stages'][i]=='axial' for i in mapped)
result['previous_failed_role_cells']={'count':len(mapped),'minimum_determinant':min(all_dets[i] for i in mapped),'internal_face_counts':dict(Counter(internal_counts[i] for i in mapped)),'not_geometric_parentage_or_field_map':True}
result['previous_archive_all_payloads_verified']=True
(w/'independent-readback.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
