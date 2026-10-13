"""Structural sum of independently verified polynomial certificates; no new geometry evaluation."""
import gzip,hashlib,json
from fractions import Fraction as F
from pathlib import Path
w=Path(__file__).parent
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
r=json.loads((w/'readback.json').read_text());v=json.loads((w/'independent-readback.json').read_text())
assert sha(w/'models.jsonl.gz')==r['models_sha256']==v['models_sha256']
sums={};n=0
with gzip.open(w/'models.jsonl.gz','rt') as stream:
 for line in stream:
  x=json.loads(line)
  if x['kind']=='cell':
   n+=1;assert list(map(F,x['fan_minus_native_volume_bound']))==[0,0]
   for k,c in enumerate(x['fan_signed_volume']['polynomial']):sums[k]=sums.get(k,F(0))+F(c)
assert n==6144 and all(x==0 for k,x in sums.items() if k)
result=dict(source_sha256=sha(Path(__file__)),models_sha256=r['models_sha256'],independent_readback_sha256=sha(w/'independent-readback.json'),cells=n,all_native_volume_error_bounds_exactly_zero=True,total_fan_and_mathematical_native_volume=str(sums[0]),total_volume_constant=True,total_volume_m3_approx=float(sums[0]),minimum_six_volume_m3_approx=float(F(r['minimum_six_volume_bound'])),minimum_cell_volume_m3_approx=float(F(r['minimum_cell_fan_volume_bound'])),structural_read_only=True,nonintersection_proved=False)
(w/'totals-readback.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
