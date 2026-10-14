"""Independent Fraction interval reconstruction; no import of the new primary evaluator."""
import hashlib,importlib.util,json
from pathlib import Path
from fractions import Fraction as F
from collections import Counter
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=Path('work/bionic-feasibility-bounds-20261013/verify_bounds.py')
assert sha(p)=='90e5212977d4b8cd426c25e1fe88ce9690ded830e5a47996632eca0df0c821ba'
spec=importlib.util.spec_from_file_location('independent_fraction_kernel',p);g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)

def polygon(points):
    n=len(points);origin=g.average(points);triangles=[];weighted_offsets=[];norms=[]
    for j in range(n):
        edge=g.vsub(points[(j+1)%n],points[j]);spoke=g.vsub(origin,points[j]);N=g.vector(edge,spoke)
        triangles.append(N);norms.append(g.length(N))
        weighted_offsets.append([norms[-1]*(points[j][i]+points[(j+1)%n][i]-2*origin[i]) for i in range(3)])
    W=sum(norms);assert W.a>0
    centre=[origin[i]+sum(q[i] for q in weighted_offsets)/(3*W) for i in range(3)]
    area=[sum(q[i] for q in triangles)/2 for i in range(3)]
    return centre,area

def moments(polygons):
    geometry=[polygon(q) for q in polygons];seed=g.average([cf for cf,S in geometry])
    offsets=[g.vsub(cf,seed) for cf,S in geometry]
    weights=[g.inner(S,d)/3 for (cf,S),d in zip(geometry,offsets)];volume=sum(weights);assert volume.a>0
    centre=[seed[i]+3*sum(v*d[i] for v,d in zip(weights,offsets))/(4*volume) for i in range(3)]
    return centre,volume,geometry

def contained(x,pair):
    assert F(pair[0])<=x.a<=x.b<=F(pair[1])

