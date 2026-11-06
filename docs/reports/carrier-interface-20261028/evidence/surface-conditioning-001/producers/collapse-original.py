"""Collapse short unprotected edges, recording an exact L1 displacement ledger."""
from fractions import Fraction as Q
from pathlib import Path
import importlib.util,hashlib,json,time
import numpy as np
w=Path('work/carrier-interface-20261028');spec=importlib.util.spec_from_file_location('flips',w/'flip_conditioned_caps_001.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);quality=mod.quality

def main():
 start=time.monotonic();source=w/'conditioned-caps-001/candidate.npz';out=w/'conditioned-short-edges-001';assert not out.exists();out.mkdir();z=np.load(source,allow_pickle=False);v=z['vertices'].copy();f=z['triangles'].copy();x=v[f,0];blocked=np.all(abs(x)<=65,1)|np.all(x<=-260,1)|np.all(x>=260,1);protected=np.zeros(len(v),bool);protected[np.unique(f[blocked])]=True;protected_faces=f[blocked].copy();active=np.ones(len(f),bool);ar=quality(v,f);initial_bad=int((ar>100).sum());initial_max=float(ar.max());ledger=[];total=Q(0);budget=Q(6,1000);stalled=set()
 for iteration in range(160):
  bad=sorted((int(i)for i in np.flatnonzero(ar>100)if int(i)not in stalled),key=lambda i:-ar[i])
  if not bad:break
  i=bad[0];options=[];old=f[i]
  for k in range(3):
   a,b=int(old[k]),int(old[(k+1)%3]);cost=sum(abs(Q(float(x))-Q(float(y)))for x,y in zip(v[a],v[b]))
   if total+cost>budget:continue
   ia=np.flatnonzero(active&np.any(f==a,axis=1));ib=np.flatnonzero(active&np.any(f==b,axis=1));edge=np.intersect1d(ia,ib)
   if len(edge)!=2:continue
   na=set(int(x)for x in f[ia].flat)-{a,b};nb=set(int(x)for x in f[ib].flat)-{a,b};opposite=set(int(x)for x in f[edge].flat)-{a,b}
   if na&nb!=opposite or len(opposite)!=2:continue
   union=np.union1d(ia,ib);before=ar[union];before_score=(int((before>100).sum()),float(np.maximum(before-100,0).sum()))
   for u,keep in [(a,b),(b,a)]:
    if protected[u]:continue
    mapped=f[union].copy();mapped[mapped==u]=keep;valid=(mapped[:,0]!=mapped[:,1])&(mapped[:,0]!=mapped[:,2])&(mapped[:,1]!=mapped[:,2])
    if int((~valid).sum())!=2:continue
    survivor=mapped[valid];keys=[tuple(sorted(int(x)for x in row))for row in survivor]
    if len(keys)!=len(set(keys)):continue
    after=quality(v,survivor)
    if not np.isfinite(after).all()or after.max()>before.max()*(1+1e-12):continue
    after_score=(int((after>100).sum()),float(np.maximum(after-100,0).sum()))
    if after_score>=before_score:continue
    oldtri=v[f[union][valid]];newtri=v[survivor];oldnorm=np.cross(oldtri[:,1]-oldtri[:,0],oldtri[:,2]-oldtri[:,0]);newnorm=np.cross(newtri[:,1]-newtri[:,0],newtri[:,2]-newtri[:,0])
    if np.any((oldnorm*newnorm).sum(1)<=0):continue
    # Every deleted triangle maps to a retained boundary edge, so deletion
    # does not remove any point from the image of the piecewise-linear map.
    edges={tuple(sorted((int(row[k]),int(row[(k+1)%3]))))for row in survivor for k in range(3)};segments=[tuple(sorted(set(int(x)for x in row)))for row in mapped[~valid]]
    if any(len(segment)!=2 or segment not in edges for segment in segments):continue
    options.append((after_score,cost,u,keep,union,mapped,valid,after,segments))
  if not options:stalled.add(i);continue
  _,cost,u,keep,rows,mapped,valid,after,segments=min(options,key=lambda x:(x[0],x[1]));ledger.append(dict(removed_vertex=u,retained_vertex=keep,affected_face_indices=rows.tolist(),deleted_face_indices=rows[~valid].tolist(),deleted_triangle_image_segments=segments,l1_bound_numerator=str(cost.numerator),l1_bound_denominator=str(cost.denominator)));f[rows]=mapped;active[rows[~valid]]=False;ar[rows[~valid]]=0;ar[rows[valid]]=after;total+=cost;stalled.clear();print(json.dumps(dict(collapses=len(ledger),remaining_bad=int((ar>100).sum()),maximum_AR=float(ar.max()),surface_displacement_bound_mm=float(total))),flush=True)
 assert active[blocked].all()and np.array_equal(f[blocked],protected_faces);used=np.unique(f[active]);final_f=np.searchsorted(used,f[active]).astype(np.int32);final_v=v[used];np.savez_compressed(out/'candidate.npz',vertices=final_v,triangles=final_f);(out/'collapse-ledger.json').write_text(json.dumps(dict(operations=ledger,total_bound_numerator=str(total.numerator),total_bound_denominator=str(total.denominator),sequential_complete_surface_change_l1_bound_mm=float(total),maximum_allowed_change_mm=float(budget)),indent=2)+'\n');r=dict(status='short_edge_candidate_requires_independent_checks',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),output_sha256=hashlib.sha256((out/'candidate.npz').read_bytes()).hexdigest(),vertices=len(final_v),triangles=len(final_f),collapses=len(ledger),protected_faces_unchanged=True,initial_triangles_AR_over_100=initial_bad,final_triangles_AR_over_100=int((ar>100).sum()),initial_maximum_AR=initial_max,final_maximum_AR=float(ar.max()),sequential_complete_surface_change_l1_bound_mm=float(total),elapsed_seconds=time.monotonic()-start,manufacturing_authorized=False);(out/'assessment.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))

if __name__=='__main__':main()
