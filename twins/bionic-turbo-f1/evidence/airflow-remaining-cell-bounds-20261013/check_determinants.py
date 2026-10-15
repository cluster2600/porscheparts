"""Necessary internal-face determinant bounds; archived intervals only."""
import csv,hashlib,importlib.util,json,sys,time
from pathlib import Path
from fractions import Fraction as F
from itertools import combinations
from collections import defaultdict,Counter
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(name,path,digest):
 p=Path(path);assert sha(p)==digest
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
# Hashes filled before execution.
p=load('polynomials','work/bionic-gram-interval-bounds-20261013/polynomials.py','f4122e6b4051c7e6b3aeaa464b04f8fdbc9f395a9f8a42bf831265f6e0ea00e0')
g=load('gram_bounds','work/bionic-gram-interval-bounds-20261013/refine_bounds.py','3315632142a138be4c7685efe13490b8c6fa1e1f1dcf70afe73ca07964521160')
def main():
 w=Path(__file__).parent;started=time.monotonic()
 anchor='b7c9e66f5cb44f3554dedc8eddb9703504a84135'
 import subprocess
 base='twins/bionic-turbo-f1/evidence/airflow-remaining-angle-bounds-20261013/'
 expected=json.loads(subprocess.check_output(['git','show',anchor+':'+base+'dependencies.json']))
 receipt=json.loads(subprocess.check_output(['git','show',anchor+':'+base+'archive-receipt.json']))
 expected['work/bionic-airflow-delivery-20261013-remaining-angle-bounds/file-manifest.json']=receipt['manifest_sha256']
 count=0
 for name,digest in expected.items():
  path=Path(name);assert sha(path)==digest
  for row in json.loads(path.read_text())['files']:assert sha(Path('work')/row['path'])==row['sha256'];count+=1
 (w/'dependencies.json').write_text(json.dumps(dict(anchor_commit=anchor,manifests=expected,payload_entries_verified=count),indent=2)+'\n')
 src=Path('work/bionic-remaining-angle-bounds-20261013/records.jsonl');rows=[json.loads(x) for x in src.read_text().splitlines()];boxes=[r for r in rows if r['status']!='excluded'];assert len(boxes)==153
 for a,b in zip(boxes,boxes[1:]):assert a['upper']==b['lower']
 s=json.loads(Path('work/bionic-buffered-transition-20261013/construction.json').read_text());sy=json.loads(Path('work/bionic-joint-constraints-20261013/system.json').read_text());old=json.loads(Path('work/bionic-feasibility-bounds-20261013/certificate.json').read_text())
 u,end=map(F,old['domain']);bindings={r['point']:r for r in sy['coordinate_bindings']};moving={i for i,r in bindings.items() if r['variable']=='v'};points=[]
 for i,q in enumerate(s['vertices']):
  r=bindings.get(i)
  if r and r['variable']=='v':points.append([(F(r[k])*u,F(r[k])*(end-u)) for k in ('x_coefficient','y_coefficient')]+[(F(r['z_exact']),)])
  else:points.append([(F(x),) for x in q])
 fs=[];reg=defaultdict(list)
 for c,block in enumerate(s['blocks']):
  n=4 if s['stages'][c]=='buffer' else 3;lo,hi=block[:n],block[4:4+n];faces=[lo[::-1],hi]+[[lo[i],lo[(i+1)%n],hi[(i+1)%n],hi[i]] for i in range(n)];fs.append(faces)
  for f in faces:reg[tuple(sorted(f))].append(c)
 assert all(len(v) in (1,2) for v in reg.values())
 changing={c for c,b in enumerate(s['blocks']) if set(b)&moving};assert len(changing)==3840
 skip={x['cell'] for x in old['selected'][2:]};csvrows=list(csv.DictReader(Path('work/bionic-neighbour-constraints-20261013/cells.csv').open()))
 ordered=sorted((r for r in csvrows if int(r['cell']) in changing-skip),key=lambda r:(F(r['determinant']),int(r['cell'])));assert len(ordered)==3836
 (w/'order.json').write_text(json.dumps(ordered,indent=2)+'\n');(w/'boxes.json').write_text(json.dumps([dict(parent_leaf=r['parent_leaf'],lower=r['lower'],upper=r['upper']) for r in boxes],indent=2)+'\n')
 def interval(r):return (F(r['lower'])-u)/(end-u),(F(r['upper'])-u)/(end-u)
 ha=(F(boxes[0]['lower'])-u)/(end-u);hb=(F(boxes[-1]['upper'])-u)/(end-u)
 excluded={};counts=Counter();modelcount=0
 with (w/'models.jsonl').open('x') as models,(w/'bounds.jsonl').open('x') as bounds:
  for rank,row in enumerate(ordered):
   c=int(row['cell']);faces=[f for f in fs[c] if len(reg[tuple(sorted(f))])==2];assert len(faces)==int(row['internal_faces'])
   areas=[p.area([points[i] for i in f]) for f in faces]
   assert all(a==p.fan_area([points[i] for i in f]) for a,f in zip(areas,faces))
   minors=[p.dot(areas[i],p.cross(areas[j],areas[k])) for i,j,k in combinations(range(len(areas)),3)]
   det=p.summ(p.mul(x,x) for x in minors);matrix=[[p.summ(p.mul(a[i],a[j]) for a in areas) for j in range(3)] for i in range(3)];assert p.determinant(matrix)==det
   m=dict(cell=c,faces=faces,area_components=[[p.serialize(q) for q in a] for a in areas],norm_squared=[p.serialize(p.dot(a,a)) for a in areas],minors=[p.serialize(q) for q in minors],gram_determinant=p.serialize(det))
   models.write(json.dumps(m)+'\n');models.flush();modelcount+=1
   whole=g.gram_bounds(m,ha,hb);local=[];counts['hull_'+whole['status']]+=1
   if whole['status']=='excluded':
    for r in boxes:
     if r['parent_leaf'] not in excluded:excluded[r['parent_leaf']]=dict(cell=c,rank=rank,scope='hull',bound=whole)
   elif whole['status']!='selected_pass':
    for r in boxes:
     i=r['parent_leaf']
     if i in excluded:continue
     val=g.gram_bounds(m,*interval(r));local.append(dict(parent_leaf=i,**val));counts['local_'+val['status']]+=1
     if val['status']=='excluded':excluded[i]=dict(cell=c,rank=rank,scope='leaf',bound=val)
   bounds.write(json.dumps(dict(rank=rank,cell=c,hull=whole,local=local))+'\n');bounds.flush()
   if rank%25==0:print(json.dumps(dict(done=rank+1,excluded=len(excluded),counts=dict(counts),elapsed_s=time.monotonic()-started)),flush=True)
   if len(excluded)==153:break
 result=dict(source_sha256=sha(Path(__file__)),preflight_sha256=sha(w/'preflight.md'),parent_records_sha256=sha(src),models_sha256=sha(w/'models.jsonl'),bounds_sha256=sha(w/'bounds.jsonl'),order_sha256=sha(w/'order.json'),boxes_sha256=sha(w/'boxes.json'),scheduled=3836,evaluated_models=modelcount,counts=dict(counts),exclusions=excluded,remaining_boxes=153-len(excluded),elapsed_s=time.monotonic()-started,solution_accepted=False,native_executed=False,new_ratio_point=False)
 (w/'readback.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
