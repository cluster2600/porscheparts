"""Pre-application arithmetic and geometrically consistent cube references."""
import hashlib,json,runpy,time
from pathlib import Path
from fractions import Fraction as F
W=Path(__file__).parent
T=((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))
results={}
for name in ('check_orthogonality.py','verify_orthogonality.py'):
 m=runpy.run_path(str(W/name));scale=m['SCALE'];root=m['ROOT'];rows=[]
 def contains(pair,value):assert F(pair[0],scale)<=value<=F(pair[1],scale)
 for d in (F(-3),F(0),F(3)):
  contains(m['evaluate']((d,d),(F(9),F(9))),d/(3+root));rows.append({'kind':'signed_formula','D':str(d),'Q':'9'})
 # Addition below the dyadic quantum is retained in exact denominators.
 contains(m['evaluate']((root,root),(root*root,root*root)),F(1,2));rows.append({'kind':'ROOT_scale_formula','expected':'1/2'})
 for x in (F(0),F(2),root*root,F(9,49)):
  lo,hi=m['root_bounds'](x);assert lo*lo<=x<=hi*hi;rows.append({'kind':'root_square_bracket','input':str(x)})
 assert m['quotient']((root,root),(2*root,2*root))==(scale//2,scale//2);rows.append({'kind':'exact_small_denominator','expected':'1/2'})
 q=m['recover_q']((F(2),F(2)),(F(1,4),F(1,4)),(F(1,4),F(1,4)));assert q==(F(8),F(8));rows.append({'kind':'witness_recovery','Q':'8'})
 try:m['quotient']((F(1),F(1)),(F(0),F(1)))
 except AssertionError:rows.append({'kind':'zero_denominator_rejected'})
 else:raise AssertionError('zero denominator accepted')
 C=m.get('I',m.get('R'));native=m['h']
 for side in (F(1),F(1,1000),F(1,1000000)):
  cells=[]
  for shift in (0,1):
   points=[[C(side*(x+shift)),C(side*y),C(side*z)] for x,y,z in ((0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1))]
   faces=[[points[i] for i in f] for f in T]
   if name.startswith('check_'):geo=[native.face(p) for p in faces];centre,volume=native.cell(geo)
   else:centre,volume,geo=native.moments(faces)
   contains((volume.lo,volume.hi),side**3)
   for axis,value in enumerate(centre):contains((value.lo,value.hi),side*(F(1,2)+(shift if axis==0 else 0)))
   area=geo[3][1]
   for axis,value in enumerate(area):contains((value.lo,value.hi),side**2 if axis==0 else F(0))
   cells.append((centre,area))
  d,q=m['native_dq'](cells[0][0],cells[1][0],cells[0][1]);assert d[0]<=side**3<=d[1] and q[0]<=side**6<=q[1]
  contains(m['evaluate'](d,q),side**3/(side**3+root));rows.append({'kind':'adjacent_coherent_cubes','side':str(side),'volume_centres_area_D_Q_checked':True})
 results[name]={'program_sha256':hashlib.sha256((W/name).read_bytes()).hexdigest(),'references':rows}
out={'executed_before_application':True,'turbo_domain_evaluated':False,'time_unix':time.time(),'results':results}
with (W/'reference-readback.json').open('x') as f:f.write(json.dumps(out,indent=2)+'\n')
print({name:len(r['references']) for name,r in results.items()})
