"""Correct the remaining slivers with bounded, exactly postchecked vertex moves.

The face set and indices stay fixed. Barycentric convexity bounds both surface
directions by the maximum L1 displacement of an original vertex. Each local
normal keeps a strictly positive exact dot product with its previous normal;
the final independent full self-intersection check remains mandatory.
"""
import argparse
from fractions import Fraction as F
import hashlib
import importlib.util
import json
from pathlib import Path


def exact_normal(points):
 a,b,c=[tuple(F(float(x))for x in p)for p in points];u=[b[i]-a[i]for i in range(3)];w=[c[i]-a[i]for i in range(3)]
 return(u[1]*w[2]-u[2]*w[1],u[2]*w[0]-u[0]*w[2],u[0]*w[1]-u[1]*w[0])


def main():
 p=argparse.ArgumentParser(__doc__);p.add_argument('--mesh',type=Path,required=True);p.add_argument('--prior-envelope',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('Fresh output required')
 a.output.mkdir(parents=True)
 import numpy as np
 def load(name,file):
  spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(file));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 geometry=load('_nudge_geometry','certified_patch_collapse.py');exact=load('_nudge_quality','certified_union_flip_quality.py')
 prior=json.loads(a.prior_envelope.read_text());digest=hashlib.sha256(a.mesh.read_bytes()).hexdigest()
 if prior['output_sha256']!=digest:raise ValueError('Prior geometry identity differs')
 before=F(prior['complete_exact_master_L1_bound_mm']);maximum=F(0)
 with a.mesh.open()as stream:nv,nf=map(int,stream.readline().split());v=np.loadtxt(stream,max_rows=nv);faces=np.loadtxt(stream,dtype=np.int64)
 original=v.copy();report=dict(status='incomplete',source_mesh_sha256=digest,prior_proof_sha256=hashlib.sha256(a.prior_envelope.read_bytes()).hexdigest(),prior_bound_mm=str(before),needle_ratio_threshold=.001,steps=[],source_face_indices_unchanged=True,global_admission=False)
 try:
  while True:
   q=geometry.ratios(v,faces,np);bad=np.flatnonzero(q<.001)
   if not len(bad):break
   best=None
   for face_id in bad:
    triangle=faces[face_id]
    for k,vertex in enumerate(triangle):
     ids=np.flatnonzero(np.any(faces==vertex,axis=1));old=v[faces[ids]].copy();old_count=int((q[ids]<.001).sum());points=v[triangle].copy();c=points[k];a0,b0=points[(k+1)%3],points[(k+2)%3];u=b0-a0;length=float(np.linalg.norm(u));perp=c-a0-np.dot(c-a0,u)/np.dot(u,u)*u;height=float(np.linalg.norm(perp))
     if not height or not length:continue
     direction=perp/height;candidate=c.copy();valid=False
     for attempt in range(128):
      points[k]=candidate;ratio=geometry.ratios(points,np.array([[0,1,2]]),np)[0]
      if ratio>=.001 and exact.quality_squared(points)>=F(.001)**2:valid=True;break
      twice=float(np.linalg.norm(np.cross(points[1]-points[0],points[2]-points[0])));longest=float(np.max(np.sum((points-np.roll(points,-1,axis=0))**2,axis=1)));shift=max(0.,(.001*longest-twice)/length);new=candidate+direction*shift
      if np.array_equal(new,candidate)or attempt>10:
       towards=np.where(direction>0,np.inf,np.where(direction<0,-np.inf,candidate));new=np.nextafter(candidate,towards)
      if np.array_equal(new,candidate):break
      candidate=new
     if not valid:continue
     movement=sum(abs(F(float(x))-F(float(y)))for x,y in zip(candidate,original[vertex]));bound=max(maximum,movement)
     if before+bound>F(.06):continue
     local=old.copy();local[faces[ids]==vertex]=candidate;quality=geometry.ratios(local.reshape(-1,3),np.arange(local.size//3).reshape(-1,3),np)
     if not np.isfinite(quality).all()or np.any(quality==0):continue
     new_count=int((quality<.001).sum())
     if new_count>=old_count:continue
     dots=[]
     for old_tri,new_tri in zip(old,local):
      old_n=exact_normal(old_tri);new_n=exact_normal(new_tri);dots.append(sum(x*y for x,y in zip(old_n,new_n)))
     if min(dots)<=0:continue
     score=(bound,len(bad)-old_count+new_count,int(vertex),int(face_id))
     if best is None or score<best[0]:best=(score,candidate,ids,dots,attempt)
   if best is None:raise ValueError(f'No admissible bounded quality move for {len(bad)} needles')
   (bound,count,vertex,face_id),candidate,ids,dots,attempt=best;old_point=v[vertex].copy();v[vertex]=candidate;maximum=bound
   report['steps'].append(dict(vertex=vertex,trigger_face=face_id,old_point_mm=old_point.tolist(),new_point_mm=candidate.tolist(),affected_face_ids=ids.tolist(),minimum_exact_old_new_normal_dot=str(min(dots)),maximum_original_vertex_L1_displacement_mm=str(maximum),remaining_needles=count,directed_rounding_iterations=attempt))
  target=a.output/'union.mesh64'
  with target.open('w')as stream:stream.write(f'{len(v)} {len(faces)}\n');np.savetxt(stream,v,fmt='%.17g');np.savetxt(stream,faces,fmt='%d')
  report.update(status='all_union_needles_removed_with_complete_surface_bound',vertices=len(v),triangles=len(faces),maximum_vertex_L1_displacement_mm=str(maximum),complete_exact_master_L1_bound_mm=str(before+maximum),complete_bound_mm_float=float(before+maximum),minimum_triangle_ratio=float(geometry.ratios(v,faces,np).min()),output_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),independent_full_surface_audit_pending=True)
 except Exception as error:report['failure']=dict(type=type(error).__name__,message=str(error));raise
 finally:(a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:report[k]for k in ['status','vertices','triangles','complete_bound_mm_float','minimum_triangle_ratio']}))

if __name__=='__main__':main()
