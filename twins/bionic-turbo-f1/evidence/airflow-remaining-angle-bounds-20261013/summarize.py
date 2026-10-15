"""Summarize complete traversal and distinguish exclusion certificates from raw positive counts."""
import hashlib,json
from fractions import Fraction as F
from pathlib import Path
from collections import Counter
w=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
records=[json.loads(x) for x in (w/'records.jsonl').read_text().splitlines()];assert len(records)==159
report=json.loads((w/'readback.json').read_text());assert sha(w/'records.jsonl')==report['records_sha256']
order=json.loads((w/'order.json').read_text());counts=Counter();witnesses=Counter();parent_counts=Counter()
for r in records:
 counts.update(r['counts']);parent_counts[r['parent_status']]+=1
 if r['witness']:witnesses[str((r['witness']['choice']['owner'],r['witness']['choice']['neighbour']))]+=1
full_positive=[r for r in records if r['counts'].get('positive')==9470]
nonexcluded=[r for r in records if r['status']!='excluded'];uncertain=[r for r in nonexcluded if r['counts'].get('unknown',0)+r['counts'].get('singular',0)>0]
assert len(full_positive)+len(uncertain)==len(nonexcluded)
old=json.loads(Path('work/bionic-feasibility-bounds-20261013/certificate.json').read_text());u,end=map(F,old['domain'])
mid={r['parent_leaf']:r for r in json.loads(Path('work/bionic-gram-interval-bounds-20261013/refined-certificate.json').read_text())['rows']}
centre={r['parent_leaf']:r for r in json.loads(Path('work/bionic-centre-interval-bounds-20261013/centred-certificate.json').read_text())['rows']}
new={r['parent_leaf']:r for r in records};ranges=[];leaf_counts=Counter()
for i,oldrow in enumerate(old['leaves']):
 row=new.get(i,centre.get(i,mid.get(i,oldrow)));status='excluded' if row['status']=='excluded' else 'not_excluded'
 leaf_counts[status]+=1
 if ranges and ranges[-1]['status']==status:
  assert ranges[-1]['upper']==oldrow['lower'];ranges[-1]['upper']=oldrow['upper'];ranges[-1]['leaves']+=1
 else:ranges.append(dict(lower=oldrow['lower'],upper=oldrow['upper'],status=status,leaves=1))
assert ranges[0]['lower']==old['domain'][0] and ranges[-1]['upper']==old['domain'][1]
assert all(a['upper']==b['lower'] for a,b in zip(ranges,ranges[1:]))
widths={k:sum((F(r['upper'])-F(r['lower']) for r in ranges if r['status']==k),F(0))/(end-u) for k in leaf_counts};assert sum(widths.values())==1
out=dict(source_sha256=sha(Path(__file__)),records_sha256=sha(w/'records.jsonl'),scheduled_family_counts=dict(Counter(r['family'] for r in order)),evaluated_constraint_counts=dict(counts),total_constraints_evaluated=sum(counts.values()),exclusion_witness_counts=dict(witnesses),input_parent_statuses=dict(parent_counts),full_traversal_nonexcluded_boxes=len(nonexcluded),raw_all_remaining_angles_positive_boxes=len(full_positive),raw_prior_six_positive_and_remaining_angles_positive_boxes=sum(r['parent_status']=='selected_subset_only' for r in full_positive),raw_unknown_angle_boxes=len(uncertain),raw_positive_counts_not_independently_recomputed=True,combined_leaf_counts=dict(leaf_counts),combined_relative_widths={k:str(v) for k,v in widths.items()},ranges=ranges,solution_accepted=False)
(w/'summary.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
