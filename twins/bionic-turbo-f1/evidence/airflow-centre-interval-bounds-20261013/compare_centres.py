"""Exact coverage and raw enclosure comparison, without selecting a ratio."""
import hashlib,json
from pathlib import Path
from fractions import Fraction as F
from collections import Counter
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
w=Path(__file__).parent
old=json.loads(Path('work/bionic-feasibility-bounds-20261013/certificate.json').read_text())
gram=json.loads(Path('work/bionic-gram-interval-bounds-20261013/refined-certificate.json').read_text())
cert=json.loads((w/'centred-certificate.json').read_text());fresh={r['parent_leaf']:r for r in cert['rows']};middle={r['parent_leaf']:r for r in gram['rows']}
u,end=map(F,old['domain']);ranges=[];counts=Counter();raw_subset=Counter();improvement=[];first_reason=Counter()
for i,row in enumerate(old['leaves']):
 r=fresh.get(i,middle.get(i,row));status=r['status'];counts[status]+=1
 if ranges and ranges[-1]['status']==status:
  assert ranges[-1]['upper']==row['lower'];ranges[-1]['upper']=row['upper'];ranges[-1]['leaves']+=1
 else:ranges.append(dict(lower=row['lower'],upper=row['upper'],status=status,leaves=1))
 if i in fresh:
  if status=='excluded':first_reason[str(next(k for k,a in enumerate(r['angles']) if a['combined']['status']=='excluded'))]+=1
  for k,a in enumerate(r['angles']):
   for key in ('D','residual'):
    before=list(map(F,row['checks'][k][key]));now=list(map(F,a['raw'][key]));raw_subset[key]+=int(before[0]<=now[0]<=now[1]<=before[1])
    if key=='residual':improvement.append((now[1]-now[0])/(before[1]-before[0]))
assert ranges[0]['lower']==old['domain'][0] and ranges[-1]['upper']==old['domain'][1]
assert all(a['upper']==b['lower'] for a,b in zip(ranges,ranges[1:]))
widths={k:sum((F(r['upper'])-F(r['lower']) for r in ranges if r['status']==k),F(0))/(end-u) for k in counts}
assert sum(widths.values())==1
out=dict(source_sha256=sha(Path(__file__)),certificate_sha256=sha(w/'centred-certificate.json'),combined_leaf_counts=dict(counts),relative_widths={k:str(v) for k,v in widths.items()},raw_interval_subset_of_previous=dict(raw_subset),raw_residual_width_ratio_min=float(min(improvement)),raw_residual_width_ratio_max=float(max(improvement)),first_new_angle_exclusion=dict(first_reason),ranges=ranges,range_count=len(ranges),not_physical_components=True,no_admission=True)
(w/'comparison.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
