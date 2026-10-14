"""Merge adjacent certificate leaves for reporting, without changing status."""
import hashlib,json
from fractions import Fraction as F
from collections import Counter
from pathlib import Path
w=Path(__file__).parent;c=json.loads((w/'certificate.json').read_text());runs=[];witnesses=Counter()
for row in c['leaves']:
 if row['status']=='excluded':witnesses[next(i for i,x in enumerate(row['checks']) if x['status']=='excluded')]+=1
 if runs and runs[-1]['status']==row['status'] and runs[-1]['upper']==row['lower']:runs[-1]['upper']=row['upper']
 else:runs.append({k:row[k] for k in ('lower','upper','status')})
lo,hi=map(F,c['domain']);widths={kind:str(sum((F(x['upper'])-F(x['lower']) for x in runs if x['status']==kind),F(0))/(hi-lo)) for kind in {x['status'] for x in runs}}
assert widths==json.loads((w/'readback.json').read_text())['relative_widths']
out={'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'certificate_sha256':hashlib.sha256((w/'certificate.json').read_bytes()).hexdigest(),'selected':c['selected'],'first_exclusion_witness_counts':dict(witnesses),'contiguous_ranges':runs,'relative_widths':widths,'all_intervals_closed_for_enclosure_only':True,'actual_domain_open':c['domain'],'no_monotonicity_claim':True}
(w/'range-readback-v2.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'relative_widths':widths,'contiguous_ranges':len(runs)}))
