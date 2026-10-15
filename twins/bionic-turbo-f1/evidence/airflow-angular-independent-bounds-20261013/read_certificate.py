"""Structural and sign readback of the new complete independent certificate, not a second geometry replay."""
import gzip,hashlib,json
from pathlib import Path
from fractions import Fraction as F
from collections import Counter
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 w=Path(__file__).parent;r=json.loads((w/'readback.json').read_text())
 for name,key in [('verify_angles.py','source_sha256'),('preflight.md','preflight_sha256'),('angular-bounds.jsonl.gz','bounds_sha256'),('records.json','records_sha256'),('boxes.json','boxes_sha256'),('order.json','order_sha256')]:assert sha(w/name)==r[key]
 boxes=json.loads((w/'boxes.json').read_text());records=json.loads((w/'records.json').read_text());assert len(boxes)==len(records)==153
 counts={b['parent_leaf']:Counter() for b in boxes};total=0
 with gzip.open(w/'angular-bounds.jsonl.gz','rt') as stream:
  for total,line in enumerate(stream,1):
   leaf,rank,dl,dh,ql,qh,rl,rh=json.loads(line);j,i=divmod(total-1,9470)
   assert j<len(boxes) and leaf==boxes[j]['parent_leaf'] and rank==i
   assert dl<=dh and 0<ql<=qh and rl<=rh
   status='positive' if dl>0 and rl>=0 else 'excluded' if dh<=0 or rh<0 else 'unknown'
   counts[leaf][status]+=1
 assert total==153*9470==r['angular_evaluations']
 summed=Counter();differences=[]
 for row in records:
  leaf=row['parent_leaf'];assert dict(counts[leaf])==row['counts'];summed.update(counts[leaf])
  assert row['all_positive']==(counts[leaf]['positive']==9470)
  if counts[leaf]!=Counter(row['primary_counts']):differences.append(dict(parent_leaf=leaf,primary=row['primary_counts'],independent=row['counts']))
 assert dict(summed)==r['counts']
 old=Path('work/bionic-centre-interval-bounds-20261013/centred-certificate.json');oldrows={x['parent_leaf']:x for x in json.loads(old.read_text())['rows']}
 cellpath=Path('work/bionic-remaining-cell-bounds-20261013/summary.json');cells=json.loads(cellpath.read_text())['box_results']
 result=[]
 for box,row in zip(boxes,records):
  leaf=box['parent_leaf'];oldrow=oldrows[leaf];assert (oldrow['lower'],oldrow['upper'])==(box['lower'],box['upper'])
  old_angles_positive=all(F(x['combined']['D'][0])>0 and F(x['combined']['residual'][0])>=0 for x in oldrow['angles'])
  cc=cells[str(leaf)];assert sum(cc['determinants'].values())==3840 and cc['planes']=={'positive':92160} and cc['volumes']=={'positive':3840}
  all_angles=row['all_positive'] and old_angles_positive
  necessary=all_angles and cc['determinants'].get('selected_pass',0)==3840
  result.append(dict(**box,all_9470_new_angles_positive=row['all_positive'],two_inherited_angles_positive=old_angles_positive,all_9472_variable_angles_positive=all_angles,all_variable_cell_predicates_positive=cc['determinants'].get('selected_pass',0)==3840,all_variable_necessary_predicates_positive=necessary))
 out=dict(source_sha256=sha(Path(__file__)),evaluation_readback_sha256=sha(w/'readback.json'),bounds_sha256=r['bounds_sha256'],records_read=total,counts=dict(summed),primary_count_differences=differences,all_primary_positive_boxes_confirmed=r['primary_all_positive_boxes_confirmed'],complete_independent_geometry_replay='verify_angles.py only; this reader checks inventory and signs',inherited_angles_certificate_sha256=sha(old),inherited_cell_summary_sha256=sha(cellpath),all_variable_angles_positive_boxes=sum(x['all_9472_variable_angles_positive'] for x in result),all_variable_necessary_predicates_positive_boxes=sum(x['all_variable_necessary_predicates_positive'] for x in result),box_results=result,remaining_relative_width=str(F(153-r['new_excluded_boxes'],4096)),excluded_relative_width=str(F(3943+r['new_excluded_boxes'],4096)),solution_accepted=False,native_executed=False)
 (w/'certificate-readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ('box_results','primary_count_differences')}))
if __name__=='__main__':main()
