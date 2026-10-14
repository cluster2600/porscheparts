"""Exact comparison of archived interval endpoints; no geometry evaluation."""
import hashlib,json
from fractions import Fraction as F
from collections import Counter
from pathlib import Path
w=Path(__file__).parent;oldpath=Path('work/bionic-feasibility-bounds-20261013/certificate.json');old=json.loads(oldpath.read_text());new=json.loads((w/'refined-certificate.json').read_text());counts=Counter();remaining=Counter();witness=Counter();replacements={}
for row in new['rows']:
 prior=old['leaves'][row['parent_leaf']];replacements[row['parent_leaf']]=row['status']
 for j,result in enumerate(row['determinants']):
  before=prior['checks'][j+2]
  if 'residual' not in before:counts['old_singular_geometry_no_finite_comparison']+=1;continue
  if result['residual'][1] is None:counts['new_upper_unbounded']+=1;continue
  a,b=map(F,before['residual']);c,d=map(F,result['residual'])
  counts['new_interval_contained_in_old' if a<=c<=d<=b else 'not_nested']+=1
 if row['status']=='unresolved':remaining['all_four_determinants_pass' if all(x['status']=='selected_pass' for x in row['determinants']) else 'determinant_also_indeterminate']+=1
 if row['status']=='excluded':
  j=next(j for j,x in enumerate(row['determinants']) if x['status']=='excluded');witness[old['selected'][j+2]['cell']]+=1
runs=[]
for i,row in enumerate(old['leaves']):
 status=replacements.get(i,row['status'])
 if runs and runs[-1]['status']==status and runs[-1]['upper']==row['lower']:runs[-1]['upper']=row['upper']
 else:runs.append({'lower':row['lower'],'upper':row['upper'],'status':status})
lo,hi=map(F,old['domain']);widths={status:str(sum((F(r['upper'])-F(r['lower']) for r in runs if r['status']==status),F(0))/(hi-lo)) for status in {r['status'] for r in runs}}
assert widths==json.loads((w/'readback.json').read_text())['combined_relative_widths']
out={'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'old_certificate_sha256':hashlib.sha256(oldpath.read_bytes()).hexdigest(),'new_certificate_sha256':hashlib.sha256((w/'refined-certificate.json').read_bytes()).hexdigest(),'endpoint_comparisons':dict(counts),'remaining_boxes':dict(remaining),'first_new_exclusion_witness':dict(witness),'contiguous_ranges':runs,'relative_widths':widths,'no_monotonicity_or_feasibility_claim':True}
(w/'comparison.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'counts':counts,'remaining':remaining,'witness':witness,'ranges':len(runs)}))
