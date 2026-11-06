"""Improve thin triangles using flips with exact per-operation surface bounds."""
from fractions import Fraction as Q
from pathlib import Path
import hashlib,json,time
import numpy as np


def quality(v,f):
 t=v[np.asarray(f)];length=np.stack([np.linalg.norm(t[:,1]-t[:,0],axis=1),np.linalg.norm(t[:,2]-t[:,1],axis=1),np.linalg.norm(t[:,0]-t[:,2],axis=1)],axis=1);return length.max(1)**2/np.linalg.norm(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]),axis=1)


def exact_gap(points,drop):
 # Both triangulations are graphs over a convex projected quadrilateral.
 # Their height difference is piecewise linear on the overlay: its maximum
 # occurs at their diagonal intersection (all four boundary values are zero).
 axis=[x for x in range(3)if x!=drop];a,b,c,d=[[Q(float(x))for x in point]for point in points]
 cross=lambda p,q:p[0]*q[1]-p[1]*q[0]
 ab=[b[k]-a[k]for k in axis];cd=[d[k]-c[k]for k in axis];ac=[c[k]-a[k]for k in axis];den=cross(ab,cd)
 if not den:return None
 t=cross(ac,cd)/den;u=cross(ac,ab)/den
 if not(0<t<1 and 0<u<1):return None
 gap=abs(a[drop]+t*(b[drop]-a[drop])-c[drop]-u*(d[drop]-c[drop]));return gap,t,u


def best_bound(points,drop):
 graph=exact_gap(points,drop);terms=[]
 if graph is not None:terms.append(dict(cost=graph[0],kind='convex_overlay',t=graph[1],u=graph[2],cap=None))
 # Flattening either opposite vertex to the shared segment makes both
 # triangulations identical. Two vertex homotopies give H <= 2*L1(C-P).
 q=[[Q(float(x))for x in point]for point in points];a,b=q[:2];ab=[b[k]-a[k]for k in range(3)];den=sum(x*x for x in ab)
 for cap in [2,3]:
  c=q[cap];t=max(Q(0),min(Q(1),sum((c[k]-a[k])*ab[k]for k in range(3))/den));cost=2*sum(abs(c[k]-a[k]-t*ab[k])for k in range(3));terms.append(dict(cost=cost,kind='twice_cap_to_shared_edge_L1',t=t,u=None,cap=cap))
 return min(terms,key=lambda x:x['cost'])


def controls():
 assert exact_gap(np.array([[0,0,0],[1,1,0],[0,1,0],[1,0,0]]),2)[0]==0
 assert exact_gap(np.array([[0,0,0],[1,1,.2],[0,1,0],[1,0,0]]),2)[0]==Q(.2)/2
 assert exact_gap(np.array([[0,0,0],[1,0,0],[0,1,0],[.1,.1,0]]),2)is None


def main():
 controls();start=time.monotonic();w=Path('work/carrier-interface-20261028');source=w/'conditioned-short-edges-001/candidate.npz';out=w/'conditioned-caps-003';assert not out.exists();out.mkdir();z=np.load(source,allow_pickle=False);v=z['vertices'].copy();f=z['triangles'].copy();x=v[f,0];blocked=np.all(abs(x)<=65,axis=1)|np.all(x<=-260,axis=1)|np.all(x>=260,axis=1);initial_protected=f[blocked].copy();ar=quality(v,f);initial_bad=int((ar>100).sum());initial_max=float(ar.max());ledger=[];total=Q(0);budget=Q(2,1000);stalled=set()
 for iteration in range(300):
  ids=np.flatnonzero(ar>100);ids=sorted((int(i)for i in ids if int(i)not in stalled),key=lambda i:-ar[i])
  if not ids:break
  i=ids[0]
  if blocked[i]:stalled.add(i);continue
  old=f[i].copy();options=[]
  for k in range(3):
   a,b,c=[int(old[(k+h)%3])for h in range(3)];neighbor=np.flatnonzero(np.any(f==a,axis=1)&np.any(f==b,axis=1));assert len(neighbor)==2;j=int(neighbor[neighbor!=i][0])
   if blocked[j]:continue
   other=f[j];where=int(np.flatnonzero(other==b)[0])
   if int(other[(where+1)%3])!=a:raise ValueError('Oriented edge pairing differs')
   d=int(other[(where+2)%3]);duplicate=np.flatnonzero(np.any(f==c,axis=1)&np.any(f==d,axis=1))
   if len(duplicate):continue
   proposed=np.asarray([[c,d,b],[d,c,a]],dtype=f.dtype);after=quality(v,proposed)
   if not np.isfinite(after).all():continue
   before=ar[[i,j]];before_score=(int((before>100).sum()),float(np.maximum(before-100,0).sum()));after_score=(int((after>100).sum()),float(np.maximum(after-100,0).sum()))
   if after_score>=before_score:continue
   points=v[[a,b,c,d]];normal=np.cross(points[1]-points[0],points[2]-points[0])+np.cross(points[0]-points[1],points[3]-points[1]);drop=int(abs(normal).argmax());bound=best_bound(points,drop)
   if total+bound["cost"]>budget:continue
   options.append((after_score,bound["cost"],j,proposed,after,drop,bound["t"],bound["u"],[a,b,c,d],bound["kind"],bound["cap"]))
  if not options:stalled.add(i);continue
  _,cost,j,new,after,drop,t,u,abcd,kind,cap=min(options,key=lambda x:(x[0],x[1]));entry=dict(face_indices=[i,j],old_triangles=f[[i,j]].tolist(),new_triangles=new.tolist(),diagonal_vertex_indices=abcd,projection_drop_axis=drop,gap_numerator=str(cost.numerator),gap_denominator=str(cost.denominator),bound_method=kind,cap_point_local_index=cap,bound_t=[str(t.numerator),str(t.denominator)],bound_u=None if u is None else[str(u.numerator),str(u.denominator)]);f[[i,j]]=new;ar[[i,j]]=after;total+=cost;ledger.append(entry);stalled.clear();print(json.dumps(dict(flips=len(ledger),remaining_bad=int((ar>100).sum()),maximum_AR=float(ar.max()),accumulated_surface_bound_mm=float(total))),flush=True)
 assert np.array_equal(initial_protected,f[blocked]);np.savez_compressed(out/'candidate.npz',vertices=v,triangles=f);(out/'flip-ledger.json').write_text(json.dumps(dict(controls_passed=True,operations=ledger,total_bound_numerator=str(total.numerator),total_bound_denominator=str(total.denominator),complete_surface_change_l1_bound_mm=float(total),maximum_allowed_change_mm=float(budget)),indent=2)+'\n');r=dict(status='edge_flip_candidate_requires_independent_checks',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),output_sha256=hashlib.sha256((out/'candidate.npz').read_bytes()).hexdigest(),vertices=len(v),triangles=len(f),flips=len(ledger),protected_face_indices_unchanged=True,initial_triangles_AR_over_100=initial_bad,final_triangles_AR_over_100=int((ar>100).sum()),initial_maximum_AR=initial_max,final_maximum_AR=float(ar.max()),sequential_complete_surface_change_bound_mm=float(total),elapsed_seconds=time.monotonic()-start,manufacturing_authorized=False);(out/'assessment.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))

if __name__=='__main__':main()
