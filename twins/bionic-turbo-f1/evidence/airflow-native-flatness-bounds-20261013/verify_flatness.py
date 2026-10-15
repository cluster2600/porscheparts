"""Independent native-centre flatness reconstruction with pinned 192-bit moments."""
import gzip,hashlib,importlib.util,json,subprocess,time
from pathlib import Path
from fractions import Fraction as F
from collections import defaultdict,Counter
W=Path(__file__).parent
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def module(name,path,digest):
 assert sha(path)==digest
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
v=module('independent_centres',Path('work/bionic-centre-interval-bounds-20261013/verify_centres_v2.py'),'a259f163405dec0cfb4f1b707698249ea9069de9b02a9db1835fb172f1a0b992')
d=module('dyadic192',Path('work/bionic-remaining-cell-bounds-20261013/dyadic192.py'),'f216b134a93a893b0c04bbe47671eb5ba497e4836e0e2a346220f0b14d83ac14');g=v.g;g.R=d.R;R=d.R
ROOT=F(float('1e-150'));SMALL=F(float('1e-300'));LIMIT=F(float('0.8'))
def calculate(q):
 if len(q)==3:
  vec=g.vector(g.vsub(q[1],q[0]),g.vsub(q[2],q[0]));return {'magS':g.length([x/2 for x in vec]),'flatness':R(1)}
 cf,S=v.polygon(q);mean=g.average(q);w=[];a=[]
 for j in range(len(q)):
  edge=g.vsub(q[(j+1)%len(q)],q[j]);w.append(g.length(g.vector(edge,g.vsub(mean,q[j]))));a.append(g.length([x/2 for x in g.vector(edge,g.vsub(cf,q[j]))]))
 area=sum(a);mag=g.length(S);return dict(W=sum(w),magS=mag,A=area,flatness=mag/(area+R(ROOT)))
def refs():
 count=0
 for scale in (F(1),F(1,1000),F(1,1000000)):
  for mode in range(3):
   raw=((0,0,0),(1,0,0),(0,1,0)) if mode==0 else tuple((x,y,(x*y if mode==2 else 0)) for x,y in ((-1,-1),(1,-1),(1,1),(-1,1)))
   flat=calculate([[R(scale*x) for x in p] for p in raw])['flatness'];A=4*scale*scale
   if mode<2:
    target=F(1) if mode==0 else A/(A+ROOT);assert flat.a<=target<=flat.b
   else:
    left=(A-ROOT*flat.a)/(A*flat.a);right=(A-ROOT*flat.b)/(A*flat.b)
    assert flat.a>0 and left>0 and left*left>=2 and (right<=0 or right*right<=2)
   count+=1
 return count

