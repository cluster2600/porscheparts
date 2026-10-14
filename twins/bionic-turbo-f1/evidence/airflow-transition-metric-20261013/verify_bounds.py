"""Check derived interval endpoints against direct triangle-centre geometry."""
import json,math,hashlib
from pathlib import Path
import numpy as np
w=Path(__file__).parent;t=math.tan(math.radians(70));rows=[]
for s in (0.,.5,-.5,3*t):
 k=3*t-abs(s);root=math.sqrt(k*k+8*(1+s*s));lo=2*(1+s*s)/(root+k);hi=(root+k)/4
 for role,r in [('lower',lo),('upper',hi)]:
  p={name:np.array([x+s*z,z]) for name,x,z in [('A',0,0),('B',0,1),('D',r,0),('M',r,.5),('C',r,1)]}
  centres=[sum((p[x] for x in keys))/3 for keys in [('A','B','M'),('A','M','D'),('B','C','M')]];angles=[]
  for other,a,b in [(1,'A','M'),(2,'M','B')]:
   edge=p[b]-p[a];delta=centres[other]-centres[0];normal=abs(edge[0]*delta[1]-edge[1]*delta[0]);tangent=abs(float(edge@delta));angles.append(math.degrees(math.atan2(tangent,normal)))
  assert abs(max(angles)-70)<1e-10
  rows.append({'shear':s,'endpoint':role,'dimensionless_ratio':r,'direct_angles_deg':angles})
# A negative K makes |2r²-(1+s²)| <= K*r impossible for every r>0.
assert 3*t-abs(4*t)<0
out={'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'checks':rows,'max_boundary_error_deg':max(abs(max(r['direct_angles_deg'])-70) for r in rows),'negative_K_excluded_algebraically':True,'candidate_created':False,'collar_subdivision_selected':False}
(w/'bounds-readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
