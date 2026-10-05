import json
from pathlib import Path
p=json.load(open('V2-edge-resolution-refinement.json'))
p['trigger']='Common sizing policy for R0 and V2: diagnosed repeated neighborhoods and the same native V2 short-edge centres; original CAD retained'
Path('common-grid-refinement.json').write_text(json.dumps(p,indent=2)+'\n')
f=json.loads(json.dumps(p));f['size_inside_m']*=.8
for ball in f['additional_balls']:ball['size_inside_m']*=.8
f['trigger']='Common sizing policy refined by 0.8 in global/local target size, fixed centres/radii, original CAD retained'
Path('common-grid-refinement-fine.json').write_text(json.dumps(f,indent=2)+'\n')
