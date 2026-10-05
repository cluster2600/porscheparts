import json,math
from pathlib import Path
p=json.load(open('common-grid-refinement-fine.json'));diagnosis=json.load(open('R0-fine-diagnosis/localized-diagnostic.json'))
for row in diagnosis['bad_cells']:
 x,y,z=[v*.001 for v in row['center_mm']]
 for k in range(9):
  angle=k*2*math.pi/9
  p['additional_balls'].append({'center_m':[x*math.cos(angle)-y*math.sin(angle),x*math.sin(angle)+y*math.cos(angle),z],'radius_m':.00018,'transition_m':.0007,'size_inside_m':.00002,'trigger_bad_cell':row['cell'],'exact_blade_symmetry_index':k})
p['trigger']='Common fine-grid recovery: 27 symmetric neighborhoods from independently diagnosed three rejected R0 fine cells; global target 5.6mm unchanged and original CAD retained'
p['diagnostic_source_mesh_sha256']=diagnosis['source_mesh_sha256']
Path('common-grid-refinement-fine-repair1.json').write_text(json.dumps(p,indent=2)+'\n')
print('27 symmetric local balls added; CAD and QA thresholds retained')
