"""Structural coverage/maximum readback; not a third geometric reconstruction."""
import gzip,json,hashlib
from pathlib import Path
from fractions import Fraction as F
from collections import Counter
W=Path(__file__).parent
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def main():
 r=json.loads((W/'readback.json').read_text());v=json.loads((W/'independent-readback.json').read_text());assert v['primary_readback_sha256']==sha(W/'readback.json') and v['all_bounds_contained'] and v['all_claimed_signs_confirmed']
 assert sha(W/'skewness-bounds.jsonl.gz')==r['bounds_sha256'];counts=Counter();maximum=None;where=None;hull={};local={};records=0
 with gzip.open(W/'skewness-bounds.jsonl.gz','rt') as stream:
  for line in stream:
   dom,rank,bounds,status=json.loads(line);records+=1;counts[str(dom)+':'+status]+=1
   target=hull if dom=='envelope' else local.setdefault(dom,{})
   assert rank not in target;target[rank]=status
   if status=='positive' and (maximum is None or bounds[-1]>maximum):maximum=bounds[-1];where={'domain':dom,'rank':rank}
 assert len(hull)==18560 and dict(counts)==r['counts'] and records==r['records']==v['records_verified'];assert str(F(maximum,2**160))==r['maximum_positive_upper']
 unknown={rank for rank,status in hull.items() if status=='unknown'};boxes=json.loads(Path('work/bionic-angular-independent-bounds-20261013/certificate-readback.json').read_text())['box_results'];results=[]
 assert set(local)==({b['parent_leaf'] for b in boxes} if unknown else set())
 for box in boxes:
  leaf=box['parent_leaf'];loc=local.get(leaf,{})
  assert set(loc)==unknown
  c=Counter(loc.values());c.update(status for status in hull.values() if status!='unknown')
  assert sum(c.values())==18560;results.append({'parent_leaf':leaf,'counts':dict(c),'all_skewness_positive':c['positive']==18560})
 out={'primary_readback_sha256':sha(W/'readback.json'),'independent_readback_sha256':sha(W/'independent-readback.json'),'records':records,'envelope_counts':dict(Counter(hull.values())),'local_counts':dict(Counter(s for rows in local.values() for s in rows.values())),'maximum_positive_upper':str(F(maximum,2**160)),'maximum_location':where,'boxes':results,'all_boxes_skewness_positive':all(x['all_skewness_positive'] for x in results),'structural_readback_only':True,'native_admission':False}
 (W/'summary.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='boxes'}))
if __name__=='__main__':main()
