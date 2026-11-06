"""Bounded exact-coordinate incidence/vertex-fan screen; never repairs source STL."""
from pathlib import Path
import hashlib,json,sys,time
import numpy as np

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as s:
  for b in iter(lambda:s.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def combinatorial(f,nv):
 flat=f.reshape(-1);end=np.roll(f,-1,axis=1).reshape(-1)
 key=np.minimum(flat,end).astype(np.uint64);key<<=32;key|=np.maximum(flat,end)
 order=np.argsort(key);ks=key[order];cuts=np.r_[0,np.flatnonzero(ks[1:]!=ks[:-1])+1,len(ks)];counts=np.diff(cuts)
 hist={str(int(n)):int((counts==n).sum()) for n in np.unique(counts)};result={'exact_indexed_vertices':nv,'original_faces_retained':len(f),'edge_incidence_histogram':hist,'self_loop_occurrences':int((flat==end).sum()),'original_faces_removed':0}
 del key,ks,cuts
 if not np.all(counts==2):
  result.update({'two_incidence_orientation_conflicts':None,'vertex_fan_check':'not_admitted_non_two_incidence_edges','closed_oriented_vertex_manifold_screen_pass':False});return result
 del counts
 conflicts=0;nxt=np.empty(len(flat),dtype=np.uint32)
 for j in range(0,len(order),400000):
  pair=order[j:j+400000].reshape(-1,2);a=pair[:,0];b=pair[:,1];conflicts+=int(np.count_nonzero((flat[a]!=end[b])|(end[a]!=flat[b])));nxt[a]=3*(b//3)+(b%3+1)%3;nxt[b]=3*(a//3)+(a%3+1)%3
 del order
 result['two_incidence_orientation_conflicts']=conflicts
 if conflicts or result['self_loop_occurrences']:
  result.update({'vertex_fan_check':'not_admitted_winding_or_self_loop_defect','closed_oriented_vertex_manifold_screen_pass':False});return result
 for j in range(0,len(flat),1000000):assert np.array_equal(flat[nxt[j:j+1000000]],flat[j:j+1000000])
 labels=np.arange(len(flat),dtype=np.uint32);jumps=nxt;converged=False
 for iteration in range(32):
  following=np.minimum(labels,labels[jumps]);converged=np.array_equal(following,labels);labels=following
  if converged:break
  jumps=jumps[jumps]
 if not converged:raise RuntimeError('Vertex-fan cycle propagation did not converge within fixed32rounds')
 low=np.full(nv,np.iinfo(np.uint32).max,dtype=np.uint32);high=np.zeros(nv,dtype=np.uint32);np.minimum.at(low,flat,labels);np.maximum.at(high,flat,labels);bad=int(np.count_nonzero(low!=high));result.update({'vertex_fan_check':'Outgoing-corner permutation cycles across every paired oriented edge; each cycle remains on the exact original vertex; one cycle required per vertex','vertex_fan_cycle_rounds':iteration+1,'nonmanifold_vertex_fans':bad,'closed_oriented_vertex_manifold_screen_pass':bad==0});return result

# Discriminating controls: closed tetra and two closed shells pinched at one vertex.
f=np.array([[0,2,1],[0,1,3],[1,2,3],[2,0,3]],dtype=np.uint32)
assert combinatorial(f,4)['closed_oriented_vertex_manifold_screen_pass']
pinched=np.vstack([f,np.where(f==0,0,f+3)])
assert combinatorial(pinched,7)['nonmanifold_vertex_fans']==1
assert not combinatorial(np.array([[0,1,2]],dtype=np.uint32),3)['closed_oriented_vertex_manifold_screen_pass']
path=Path(sys.argv[1]);out=Path(sys.argv[2]);start=time.monotonic();original_sha=sha(path)
with path.open('rb') as stream:head=stream.read(84)
n=int.from_bytes(head[80:84],'little');assert 0<n<=40000000 and path.stat().st_size==84+50*n
a=np.memmap(path,dtype=np.dtype([('normal','<f4',(3,)),('v','<f4',(3,3)),('attr','<u2')]),mode='r',offset=84,shape=(n,))
vertices,inverse=np.unique(np.asarray(a['v']).reshape(-1,3),axis=0,return_inverse=True);faces=inverse.astype(np.uint32).reshape(-1,3);del inverse
assert np.isfinite(vertices).all();print('Indexed original faces',n,'vertices',len(vertices),flush=True)
sorted_faces=np.sort(faces,axis=1);_,dup_counts=np.unique(sorted_faces,axis=0,return_counts=True);dup=int(np.sum(dup_counts-1));del sorted_faces,dup_counts
zero=[];volume=0.
for j in range(0,n,200000):
 tri=vertices[faces[j:j+200000]].astype(np.float64);raw=np.asarray(a['v'][j:j+200000],dtype=np.float64);assert np.array_equal(tri,raw);cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);candidate=np.flatnonzero(np.all(cross==0,axis=1))
 for local in candidate:
  vals=tri[local];ratios=[float(x).as_integer_ratio() for x in vals.reshape(-1)];power=max(d.bit_length()-1 for _,d in ratios);ints=[n0<<(power-(d.bit_length()-1)) for n0,d in ratios];p=[ints[k:k+3] for k in [0,3,6]];u=[p[1][k]-p[0][k] for k in range(3)];v=[p[2][k]-p[0][k] for k in range(3)]
  if u[1]*v[2]==u[2]*v[1] and u[2]*v[0]==u[0]*v[2] and u[0]*v[1]==u[1]*v[0]:zero.append(j+int(local))
 volume+=float(np.einsum('ij,ij->i',tri[:,0],np.cross(tri[:,1],tri[:,2])).sum()/6)
print('Original zero-area count',len(zero),'duplicate excess',dup,flush=True)
r=combinatorial(faces,len(vertices));r.update({'classification':'original_Pico_STL_exact_coordinate_combinatorial_screen_no_repair','source_sha256':original_sha,'script_sha256':sha(__file__),'exact_zero_area_faces':len(zero),'exact_zero_area_original_face_ids':zero[:100],'duplicate_unoriented_face_excess':dup,'zero_area_method':'Float64 zero-cross candidates independently checked with exact dyadic integer cross products; original float32 coordinates indexed exactly','signed_triangle_integral_mm3':volume,'geometric_self_intersections':'untested','component_shell_orientation_relative_to_material':'untested','component_nesting':'untested','closed_surface_geometric_embedding_qualified':False,'elapsed_seconds':time.monotonic()-start,'discriminating_tetra_pinched_vertex_and_open_triangle_controls_passed':True})
r['combinatorial_acceptance']=r['closed_oriented_vertex_manifold_screen_pass'] and len(zero)==0 and dup==0
assert sha(path)==original_sha;out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
