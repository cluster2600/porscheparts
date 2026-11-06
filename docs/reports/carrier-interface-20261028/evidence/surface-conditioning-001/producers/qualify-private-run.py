"""Bind full-part mesh checks to complete-face partitioned fidelity receipts."""
import hashlib,json,signal,sys
from pathlib import Path
import numpy as np,manifold3d as mf
sys.path.insert(0,'parts/993-eng-carrier-0001/source/design-20261016/convergence-20261022');from reconstruct_core_envelopes import canonical_surface
w=Path('work/carrier-interface-20261028');source=w/'conditioned-short-edges-002';out=w/'conditioned-ported-carrier-004';assert not out.exists();out.mkdir();signal.alarm(180);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();inputs={}
def read(p):
 inputs[str(p)]=sha(p);return json.loads(p.read_text())
archive=source/'analysis/candidate.npz';reference=w/'ported-seams-002/candidate.npz';z=np.load(archive);old=np.load(reference);v,f=z['vertices'],z['triangles'];rv,rf=old['vertices'],old['triangles'];inputs[str(archive)]=sha(archive);inputs[str(reference)]=sha(reference);native=read(source/'analysis/protected-assessment.json');assert native['candidate_sha256']==sha(archive)and native['status']=='native_protected_and_connectivity_checks_passed';assert all(x['oriented_triangles_exact']for x in native['protected']);assert native['native_oriented_roundtrip_exact']and native['positive_material_shells']==1 and native['negative_closed_void_shells']==0
independent=w/'conditioned-short-edges-independent-002';surface=read(independent/'output/assessment.json');terminal=read(independent/'actual-terminal.json');plan=read(independent/'plan.json');raw=source/'output/candidate.mesh64';assert plan['input_sha256'][str(raw.resolve())]==sha(raw);assert terminal['actual_returncode']==0 and terminal['inputs_unchanged']and terminal['container_removed']and not surface['first_self_intersects']and surface['first_triangles']==len(f)
with raw.open()as stream:nv,nf=map(int,stream.readline().split());backv=np.loadtxt(stream,max_rows=nv);backf=np.loadtxt(stream,dtype=np.uint64)
assert np.array_equal(v,backv)and np.array_equal(f,backf);partition=source/'fidelity-partitions';coverage=read(partition/'coverage.json');assert coverage['input_reference_sha256']==sha(reference)and coverage['input_candidate_sha256']==sha(archive);_,inv=np.unique(np.vstack([rv,v]),axis=0,return_inverse=True)
def keys(f,ids):
 q=ids[f];start=q.argmin(1);q=np.take_along_axis(q,(start[:,None]+np.arange(3))%3,axis=1);return np.ascontiguousarray(q).view('V24').ravel()
rkeys=keys(rf,inv[:len(rv)]);ckeys=keys(f,inv[len(rv):]);rcovered=np.zeros(len(rf),bool);ccovered=np.zeros(len(f),bool);bounds=[]
for patch in coverage['patches']:
 rank=patch['rank'];ip=partition/f'indices-{rank}.npz';inputs[str(ip)]=sha(ip);assert sha(ip)==patch['indices_sha256'];indices=np.load(ip);ri=indices['reference_faces'];ci=indices['candidate_faces'];assert ri.min()>=0 and ri.max()<len(rf)and ci.min()>=0 and ci.max()<len(f);rcovered[ri]=True;ccovered[ci]=True
 for label,vertices,faces,selection in [('reference',rv,rf,ri),('candidate',v,f,ci)]:
  mesh=partition/patch[label]['file'];inputs[str(mesh)]=sha(mesh);assert sha(mesh)==patch[label]['sha256'];used,new=np.unique(faces[selection],return_inverse=True)
  with mesh.open()as stream:pnv,pnf=map(int,stream.readline().split());pv=np.loadtxt(stream,max_rows=pnv);pf=np.loadtxt(stream,dtype=np.uint64)
  assert pnf==len(selection)and np.array_equal(vertices[used],pv)and np.array_equal(new.reshape(-1,3),pf)
 check=w/f'fast-envelope-final-fidelity-r{rank}-001';report=read(check/'output/assessment.json');receipt=read(check/'actual-terminal.json');p=read(check/'plan.json');assert receipt['actual_returncode']==0 and receipt['inputs_unchanged']and receipt['container_removed'];assert report['status']=='symmetric_complete_triangle_envelope_containment_passed'and report['controls_passed']and report['complete_faces_checked']and report['epsilon_mm']==.01 and report['candidate_triangles_not_certified']==0 and report['reference_triangles_not_certified']==0;assert report['reference_faces']==len(ri)and report['candidate_faces']==len(ci)
 for label in ['reference','candidate']:
  mp=partition/patch[label]['file'];assert p['input_sha256'][str(mp)]==sha(mp)
 bounds.append(report['epsilon_mm'])
