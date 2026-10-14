"""Independent complete angular bounds on the 153 unchanged surviving boxes."""
import csv,gzip,hashlib,importlib.util,json,subprocess,time
from pathlib import Path
from fractions import Fraction as F
from collections import Counter,defaultdict
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load_module(name,path,digest):
 assert sha(path)==digest
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
helper=Path('work/bionic-centre-interval-bounds-20261013/verify_centres_v2.py')
h=load_module('pinned_independent_centres',helper,'a259f163405dec0cfb4f1b707698249ea9069de9b02a9db1835fb172f1a0b992');g=h.g
kernel=Path('work/bionic-remaining-cell-bounds-20261013/dyadic192.py')
k=load_module('pinned_integer_representation',kernel,'f216b134a93a893b0c04bbe47671eb5ba497e4836e0e2a346220f0b14d83ac14');g.R=k.R

def main():
 w=Path(__file__).parent;start=time.monotonic();base='522b972cc9bf6fd3d3e130303e795790b947ffe7'
 ep='twins/bionic-turbo-f1/evidence/airflow-remaining-cell-bounds-20261013/'
 dep=json.loads(subprocess.check_output(['git','show',base+':'+ep+'dependencies.json']))['manifests']
 receipt=json.loads(subprocess.check_output(['git','show',base+':'+ep+'archive-receipt.json']))
 dep['work/bionic-airflow-delivery-20261013-remaining-cell-bounds/file-manifest.json']=receipt['manifest_sha256']
 entries=0
 for name,digest in dep.items():
  path=Path(name);assert sha(path)==digest
  for row in json.loads(path.read_text())['files']:
   payload=Path('work')/row['path'];assert payload.stat().st_size==row['bytes'] if 'bytes' in row else True
   assert sha(payload)==row['sha256'];entries+=1
 (w/'dependencies.json').write_text(json.dumps(dict(anchor_commit=base,manifests=dep,payload_entries_verified=entries),indent=2)+'\n')
 parent=Path('work/bionic-remaining-angle-bounds-20261013');report=json.loads((parent/'readback.json').read_text())
 assert sha(parent/'records.jsonl')==report['records_sha256'] and sha(parent/'order.json')==report['order_sha256']
 records=[json.loads(x) for x in (parent/'records.jsonl').read_text().splitlines()];rows=[r for r in records if r['status']!='excluded'];assert len(rows)==153
 boxes=json.loads(Path('work/bionic-remaining-cell-bounds-20261013/boxes.json').read_text());assert boxes==[{key:r[key] for key in ('parent_leaf','lower','upper')} for r in rows]
 old=json.loads(Path('work/bionic-feasibility-bounds-20261013/certificate.json').read_text());u,end=map(F,old['domain']);kap=g.R(*map(F,old['kappa']))
 s=json.loads(Path('work/bionic-buffered-transition-20261013/construction.json').read_text());sy=json.loads(Path('work/bionic-joint-constraints-20261013/system.json').read_text());bindings={r['point']:r for r in sy['coordinate_bindings']}
 templates=((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7));fs=[];reg=defaultdict(list)
 for c,block in enumerate(s['blocks']):
  rr=[]
  for template in templates:
   face=[]
   for j in template:
    if not face or face[-1]!=block[j]:face.append(block[j])
   if face[-1]==face[0]:face.pop()
   if len(face)>2:rr.append(face);reg[tuple(sorted(face))].append((c,face))
  fs.append(rr)
 canonical=lambda f:min(tuple(f[i:]+f[:i]) for i in range(len(f)))
 for occurrences in reg.values():
  assert len(occurrences) in (1,2)
  if len(occurrences)==2:assert canonical(occurrences[0][1])==canonical(occurrences[1][1][::-1])
 moving={i for i,r in bindings.items() if r['variable']=='v'};changing=[bool(set(b)&moving) for b in s['blocks']]
 pairs={(a,c):f for rr in reg.values() if len(rr)==2 for (a,f),(c,other) in [rr] if changing[a] or changing[c]};assert len(pairs)==9472
 skip={(r['owner'],r['neighbour']) for r in old['selected'][:2]}
 source=list(csv.DictReader(Path('work/bionic-neighbour-constraints-20261013/faces.csv').open()))
 ordered=sorted((r for r in source if (int(r['owner']),int(r['neighbour'])) in pairs and (int(r['owner']),int(r['neighbour'])) not in skip),key=lambda r:(-F(r['angle_deg']),int(r['owner']),int(r['neighbour'])))
 order=json.loads((parent/'order.json').read_text());assert len(order)==len(ordered)==9470
 indices=[]
 for src,r in zip(ordered,order):
  a,c=int(src['owner']),int(src['neighbour']);assert (r['owner'],r['neighbour'])==(a,c) and r['family']==src['family'] and r['archived_angle_deg']==src['angle_deg']
  assert canonical(r['face'])==canonical(pairs[a,c]);indices.append(next(i for i,f in enumerate(fs[a]) if canonical(f)==canonical(r['face'])))
 (w/'boxes.json').write_text(json.dumps(boxes,indent=2)+'\n');(w/'order.json').write_bytes((parent/'order.json').read_bytes())
 exact={i:[g.R(F(x)) for x in p] for i,p in enumerate(s['vertices']) if i not in bindings}
 coeff={i:(r['variable'],g.R(F(r['x_coefficient'])),g.R(F(r['y_coefficient'])),g.R(F(r['z_exact']))) for i,r in bindings.items()}
 anchors=[[g.R(F(x)) for x in s['vertices'][b[0]]] for b in s['blocks']];uu=g.R(u)
 total=Counter();results=[];all_old_positive=0
 with gzip.open(w/'angular-bounds.jsonl.gz','xt',compresslevel=3) as out:
  for row in rows:
   v=g.R(F(row['lower']),F(row['upper']));points=dict(exact);cache={};counts=Counter();minimum_volume=None
   for i,(var,x,y,z) in coeff.items():
    t=uu if var=='u' else v;points[i]=[x*t,y*t,z]
   def cell(c):
    nonlocal minimum_volume
    if c not in cache:
     anchor=anchors[c];C,V,geometry=h.moments([[g.vsub(points[i],anchor) for i in f] for f in fs[c]])
     assert V.lo>0;minimum_volume=V.lo if minimum_volume is None else min(minimum_volume,V.lo)
     cache[c]=(g.vadd(C,anchor),geometry)
    return cache[c]
   for rank,r in enumerate(order):
    a,c=r['owner'],r['neighbour'];Ca,geo=cell(a);Cc,_=cell(c);S=geo[indices[rank]][1]
    delta=g.vsub(Cc,Ca);D=g.inner(delta,S);Q=sum(x.square() for x in delta)*sum(x.square() for x in S);assert Q.lo>0
    res=D.square()/Q-kap
    status='positive' if D.lo>0 and res.lo>=0 else 'excluded' if D.hi<=0 or res.hi<0 else 'unknown'
    counts[status]+=1
    out.write(json.dumps([row['parent_leaf'],rank,D.lo,D.hi,Q.lo,Q.hi,res.lo,res.hi],separators=(',',':'))+'\n')
   assert sum(counts.values())==9470
   old_positive=row['counts'].get('positive',0)==9470
   if old_positive:assert counts['positive']==9470;all_old_positive+=1
   result=dict(parent_leaf=row['parent_leaf'],lower=row['lower'],upper=row['upper'],counts=dict(counts),primary_counts=row['counts'],primary_all_positive=old_positive,all_positive=counts['positive']==9470,cell_moment_evaluations=len(cache),minimum_volume_lower_integer=minimum_volume)
   results.append(result);total.update(counts)
   print(json.dumps(dict(boxes_done=len(results),counts=dict(total),elapsed_s=time.monotonic()-start)),flush=True)
 assert all_old_positive==115
 (w/'records.json').write_text(json.dumps(results,indent=2)+'\n')
 result=dict(source_sha256=sha(Path(__file__)),preflight_sha256=sha(w/'preflight.md'),helper_sha256=sha(helper),kernel_sha256=sha(kernel),dependencies_sha256=sha(w/'dependencies.json'),boxes_sha256=sha(w/'boxes.json'),order_sha256=sha(w/'order.json'),bounds_sha256=sha(w/'angular-bounds.jsonl.gz'),records_sha256=sha(w/'records.json'),fractional_bits=192,boxes=len(results),angles_per_box=9470,angular_evaluations=sum(total.values()),counts=dict(total),primary_all_positive_boxes_confirmed=all_old_positive,independent_all_positive_boxes=sum(r['all_positive'] for r in results),new_excluded_boxes=sum(r['counts'].get('excluded',0)>0 for r in results),primary_individual_bounds_unavailable=True,elapsed_s=time.monotonic()-start,solution_accepted=False,new_ratio_point=False,native_executed=False)
 (w/'readback.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
if __name__=='__main__':main()
