from pathlib import Path
from fractions import Fraction as Q
import numpy as np,json,hashlib,struct,math
r=Path(__file__).resolve().parent;w=r.parent
load=lambda p:json.loads(p.read_text())
proposal=load(r/'proposal.json');partition=load(r/'partition.json');distance=load(r/'distance.json');topology=load(r/'material-topology.json');embedding=load(r/'embedding.json');domain=load(r/'decoded-001/independent-domain.json');proof=load(r/'proof-terminal.json');previous=load(w/'fast-quadric-coarsening-001/r3-positive-001/acceptance.json');controls=load(r/'export-regression.json')
assert proposal['candidate_sha256']==embedding['input_sha256']==proof['candidate_sha256']==hashlib.sha256((r/'candidate.meshbin').read_bytes()).hexdigest()
assert topology['status']=='closed_oriented_vertex_manifold'and topology['boundary_components']==1 and topology['reentrant_edges_above_degrees']['45']==0
assert embedding['status']=='embedding_passed'and domain['status']=='complete_strict_domain_containment_passed'and proof['returncode']==0
assert controls['status']=='deleted_face_export_regression_passed'
assert distance['status']=='complete_tiled_symmetric_envelopes_passed'and load(r/'distance-terminal.json')['returncode']==0
for name in ['source','candidate']:
 assert distance[name+'_faces_checked']==distance[name+'_faces']==partition[name+'_residual_faces']
 assert partition['common_faces']+partition[name+'_residual_faces']==partition[name+'_faces']
 p=r/(name+'.meshbin');array=(w/'fast-quadric-coarsening-001/r3-positive-001/decoded-001/candidate.npz')if name=='source'else r/'candidate.npz';z=np.load(array)
 with p.open('rb')as stream:nv,nf=struct.unpack('<QQ',stream.read(16))
 assert p.stat().st_size==16+24*(nv+nf)
 assert np.array_equal(np.memmap(p,dtype='<f8',mode='r',offset=16,shape=(nv,3)),z['vertices'])
 assert np.array_equal(np.memmap(p,dtype='<u8',mode='r',offset=16+24*nv,shape=(nf,3)),z['triangles'])
 if name=='source':assert hashlib.sha256(array.read_bytes()).hexdigest()==previous['candidate_npz_sha256']==proposal['input_sha256']
bound=Q(previous['composed_upper_bound_rational'])+Q(distance['tolerance_mm']);assert bound<Q('0.005');upper=float(bound)
if Q(upper)<bound:upper=math.nextafter(upper,math.inf)
files=[r/name for name in ['proposal.json','partition.json','distance.json','distance-terminal.json','material-topology.json','embedding.json','proof-terminal.json','export-regression.json','propose.py','check.py','distance.py']]+[r/'decoded-001/independent-domain.json',w/'tiled-exact-envelopes-001/check.cpp',w/'tiled-exact-envelopes-001/check']
result=dict(status='meshlib_coarsened_r3_positive_geometry_stage_accepted',source_faces=partition['source_faces'],candidate_faces=partition['candidate_faces'],complete_coarsening_bound_mm=distance['tolerance_mm'],composed_upper_bound_rational=str(bound),composed_bound_from_original_rounded_surface_mm=upper,original_rounded_budget_mm=.005,candidate_binary_sha256=proposal['candidate_sha256'],candidate_npz_sha256=hashlib.sha256((r/'candidate.npz').read_bytes()).hexdigest(),maximum_material_turn_degrees=-topology['worst_edges'][0]['angle_degrees'],embedding_and_original_void_containment_passed=True,whole_carrier_reassembled=False,mechanical_convergence_established=False,source_sha256={str(p.relative_to(w)):hashlib.sha256(p.read_bytes()).hexdigest()for p in files})
(r/'acceptance.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='source_sha256'}))
