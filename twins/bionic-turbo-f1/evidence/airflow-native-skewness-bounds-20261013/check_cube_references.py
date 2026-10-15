"""Additional consistent cubes; run after primary start, before full reader."""
import hashlib,json,runpy,time
from fractions import Fraction as F
from pathlib import Path
W=Path(__file__).parent
T=((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))
out={}
for name in ('check_skewness.py','verify_skewness.py'):
 m=runpy.run_path(str(W/name));R=m.get('I',m.get('R'));Q=m['Q'];native=m['h'];results=[]
 for s in (F(1),F(1,1000),F(1,1000000)):
  cells=[]
  for shift in (0,1):
   points=[[R(s*(x+shift)),R(s*y),R(s*z)] for x,y,z in ((0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1))]
   faces=[[points[i] for i in f] for f in T]
   if name.startswith('check_'):geo=[native.face(p) for p in faces];centre,volume=native.cell(geo)
   else:centre,volume,geo=native.moments(faces)
   assert F(volume.lo,Q)<=s**3<=F(volume.hi,Q);cells.append((centre,geo,faces))
  cf,area=cells[0][1][3]
  for boundary in (False,True):
   fn=m.get('skew',m.get('evaluate_skew'));data=fn(cf,area,cells[0][0],None if boundary else cells[1][0],cells[0][2][3]);d=s/2 if boundary else s;r=m['S'];alpha=F(float('0.4' if boundary else '0.2'))
   expected=(s*r/2)/((s*s*d+r)*(alpha*d+r));assert F(data[-2],Q)<=expected<=F(data[-1],Q)
   results.append({'scale':str(s),'boundary':boundary,'expected':str(expected),'bounded':True})
 out[name]=results
out={'source_sha256':hashlib.file_digest(Path(__file__).open('rb'),'sha256').hexdigest(),'executed_after_primary_start':True,'results':out,'turbo_domain_evaluated':False,'time_unix':time.time()}
(W/'cube-reference-readback.json').write_text(json.dumps(out,indent=2)+'\n');print('12 additional consistent-cube references passed; after primary start')