def main():
 w=Path(__file__).parent;report=json.loads((w/'readback.json').read_text());cert=json.loads((w/'centred-certificate.json').read_text())
 assert sha(w/'centred-certificate.json')==report['certificate_sha256']
 for path,digest in report['dependencies'].items():
  p=Path(path);assert sha(p)==digest
  for r in json.loads(p.read_text())['files']:assert sha(Path('work')/r['path'])==r['sha256']
 oldpath=Path('work/bionic-feasibility-bounds-20261013/certificate.json');assert sha(oldpath)==cert['original_certificate_sha256'];old=json.loads(oldpath.read_text())
 parentpath=Path('work/bionic-gram-interval-bounds-20261013/refined-certificate.json');assert sha(parentpath)==cert['parent_certificate_sha256'];parent=json.loads(parentpath.read_text())
 parents={r['parent_leaf']:r for r in parent['rows'] if r['status']=='unresolved'}
 assert len(parents)==447 and set(parents)=={r['parent_leaf'] for r in cert['rows']}
 s=json.loads(Path('work/bionic-buffered-transition-20261013/construction.json').read_text());sy=json.loads(Path('work/bionic-joint-constraints-20261013/system.json').read_text())
 bindings={r['point']:r for r in sy['coordinate_bindings']};u,end=map(F,old['domain']);kap=g.R(*map(F,old['kappa']))
 templates=((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))
 # Analytic controls use independently assembled polygons, and nonplanar face symmetry.
 references=0
 for scale in (F(1),F(1,1000),F(1,1000000)):
  for shape in ('cube','pyramid'):
   coords=((0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1)) if shape=='cube' else ((0,0,0),(1,0,0),(1,1,0),(0,1,0),(F(1,2),F(1,2),1))
   fs=templates if shape=='cube' else ((0,3,2,1),(0,1,4),(1,2,4),(2,3,4),(3,0,4))
   points=[[g.R(x*scale) for x in q] for q in coords];c,V,_=moments([[points[j] for j in f] for f in fs])
   expected=[scale/2,scale/2,scale/(2 if shape=='cube' else 4)];ev=scale**3/(1 if shape=='cube' else 3)
   assert V.a<=ev<=V.b and all(x.a<=e<=x.b for x,e in zip(c,expected));references+=1
  cf,area=polygon([[g.R(scale*x) for x in q] for q in ((-1,-1,1),(1,-1,-1),(1,1,1),(-1,1,-1))])
  assert all(x.a<=0<=x.b for x in cf) and all(x.a<=e<=x.b for x,e in zip(area,(0,0,4*scale**2)));references+=1
 def faces(c):
  out=[];block=s['blocks'][c]
  for t in templates:
   row=[]
   for j in t:
    if not row or row[-1]!=block[j]:row.append(block[j])
   if row[-1]==row[0]:row.pop()
   if len(row)>2:out.append(row)
  return out
 def point(i,v):
  r=bindings.get(i)
  if not r:return [g.R(F(x)) for x in s['vertices'][i]]
  t=g.R(u) if r['variable']=='u' else v
  return [g.R(F(r['x_coefficient']))*t,g.R(F(r['y_coefficient']))*t,g.R(F(r['z_exact']))]
 counts=Counter();bounds=0;positive_volumes=0
 for row in cert['rows']:
  parent=parents[row['parent_leaf']];previous=old['leaves'][row['parent_leaf']]
  assert (row['lower'],row['upper'])==(parent['lower'],parent['upper']) and row['inherited_determinants']==parent['determinants']
  v=g.R(F(row['lower']),F(row['upper']));statuses=[]
  for k,choice in enumerate(old['selected'][:2]):
   raw=row['angles'][k]['raw'];combined=row['angles'][k]['combined'];centres={};geo={};fs={}
   for c in (choice['owner'],choice['neighbour']):
    anchor=[g.R(F(x)) for x in s['vertices'][s['blocks'][c][0]]];fs[c]=faces(c)
    centre,V,geo[c]=moments([[g.vsub(point(j,v),anchor) for j in f] for f in fs[c]])
    centres[c]=g.vadd(centre,anchor);contained(V,raw['volumes'][str(c)]);positive_volumes+=1
    for x,interval in zip(centres[c],raw['centres'][str(c)]):contained(x,interval)
   a,c=choice['owner'],choice['neighbour'];S=next(data[1] for f,data in zip(fs[a],geo[a]) if set(f)==set(choice['face']))
   delta=g.vsub(centres[c],centres[a]);D=g.inner(delta,S);den=sum(x.square() for x in delta)*sum(x.square() for x in S);assert den.a>0
   residual=D.square()/den-kap;contained(D,raw['D']);contained(residual,raw['residual']);bounds+=1
   expected={}
   for key in ('D','residual'):
    l,h=map(F,raw[key]);prior=previous['checks'][k]
    if key in prior:l=max(l,F(prior[key][0]));h=min(h,F(prior[key][1]))
    assert l<=h and combined[key]==[str(l),str(h)];expected[key]=(l,h)
   status=lambda d,r:'excluded' if d[1]<=0 or r[1]<0 else ('selected_pass' if d[0]>0 and r[0]>=0 else 'unknown')
   assert status(tuple(map(F,raw['D'])),tuple(map(F,raw['residual'])))==raw['status']
   assert status(expected['D'],expected['residual'])==combined['status']
   # All present classifications are justified by the new independent bounds alone.
   if combined['status']=='excluded':assert D.b<=0 or residual.b<0
   if combined['status']=='selected_pass':assert D.a>0 and residual.a>=0
   statuses.append(combined['status'])
  statuses.extend(d['status'] for d in parent['determinants'])
  expected='excluded' if 'excluded' in statuses else ('selected_subset_only' if all(x=='selected_pass' for x in statuses) else 'unresolved')
  assert row['status']==expected;counts[expected]+=1
 widths={k:sum((F(r['upper'])-F(r['lower']) for r in cert['rows'] if r['status']==k),F(0))/(end-u) for k in counts};widths['excluded']=widths.get('excluded',F(0))+F(3649,4096)
 assert {k:str(v) for k,v in widths.items()}==report['combined_relative_widths']
 out=dict(source_sha256=sha(Path(__file__)),certificate_sha256=sha(w/'centred-certificate.json'),pinned_fraction_kernel_sha256=sha(p),boxes_verified=len(parents),angle_bounds_verified=bounds,positive_cell_volume_enclosures=positive_volumes,analytic_references=references,counts=dict(counts),combined_relative_widths={k:str(v) for k,v in widths.items()},determinants_inherited_byte_exact=True,independent_bounds_contained=True,solution_accepted=False,native_executed=False)
 (w/'independent-readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
if __name__=='__main__':main()
