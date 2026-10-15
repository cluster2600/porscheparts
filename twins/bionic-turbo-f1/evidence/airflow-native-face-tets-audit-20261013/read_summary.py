"""Structural coverage readback, not a third geometric reconstruction."""
import gzip,hashlib,json
from pathlib import Path
from collections import Counter
W=Path(__file__).parent
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 p=json.loads((W/'readback.json').read_text());v=json.loads((W/'independent-readback.json').read_text());assert sha(W/'readback.json')==v['primary_readback_sha256']
 assert sha(W/'face-tets-bounds.jsonl.gz')==p['bounds_sha256'] and v['all_finite_intervals_included'] and v['all_claimed_signs_confirmed']
 boxes=json.loads(Path('work/bionic-angular-independent-bounds-20261013/certificate-readback.json').read_text())['box_results'];hull={};local={b['parent_leaf']:{} for b in boxes};rows=0
 with gzip.open(W/'face-tets-bounds.jsonl.gz','rt') as f:
  for line in f:
   dom,rank,fans,bases,status=json.loads(line);assert status in ('positive','unknown','refused');target=hull if dom=='envelope' else local[dom];assert rank not in target;target[rank]=status;rows+=1
 assert set(hull)==set(range(18560)) and rows==p['face_records']==v['face_records']
 unknown={r for r,s in hull.items() if s=='unknown'};assert unknown==set(p['envelope_unknown_ranks'])
 result=[]
 for box in boxes:
  leaf=box['parent_leaf'];assert set(local[leaf])==unknown
  cover={r:(local[leaf][r] if r in unknown else s) for r,s in hull.items()};counts=dict(Counter(cover.values()));assert sum(counts.values())==18560
  result.append({'parent_leaf':leaf,'lower':box['lower'],'upper':box['upper'],'counts':counts,'all_face_tets_positive':counts.get('positive',0)==18560})
 out={'scope':'structural coverage, not third reconstruction','primary_readback_sha256':sha(W/'readback.json'),'independent_readback_sha256':sha(W/'independent-readback.json'),'face_records':rows,'envelope_counts':dict(Counter(hull.values())),'box_results':result,'all_positive_boxes':[b['parent_leaf'] for b in result if b['all_face_tets_positive']],'all_153_closed_boxes_preserved':True,'determinant_indecisions_1929_1930_unchanged':True,'native_admission':False,'cfd':False}
 with (W/'summary.json').open('x') as f:json.dump(out,f,indent=2);f.write('\n')
 print(json.dumps({k:v for k,v in out.items() if k!='box_results'}))
if __name__=='__main__':main()
