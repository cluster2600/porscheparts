from pathlib import Path
import hashlib,importlib.util,json,struct,sys,time
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
reader=ROOT/'twins/962-cylinder-head-f0/source/mesh_head.py';stl=ROOT/'work/962-family/bore-95-run-001/inspected-bound-002/solid.stl';indexed=ROOT/'work/962-engineering/analysis-envelope-025-003/exact-input.bin'
pins={'reader':'69c8012e99057e384d44d6971d41f0e2cc7197a978120a7c566b0ad5a6477da5','STL':'ba7a0e28dade659550705e9737177c64c7f6fecd8d86d01e31732d7e739cd906','indexed':'894ece6e63d99684fd7c8710caf73132cd73731ac8bc667548c21c85962d4c95'}
for key,p in [('reader',reader),('STL',stl),('indexed',indexed)]:assert sha(p)==pins[key]
spec=importlib.util.spec_from_file_location('original_STL_reader',reader);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
t=time.monotonic();raw,points,faces=module.read_binary_stl(stl)
with indexed.open('rb') as h:magic,nv,nf=struct.unpack('<8sQQ',h.read(24))
assert magic==b'962SURF1' and indexed.stat().st_size==24+24*(nv+nf)
ip=np.memmap(indexed,mode='r',dtype='<f8',offset=24,shape=(nv,3));iff=np.memmap(indexed,mode='r',dtype='<u8',offset=24+24*nv,shape=(nf,3))
assert np.array_equal(points,ip) and np.array_equal(faces,iff)
dtype=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attribute','<u2')]);source=np.memmap(stl,mode='r',dtype=dtype,offset=84,shape=(nf,))
checked=0
for start in range(0,nf,65536):
 exact=ip[iff[start:start+65536]];original=np.asarray(source['vertices'][start:start+65536],dtype=np.float64)
 assert np.array_equal(exact,original);checked+=len(exact)
assert checked==1804706 and nv==902145
for key,p in [('reader',reader),('STL',stl),('indexed',indexed)]:assert sha(p)==pins[key]
r={'schema':'962-original-indexed-identity/v1','status':'full_original_coordinate_and_oriented_triangle_identity_passed','source_sha256':pins,'all_indexed_points_equal_existing_reader':True,'all_indexed_face_indices_equal_existing_reader':True,'direct_original_STL_ordered_oriented_coordinate_triangles_checked':checked,'triangle_order_winding_and_multiplicity_unchanged':True,'canonical_oriented_coordinate_multiset_identity_follows_from_stronger_ordered_identity':True,'coordinate_policy':'Exact binary64 values of original IEEEfloat32 coordinates; signed zero compared numerically. No fitting, rounding, welding or sampled comparison.','vertices':nv,'triangles':nf,'source_inputs_unchanged':True,'runtime':{'executable_sha256':sha(Path(sys.executable)),'python':sys.version,'NumPy':np.__version__},'verifier_source_sha256':sha(Path(__file__)),'wall_seconds':time.monotonic()-t,'no_remeshing_or_head_algorithm_executed':True,'engineering_accepted':False}
with (OUT/'original-indexed-identity.json').open('x') as h:json.dump(r,h,indent=2);h.write('\n')
print(json.dumps(r,indent=2))
