"""Check remaining angular necessary constraints on archived boxes; stop only on proof of refusal."""
import csv,hashlib,importlib.util,json,time
from pathlib import Path
from fractions import Fraction as F
from collections import defaultdict,Counter
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=Path('work/bionic-centre-interval-bounds-20261013/centred.py')
assert sha(p)=='4f366b9571c931fa8d4bf19e90e94c5bd77d0093c193a1e0de9caf1f3590361b'
spec=importlib.util.spec_from_file_location('pinned_centred',p);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
b=h.b;I=h.I

def main():
 w=Path(__file__).parent;start=time.monotonic();dependencies={}
 for name in ('buffered-transition','neighbour-constraints','joint-constraints','feasibility-bounds','gram-interval-bounds','centre-interval-bounds'):
  path=Path(f'work/bionic-airflow-delivery-20261013-{name}/file-manifest.json');dependencies[str(path)]=sha(path)
  for r in json.loads(path.read_text())['files']:assert sha(Path('work')/r['path'])==r['sha256']
 s=json.loads(Path('work/bionic-buffered-transition-20261013/construction.json').read_text());sy=json.loads(Path('work/bionic-joint-constraints-20261013/system.json').read_text())
 parentpath=Path('work/bionic-centre-interval-bounds-20261013/centred-certificate.json');assert sha(parentpath)=='0eefe3377477c48956a9289d5be1d4b68d0266669cb7e9850d78cabab7cb7b1b';parent=json.loads(parentpath.read_text())
 old=json.loads(Path('work/bionic-feasibility-bounds-20261013/certificate.json').read_text());u,end=map(F,old['domain']);kl,kh=map(F,old['kappa']);kap=I(I(kl).lo,I(kh).hi,True)
 bindings={r['point']:r for r in sy['coordinate_bindings']};moving={i for i,r in bindings.items() if r['variable']=='v'}
 faces=[];registry=defaultdict(list)
 for c,block in enumerate(s['blocks']):
  n=4 if s['stages'][c]=='buffer' else 3;lo,hi=block[:n],block[4:4+n]
  fs=[lo[::-1],hi]+[[lo[i],lo[(i+1)%n],hi[(i+1)%n],hi[i]] for i in range(n)]
  faces.append(fs)
  for f in fs:registry[tuple(sorted(f))].append((c,f))
 changing=[bool(set(block)&moving) for block in s['blocks']];pairs={}
 for occurrences in registry.values():
  if len(occurrences)==2 and any(changing[c] for c,f in occurrences):
   (a,f),(c,other)=occurrences;pairs[(a,c)]=f
 assert len(pairs)==9472
 skip={(r['owner'],r['neighbour']) for r in old['selected'][:2]}
 rows=list(csv.DictReader(Path('work/bionic-neighbour-constraints-20261013/faces.csv').open()))
 choices=sorted((r for r in rows if (int(r['owner']),int(r['neighbour'])) in pairs and (int(r['owner']),int(r['neighbour'])) not in skip),key=lambda r:(-F(r['angle_deg']),int(r['owner']),int(r['neighbour'])))
 assert len(choices)==9470
 ordered=[dict(owner=int(r['owner']),neighbour=int(r['neighbour']),face=pairs[(int(r['owner']),int(r['neighbour']))],family=r['family'],archived_angle_deg=r['angle_deg']) for r in choices]
 (w/'order.json').write_text(json.dumps(ordered,indent=2)+'\n')
 (w/'dependencies.json').write_text(json.dumps(dependencies,indent=2)+'\n')
 def point(i,v):
  r=bindings.get(i)
  if not r:return [I(F(x)) for x in s['vertices'][i]]
  t=I(u) if r['variable']=='u' else v
  return [I(F(r['x_coefficient']))*t,I(F(r['y_coefficient']))*t,I(F(r['z_exact']))]
 records=[];targets=[r for r in parent['rows'] if r['status']!='excluded'];assert len(targets)==159
 with (w/'records.jsonl').open('x') as stream:
  for index,source in enumerate(targets):
   v=I(I(F(source['lower'])).lo,I(F(source['upper'])).hi,True);cache={};points={};counts=Counter();witness=None
   def geometry(c):
    if c not in cache:
     anchor=[I(F(x)) for x in s['vertices'][s['blocks'][c][0]]]
     for i in set(s['blocks'][c]):
      if i not in points:points[i]=point(i,v)
     try:
      geo=[h.face([b.minus(points[i],anchor) for i in f]) for f in faces[c]];centre,V=h.cell(geo);cache[c]=(b.plus(centre,anchor),V,geo)
     except ZeroDivisionError:cache[c]=None
    return cache[c]
   for rank,choice in enumerate(ordered):
    a,c=choice['owner'],choice['neighbour'];ga,gc=geometry(a),geometry(c)
    try:
     if ga is None or gc is None:raise ZeroDivisionError
     delta=b.minus(gc[0],ga[0]);S=ga[2][faces[a].index(choice['face'])][1];D=b.dot(delta,S)
     den=sum(x.sq() for x in delta)*sum(x.sq() for x in S)
     if den.lo<=0:raise ZeroDivisionError
     res=D.sq()/den-kap
     status='excluded' if D.hi<=0 or res.hi<0 else ('positive' if D.lo>0 and res.lo>=0 else 'unknown')
     counts[status]+=1
     if status=='excluded':
      witness=dict(rank=rank,choice=choice,D=D.pair(),residual=res.pair(),centres={str(a):[x.pair() for x in ga[0]],str(c):[x.pair() for x in gc[0]]},volumes={str(a):ga[1].pair(),str(c):gc[1].pair()});break
    except ZeroDivisionError:counts['singular']+=1
   r=dict(parent_leaf=source['parent_leaf'],lower=source['lower'],upper=source['upper'],parent_status=source['status'],status='excluded' if witness else 'not_excluded_by_remaining_angles',counts=dict(counts),evaluated_cells=len(cache),witness=witness)
   stream.write(json.dumps(r)+'\n');stream.flush();records.append(r)
   print(json.dumps(dict(box=index+1,total=159,counts=dict(counts),elapsed_s=time.monotonic()-start)),flush=True)
 counts=Counter(r['status'] for r in records);widths={k:sum((F(r['upper'])-F(r['lower']) for r in records if r['status']==k),F(0))/(end-u) for k in counts};widths['excluded']=widths.get('excluded',F(0))+F(3937,4096)
 report=dict(source_sha256=sha(Path(__file__)),parent_certificate_sha256=sha(parentpath),preflight_sha256=sha(w/'preflight.md'),records_sha256=sha(w/'records.jsonl'),order_sha256=sha(w/'order.json'),boxes=len(records),scheduled_constraints=len(ordered),new_counts=dict(counts),combined_relative_widths={k:str(v) for k,v in widths.items()},elapsed_s=time.monotonic()-start,no_new_subdivision=True,new_ratio_point=False,solution_accepted=False,native_executed=False)
 (w/'readback.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
