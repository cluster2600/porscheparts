"""Rebound the two necessary angles on exactly the 447 archived unresolved boxes."""
import hashlib,json
from pathlib import Path
from fractions import Fraction as F
from collections import Counter
from centred import I,b,face,cell
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 w=Path(__file__).parent
 proof=json.loads((w/'preliminary-publication.json').read_text())
 for row in proof['assets']:assert sha(w/row['name'])==row['sha256']
 dependencies={}
 for name in ('buffered-transition','neighbour-constraints','joint-constraints','feasibility-bounds','gram-interval-bounds'):
  path=Path(f'work/bionic-airflow-delivery-20261013-{name}/file-manifest.json');dependencies[str(path)]=sha(path)
  for row in json.loads(path.read_text())['files']:assert sha(Path('work')/row['path'])==row['sha256']
 oldpath=Path('work/bionic-feasibility-bounds-20261013/certificate.json');old=json.loads(oldpath.read_text())
 parentpath=Path('work/bionic-gram-interval-bounds-20261013/refined-certificate.json');parent=json.loads(parentpath.read_text())
 assert sha(parentpath)=='b68c186afdb2c3c6acb08b26ffae4bc3b2d7baae76372b2bd348d2a1a3d62a64'
 s=json.loads(Path('work/bionic-buffered-transition-20261013/construction.json').read_text())
 sy=json.loads(Path('work/bionic-joint-constraints-20261013/system.json').read_text())
 bindings={r['point']:r for r in sy['coordinate_bindings']};u,end=map(F,old['domain']);kl,kh=map(F,old['kappa']);kap=I(I(kl).lo,I(kh).hi,True)
 def point(i,v):
  row=bindings.get(i)
  if not row:return [I(F(x)) for x in s['vertices'][i]]
  t=I(u) if row['variable']=='u' else v
  return [I(F(row['x_coefficient']))*t,I(F(row['y_coefficient']))*t,I(F(row['z_exact']))]
 needed={x for r in old['selected'][:2] for x in (r['owner'],r['neighbour'])};faces={}
 for c in needed:
  block=s['blocks'][c];n=4 if s['stages'][c]=='buffer' else 3;lo,hi=block[:n],block[4:4+n]
  faces[c]=[lo[::-1],hi]+[[lo[i],lo[(i+1)%n],hi[(i+1)%n],hi[i]] for i in range(n)]
 records=[];raw_counts=Counter();intersections=Counter();narrower=0;wider=0
 for source in parent['rows']:
  if source['status']!='unresolved':continue
  idx=source['parent_leaf'];previous=old['leaves'][idx];assert (previous['lower'],previous['upper'])==(source['lower'],source['upper'])
  v=I(I(F(source['lower'])).lo,I(F(source['upper'])).hi,True);cs={};geo={};volume={}
  for c in needed:
   anchor=[I(F(x)) for x in s['vertices'][s['blocks'][c][0]]]
   try:
    geo[c]=[face([b.minus(point(i,v),anchor) for i in f]) for f in faces[c]]
    centre,V=cell(geo[c]);cs[c]=b.plus(centre,anchor);volume[c]=V.pair()
   except ZeroDivisionError:pass
  rr=[]
  for k,choice in enumerate(old['selected'][:2]):
   try:
    a,c=choice['owner'],choice['neighbour'];delta=b.minus(cs[c],cs[a]);S=geo[a][faces[a].index(choice['face'])][1]
    D=b.dot(delta,S);den=sum(x.sq() for x in delta)*sum(x.sq() for x in S)
    if den.lo<=0:raise ZeroDivisionError
    res=D.sq()/den-kap
    raw=dict(D=D.pair(),residual=res.pair(),centres={str(c):[x.pair() for x in cs[c]] for c in (a,c)},volumes={str(c):volume[c] for c in (a,c)})
    status=lambda d,r:'excluded' if d[1]<=0 or r[1]<0 else ('selected_pass' if d[0]>0 and r[0]>=0 else 'unknown')
    dp=list(map(F,raw['D']));rp=list(map(F,raw['residual']));raw['status']=status(dp,rp);raw_counts[raw['status']]+=1
    inherited=previous['checks'][k];combined={}
    for key in ('D','residual'):
     now=list(map(F,raw[key]))
     if key in inherited:
      before=list(map(F,inherited[key]));now=[max(now[0],before[0]),min(now[1],before[1])];assert now[0]<=now[1]
      if key=='residual':
       narrower+=int(F(raw[key][1])-F(raw[key][0])<=before[1]-before[0]);wider+=int(F(raw[key][1])-F(raw[key][0])>before[1]-before[0])
     combined[key]=[str(x) for x in now]
    combined['status']=status(list(map(F,combined['D'])),list(map(F,combined['residual'])))
    intersections[combined['status']]+=1;rr.append(dict(raw=raw,combined=combined))
   except (ZeroDivisionError,KeyError):
    raw_counts['singular']+=1;rr.append(dict(raw=dict(status='unknown',reason='singular_enclosure'),combined=previous['checks'][k]));intersections[previous['checks'][k]['status']]+=1
  checks=[r['combined']['status'] for r in rr]+[r['status'] for r in source['determinants']]
  status='excluded' if 'excluded' in checks else ('selected_subset_only' if all(x=='selected_pass' for x in checks) else 'unresolved')
  records.append(dict(parent_leaf=idx,lower=source['lower'],upper=source['upper'],status=status,angles=rr,inherited_determinants=source['determinants']))
 assert len(records)==447
 out=dict(parent_certificate_sha256=sha(parentpath),original_certificate_sha256=sha(oldpath),bits=b.BITS,rows=records,no_new_subdivision=True,new_ratio_point=False,solution_accepted=False)
 (w/'centred-certificate.json').write_text(json.dumps(out,indent=2)+'\n')
 counts=Counter(r['status'] for r in records);widths={k:sum((F(r['upper'])-F(r['lower']) for r in records if r['status']==k),F(0))/(end-u) for k in counts};widths['excluded']=widths.get('excluded',F(0))+F(3649,4096)
 summary=dict(source_sha256=sha(Path(__file__)),implementation_sha256=sha(w/'centred.py'),dependencies=dependencies,certificate_sha256=sha(w/'centred-certificate.json'),boxes=447,new_counts=dict(counts),raw_angle_counts=dict(raw_counts),combined_angle_counts=dict(intersections),raw_residual_width_not_larger=narrower,raw_residual_width_larger=wider,combined_relative_widths={k:str(v) for k,v in widths.items()},solution_accepted=False,new_ratio_point=False,native_executed=False)
 (w/'readback.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
if __name__=='__main__':main()
