"""Independent de Casteljau replay and pinned independent angle enclosures."""
import hashlib,importlib.util,json,math
from fractions import Fraction as F
from itertools import combinations
from pathlib import Path
from collections import defaultdict,Counter
from verify_models import restricted,from_strings,scalar,vector,total,prod

P=1<<192
def sqrt_limits(value):
 assert value>=0
 lo=math.isqrt(value.numerator*P*P//value.denominator)
 return F(lo,P),F(lo+(lo*lo*value.denominator<value.numerator*P*P),P)
def enclosure(poly,a,b):
 c=restricted(poly,a,b);return min(c),max(c)
def main():
 w=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 assert sha(w/'verify_models.py')=='1a2c0167b9d76d6f515d20bca1d2f244d172aebdbf49887a8c36f603b891d97c'
 models=json.loads((w/'models.json').read_text());cert=json.loads((w/'refined-certificate.json').read_text())
 assert sha(w/'models.json')==cert['models_sha256']
 cp=Path('work/bionic-feasibility-bounds-20261013/certificate.json');assert sha(cp)==cert['parent_certificate_sha256'];old=json.loads(cp.read_text())
 parent=Path('work/bionic-airflow-delivery-20261013-feasibility-bounds/file-manifest.json');assert sha(parent)==models['parent_manifest_sha256']
 for row in json.loads(parent.read_text())['files']:assert sha(Path('work')/row['path'])==row['sha256']
 for path,digest in json.loads(Path('work/bionic-feasibility-bounds-20261013/readback.json').read_text())['dependencies'].items():
  p=Path(path);assert sha(p)==digest
  for row in json.loads(p.read_text())['files']:assert sha(Path('work')/row['path'])==row['sha256']
 native_models=[]
 for m in models['models']:
  areas=[[from_strings(p) for p in S] for S in m['area_components']]
  minors=[scalar(areas[i],vector(areas[j],areas[k])) for i,j,k in combinations(range(len(areas)),3)]
  assert minors==[from_strings(p) for p in m['minors']]
  assert total(prod(p,p) for p in minors)==from_strings(m['gram_determinant'])
  norm=[scalar(S,S) for S in areas];assert norm==[from_strings(p) for p in m['norm_squared']]
  native_models.append((areas,minors,norm,from_strings(m['gram_determinant'])))
 # The angle reader is reused at its published hash, with main never called.
 helper=Path('work/bionic-feasibility-bounds-20261013/verify_bounds.py')
 assert sha(helper)=='90e5212977d4b8cd426c25e1fe88ce9690ded830e5a47996632eca0df0c821ba'
 spec=importlib.util.spec_from_file_location('pinned_interval_reader',helper);g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
 sy=json.loads(Path('work/bionic-joint-constraints-20261013/system.json').read_text());s=json.loads(Path('work/bionic-buffered-transition-20261013/construction.json').read_text())
 bindings={r['point']:r for r in sy['coordinate_bindings']};u,end=map(F,old['domain']);kap=g.R(*map(F,old['kappa']))
 templates=((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))
 def faces(c):
  b=s['blocks'][c];out=[]
  for template in templates:
   f=[]
   for j in template:
    if not f or f[-1]!=b[j]:f.append(b[j])
   if f[-1]==f[0]:f.pop()
   if len(f)>2:out.append(f)
  return out
 def point(i,v):
  r=bindings.get(i)
  if not r:return [g.R(F(x)) for x in s['vertices'][i]]
  t=g.R(u) if r['variable']=='u' else v
  return [g.R(F(r['x_coefficient']))*t,g.R(F(r['y_coefficient']))*t,g.R(F(r['z_exact']))]
 def check_angles(row):
  v=g.R(F(row['lower']),F(row['upper']))
  for choice in old['selected'][:2]:
   cs={};geometry={};fs={}
   for c in (choice['owner'],choice['neighbour']):
    anchor=[g.R(F(x)) for x in s['vertices'][s['blocks'][c][0]]];fs[c]=faces(c)
    centre,V,geometry[c]=g.native_moments([[g.vsub(point(i,v),anchor) for i in f] for f in fs[c]]);cs[c]=g.vadd(centre,anchor)
   c,d=choice['owner'],choice['neighbour'];S=next(data[1] for f,data in zip(fs[c],geometry[c]) if set(f)==set(choice['face']))
   delta=g.vsub(cs[d],cs[c]);D=g.inner(delta,S);den=sum(x.square() for x in delta)*sum(x.square() for x in S)
   assert D.a>0 and den.a>0 and (D.square()/den-kap).a>=0
 counts=Counter();seen=set();checked_bounds=0;angle_boxes=0;new_excluded=0
 for row in cert['rows']:
  i=row['parent_leaf'];assert i not in seen;seen.add(i);previous=old['leaves'][i]
  assert previous['status']=='unresolved' and (row['lower'],row['upper'])==(previous['lower'],previous['upper'])
  a=(F(row['lower'])-u)/(end-u);b=(F(row['upper'])-u)/(end-u)
  independently_excluded=False;all_dets_positive=True
  for (areas,minors,norm,det),record in zip(native_models,row['determinants']):
   dl,dh=enclosure(det,a,b);low=F(0);high=F(0)
   for p in minors:
    l,h=enclosure(p,a,b);low+=0 if l<=0<=h else min(l*l,h*h);high+=max(l*l,h*h)
   dl=max(F(0),dl,low);dh=min(dh,high);assert 0<=dl<=dh
   el=F(0);eh=F(0)
   for p in norm:
    l,h=enclosure(p,a,b);assert h>=0
    el+=sqrt_limits(max(F(0),l))[0];eh+=sqrt_limits(h)[1]
   assert eh>0
   lower=125*len(areas)**6*dl/eh**6-1
   upper=None if el==0 else 125*len(areas)**6*dh/el**6-1
   assert lower>=F(record['residual'][0])
   if record['residual'][1] is not None:assert upper is not None and upper<=F(record['residual'][1])
   if record['status']=='excluded':assert upper is not None and upper<0;independently_excluded=True
   if record['status']=='selected_pass':assert lower>=0
   all_dets_positive &= lower>=0;checked_bounds+=1
  if row['inherited_angles_both_positive']:check_angles(row);angle_boxes+=1
  if row['status']=='excluded':assert independently_excluded;new_excluded+=1
  elif row['status']=='selected_subset_only':assert row['inherited_angles_both_positive'] and all_dets_positive
  else:assert row['status']=='unresolved'
  counts[row['status']]+=1
 assert seen=={i for i,r in enumerate(old['leaves']) if r['status']=='unresolved'}
 widths={k:sum((F(r['upper'])-F(r['lower']) for r in cert['rows'] if r['status']==k),F(0))/(end-u) for k in counts}
 widths['excluded']=widths.get('excluded',F(0))+F(3269,4096)
 summary=json.loads((w/'readback.json').read_text());assert {k:str(v) for k,v in widths.items()}==summary['combined_relative_widths']
 out=dict(source_sha256=sha(Path(__file__)),models_sha256=sha(w/'models.json'),certificate_sha256=sha(w/'refined-certificate.json'),de_casteljau_boxes=len(seen),determinant_bounds_rechecked=checked_bounds,new_exclusions_verified=new_excluded,positive_angle_pair_boxes_rechecked=angle_boxes,combined_relative_widths={k:str(v) for k,v in widths.items()},no_new_subdivision=True,no_new_ratio_point=True,solution_accepted=False)
 (w/'independent-readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
if __name__=='__main__':main()