assert len(bounds)==4;outside_r=np.sort(rkeys[~rcovered]);outside_c=np.sort(ckeys[~ccovered]);assert np.array_equal(outside_r,outside_c)and len(outside_r)==coverage['outside_faces'];assert hashlib.sha256(outside_r.tobytes()).hexdigest()==coverage['outside_face_roster_sha256'];body=mf.Manifold(mf.Mesh64(v,f));assert body.status()==mf.Error.NoError and body.volume()*4.42e-6<=1.3
copy=body.to_mesh64();assert all(np.array_equal(a,b)for a,b in zip(canonical_surface(v,f),canonical_surface(np.array(copy.vert_properties)[:,:3],np.array(copy.tri_verts,dtype=np.uint64))));assert len(body.decompose())==1;target=out/'candidate.npz';target.write_bytes(archive.read_bytes());t=v[f];area=np.linalg.norm(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]),axis=1);edge=np.linalg.norm(np.stack([t[:,1]-t[:,0],t[:,2]-t[:,1],t[:,0]-t[:,2]],1),axis=2).max(1);vv=v.astype(np.float32).astype(np.float64);tt=vv[f];collapsed=int((np.linalg.norm(np.cross(tt[:,1]-tt[:,0],tt[:,2]-tt[:,0]),axis=1)==0).sum())
from fractions import Fraction
import math
seed=w/'conditioned-ported-carrier-003';seed_report=read(seed/'assessment.json');assert seed_report['status']=='conditioned_ported_geometry_checked'and seed_report['output_sha256']==sha(seed/'candidate.npz');assert seed_report['source_sha256']==sha(w/'qualify_cgal_local_remesh_003.py')
for path,digest in seed_report['input_sha256'].items():
 assert sha(Path(path))==digest;inputs[path]=digest
seed_coverage=read(w/'cgal-local-remesh-trial-003/fidelity-partitions/coverage.json');tight_bounds=[]
for patch in seed_coverage['patches']:
 rank=patch['rank'];check=w/f'fast-envelope-tight-fidelity-003-r{rank}-001';r=read(check/'output/assessment.json');terminal=read(check/'actual-terminal.json');plan=read(check/'plan.json');assert r['status']=='symmetric_complete_triangle_envelope_containment_passed'and r['controls_passed']and r['complete_faces_checked']and r['epsilon_mm']==.003 and r['candidate_triangles_not_certified']==0 and r['reference_triangles_not_certified']==0;assert terminal['actual_returncode']==0 and terminal['inputs_unchanged']and terminal['container_removed'];assert r['reference_faces']==patch['reference']['faces']and r['candidate_faces']==patch['candidate']['faces']
 for label in ['reference','candidate']:
  path=w/'cgal-local-remesh-trial-003/fidelity-partitions'/patch[label]['file'];assert plan['input_sha256'][str(path)]==sha(path)==patch[label]['sha256']
 tight_bounds.append(r['epsilon_mm'])
assert len(tight_bounds)==4
ledger=read(w/'conditioning-exact-replay-003/assessment.json');assert ledger['status']=='exact_regional_conditioning_bounds_replayed'and ledger['source_sha256']==sha(Path('parts/993-eng-carrier-0001/source/design-20261016/convergence-20261022/replay_surface_conditioning_bounds.py'))
for path,digest in ledger['input_sha256'].items():
 assert sha(Path(path))==digest;inputs[path]=digest
assert ledger['input_sha256'][str(seed/'candidate.npz')]==sha(seed/'candidate.npz');replayed=np.load(w/'conditioning-exact-replay-003/candidate.npz');assert np.array_equal(replayed['vertices'],v)and np.array_equal(replayed['triangles'],f);inputs[str(w/'conditioning-exact-replay-003/candidate.npz')]=sha(w/'conditioning-exact-replay-003/candidate.npz');exact=ledger['whole_surface_additional_bound_exact'];combined=Fraction(3,1000)+Fraction(int(exact['numerator']),int(exact['denominator']));bound=float(combined)
if Fraction(bound)<combined:bound=math.nextafter(bound,math.inf)
assert bound<=.01
report=dict(status='conditioned_ported_geometry_checked',output_sha256=sha(target),vertices=len(v),triangles=len(f),nominal_mass_kg=body.volume()*4.42e-6,protected_original_oriented_triangles_exact=True,final_oriented_triangle_roundtrip_exact=True,independent_complete_surface_check_passed=True,positive_material_shells=1,negative_closed_void_shells=0,complete_surface_fidelity_bound_mm=bound,maximum_allowed_surface_change_mm=.01,fidelity_method='Complete conservative FastEnvelope containment, exact outside rosters, and independently replayed regional rational edit bounds',outside_oriented_triangles_exact=len(outside_r),formal_interval_certificate=False,direct_final_envelope_mm=max(bounds),remesh_seed_complete_envelope_mm=max(tight_bounds),additional_regional_edit_bound_mm=ledger['whole_surface_additional_change_upper_mm'],maximum_triangle_aspect_ratio=float((edge**2/area).max()),triangles_above_aspect100=int((edge**2/area>100).sum()),float32_collapsed_triangles=collapsed,float32_maximum_vertex_displacement_mm=float(np.linalg.norm(vv-v,axis=1).max()),gpu_queries_qualified=False,complete_carrier_mechanics_converged=False,powder_drainability_demonstrated=False,manufacturing_authorized=False,input_sha256=inputs,source_sha256=sha(Path(__file__)));(out/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');signal.alarm(0);print(json.dumps({k:v for k,v in report.items()if k!='input_sha256'}))
