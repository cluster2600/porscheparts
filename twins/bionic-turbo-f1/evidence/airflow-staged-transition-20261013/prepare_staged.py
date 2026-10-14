"""One parameter-free staged transition design derived from a recorded source interval."""
import json,sys,math
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from frame_balance_batches import geometry
w=Path(__file__).parent;source=Path('work/bionic-airflow-20261012/full-collar-063');r=json.loads((source/'report.json').read_text());assert all(sha(source/k)==v for k,v in r['output_sha256'].items())
spec=json.loads((source/'construction.json').read_text());audit=json.loads(Path('twins/bionic-turbo-f1/evidence/airflow-castellation-transition-audit-20261013/readback.json').read_text())['reports'][-1];target=audit['worst_face']['face_centre_m'][2] if 'face_centre_m' in audit['worst_face'] else .031518768909020604
# Face centre is independently read from the archived native face, not tuned.
from audit_diagnostic import ascii_list
from run_case import ascii_faces
case=Path('work/bionic-airflow-20261012/regional-castellation-fixed-091');rec=json.loads((case/'report.json').read_text());assert all(sha(case/k)==v for k,v in rec['output_sha256'].items());m=case/'2.6e-06/polyMesh';points=ascii_list((m/'points').read_text(),True);faces=list(ascii_faces((m/'faces').read_text()));cf,_,_=geometry(points[np.array(faces[audit['worst_face']['label']])][None,:,:]);target=float(cf[0,2])
z=spec['stations_m'];k=next(i for i in range(len(z)-1) if z[i]<target<z[i+1]);assert 0<k<len(z)-2;indices=list(range(k-1,k+3));stations=np.array(z)[indices];radii=np.array(spec['radii_m'])[indices];qi,_,qo=spec['radial_ratios'];qm=(1+qo)/2;ratios=[qi,1,qm,qo]
zs=[];rs=[]
for i in range(3):zs.extend([float(stations[i]),float((stations[i]+stations[i+1])/2)]);rs.extend([float(radii[i]),float((radii[i]+radii[i+1])/2)])
zs.append(float(stations[-1]));rs.append(float(radii[-1]));vertices=[];lookup={}
def v(ring,theta,iz):
 key=(ring,theta%256,iz)
 if key not in lookup:
  angle=2*math.pi*(theta%256)/256;lookup[key]=len(vertices);vertices.append([(ratios[ring]*math.cos(angle))*rs[iz],(ratios[ring]*math.sin(angle))*rs[iz],zs[iz]])
 return lookup[key]
blocks=[];zones=[];stages=[]
def prism(lo,hi,stage):blocks.append(lo+[lo[-1]]+hi+[hi[-1]]);zones.append(stage=='rotor');stages.append(stage)
for j in range(3):
 loz=2*j;hiz=loz+2
 for i in range(128):
  t=2*i;a=(1,t);b=(1,t+2);d=(0,t);mid=(0,t+1);c=(0,t+2)
  for poly in ((a,b,mid),(a,mid,d),(b,c,mid)):prism([v(*x,loz) for x in poly],[v(*x,hiz) for x in poly],'rotor')
  a=(1,t);b=(1,t+2);d=(2,t);mid=(2,t+1);c=(2,t+2)
  for poly in ((a,mid,b),(a,d,mid),(b,mid,c)):prism([v(*x,loz) for x in poly],[v(*x,hiz) for x in poly],'angular')
 for t in range(256):
  # Clockwise (r,z) triangles with extrusion in increasing theta give positive xyz orientation.
  a=(2,loz);b=(2,hiz);d=(3,loz);mid=(3,loz+1);c=(3,hiz)
  for poly in ((a,b,mid),(a,mid,d),(b,c,mid)):prism([v(rr,t,zz) for rr,zz in poly],[v(rr,t+1,zz) for rr,zz in poly],'axial')
rawfaces=((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7));registry=defaultdict(list);cellfaces=[]
for cell,block in enumerate(blocks):
 out=[]
 for template in rawfaces:
  raw=[block[i] for i in template];poly=[]
  for x in raw:
   if not poly or poly[-1]!=x:poly.append(x)
  if len(poly)>1 and poly[0]==poly[-1]:poly.pop()
  if len(poly)<3:continue
  assert len(set(poly))==len(poly);registry[tuple(sorted(poly))].append((cell,poly,raw));out.append(poly)
 edges=Counter((a,b) for poly in out for a,b in zip(poly,poly[1:]+poly[:1]));assert all(num==1 and edges[b,a]==1 for (a,b),num in edges.items());cellfaces.append(out)
assert all(len(rows) in (1,2) for rows in registry.values())
for rows in registry.values():
 if len(rows)==2:
  p,q=rows[0][1],rows[1][1];assert set(zip(p,p[1:]+p[:1]))=={(b,a) for a,b in zip(q,q[1:]+q[:1])}
