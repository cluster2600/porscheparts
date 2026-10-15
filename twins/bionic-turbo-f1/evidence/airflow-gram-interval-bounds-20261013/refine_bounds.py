"""Bernstein bounds on the SAME 827 archived boxes, no new subdivision."""
import hashlib,json,math
from fractions import Fraction as F
from pathlib import Path
from collections import Counter
from polynomials import bernstein

Q=1<<160
def root_bounds(x):
 assert x>=0
 low=math.isqrt(x.numerator*Q*Q//x.denominator)
 return F(low,Q),F(low+(F(low*low,Q*Q)<x),Q)
def range_of(p,a,b):
 values=bernstein(tuple(F(x) for x in p),a,b);return min(values),max(values)
def gram_bounds(m,a,b):
 lo,hi=range_of(m['gram_determinant'],a,b);sumlo=F(0);sumhi=F(0)
 for p in m['minors']:
  l,h=range_of(p,a,b);sumlo+=0 if l<=0<=h else min(l*l,h*h);sumhi+=max(l*l,h*h)
 lo=max(F(0),lo,sumlo);hi=min(hi,sumhi);assert 0<=lo<=hi
 el=F(0);eh=F(0)
 for p in m['norm_squared']:
  l,h=range_of(p,a,b);assert h>=0
  el+=root_bounds(max(F(0),l))[0];eh+=root_bounds(h)[1]
 assert eh>0
 lower=125*len(m['faces'])**6*lo/eh**6-1
 upper=None if el<=0 else 125*len(m['faces'])**6*hi/el**6-1
 assert upper is None or lower<=upper
 return dict(residual=[str(lower),None if upper is None else str(upper)],status='excluded' if upper is not None and upper<0 else ('selected_pass' if lower>=0 else 'unknown'))
def main():
 w=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 pub=json.loads((w/'preliminary-publication.json').read_text())
 assert pub['all_verified_before_interval_replay']
 for r in pub['assets']:assert sha(w/r['name'])==r['sha256']
 model=json.loads((w/'models.json').read_text());cp=Path('work/bionic-feasibility-bounds-20261013/certificate.json');assert sha(cp)==model['parent_certificate_sha256'];old=json.loads(cp.read_text())
 origin,end=map(F,old['domain']);out=[]
 for i,leaf in enumerate(old['leaves']):
  if leaf['status']!='unresolved':continue
  a=(F(leaf['lower'])-origin)/(end-origin);b=(F(leaf['upper'])-origin)/(end-origin)
  results=[gram_bounds(m,a,b) for m in model['models']]
  angles_ok=all(x['status']=='selected_pass' for x in leaf['checks'][:2])
  status='excluded' if any(r['status']=='excluded' for r in results) else ('selected_subset_only' if angles_ok and all(r['status']=='selected_pass' for r in results) else 'unresolved')
  out.append(dict(parent_leaf=i,lower=leaf['lower'],upper=leaf['upper'],status=status,determinants=results,inherited_angles_both_positive=angles_ok))
 assert len(out)==827
 result=dict(source_sha256=sha(Path(__file__)),models_sha256=sha(w/'models.json'),parent_certificate_sha256=sha(cp),root_fractional_bits=160,new_subdivisions=0,new_ratio_evaluations=0,rows=out,feasibility_solved=False)
 (w/'refined-certificate.json').write_text(json.dumps(result,indent=2)+'\n')
 counts=Counter(r['status'] for r in out);allcounts=dict(counts);allcounts['excluded']=allcounts.get('excluded',0)+1524
 widths={status:str(sum((F(r['upper'])-F(r['lower']) for r in out if r['status']==status),F(0))/(end-origin)) for status in counts}
 widths['excluded']=str(F(widths.get('excluded','0'))+F(3269,4096))
 transitions=Counter((old['leaves'][r['parent_leaf']]['checks'][j+2]['status'],x['status']) for r in out for j,x in enumerate(r['determinants']))
 summary=dict(certificate_sha256=sha(w/'refined-certificate.json'),parent_certificate_sha256=sha(cp),updated_leaf_counts=dict(counts),combined_leaf_counts=allcounts,combined_relative_widths=widths,determinant_status_transitions={a+' -> '+b:n for (a,b),n in transitions.items()},all_original_exclusions_retained=True,new_ratio_selected=False,solution_accepted=False)
 (w/'readback.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
if __name__=='__main__':main()
