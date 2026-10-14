"""Independent verification of all new exclusion witnesses; other counts remain diagnostics."""
import csv,hashlib,importlib.util,json
from pathlib import Path
from fractions import Fraction as F
from collections import Counter,defaultdict
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
helper=Path('work/bionic-centre-interval-bounds-20261013/verify_centres_v2.py')
assert sha(helper)=='a259f163405dec0cfb4f1b707698249ea9069de9b02a9db1835fb172f1a0b992'
spec=importlib.util.spec_from_file_location('pinned_independent_centres',helper);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);g=m.g

def main():
 w=Path(__file__).parent;report=json.loads((w/'readback.json').read_text());records=[json.loads(line) for line in (w/'records.jsonl').read_text().splitlines()]
 assert sha(w/'records.jsonl')==report['records_sha256'] and sha(w/'order.json')==report['order_sha256']
 for path,digest in json.loads((w/'dependencies.json').read_text()).items():
  manifest=Path(path);assert sha(manifest)==digest
  for row in json.loads(manifest.read_text())['files']:assert sha(Path('work')/row['path'])==row['sha256']
 parentpath=Path('work/bionic-centre-interval-bounds-20261013/centred-certificate.json');assert sha(parentpath)==report['parent_certificate_sha256']
 parents={r['parent_leaf']:r for r in json.loads(parentpath.read_text())['rows'] if r['status']!='excluded'}
 assert len(records)==len(parents)==159 and len({r['parent_leaf'] for r in records})==159 and set(parents)=={r['parent_leaf'] for r in records}
 old=json.loads(Path('work/bionic-feasibility-bounds-20261013/certificate.json').read_text());u,end=map(F,old['domain']);kap=g.R(*map(F,old['kappa']))
 s=json.loads(Path('work/bionic-buffered-transition-20261013/construction.json').read_text());sy=json.loads(Path('work/bionic-joint-constraints-20261013/system.json').read_text());bindings={r['point']:r for r in sy['coordinate_bindings']}
 templates=((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7));fs=[];reg=defaultdict(list)
 for c,block in enumerate(s['blocks']):
  rr=[]
  for template in templates:
   f=[]
   for j in template:
    if not f or f[-1]!=block[j]:f.append(block[j])
   if f[-1]==f[0]:f.pop()
   if len(f)>2:rr.append(f);reg[tuple(sorted(f))].append((c,f))
  fs.append(rr)
 canonical=lambda f:min(tuple(f[i:]+f[:i]) for i in range(len(f)))
 for occurrences in reg.values():
  if len(occurrences)==2:assert canonical(occurrences[0][1])==canonical(occurrences[1][1][::-1])
 moving={i for i,r in bindings.items() if r['variable']=='v'};changing=[bool(set(block)&moving) for block in s['blocks']]
 pairs={(a,c):f for rr in reg.values() if len(rr)==2 for (a,f),(c,other) in [rr] if changing[a] or changing[c]}
 skip={(r['owner'],r['neighbour']) for r in old['selected'][:2]};assert len(pairs)==9472
 source_rows=list(csv.DictReader(Path('work/bionic-neighbour-constraints-20261013/faces.csv').open()))
 order=sorted((r for r in source_rows if (int(r['owner']),int(r['neighbour'])) in pairs and (int(r['owner']),int(r['neighbour'])) not in skip),key=lambda r:(-F(r['angle_deg']),int(r['owner']),int(r['neighbour'])))
 declared=json.loads((w/'order.json').read_text());assert len(order)==len(declared)==9470
 for source,r in zip(order,declared):
  pair=(int(source['owner']),int(source['neighbour']));assert (r['owner'],r['neighbour'])==pair and r['family']==source['family'] and r['archived_angle_deg']==source['angle_deg']
  assert canonical(r['face'])==canonical(pairs[pair])
 def point(i,v):
  r=bindings.get(i)
  if not r:return [g.R(F(x)) for x in s['vertices'][i]]
  t=g.R(u) if r['variable']=='u' else v
  return [g.R(F(r['x_coefficient']))*t,g.R(F(r['y_coefficient']))*t,g.R(F(r['z_exact']))]
 verified=[];counts=Counter()
 for row in records:
  p=parents[row['parent_leaf']];assert (p['lower'],p['upper'],p['status'])==(row['lower'],row['upper'],row['parent_status'])
  counts[row['status']]+=1
  if row['status']!='excluded':
   assert row['status']=='not_excluded_by_remaining_angles' and row['witness'] is None and sum(row['counts'].values())==9470 and row['counts'].get('excluded',0)==0
   continue
  wtn=row['witness'];choice=declared[wtn['rank']];assert choice==wtn['choice'] and sum(row['counts'].values())==wtn['rank']+1 and row['counts']['excluded']==1
  v=g.R(F(row['lower']),F(row['upper']));centres={};geometry={}
  for c in (choice['owner'],choice['neighbour']):
   anchor=[g.R(F(x)) for x in s['vertices'][s['blocks'][c][0]]]
   C,V,geometry[c]=m.moments([[g.vsub(point(i,v),anchor) for i in f] for f in fs[c]])
   centres[c]=g.vadd(C,anchor);m.contained(V,wtn['volumes'][str(c)])
   for x,pair in zip(centres[c],wtn['centres'][str(c)]):m.contained(x,pair)
  a,c=choice['owner'],choice['neighbour'];S=next(S for f,(cf,S) in zip(fs[a],geometry[a]) if set(f)==set(choice['face']))
  delta=g.vsub(centres[c],centres[a]);D=g.inner(delta,S);den=sum(x.square() for x in delta)*sum(x.square() for x in S);assert den.a>0
  res=D.square()/den-kap;m.contained(D,wtn['D']);m.contained(res,wtn['residual']);assert D.b<=0 or res.b<0
  verified.append(dict(parent_leaf=row['parent_leaf'],owner=a,neighbour=c,D=[str(D.a),str(D.b)],residual=[str(res.a),str(res.b)]))
 widths={k:sum((F(r['upper'])-F(r['lower']) for r in records if r['status']==k),F(0))/(end-u) for k in counts};widths['excluded']=widths.get('excluded',F(0))+F(3937,4096)
 assert {k:str(v) for k,v in widths.items()}==report['combined_relative_widths']
 out=dict(source_sha256=sha(Path(__file__)),pinned_reader_sha256=sha(helper),records_sha256=sha(w/'records.jsonl'),boxes_verified=len(records),ordered_constraints_verified=len(declared),new_exclusions_verified=len(verified),witnesses=verified,combined_relative_widths={k:str(v) for k,v in widths.items()},nonexclusion_counts_not_independently_recomputed=True,solution_accepted=False,new_ratio_point=False,native_executed=False)
 (w/'independent-readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='witnesses'}))
if __name__=='__main__':main()
