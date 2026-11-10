"""Check the exported MSH2 chain independently of Gmsh, using integer node IDs."""
from pathlib import Path
import hashlib,json,struct,shlex,sys
import numpy as np

def canonical(a):
 return np.take_along_axis(a,(np.argmin(a,axis=1)[:,None]+np.arange(3))%3,axis=1)
def order(a):
 return np.lexsort(tuple(a[:,i] for i in reversed(range(a.shape[1]))))
def chain(tets,boundary):
 keys=np.sort(tets,axis=1);keys=keys[order(keys)]
 assert not np.any(np.all(keys[1:]==keys[:-1],axis=1)),'duplicate tetrahedra'
 del keys
 faces=canonical(tets[:,[[1,2,3],[0,3,2],[0,1,3],[0,2,1]]].reshape(-1,3))
 keys=np.sort(faces,axis=1);permutation=order(keys);keys=keys[permutation];faces=faces[permutation]
 starts=np.r_[0,np.flatnonzero(np.any(keys[1:]!=keys[:-1],axis=1))+1];counts=np.diff(np.r_[starts,len(keys)])
 assert np.all((counts==1)|(counts==2)),'nonmanifold face incidence'
 paired=starts[counts==2];assert np.array_equal(faces[paired],faces[paired+1][:,[0,2,1]]),'internal orientations do not cancel'
 actual=faces[starts[counts==1]];expected=canonical(boundary);expected=expected[order(np.sort(expected,axis=1))]
 assert np.array_equal(actual,expected),'actual oriented boundary differs from declared triangles'
 return {'internal_faces':int((counts==2).sum()),'boundary_faces':int((counts==1).sum())}
# A two-tetrahedron control and two deliberately invalid chains.
t=np.array([[0,1,2,3],[0,2,1,4]],dtype=np.uint32)
b=t[:,[[1,2,3],[0,3,2],[0,1,3]]].reshape(-1,3)
assert chain(t,b)=={'internal_faces':1,'boundary_faces':6}
for bad in [np.vstack([t,t[0]]),t[:,[0,2,1,3]]]:
 try:chain(bad,b)
 except AssertionError:pass
 else:raise AssertionError('bad control accepted')
assert len(sys.argv)==2,'provide the private optimized600 trial directory'
r=Path(sys.argv[1]);path=r/'duct.msh';assert hashlib.sha256(path.read_bytes()).hexdigest()=='76c052c1df8613905055a4befebe05f3fd8f481f6210a6371bd9e09eb1c004d5'
source=(r.parent/'installed-cooling-feature-extract-20261107/native-ingested-source.bin').read_bytes();assert hashlib.sha256(source).hexdigest()=='80daaea26b32bc5a39579128f73a40e463a72624aff51ebbe1908db5ef6c19ca';nv,nf=struct.unpack_from('<QQ',source,8);original=np.frombuffer(source,dtype='<f8',count=3*nv,offset=24).reshape(-1,3);source_tri=np.frombuffer(source,dtype='<u8',count=3*nf,offset=24+24*nv).reshape(-1,3)+1
labels=np.array(json.loads((r/'regions.json').read_text()));assert len(labels)==nf
with path.open() as f:
 assert next(f).strip()=='$MeshFormat' and next(f).strip()=='2.2 0 8' and next(f).strip()=='$EndMeshFormat'
 assert next(f).strip()=='$PhysicalNames';names={}
 for _ in range(int(next(f))):
  dim,tag,name=shlex.split(next(f));names[(int(dim),int(tag))]=name
 assert next(f).strip()=='$EndPhysicalNames' and next(f).strip()=='$Nodes'
 nn=int(next(f));points=np.full((nn+1,3),np.nan)
 for _ in range(nn):
  row=next(f).split();tag=int(row[0]);assert 1<=tag<=nn and np.isnan(points[tag]).all();points[tag]=list(map(float,row[1:]))
 assert np.isfinite(points[1:]).all() and np.array_equal(points[1:nv+1],original)
 assert next(f).strip()=='$EndNodes' and next(f).strip()=='$Elements'
 ne=int(next(f));tri=np.empty((nf,3),dtype=np.uint32);patch=np.empty(nf,dtype=np.uint32);tet=np.empty((ne-nf,4),dtype=np.uint32);a=c=0
 for _ in range(ne):
  row=list(map(int,next(f).split()));assert row[2]==2;ids=row[5:];assert min(ids)>0 and max(ids)<=nn
  if row[1]==2:
   assert len(ids)==3;tri[a]=ids;patch[a]=row[3];a+=1
  else:
   assert row[1]==4 and len(ids)==4 and names[(3,row[3])]=='fluid';tet[c]=ids;c+=1
 assert a==nf and c==len(tet) and next(f).strip()=='$EndElements'
for tag in np.unique(patch):
 name=names[(2,int(tag))];got=canonical(tri[patch==tag]);expected=canonical(source_tri[labels==name]);assert np.array_equal(got[order(got)],expected[order(expected)])
result=chain(tet,tri);total=0.;minimum=float('inf')
for start in range(0,len(tet),10000):
 p=points[tet[start:start+10000]];v=np.linalg.det(p[:,1:]-p[:,:1])/6;assert np.isfinite(v).all() and (v>0).all();total+=float(v.sum());minimum=min(minimum,float(v.min()))
result.update({'tetrahedra':len(tet),'source_coordinates_exact':True,'source_patch_triangles_exact':True,'all_internal_faces_cancel':True,'duplicate_tetrahedra':False,'all_float64_volumes_positive':True,'float64_volume_sum_m3':total,'minimum_float64_cell_volume_m3':minimum,'mesh_admitted':False,'mesh_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
assert result==json.loads((r/'export-chain-verification.json').read_text())
print(json.dumps(result))
