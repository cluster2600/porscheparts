"""Independent template geometry and Fraction-192 replay of every recorded plane/volume bound."""
import csv,hashlib,importlib.util,json,time
from pathlib import Path
from fractions import Fraction as F
from collections import Counter
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=Path('work/bionic-centre-interval-bounds-20261013/verify_centres_v2.py');assert sha(p)=='a259f163405dec0cfb4f1b707698249ea9069de9b02a9db1835fb172f1a0b992'
spec=importlib.util.spec_from_file_location('independent_centres',p);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h);g=h.g
from dyadic192 import R
assert sha(Path(__file__).parent/'dyadic192.py')=='f216b134a93a893b0c04bbe47671eb5ba497e4836e0e2a346220f0b14d83ac14'
g.R=R

def main():
 w=Path(__file__).parent;start=time.monotonic();r=json.loads((w/'planes-readback.json').read_text())
 for name,key in [('check_planes.py','source_sha256'),('planes-bounds.jsonl','bounds_sha256'),('planes-order.json','order_sha256'),('boxes.json','boxes_sha256'),('planes-preflight.md','preflight_sha256')]:assert sha(w/name)==r[key]
 for name,digest in json.loads((w/'dependencies.json').read_text())['manifests'].items():
  path=Path(name);assert sha(path)==digest
  for row in json.loads(path.read_text())['files']:assert sha(Path('work')/row['path'])==row['sha256']
 boxes=json.loads((w/'boxes.json').read_text());byid={x['parent_leaf']:x for x in boxes};assert len(boxes)==153
 sy=json.loads(Path('work/bionic-joint-constraints-20261013/system.json').read_text());s=json.loads(Path('work/bionic-buffered-transition-20261013/construction.json').read_text());bindings={x['point']:x for x in sy['coordinate_bindings']};u=F(sy['archived_regression_point']['u'])
 moving={i for i,x in bindings.items() if x['variable']=='v'};changing={c for c,b in enumerate(s['blocks']) if set(b)&moving};assert len(changing)==3840
 csvrows=list(csv.DictReader(Path('work/bionic-neighbour-constraints-20261013/cells.csv').open()));ordered=sorted((x for x in csvrows if int(x['cell']) in changing),key=lambda x:(-F(x['plane_score']),int(x['cell'])));assert ordered==json.loads((w/'planes-order.json').read_text())
 templates=((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))
 def faces(c):
  b=s['blocks'][c];out=[]
  for t in templates:
   f=[]
   for j in t:
    if not f or f[-1]!=b[j]:f.append(b[j])
   if f[-1]==f[0]:f.pop()
   if len(f)>2:out.append(f)
  return out
 counts=Counter();excluded=set();volumes=0;pairs=0
 def check(c,record,l,r):
  nonlocal pairs,volumes
  vv=g.R(F(l),F(r));anchor=[g.R(F(x)) for x in s['vertices'][s['blocks'][c][0]]]
  def point(i):
   binding=bindings.get(i)
   if not binding:return [g.R(F(x)) for x in s['vertices'][i]]
   value=g.R(u) if binding['variable']=='u' else vv
   return [g.R(F(binding['x_coefficient']))*value,g.R(F(binding['y_coefficient']))*value,g.R(F(binding['z_exact']))]
  geo=[h.polygon([g.vsub(point(i),anchor) for i in f]) for f in faces(c)];seed=g.average([cf for cf,S in geo]);V=sum(g.inner(S,g.vsub(cf,seed))/3 for cf,S in geo)
  h.contained(V,record['volume']);volumes+=1
  allpos=V.a>0;anyref=V.b<=0
  expected=[(i,j) for i in range(len(geo)) for j in range(len(geo)) if i!=j];assert [(x['i'],x['j']) for x in record['pairs']]==expected
  for item in record['pairs']:
   i,j=item['i'],item['j'];cf,S=geo[i];cg=geo[j][0];d=g.vsub(cg,cf);L=g.inner(S,d);den=g.inner(S,S)*g.inner(d,d);h.contained(L,item['L']);assert den.a>0
   residual=L.square()/den-g.R(F(1,10**12));h.contained(residual,item['residual']);pairs+=1
   if item['status']=='positive':assert L.b<0 and residual.a>=0
   if item['status']=='excluded':assert L.a>=0 or residual.b<0
   allpos &= L.b<0 and residual.a>=0;anyref |= L.a>=0 or residual.b<0;counts['pair_'+item['status']]+=1
  if record['status']=='positive':assert allpos
  if record['status']=='excluded':assert anyref
  counts['cell_'+record['status']]+=1
 done=0
 for rank,line in enumerate((w/'planes-bounds.jsonl').open()):
  record=json.loads(line);c=record['cell'];assert record['rank']==rank and c==int(ordered[rank]['cell']);check(c,record['hull'],boxes[0]['lower'],boxes[-1]['upper'])
  if record['hull']['status']=='excluded':excluded.update(byid)
  ids=[] if record['hull']['status']!='unknown' else [i for i in byid if i not in excluded];assert [x['parent_leaf'] for x in record['local']]==ids
  for item in record['local']:
   box=byid[item['parent_leaf']];check(c,item,box['lower'],box['upper'])
   if item['status']=='excluded':excluded.add(item['parent_leaf'])
  done+=1
  if rank%200==0:print(json.dumps(dict(verified=done,pairs=pairs,elapsed_s=time.monotonic()-start)),flush=True)
 assert done==r['evaluated_cells'];assert excluded==set(map(int,r['exclusions']))
 out=dict(source_sha256=sha(Path(__file__)),representation_readback_sha256=sha(w/'representation-readback.json'),bounds_sha256=sha(w/'planes-bounds.jsonl'),cells_verified=done,ordered_plane_bounds_verified=pairs,signed_volume_bounds_verified=volumes,counts=dict(counts),new_excluded_boxes=len(excluded),all_recorded_bounds_verified=True,elapsed_s=time.monotonic()-start,solution_accepted=False,native_executed=False)
 (w/'planes-independent-readback-v2.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
if __name__=='__main__':main()
