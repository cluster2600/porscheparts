"""Close only exact planar convex quadrilateral cracks with a full rational bound."""
from pathlib import Path
from fractions import Fraction as Q
import numpy as np,json,struct,hashlib,sys
LIMIT=Q(1,1000000) # 0.000001 mm, fixed before actual trials.
def repair(v,f):
 oriented=np.vstack([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]);keys=np.sort(oriented,axis=1)
 _,inverse,counts=np.unique(keys,axis=0,return_inverse=True,return_counts=True)
 if np.any(counts>2):raise ValueError('Non-manifold edge refused')
 b=oriented[counts[inverse]==1];outgoing={int(a):int(c)for a,c in b}
 if len(outgoing)!=len(b) or len(set(outgoing.values()))!=len(b):raise ValueError('Boundary must be disjoint oriented cycles')
 added=[];proofs=[]
 while outgoing:
  start=min(outgoing);loop=[];current=start
  while current not in loop:
   loop.append(current);current=outgoing.pop(current)
  if current!=start or len(loop)!=4:raise ValueError('Only four-edge cracks admitted')
  p=[[Q(float(t))for t in v[i]]for i in loop]
  axes=[k for k in range(3)if all(x[k]==p[0][k]for x in p)]
  if len(axes)!=1:raise ValueError('Exact axis-planarity required')
  dims=[k for k in range(3)if k!=axes[0]];turns=[]
  for i in range(4):
   a,c,d=p[i],p[(i+1)%4],p[(i+2)%4];u,w=dims
   turns.append((c[u]-a[u])*(d[w]-c[w])-(c[w]-a[w])*(d[u]-c[u]))
  if not(all(t>0 for t in turns)or all(t<0 for t in turns)):raise ValueError('Strictly convex simple quadrilateral required')
  bounds=[]
  for i in range(4):
   a,c=p[i],p[(i+1)%4];d=[y-x for x,y in zip(a,c)];den=sum(x*x for x in d);errors=[]
   for x in p:
    t=max(Q(0),min(Q(1),sum((x[k]-a[k])*d[k]for k in range(3))/den))
    errors.append(sum(abs(x[k]-a[k]-t*d[k])for k in range(3)))
   bounds.append(max(errors))
  bound=min(bounds)
  if bound>LIMIT:raise ValueError('Complete patch distance exceeds fixed crack bound')
  a,c,d,e=loop;added.extend([[a,d,c],[a,e,d]])
  proofs.append(dict(boundary=loop,axis=axes[0],bound_mm=float(bound),bound_rational=str(bound),reference_boundary_segment=loop[bounds.index(bound):bounds.index(bound)+1]+[loop[(bounds.index(bound)+1)%4]],method='Each patch point is a convex combination of the four vertices; corresponding rational projected points lie on one existing boundary segment; convexity bounds complete L1 distance. All old faces are retained, giving zero reverse distance.'))
 return np.vstack([f,np.asarray(added,dtype=np.uint64).reshape(-1,3)]),proofs
if __name__=='__main__':
 source=Path(sys.argv[1]);out=Path(sys.argv[2]);assert not out.exists();raw=source.read_bytes();nv,nf=struct.unpack('<QQ',raw[:16]);assert len(raw)==16+nv*24+nf*24
 v=np.frombuffer(raw,dtype='<f8',offset=16,count=nv*3).reshape(-1,3).copy();f=np.frombuffer(raw,dtype='<u8',offset=16+nv*24,count=nf*3).reshape(-1,3).copy();assert np.isfinite(v).all()
 new,proofs=repair(v,f);out.mkdir();target=out/'candidate.meshbin';target.write_bytes(struct.pack('<QQ',len(v),len(new))+v.astype('<f8').tobytes()+new.astype('<u8').tobytes());np.savez(out/'candidate.npz',vertices=v,triangles=new)
 report=dict(status='bounded_narrow_gap_candidate_complete_embedding_pending',source_sha256=hashlib.sha256(raw).hexdigest(),output_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),unchanged_vertices=True,all_original_faces_preserved=True,added_faces=len(new)-len(f),fixed_bound_mm=float(LIMIT),patches=proofs)
 (out/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
