"""Independent sparse fan/permutation models and 192-bit Casteljau bounds."""
import csv,hashlib,importlib.util,json,sys,time
from pathlib import Path
from fractions import Fraction as F
from itertools import combinations
from collections import defaultdict,Counter
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(name,path,digest):
 p=Path(path);assert sha(p)==digest
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
v=load('verify_models','work/bionic-gram-interval-bounds-20261013/verify_models.py','1a2c0167b9d76d6f515d20bca1d2f244d172aebdbf49887a8c36f603b891d97c')
g=load('verify_refinement','work/bionic-gram-interval-bounds-20261013/verify_refinement.py','bd10cdff91eb03003960c7bb48c68952844a4f81f002c08e1a3de27e3fce5505')
def main():
 w=Path(__file__).parent;started=time.monotonic();report=json.loads((w/'readback.json').read_text())
 for filename,key in [('models.jsonl','models_sha256'),('bounds.jsonl','bounds_sha256'),('boxes.json','boxes_sha256'),('order.json','order_sha256')]:assert sha(w/filename)==report[key]
 dep=json.loads((w/'dependencies.json').read_text())
 import subprocess
 prefix='twins/bionic-turbo-f1/evidence/airflow-remaining-angle-bounds-20261013/'
 expected=json.loads(subprocess.check_output(['git','show',dep['anchor_commit']+':'+prefix+'dependencies.json']))
 expected['work/bionic-airflow-delivery-20261013-remaining-angle-bounds/file-manifest.json']=json.loads(subprocess.check_output(['git','show',dep['anchor_commit']+':'+prefix+'archive-receipt.json']))['manifest_sha256'];assert expected==dep['manifests']
 for name,digest in expected.items():
  path=Path(name);assert sha(path)==digest
  for r in json.loads(path.read_text())['files']:assert sha(Path('work')/r['path'])==r['sha256']
 old=json.loads(Path('work/bionic-feasibility-bounds-20261013/certificate.json').read_text());u,end=map(F,old['domain'])
 parent=[json.loads(x) for x in Path('work/bionic-remaining-angle-bounds-20261013/records.jsonl').read_text().splitlines()];boxes=json.loads((w/'boxes.json').read_text());assert boxes==[dict(parent_leaf=r['parent_leaf'],lower=r['lower'],upper=r['upper']) for r in parent if r['status']!='excluded']
 byid={r['parent_leaf']:r for r in boxes};hull=((F(boxes[0]['lower'])-u)/(end-u),(F(boxes[-1]['upper'])-u)/(end-u))
 s=json.loads(Path('work/bionic-buffered-transition-20261013/construction.json').read_text());sy=json.loads(Path('work/bionic-joint-constraints-20261013/system.json').read_text());bindings={r['point']:r for r in sy['coordinate_bindings']};points=[]
 for i,q in enumerate(s['vertices']):
  r=bindings.get(i)
  if r and r['variable']=='v':points.append([{0:F(r[k])*u,1:F(r[k])*(end-u)} for k in ('x_coefficient','y_coefficient')]+[{0:F(r['z_exact'])}])
  else:points.append([{0:F(x)} for x in q])
 templates=((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7));faces=[];reg=defaultdict(list)
 for c,b in enumerate(s['blocks']):
  fs=[]
  for t in templates:
   f=[]
   for j in t:
    if not f or f[-1]!=b[j]:f.append(b[j])
   if f[-1]==f[0]:f.pop()
   if len(f)>2:fs.append(f);reg[tuple(sorted(f))].append((c,f))
  faces.append(fs)
 def cycle(f):return min(tuple(f[i:]+f[:i]) for i in range(len(f)))
 for hits in reg.values():
  assert len(hits) in (1,2)
  if len(hits)==2:assert cycle(hits[0][1])==cycle(hits[1][1][::-1])
 moving={i for i,r in bindings.items() if r['variable']=='v'};changing={c for c,b in enumerate(s['blocks']) if set(b)&moving};assert len(changing)==3840
 skip={r['cell'] for r in old['selected'][2:]};data=list(csv.DictReader(Path('work/bionic-neighbour-constraints-20261013/cells.csv').open()));ordered=sorted((r for r in data if int(r['cell']) in changing-skip),key=lambda r:(F(r['determinant']),int(r['cell'])));assert ordered==json.loads((w/'order.json').read_text())
 count=0;statuscounts=Counter();excluded=set();verifiedfaces=0
 for rank,(modeltext,boundtext) in enumerate(zip((w/'models.jsonl').open(),(w/'bounds.jsonl').open(),strict=True)):
  m=json.loads(modeltext);record=json.loads(boundtext);c=m['cell'];assert c==int(ordered[rank]['cell'])==record['cell'] and rank==record['rank']
  fs=[f for f in faces[c] if len(reg[tuple(sorted(f))])==2];assert {cycle(f) for f in fs}=={cycle(f) for f in m['faces']}
  areas=[]
  for f in m['faces']:
   ps=[points[i] for i in f];seed=[v.times(v.total(q[k] for q in ps),F(1,len(ps))) for k in range(3)];crosses=[]
   for j,q in enumerate(ps):
    nxt=ps[(j+1)%len(ps)];crosses.append(v.vector([v.difference(nxt[k],q[k]) for k in range(3)],[v.difference(seed[k],q[k]) for k in range(3)]))
   areas.append([v.times(v.total(x[k] for x in crosses),F(1,2)) for k in range(3)])
  assert areas==[[v.from_strings(x) for x in S] for S in m['area_components']]
  norms=[v.scalar(S,S) for S in areas];minors=[v.scalar(areas[i],v.vector(areas[j],areas[k])) for i,j,k in combinations(range(len(areas)),3)]
  matrix=[[v.total(v.prod(S[i],S[j]) for S in areas) for j in range(3)] for i in range(3)];det=v.det(matrix)
  assert det==v.from_strings(m['gram_determinant'])==v.total(v.prod(x,x) for x in minors)
  assert norms==[v.from_strings(x) for x in m['norm_squared']];assert minors==[v.from_strings(x) for x in m['minors']];verifiedfaces+=len(areas)
  def check(bound,a,b):
   dl,dh=g.enclosure(det,a,b);low=F(0);high=F(0)
   for polynomial in minors:
    l,h=g.enclosure(polynomial,a,b);low+=0 if l<=0<=h else min(l*l,h*h);high+=max(l*l,h*h)
   dl=max(F(0),dl,low);dh=min(dh,high);assert 0<=dl<=dh
   el=F(0);eh=F(0)
   for polynomial in norms:
    l,h=g.enclosure(polynomial,a,b);assert h>=0;el+=g.sqrt_limits(max(F(0),l))[0];eh+=g.sqrt_limits(h)[1]
   assert eh>0
   lower=125*len(areas)**6*dl/eh**6-1;upper=None if el==0 else 125*len(areas)**6*dh/el**6-1
   assert lower>=F(bound['residual'][0])
   if bound['residual'][1] is not None:assert upper is not None and upper<=F(bound['residual'][1])
   if bound['status']=='selected_pass':assert lower>=0
   if bound['status']=='excluded':assert upper is not None and upper<0
   statuscounts[bound['status']]+=1
  check(record['hull'],*hull)
  if record['hull']['status']=='excluded':excluded.update(byid)
  expectedids=[] if record['hull']['status']!='unknown' else [i for i in byid if i not in excluded]
  assert [r['parent_leaf'] for r in record['local']]==expectedids
  for r in record['local']:
   box=byid[r['parent_leaf']];check(r,(F(box['lower'])-u)/(end-u),(F(box['upper'])-u)/(end-u))
   if r['status']=='excluded':excluded.add(r['parent_leaf'])
  count+=1
  if rank%100==0:print(json.dumps(dict(verified=count,elapsed_s=time.monotonic()-started)),flush=True)
 assert count==report['evaluated_models'];assert excluded=={int(i) for i in report['exclusions']}
 out=dict(source_sha256=sha(Path(__file__)),models_sha256=sha(w/'models.jsonl'),bounds_sha256=sha(w/'bounds.jsonl'),models_verified=count,internal_face_polynomials_verified=verifiedfaces,bound_statuses_verified=dict(statuscounts),excluded_boxes=len(excluded),all_recorded_bounds_verified=True,remaining_boxes=153-len(excluded),solution_accepted=False,native_executed=False,elapsed_s=time.monotonic()-started)
 (w/'independent-readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
if __name__=='__main__':main()
