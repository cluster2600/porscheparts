"""Structural coverage/minimum readback; not another geometric reconstruction."""
import gzip,hashlib,json
from pathlib import Path
from fractions import Fraction as F
from collections import Counter
W=Path(__file__).parent
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def main():
 report=json.loads((W/'readback.json').read_text());verified=json.loads((W/'independent-readback.json').read_text());assert sha(W/'readback.json')==verified['primary_readback_sha256'] and verified['independent_bounds_contained']
 assert sha(W/'flatness-bounds.jsonl.gz')==report['bounds_sha256'];counts=Counter();hull_positive=set();hull_unknown=set();local=Counter();minima={};rows=0
 with gzip.open(W/'flatness-bounds.jsonl.gz','rt') as stream:
  for line in stream:
   r=json.loads(line);rows+=1;counts[r['status']]+=1
   if r['domain']=='envelope':
    (hull_positive if r['status']=='positive' else hull_unknown).add(r['rank'])
   else:local[r['domain']]+=r['status']=='positive'
   if r['status']=='positive':
    for key,pair in r['bounds'].items():
     lo=F(pair[0])
     if key not in minima or lo<F(minima[key]['lower']):minima[key]={'lower':str(lo),'domain':r['domain'],'rank':r['rank']}
 assert rows==verified['face_records_verified'] and hull_positive.isdisjoint(hull_unknown) and len(hull_positive|hull_unknown)==18560 and len(hull_positive)==report['envelope_positive'] and len(hull_unknown)==report['envelope_unknown']
 boxes=json.loads(Path('work/bionic-angular-independent-bounds-20261013/certificate-readback.json').read_text())['box_results'];coverage=[{'parent_leaf':b['parent_leaf'],'lower':b['lower'],'upper':b['upper'],'positive_faces':len(hull_positive)+local[b['parent_leaf']],'flatness_all_faces_positive':len(hull_positive)+local[b['parent_leaf']]==18560,'native_admission':False} for b in boxes];assert all(r['flatness_all_faces_positive'] for r in coverage)
 guards=json.loads((W/'guards.json').read_text());assert len(guards)==verified['guard_cells_verified'] and all(r['determinant_guard_inactive'] and r['volume_guard_inactive'] for r in guards)
 out={'source_sha256':sha(Path(__file__)),'bounds_sha256':report['bounds_sha256'],'independent_readback_sha256':sha(W/'independent-readback.json'),'structural_readback_only':True,'face_records':rows,'counts':dict(counts),'minimum_positive_record_bounds':minima,'minimum_internal_area_sum':str(min(F(r['E'][0]) for r in guards)),'minimum_triple_volume':str(min(F(r['triple_volume'][0]) for r in guards)),'box_results':coverage,'native_admission':False}
 (W/'summary.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='box_results'}))
if __name__=='__main__':main()
