"""Pre-application references; arithmetic tests are distinct from geometry."""
import hashlib,json,math,runpy,time,traceback
from pathlib import Path
from fractions import Fraction as F
W=Path(__file__).parent
T=((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))
results={}
for name in ('quality_primary.py','quality_independent_v2.py'):
 m=runpy.run_path(str(W/name));C=m.get('I',m.get('R'));pair=m['pair'];native=m['h'];Q=m['Q'];root=m['ROOT'];rows=[]
 def contains(value,expected):
  lo,hi=pair(value);assert lo<=expected<=hi,(name,str(lo),str(expected),str(hi))
 for side in (F(1),F(1,1000),F(1,1000000)):
  coords=[(0,0,0),(1,0,0),(0,1,0),(0,0,1)]
  points=[[C(side*x) for x in p] for p in coords]
  for inverted in (False,True):
   ps=points if not inverted else [points[0],points[2],points[1],points[3]]
   values,branch=m['quality'](ps);assert branch=='regular'
   den,volume,radius,q=values;sign=-1 if inverted else 1
   contains(volume,sign*side**3/6);a,b=pair(radius);assert a>=0 and a*a<=3*side*side/4<=b*b
   contains(q,sign*(side**3/6)/(side**3/3+root))
   rows.append({'kind':'coherent_right_tetrahedron','side':str(side),'inverted':inverted,'volume_radius_quality_checked':True})
  cells=[]
  for shift in (0,1):
   pts=[[C(side*(x+shift)),C(side*y),C(side*z)] for x,y,z in ((0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1))]
   faces=[[pts[i] for i in face] for face in T]
   if name=='quality_primary.py':geo=[native.face(p) for p in faces];centre,vol=native.cell(geo)
   else:centre,vol,geo=native.moments(faces)
   contains(vol,side**3)
   for axis,x in enumerate(centre):contains(x,side*(F(1,2)+(shift if axis==0 else 0)))
   cells.append((centre,geo,faces))
  own,geo,faces=cells[0];nei=cells[1][0];cf,area=geo[3];face=faces[3]
  for axis,x in enumerate(area):contains(x,side*side if axis==0 else F(0))
  for j in range(4):
   p,n=face[j],face[(j+1)%4]
   a,branch=m['quality']([p,n,cf,own]);assert branch=='regular';lo,hi=pair(a[-1]);assert m['classify']((-hi,-lo))=='positive'
   a,branch=m['quality']([p,n,cf,nei]);assert branch=='regular' and m['classify'](pair(a[-1]))=='positive'
  for base in range(4):
   for j in (1,2):
    a=face[(base+j)%4];b=face[(base+j+1)%4]
    for points in ([own,face[base],a,b],[nei,face[base],b,a]):
     values,branch=m['quality'](points);assert branch=='regular' and m['classify'](pair(values[-1]),strict=True)=='positive'
  rows.append({'kind':'adjacent_coherent_cubes','side':str(side),'fan_tets':8,'base_tets':16,'native_volume_centres_area_checked':True})
 # Exactly coplanar geometry, not an arbitrary supplied area.
 values,branch=m['quality']([[C(x),C(y),C(0)] for x,y in ((0,0),(1,0),(0,1),(1,1))]);assert branch=='degenerate';contains(values[1],F(0));assert pair(values[2])==(m['GREAT'],m['GREAT']) and pair(values[3])==(F(0),F(0));rows.append({'kind':'coherent_coplanar_tetrahedron'})
 for a,b,expected in [(root/2,root/2,'degenerate'),(root,root,'regular'),(-root,-root,'regular'),(-2*root,2*root,'unknown')]:
  assert m['guard'](a,b)==expected;rows.append({'kind':'guard_function','lower':str(a),'upper':str(b),'expected':expected})
 assert pair(m['ratio'](C(0),C(0),root))==(F(0),F(0));rows.append({'kind':'exact_additive_zero_denominator_function'})
 contains(m['divide'](root,root,2*root,2*root),F(1,2));rows.append({'kind':'tiny_exact_quotient_function'})
 g=m['GREAT'];assert pair(m['clipped_radius'](m['interval'](g-1,g+1)))==(g-1,g);rows.append({'kind':'radius_clamp_function'})
 assert m['classify']((F(1),F(1)),tol=(F(1),F(1)))=='positive'
 assert m['classify']((F(1),F(1)),strict=True,tol=(F(1),F(1)))=='refused'
 assert m['classify']((F(0),F(2)),strict=True,tol=(F(1),F(1)))=='unknown';rows.append({'kind':'strict_and_nonstrict_comparison_function'})
 rn=float(m['TOL_REAL']);a=(F(math.nextafter(rn,-math.inf))+F(rn))/2;b=(F(math.nextafter(rn,math.inf))+F(rn))/2
 assert a<m['TOL_REAL']<b and m['TOL_RN']==F(rn);rows.append({'kind':'exact_midpoints_confirm_binary64_round_to_nearest_square','real':str(m['TOL_REAL']),'rounded':str(m['TOL_RN']),'tol_interval':list(map(str,m['TOL']))})
 results[name]={'sha256':hashlib.sha256((W/name).read_bytes()).hexdigest(),'references':rows}
out={'time_unix':time.time(),'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'before_turbo_application':True,'turbo_geometry_evaluated':False,'results':results}
with (W/'quality-reference-readback-v2.json').open('x') as stream:stream.write(json.dumps(out,indent=2)+'\n')
print({name:len(row['references']) for name,row in results.items()})