def main():
 start=time.monotonic();references=refs();report=json.loads((W/'readback.json').read_text());dep=json.loads((W/'dependencies.json').read_text());entries=0
 assert sha(W/'check_flatness.py')==report['source_sha256'] and sha(W/'preflight.md')==report['preflight_sha256'] and sha(W/'dependencies.json')==report['dependencies_sha256']
 assert sha(W/'flatness-bounds.jsonl.gz')==report['bounds_sha256'] and sha(W/'guards.json')==report['guards_sha256']
 assert dep['anchor_commit']=='cbf1a91cf4d53872ad2b067b0dc1fe5fe95e7f2b'
 for name,digest in dep['manifests'].items():
  p=Path(name);phase=p.parent.name.split('20261013-',1)[1];blob=subprocess.check_output(['git','show',dep['anchor_commit']+':twins/bionic-turbo-f1/evidence/airflow-'+phase+'-20261013/file-manifest.json']);assert hashlib.sha256(blob).hexdigest()==sha(p)==digest
  for row in json.loads(blob)['files']:
   p=Path('work')/row['path'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'];entries+=1
 assert len(dep['manifests'])==13 and entries==309==dep['payload_entries_verified']
 source=json.loads(Path('work/bionic-buffered-transition-20261013/construction.json').read_text());system=json.loads(Path('work/bionic-joint-constraints-20261013/system.json').read_text());bindings={r['point']:r for r in system['coordinate_bindings']};u=F(system['archived_regression_point']['u']);boxes=json.loads(Path('work/bionic-angular-independent-bounds-20261013/certificate-readback.json').read_text())['box_results'];domain=[boxes[0]['lower'],boxes[-1]['upper']];assert domain==report['domain_v'] and len(boxes)==153
 templates=((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7));registry=defaultdict(list)
 for cid,block in enumerate(source['blocks']):
  for template in templates:
   face=[]
   for j in template:
    if not face or face[-1]!=block[j]:face.append(block[j])
   if face[-1]==face[0]:face.pop()
   if len(face)<3:continue
   cycle=min(tuple(face[j:]+face[:j]) for j in range(len(face)));registry[tuple(sorted(face))].append((cid,cycle))
 keys=sorted(registry);assert len(keys)==18560
 for uses in registry.values():
  assert len(uses) in (1,2)
  if len(uses)==2:
   rev=list(reversed(uses[0][1]));assert min(tuple(rev[j:]+rev[:j]) for j in range(len(rev)))==uses[1][1]
 def point(i,t):
  r=bindings.get(i)
  if r is None:return [R(F(x)) for x in source['vertices'][i]]
  ratio=R(u) if r['variable']=='u' else t
  return [R(F(r['x_coefficient']))*ratio,R(F(r['y_coefficient']))*ratio,R(F(r['z_exact']))]
 def coordinates(interval):return [point(i,R(*map(F,interval))) for i in range(len(source['vertices']))]
 hull=[];unknown=[];counts=Counter();bound_count=0;flat_min=None;w_min=None
 with gzip.open(W/'flatness-bounds.jsonl.gz','rt') as stream:
  def check(rank,ps,domain_id):
   nonlocal bound_count,flat_min,w_min
   row=json.loads(next(stream));face=registry[keys[rank]][0][1];assert row['rank']==rank and row['face']==list(face) and row['domain']==domain_id
   origin=[R(F(x)) for x in source['vertices'][face[0]]];bounds=calculate([g.vsub(ps[i],origin) for i in face]);assert set(bounds)==set(row['bounds'])
   for key,x in bounds.items():
    lo,hi=map(F,row['bounds'][key]);assert lo<=x.a<=x.b<=hi,(domain_id,rank,key);bound_count+=1
   original=row['bounds'];positive=(len(face)==3 or (F(original['W'][0])>=ROOT and F(original['magS'][0])>ROOT)) and F(original['flatness'][0])>=LIMIT
   assert row['status']==('positive' if positive else 'unknown')
   if positive:assert bounds['flatness'].a>=LIMIT and (len(face)==3 or (bounds['W'].a>=ROOT and bounds['magS'].a>ROOT))
   flat_min=bounds['flatness'].a if flat_min is None else min(flat_min,bounds['flatness'].a)
   if 'W' in bounds:w_min=bounds['W'].a if w_min is None else min(w_min,bounds['W'].a)
   return row,bounds
  ps=coordinates(domain)
  for rank in range(len(keys)):
   row,bounds=check(rank,ps,'envelope');hull.append(bounds)
   if row['status']=='unknown':unknown.append(rank)
  for box in boxes:
   if not unknown:break
   ps=coordinates([box['lower'],box['upper']])
   for rank in unknown:
    row,_=check(rank,ps,box['parent_leaf']);counts[row['status']]+=1
  assert next(stream,None) is None
 assert len(unknown)==report['envelope_unknown'] and len(keys)-len(unknown)==report['envelope_positive'] and dict(counts)==report['local_counts']
 volumes={};model=Path('work/bionic-volume-representation-20261013/models.jsonl.gz');assert sha(model)==report['inherited_models_sha256']=='780a6bece9fa9aafd010a7ff91fc78d571a1e4c3e1102b0ebef1f04cd191ea9a'

 for name in ('readback.json','independent-readback.json'):
  inherited=json.loads((model.parent/name).read_text());assert inherited['domain_v']==domain and inherited['models_sha256']==sha(model)
 assert inherited['all_coefficients_and_bounds_exact'] and inherited['cells_verified']==6144
 with gzip.open(model,'rt') as stream:
  for line in stream:
   row=json.loads(line)
   if row['kind']=='cell':volumes[row['cell']]=row['fan_signed_volume']['bounds']
 internal=defaultdict(list)
 for rank,key in enumerate(keys):
  if len(registry[key])==2:
   for cid,_ in registry[key]:internal[cid].append(rank)
 guards=json.loads((W/'guards.json').read_text());assert len(guards)==6144
 assert sum(row['determinant_guard_inactive'] for row in guards)==report['determinant_guards_inactive'] and sum(row['volume_guard_inactive'] for row in guards)==report['volume_guards_inactive']
 for cid,row in enumerate(guards):
  ranks=internal[cid];lo=sum(hull[r]['magS'].a for r in ranks);hi=sum(hull[r]['magS'].b for r in ranks);stored=list(map(F,row['E']));assert row['cell']==cid and row['internal_faces']==len(ranks) and stored[0]<=lo<=hi<=stored[1]
  triple=[3*F(x) for x in volumes[cid]];assert row['triple_volume']==list(map(str,triple)) and row['determinant_guard_inactive']==(bool(ranks) and stored[0]>=ROOT) and row['volume_guard_inactive']==(triple[0]>SMALL)
  if row['determinant_guard_inactive']:assert ranks and lo>=ROOT
 assert report['ROOTVSMALL']==str(ROOT) and report['VSMALL']==str(SMALL) and report['flatness_threshold']==str(LIMIT)
 out=dict(source_sha256=sha(Path(__file__)),primary_readback_sha256=sha(W/'readback.json'),faces_reconstructed=len(keys),face_records_verified=len(keys)+153*len(unknown),individual_bounds_verified=bound_count,guard_cells_verified=len(guards),independent_bounds_contained=True,analytic_references=references,manifests_verified=len(dep['manifests']),payload_entries_verified=entries,envelope_positive=len(keys)-len(unknown),envelope_unknown=len(unknown),local_counts=dict(counts),minimum_flatness_lower=str(flat_min),minimum_face_centre_weight_lower=str(w_min),native_execution_roundoff_bounded=False,native_admission=False,elapsed_s=time.monotonic()-start)
 (W/'independent-readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out),flush=True)
if __name__=='__main__':main()