walls=[rows[0][2] for rows in registry.values() if len(rows)==1];p=np.array(vertices);centres=[];volumes=[];dets=[];scores=[];geoms=[];warps=[]
for cell,polys in enumerate(cellfaces):
 cs=[];areas=[];ia=[]
 for poly in polys:
  cf,sf,warp=geometry(p[np.array(poly)][None,:,:]);cs.append(cf[0]);areas.append(sf[0]);warps.append(float(warp[0]))
  if len(registry[tuple(sorted(poly))])==2:ia.append(sf[0])
 cs=np.array(cs);areas=np.array(areas);est=cs.mean(axis=0);pv=np.einsum('ij,ij->i',areas,cs-est);volumes.append(float(pv.sum()/3));centres.append((pv[:,None]*(.75*cs+.25*est)).sum(axis=0)/pv.sum());geoms.append((cs,areas))
 ia=np.array(ia);avg=np.linalg.norm(ia,axis=1).mean();dets.append(float(abs(np.linalg.det(ia.T@ia/avg**2))/8));delta=cs[None,:,:]-cs[:,None,:];score=np.einsum('ijk,ik->ij',delta,areas/np.linalg.norm(areas,axis=1)[:,None])/np.maximum(np.linalg.norm(delta,axis=2),1e-300);np.fill_diagonal(score,-1);scores.append(float(score.max()))
centres=np.array(centres);angles=[];mrf=[];stagejoin=[];balance=np.zeros(len(blocks));omega=np.array([0,0,10471.975511966])
for rows in registry.values():
 cell,poly,_=rows[0];cf,sf,_=geometry(p[np.array(poly)][None,:,:]);flux=float(np.dot(np.cross(omega,cf[0]),sf[0]));balance[cell]+=flux
 if len(rows)==2:
  other=rows[1][0];balance[other]-=flux;delta=centres[other]-centres[cell];angle=float(np.degrees(np.arccos(np.clip(np.dot(delta,sf[0])/np.linalg.norm(delta)/np.linalg.norm(sf[0]),-1,1))));angles.append(dict(cells=[cell,other],angle_deg=angle,stages=[stages[cell],stages[other]],vertices=poly))
  if zones[cell]!=zones[other]:mrf.append(poly)
  if {stages[cell],stages[other]}=={'angular','axial'}:stagejoin.append(poly)
assert len(mrf)==384 and len(stagejoin)==768 and all(len(x)==4 for x in mrf+stagejoin)
header='FoamFile {version 2.0; format ascii; class dictionary; object blockMeshDict;}\n';vec=lambda x:'('+' '.join(format(v,'.17g') if isinstance(v,float) else str(v) for v in x)+')'
(w/'blockMeshDict').write_text(header+'vertices ('+' '.join(map(vec,vertices))+');\nblocks ('+'\n'.join('hex '+vec(b)+(' rotorZone' if z else '')+' (1 1 1) simpleGrading (1 1 1)' for b,z in zip(blocks,zones))+');\nedges ();\nboundary (walls {type wall; faces ('+' '.join(map(vec,walls))+');});\n')
(w/'construction.json').write_text(json.dumps(dict(source_construction_sha256=sha(source/'construction.json'),source_receipts={str(source):sha(source/'report.json'),str(case):sha(case/'report.json')},target_face=93362,target_z_m=target,source_interval_indices=indices[:-1],stations_m=stations.tolist(),radii_m=radii.tolist(),radial_ratios=ratios,vertices=vertices,blocks=blocks,rotating=zones,stages=stages,walls=walls,mrf_faces=mrf,stage_join_faces=stagejoin),indent=2)+'\n')
normal=max(abs(float(np.dot(np.cross(omega,geometry(p[np.array(poly)][None,:,:])[0][0]),geometry(p[np.array(poly)][None,:,:])[1][0])))/np.linalg.norm(geometry(p[np.array(poly)][None,:,:])[1][0]) for poly in mrf)
report=dict(source_sha256=sha(Path(__file__)),cells=len(blocks),points=len(p),stage_counts=dict(Counter(stages)),boundary_faces=len(walls),internal_faces=len(angles),mrf_faces=len(mrf),stage_join_faces=len(stagejoin),minimum_volume_m3=min(volumes),volume_m3=sum(volumes),minimum_determinant=min(dets),bad_determinants=sum(x<.001 for x in dets),flagged_plane_cells=sum(x>-1e-6 for x in scores),maximum_angle_deg=max(x['angle_deg'] for x in angles),faces_over_70=sum(x['angle_deg']>70 for x in angles),maximum_warp_m=max(warps),mrf_normal_speed_m_s=float(normal),rotating_balance_max_m3_s=float(np.max(abs(balance[np.array(zones)]))),native_executed=False)
report['preflight_pass']=bool(report['bad_determinants']==0 and report['flagged_plane_cells']==0 and report['faces_over_70']==0 and min(volumes)>0 and max(warps)<1e-12 and normal<1e-8 and report['rotating_balance_max_m3_s']<1e-16)
(w/'quality.json').write_text(json.dumps(report,indent=2)+'\n');(w/'angles.json').write_text(json.dumps(angles)+'\n');print(json.dumps(report))
