"""Combine recorded necessary constraints without upgrading them to admission."""
import hashlib,json
from fractions import Fraction as F
from pathlib import Path
from collections import Counter
w=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
boxes=json.loads((w/'boxes.json').read_text());ids=[r['parent_leaf'] for r in boxes];states={i:dict(determinants=Counter(),unknown_determinant_cells=[],planes=Counter(),volumes=Counter()) for i in ids}
prior=json.loads(Path('work/bionic-gram-interval-bounds-20261013/refined-certificate.json').read_text());priorrows={r['parent_leaf']:r for r in prior['rows']};choices=json.loads(Path('work/bionic-feasibility-bounds-20261013/certificate.json').read_text())['selected'][2:]
for box in boxes:
 row=priorrows[box['parent_leaf']];assert (row['lower'],row['upper'])==(box['lower'],box['upper'])
 for choice,result in zip(choices,row['determinants'],strict=True):
  states[box['parent_leaf']]['determinants'][result['status']]+=1
  if result['status']=='unknown':states[box['parent_leaf']]['unknown_determinant_cells'].append(choice['cell'])
for line in (w/'bounds.jsonl').open():
 row=json.loads(line);local={r['parent_leaf']:r for r in row['local']}
 for i in ids:
  item=row['hull'] if row['hull']['status']!='unknown' else local[i];states[i]['determinants'][item['status']]+=1
  if item['status']=='unknown':states[i]['unknown_determinant_cells'].append(row['cell'])
for line in (w/'planes-bounds.jsonl').open():
 row=json.loads(line);local={r['parent_leaf']:r for r in row['local']}
 for i in ids:
  item=row['hull'] if row['hull']['status']!='unknown' else local[i]
  for pair in item['pairs']:states[i]['planes'][pair['status']]+=1
  V=list(map(F,item['volume']));states[i]['volumes']['positive' if V[0]>0 else ('excluded' if V[1]<=0 else 'unknown')]+=1
for i,v in states.items():
 assert sum(v['determinants'].values())==3840 and sum(v['planes'].values())==92160 and sum(v['volumes'].values())==3840
 v['unknown_determinant_cells'].sort()
allpass=sum(v['determinants']=={'selected_pass':3840} for v in states.values())
planespass=sum(v['planes']=={'positive':92160} for v in states.values());volpass=sum(v['volumes']=={'positive':3840} for v in states.values())
out=dict(source_sha256=sha(Path(__file__)),boxes_sha256=sha(w/'boxes.json'),determinant_certificate_sha256=sha(w/'bounds.jsonl'),plane_certificate_sha256=sha(w/'planes-bounds.jsonl'),all_variable_determinants_positive_boxes=allpass,all_variable_planes_positive_boxes=planespass,all_variable_volumes_positive_boxes=volpass,box_results=states,new_excluded_boxes=0,combined_excluded_width='3943/4096',remaining_width='153/4096',angular_positive_bounds_not_all_independently_verified=True,geometric_obligations_unresolved=True,solution_accepted=False)
(w/'summary.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='box_results'}))
