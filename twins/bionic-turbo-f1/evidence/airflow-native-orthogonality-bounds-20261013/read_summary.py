"""Structural coverage and extrema only, no new geometric reconstruction."""
import gzip,hashlib,json
from collections import Counter
from fractions import Fraction as F
from pathlib import Path
W=Path(__file__).parent
report=json.loads((W/'readback.json').read_text());ind=json.loads((W/'independent-readback.json').read_text())
assert ind['all_output_bounds_contained'] and ind['all_claimed_signs_confirmed']
with (W/'readback.json').open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==ind['primary_readback_sha256']
boxes=json.loads(Path('work/bionic-angular-independent-bounds-20261013/certificate-readback.json').read_text())['box_results'];ids=[r['parent_leaf'] for r in boxes];expected=[('matrix',leaf,rank) for leaf in ids for rank in range(9470)]+[('witness',leaf,rank) for leaf in ids for rank in range(2)]+[('constant','envelope',rank) for rank in range(4224)]
counts=Counter();per={leaf:Counter() for leaf in ids};constant=Counter();minimum=None;unknown_minimum=None;rows=0
with gzip.open(W/'orthogonality-bounds.jsonl.gz','rt') as stream:
 for expectation,line in zip(expected,stream,strict=True):
  category,leaf,rank,data,status=json.loads(line);assert tuple((category,leaf,rank))==expectation
  assert len(data)==2 and data[0]<=data[1] and status in ('positive','unknown','refused');rows+=1;counts[category+':'+status]+=1
  if category=='constant':constant[status]+=1
  else:per[leaf][status]+=1
  entry={'category':category,'domain':leaf,'rank':rank,'lower':str(F(data[0],1<<160)),'upper':str(F(data[1],1<<160))}
  if status=='positive' and (minimum is None or F(entry['lower'])<F(minimum['lower'])):minimum=entry
  if status=='unknown' and (unknown_minimum is None or F(entry['lower'])<F(unknown_minimum['lower'])):unknown_minimum=entry
coverage=[]
for leaf in ids:
 assert sum(per[leaf].values())==9472
 c=per[leaf]+constant;c['positive']+=4864;assert sum(c.values())==18560
 coverage.append({'parent_leaf':leaf,'counts':dict(c),'all_mathematical_orthogonality_bounds_positive':c['positive']==18560})
assert rows==report['records']==ind['records_verified']
result={'structural_only':True,'records':rows,'category_counts':dict(counts),'constant_counts':dict(constant),'source_boxes':153,'faces_per_box':18560,'coverage':coverage,'all_positive_boxes':[r['parent_leaf'] for r in coverage if r['all_mathematical_orthogonality_bounds_positive']],'minimum_positive_certificate':minimum,'minimum_unknown_certificate':unknown_minimum,'domain_v':report['domain_v'],'native_admission':False,'third_geometric_reconstruction':False}
with (W/'summary.json').open('x') as stream:stream.write(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('coverage','all_positive_boxes')}));print('all positive boxes',result['all_positive_boxes'])
