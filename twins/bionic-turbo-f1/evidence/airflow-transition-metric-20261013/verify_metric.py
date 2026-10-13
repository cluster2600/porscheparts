"""Exact coefficient identities and independent Cartesian-prism geometry checks."""
import ast,json,hashlib,math
from fractions import Fraction as F
from pathlib import Path
import numpy as np
w=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=Path('work/bionic-airflow-delivery-20261013-buffered-transition/file-manifest.json')
for row in json.loads(manifest.read_text())['files']:
 p=Path('work')/row['path'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
# Exact sparse coefficients in W,H,s, only used to verify the displayed identities.
def add(*ps):
 out={}
 for p in ps:
  for e,c in p.items():out[e]=out.get(e,F(0))+c
 return {e:c for e,c in out.items() if c}
def scale(p,k):return {e:c*F(k) for e,c in p.items() if c*k}
def mul(p,q):
 out={}
 for a,x in p.items():
  for b,y in q.items():
   e=tuple(i+j for i,j in zip(a,b));out[e]=out.get(e,F(0))+x*y
 return {e:c for e,c in out.items() if c}
W={(1,0,0):F(1)};H={(0,1,0):F(1)};S={(0,0,1):F(1)}
WH=mul(W,H);SH=mul(S,H);HH=mul(H,H);WW=mul(W,W);SSHH=mul(mul(S,S),HH);SWH=mul(S,WH)
identities=[]
for sign in (-1,1):
 # Delta from central triangle to lower(-1) or upper(+1); tangent follows the shared diagonal.
 dx=scale(add(W,scale(SH,sign)),F(1,3));dy=scale(H,F(sign,3))
 tx=add(W,scale(SH,F(-sign,2)));ty=scale(H,F(-sign,2))
 nx=scale(H,F(1,2));ny=add(scale(W,sign),scale(SH,F(-1,2)))
 normal=add(mul(dx,nx),mul(dy,ny));tangent=add(mul(dx,tx),mul(dy,ty))
 expected=scale(add(scale(WW,2),scale(SWH,sign),scale(HH,-1),scale(SSHH,-1)),F(1,6))
 assert normal==scale(WH,F(1,2)) and tangent==expected
 identities.append({'side':sign,'normal_coefficients':{str(k):str(v) for k,v in normal.items()},'tangential_coefficients':{str(k):str(v) for k,v in tangent.items()}})
helper=Path('twins/bionic-turbo-f1/evidence/airflow-conformal-local-design-20261013/verify_pyramids.py');assert sha(helper)=='673f80a53bd03dba18820fa060c51e4cea75c660a6e546a8cda6c1e394be6c2a'
a=ast.parse(helper.read_text());exec(compile(ast.Module(body=[n for n in a.body if isinstance(n,ast.FunctionDef) and n.name in ('polygon','metrics')],type_ignores=[]),str(helper),'exec'))
def prism(poly,depth):
 # Section is x,z; extrusion is y. Clockwise x,z gives positive orientation along +y.
 lo=[np.array([x,0,z]) for x,z in poly];hi=[np.array([x,depth,z]) for x,z in poly]
 return [lo[::-1],hi]+[[lo[i],lo[(i+1)%3],hi[(i+1)%3],hi[i]] for i in range(3)]
checks=[]
# These are analytical invariance/reference tests, not candidate meshes or a design search.
for label,width,height,shear in [('rectangle',1,1,0),('orthogonal',1/math.sqrt(2),1,0),('shear_plus',1,1,.5),('shear_minus',1,1,-.5)]:
 for unit in (1.,1e-3,1e-6):
  width*=1 # retain the prescribed reference, never tune it from computed angles
  pts={k:(unit*(x+shear*z),unit*z) for k,(x,z) in {'A':(0,0),'B':(0,height),'D':(width,0),'M':(width,height/2),'C':(width,height)}.items()}
  pol=[['A','B','M'],['A','M','D'],['B','C','M']];geom=[prism([pts[k] for k in f],unit*2) for f in pol];records=[metrics(f) for f in geom];centres=[x[0] for x in records];assert all(x[1]>0 for x in records)
  measured=[];predicted=[]
  for other,edge,sign in [(1,['M','A'],-1),(2,['B','M'],1)]:
   face=[np.array([pts[k][0],y,pts[k][1]]) for k,y in [(edge[0],0),(edge[1],0),(edge[1],unit*2),(edge[0],unit*2)]];_,sf=polygon(face);delta=centres[other]-centres[0]
   if delta@sf<0:sf=-sf
   normal=float(delta@sf/np.linalg.norm(sf));tangent=float(np.linalg.norm(np.cross(delta,sf))/np.linalg.norm(sf));measured.append(tangent/normal)
   predicted.append(abs(2*width*width+sign*shear*width*height-(1+shear*shear)*height*height)/(3*width*height))
  err=max(abs(x-y) for x,y in zip(measured,predicted));assert err<1e-12
  for keys,(c,v,_) in zip(pol,records):
   expected=np.array([sum(pts[k][0] for k in keys)/3,unit,sum(pts[k][1] for k in keys)/3]);assert np.linalg.norm(c-expected)<unit*1e-12
  checks.append({'reference':label,'unit_scale':unit,'measured_tangents':measured,'analytic_tangents':predicted,'max_error':err})
out={'source_sha256':sha(Path(__file__)),'source_manifest_sha256':sha(manifest),'all_buffered_payloads_verified':True,'scalar_helper_sha256':sha(helper),'exact_coefficient_identities':identities,'cartesian_prism_checks':checks,'max_tangent_error':max(r['max_error'] for r in checks),'native_executed':False,'candidate_mesh_created':False,'collar_resolution_selected':False,'physical_dimensions_qualified':False}
(w/'readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
