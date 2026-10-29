"""Fixed ten-nanometre inward seam reconstruction; preserve original vertices."""
import hashlib,json,signal,sys,time
from pathlib import Path
from functools import lru_cache
import numpy as np
from scipy.sparse import csr_matrix
import manifold3d as mf
sys.path.insert(0,'parts/993-eng-carrier-0001/source/design-20261016/convergence-20261022');from reconstruct_core_envelopes import canonical_surface
w=Path('work/carrier-interface-20261028');out=w/'ported-seams-001';assert not out.exists();out.mkdir();signal.alarm(180);start=time.monotonic();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();paths=[w/'full-reconstructed-p10-001/candidate.npz',w/'ported-carrier-001/candidate.npz',w/'ported-residue-001/new-vertices.npz'];b=np.load(paths[0]);c=np.load(paths[1]);a=np.load(paths[2]);bv,bf=b['vertices'],b['triangles'].astype(np.int64);cv,cf=c['vertices'].copy(),c['triangles'];epsilon=1e-5;eligible=a['distances']<1e-7;indices=a['indices'][eligible];closest=a['closest_points'][eligible];faces=a['closest_faces'][eligible];assert np.abs(cv[indices,0]).min()>66.5 and np.abs(cv[indices,0]).max()<258.5
(out/'contract.json').write_text(json.dumps(dict(source_sha256=sha(Path(__file__)),input_sha256={str(p):sha(p)for p in paths},inward_displacement_mm=epsilon,eligible_new_vertex_distance_max_mm=1e-7,maximum_candidate_mass_kg=1.3,strict_no_added_material_required=True,independent_checks_pending=True,manufacturing_authorized=False),indent=2)+'\n')
incidence=csr_matrix((np.ones(bf.size,dtype=np.uint8),(bf.ravel(),np.repeat(np.arange(len(bf)),3))),shape=(len(bv),len(bf)))
@lru_cache(None)
def normal(i):
 x=bv[bf[i]];n=np.cross(x[1]-x[0],x[2]-x[0]);length=np.linalg.norm(n);assert length>0;return n/length
minimum_alignment=1.
for vertex,face,q in zip(indices,faces,closest):
 ids=bf[face];x=bv[ids];cross=np.cross(x[1]-x[0],x[2]-x[0]);area=np.dot(cross,cross);bary=np.array([np.dot(np.cross(x[1]-q,x[2]-q),cross),np.dot(np.cross(x[2]-q,x[0]-q),cross),np.dot(np.cross(x[0]-q,x[1]-q),cross)])/area;near=np.flatnonzero(bary<1e-6);adjacent={int(face)}
 if len(near)==1:
  edge=ids[[j for j in range(3)if j!=near[0]]];adjacent.update(set(incidence.getrow(edge[0]).indices)&set(incidence.getrow(edge[1]).indices))
 elif len(near)>=2:adjacent.update(incidence.getrow(ids[np.argmax(bary)]).indices)
 ns=np.array([normal(int(i))for i in adjacent]);inward=ns.sum(0);inward/=np.linalg.norm(inward);alignment=float((ns@inward).min());minimum_alignment=min(minimum_alignment,alignment);assert alignment>.05;cv[vertex]=q-epsilon*inward
candidate=mf.Manifold(mf.Mesh64(cv,cf));assert candidate.status()==mf.Error.NoError;mesh=candidate.to_mesh64();vv=np.array(mesh.vert_properties)[:,:3];ff=np.array(mesh.tri_verts,dtype=np.uint64);same=all(np.array_equal(a,b)for a,b in zip(canonical_surface(cv,cf),canonical_surface(vv,ff)));np.savez_compressed(out/'candidate.npz',vertices=vv,triangles=ff);before=mf.Manifold(mf.Mesh64(bv,bf.astype(np.uint64)));added=candidate-before;shells=candidate.decompose();positive=sum(s.volume()>0 for s in shells);negative=sum(s.volume()<0 for s in shells);passed=added.is_empty()and same and positive==1 and negative==0 and candidate.volume()*4.42e-6<=1.3
report=dict(status='inward_seam_native_checks_passed'if passed else'inward_seam_native_checks_refused',reseated_vertices=len(indices),maximum_displacement_mm=float(np.linalg.norm(cv[indices]-c['vertices'][indices],axis=1).max()),minimum_incident_normal_alignment=minimum_alignment,no_added_material=added.is_empty(),added_volume_mm3=added.volume(),added_triangles=len(added.to_mesh64().tri_verts),positive_material_shells=positive,negative_closed_void_shells=negative,oriented_triangle_import_exact=same,nominal_mass_kg=candidate.volume()*4.42e-6,output_sha256=sha(out/'candidate.npz'),elapsed_seconds=time.monotonic()-start,independent_embedding_check_passed=False,manufacturing_authorized=False);(out/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));signal.alarm(0)
