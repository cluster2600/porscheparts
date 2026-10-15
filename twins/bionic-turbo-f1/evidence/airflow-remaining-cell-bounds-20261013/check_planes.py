"""All variable ordered plane pairs and signed volumes, on archived intervals."""
import csv,hashlib,importlib.util,json,time
from pathlib import Path
from fractions import Fraction as F
from collections import Counter
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=Path('work/bionic-centre-interval-bounds-20261013/centred.py');assert sha(p)=='4f366b9571c931fa8d4bf19e90e94c5bd77d0093c193a1e0de9caf1f3590361b'
spec=importlib.util.spec_from_file_location('pinned_centres',p);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h);b=h.b;I=h.I

def main():
 w=Path(__file__).parent;start=time.monotonic();det=json.loads((w/'readback.json').read_text());assert not det['exclusions'] and det['evaluated_models']==3836
 for name,digest in json.loads((w/'dependencies.json').read_text())['manifests'].items():
  path=Path(name);assert sha(path)==digest
  for r in json.loads(path.read_text())['files']:assert sha(Path('work')/r['path'])==r['sha256']
 boxes=json.loads((w/'boxes.json').read_text());assert len(boxes)==153
 old=json.loads(Path('work/bionic-feasibility-bounds-20261013/certificate.json').read_text());u,end=map(F,old['domain'])
 s=json.loads(Path('work/bionic-buffered-transition-20261013/construction.json').read_text());sy=json.loads(Path('work/bionic-joint-constraints-20261013/system.json').read_text());bindings={r['point']:r for r in sy['coordinate_bindings']};moving={i for i,r in bindings.items() if r['variable']=='v'}
 changing={c for c,bl in enumerate(s['blocks']) if set(bl)&moving};assert len(changing)==3840
 csvrows=list(csv.DictReader(Path('work/bionic-neighbour-constraints-20261013/cells.csv').open()));ordered=sorted((r for r in csvrows if int(r['cell']) in changing),key=lambda r:(-F(r['plane_score']),int(r['cell'])))
 (w/'planes-order.json').write_text(json.dumps(ordered,indent=2)+'\n')
 faces=[]
 for c,bl in enumerate(s['blocks']):
  n=4 if s['stages'][c]=='buffer' else 3;lo,hi=bl[:n],bl[4:4+n];faces.append([lo[::-1],hi]+[[lo[i],lo[(i+1)%n],hi[(i+1)%n],hi[i]] for i in range(n)])
 assert sum(len(faces[c])*(len(faces[c])-1) for c in changing)==92160
 def point(i,v):
  r=bindings.get(i)
  if not r:return [I(F(x)) for x in s['vertices'][i]]
  t=I(u) if r['variable']=='u' else v
  return [I(F(r['x_coefficient']))*t,I(F(r['y_coefficient']))*t,I(F(r['z_exact']))]
 def check(c,l,r):
  v=I(I(F(l)).lo,I(F(r)).hi,True);anchor=[I(F(x)) for x in s['vertices'][s['blocks'][c][0]]]
  try:geo=[h.face([b.minus(point(i,v),anchor) for i in f]) for f in faces[c]]
  except ZeroDivisionError:return dict(status='unknown',singular=True)
  seed=b.mean([cf for cf,S in geo]);V=sum(b.dot(S,b.minus(cf,seed))/3 for cf,S in geo)
  status='excluded' if V.hi<=0 else ('positive' if V.lo>0 else 'unknown');pairs=[]
  for i,(cf,S) in enumerate(geo):
   for j,(cg,_) in enumerate(geo):
    if i==j:continue
    delta=b.minus(cg,cf);L=b.dot(S,delta);den=b.dot(S,S)*b.dot(delta,delta)
    if den.lo<=0:val=dict(i=i,j=j,status='unknown',singular=True,L=L.pair())
    else:
     res=L.sq()/den-I(F(1,10**12));st='excluded' if L.lo>=0 or res.hi<0 else ('positive' if L.hi<0 and res.lo>=0 else 'unknown')
     val=dict(i=i,j=j,status=st,L=L.pair(),residual=res.pair())
    pairs.append(val)
    if val['status']=='excluded':status='excluded'
    elif val['status']=='unknown' and status!='excluded':status='unknown'
  return dict(status=status,volume=V.pair(),pairs=pairs)
 counts=Counter();excluded={};done=0
 with (w/'planes-bounds.jsonl').open('x') as stream:
  for rank,row in enumerate(ordered):
   c=int(row['cell']);whole=check(c,boxes[0]['lower'],boxes[-1]['upper']);counts['hull_'+whole['status']]+=1;local=[]
   if whole['status']=='excluded':
    for r in boxes:
     if r['parent_leaf'] not in excluded:excluded[r['parent_leaf']]=dict(cell=c,scope='hull',rank=rank)
   elif whole['status']!='positive':
    for r in boxes:
     i=r['parent_leaf']
     if i in excluded:continue
     val=check(c,r['lower'],r['upper']);counts['local_'+val['status']]+=1;local.append(dict(parent_leaf=i,**val))
     if val['status']=='excluded':excluded[i]=dict(cell=c,scope='leaf',rank=rank)
   stream.write(json.dumps(dict(rank=rank,cell=c,hull=whole,local=local))+'\n');stream.flush();done+=1
   if rank%100==0:print(json.dumps(dict(done=done,excluded=len(excluded),counts=dict(counts),elapsed_s=time.monotonic()-start)),flush=True)
   if len(excluded)==153:break
 out=dict(source_sha256=sha(Path(__file__)),preflight_sha256=sha(w/'planes-preflight.md'),determinant_readback_sha256=sha(w/'readback.json'),bounds_sha256=sha(w/'planes-bounds.jsonl'),order_sha256=sha(w/'planes-order.json'),boxes_sha256=sha(w/'boxes.json'),scheduled_cells=3840,scheduled_ordered_pairs=92160,evaluated_cells=done,counts=dict(counts),exclusions=excluded,elapsed_s=time.monotonic()-start,solution_accepted=False,native_executed=False)
 (w/'planes-readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
if __name__=='__main__':main()
