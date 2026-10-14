"""Exact polygonal-wedge moments checked on existing archived axial prisms."""
import ast,json,csv,math,hashlib
from pathlib import Path
import numpy as np
w=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();src=Path('work/bionic-buffered-transition-20261013');s=json.loads((src/'construction.json').read_text());assert sha(src/'construction.json')=='ddda1839b41b7dfde9b7303d90f47e35c0ac35726f1db1278117366de71eb9e4'
for r in json.loads(Path('work/bionic-airflow-delivery-20261013-buffered-transition/file-manifest.json').read_text())['files']:assert sha(Path('work')/r['path'])==r['sha256']
helper=Path('twins/bionic-turbo-f1/evidence/airflow-conformal-local-design-20261013/verify_pyramids.py');assert sha(helper)=='673f80a53bd03dba18820fa060c51e4cea75c660a6e546a8cda6c1e394be6c2a';a=ast.parse(helper.read_text());exec(compile(ast.Module(body=[n for n in a.body if isinstance(n,ast.FunctionDef) and n.name in ('polygon','metrics')],type_ignores=[]),str(helper),'exec'))
p=np.array(s['vertices']);analytic={};polys={};errors=[];verrors=[]
for i,b in enumerate(s['blocks']):
 if s['stages'][i]!='axial':continue
 lo=b[:3];hi=b[4:7];r=np.linalg.norm(p[lo,:2],axis=1);z=p[lo,2];assert np.max(abs(np.linalg.norm(p[hi,:2],axis=1)-r))<1e-16 and np.max(abs(p[hi,2]-z))==0
 u=p[lo,:2]/r[:,None];v=p[hi,:2]/r[:,None];assert np.max(abs(u-u[0]))<1e-14 and np.max(abs(v-v[0]))<1e-14
 bis=u[0]+v[0];coshalf=np.linalg.norm(bis)/2;direction=bis/np.linalg.norm(bis);sums=float(sum(r));second=float(sum(r*r)+r[0]*r[1]+r[0]*r[2]+r[1]*r[2]);rho=coshalf*second/(2*sums);zc=(sums*sum(z)+float(r@z))/(4*sums);centre=np.array([*(rho*direction),zc])
 area=abs(float(np.linalg.det(np.column_stack((r[1:]-r[0],z[1:]-z[0])))))/2;sinangle=float(u[0,0]*v[0,1]-u[0,1]*v[0,0]);volume=sinangle*area*sums/3;assert volume>0
 f=[lo[::-1],hi]+[[lo[j],lo[(j+1)%3],hi[(j+1)%3],hi[j]] for j in range(3)];nativec,nativev,_=metrics([[p[k] for k in face] for face in f]);errors.append(float(np.linalg.norm(centre-nativec)));verrors.append(abs(volume/nativev-1));analytic[i]=centre;polys[i]=f
assert len(analytic)==2304 and max(errors)<1e-15 and max(verrors)<1e-11
rows=[]
for rec in csv.DictReader((src/'angles.csv').open()):
 a,b=int(rec['owner']),int(rec['neighbour'])
 if a not in analytic or b not in analytic:continue
 f=[f for f in polys[a] if any(set(f)==set(g) for g in polys[b])];assert len(f)==1;_,sf=polygon([p[k] for k in f[0]]);d=analytic[b]-analytic[a];angle=math.degrees(math.atan2(float(np.linalg.norm(np.cross(d,sf))),float(d@sf)));rows.append((a,b,angle,float(rec['angle_deg'])))
assert max(abs(x-y) for a,b,x,y in rows)<1e-9
out={'source_sha256':sha(Path(__file__)),'construction_sha256':sha(src/'construction.json'),'all_source_payloads_verified':True,'axial_prisms':len(analytic),'max_centre_difference_m':max(errors),'max_volume_relative_difference':max(verrors),'axial_shared_faces':len(rows),'max_angle_difference_deg':max(abs(x-y) for a,b,x,y in rows),'maximum_angle_deg':max(x for a,b,x,y in rows),'faces_over_70':sum(x>70 for a,b,x,y in rows),'new_mesh_created':False,'native_executed':False,'scope':'Straight polygonal angular extrusion of meridional triangles only; not warped faces or general blade cells.'}
(w/'angular-readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
