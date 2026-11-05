"""Independently verify the composed surface correspondence and protection."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with path.open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("trial","parent","tags","repository","output"):
        p.add_argument("--"+key,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(mode=0o700,exist_ok=False);started=time.monotonic()
    assert sha(a.parent)=="05159cdbf903729da5b8556d2ff2c2d29680a45c2b4bd42b34e031a122205594"
    assert sha(a.tags)=="877cf9c6638eb388755a378775428c7a5067409f166b3ea38d03b1837f2fae2f"
    plan=json.loads((a.trial/"plan.json").read_text())
    assert plan["quad_patch_bound_limit_mm"]==.0049 and plan["vertex_displacement_limit_mm"]==.0049
    assert plan["composed_surface_correspondence_limit_mm"]==.01 and plan["bad_face_reduction_min_fraction"]==.5
    helper=a.repository/"docs/research/935-mesh-admission-20261104/source/verify_bounded_quad_flips.py"
    spec=importlib.util.spec_from_file_location("independent_quad_bounds",helper)
    verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
    points=np.array([[0,0,0],[1,1,.009],[0,1,0],[1,0,0]],float)
    original=np.array([[0,1,2],[1,0,3]]);replacement=np.array([[2,0,3],[3,1,2]])
    expected=.009/(2*np.sqrt(1+.009**2/2))
    record=np.array([[0,1,0,1,2,3,expected,.5,.5]])
    assert abs(verifier.verify_patches(points,original,replacement,record)[0]-expected)<1e-12
    forged=record.copy();forged[:,6]+=.001
    for bad in (forged,np.repeat(record,2,axis=0)):
        try:verifier.verify_patches(points,original,replacement,bad)
        except ValueError:pass
        else:raise AssertionError("Forged quad provenance accepted")
    with np.load(a.parent,allow_pickle=False) as data:v,f=data["vertices"],data["triangles"]
    with np.load(a.trial/"flipped.npz",allow_pickle=False) as data:fv,ff=data["vertices"],data["triangles"]
    with np.load(a.trial/"candidate.npz",allow_pickle=False) as data:cv,cf=data["vertices"],data["triangles"]
    assert np.array_equal(fv,v) and np.array_equal(cf,ff) and cv.shape==v.shape and cf.shape==f.shape
    assert np.isfinite(cv).all()
    with np.load(a.trial/"private-quad-provenance.npz",allow_pickle=False) as data:records=data["records"]
    bounds=verifier.verify_patches(v,f,ff,records)
    phase_a=float(bounds.max()) if len(bounds) else 0.
    assert phase_a<=.0049+1e-12
    phase_b=float(np.linalg.norm(cv-v,axis=1).max())
    assert phase_b<=.0049+1e-12 and phase_a+phase_b<=.01
    # Reconstruct protection from the original input, not the producer's mask.
    normal=np.empty((len(f),3));before=np.empty(len(f));after=np.empty(len(f))
    source_volume=0.;candidate_volume=0.;origin=v[0]
    for start in range(0,len(f),100000):
        q=v[f[start:start+100000]];r=cv[cf[start:start+100000]];n=len(q)
        cross=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]);norm=np.linalg.norm(cross,axis=1)
        normal[start:start+n]=cross/norm[:,None]
        s=sum(np.sum((q[:,i]-q[:,j])**2,axis=1) for i,j in [(0,1),(1,2),(2,0)])
        before[start:start+n]=2*np.sqrt(3)*norm/s
        cross_r=np.cross(r[:,1]-r[:,0],r[:,2]-r[:,0])
        denominator=sum(np.sum((r[:,i]-r[:,j])**2,axis=1) for i,j in [(0,1),(1,2),(2,0)])
        after[start:start+n]=2*np.sqrt(3)*np.linalg.norm(cross_r,axis=1)/denominator
        source_volume+=float(np.einsum('ij,ij->',q[:,0]-origin,np.cross(q[:,1]-origin,q[:,2]-origin))/6)
        candidate_volume+=float(np.einsum('ij,ij->',r[:,0]-origin,np.cross(r[:,1]-origin,r[:,2]-origin))/6)
    keys=np.concatenate([np.minimum(f[:,i],f[:,j])*len(v)+np.maximum(f[:,i],f[:,j]) for i,j in [(0,1),(1,2),(2,0)]])
    ordering=np.argsort(keys,kind='stable');ordered=keys[ordering]
    assert np.array_equal(ordered[::2],ordered[1::2]) and not np.any(ordered[1:-1:2]==ordered[2::2])
    paired=(ordering%len(f)).reshape(-1,2)
    crease=np.sum(normal[paired[:,0]]*normal[paired[:,1]],axis=1)<np.cos(np.pi/6)
    protected=np.load(a.tags,allow_pickle=False)>0
    protected[np.unique(paired[crease])]=True
    protected_ids=np.flatnonzero(protected)
    assert np.array_equal(protected_ids,np.load(a.trial/"private-protected-face-ids.npy",allow_pickle=False))
    locked=np.zeros(len(v),bool);locked[np.unique(f[protected])]=True
    assert np.array_equal(locked,np.load(a.trial/"private-locked-vertices.npy",allow_pickle=False))
    assert np.array_equal(cf[protected],f[protected]) and np.array_equal(cv[locked],v[locked])
    bad_before=int((before<.01).sum());bad_after=int((after<.01).sum())
    relative=abs(candidate_volume/source_volume-1)
    assert relative<=.0001
    result={"source_sha256":sha(Path(__file__)),"helper_sha256":sha(helper),"plan_sha256":sha(a.trial/"plan.json"),
            "parent_sha256":sha(a.parent),"candidate_sha256":sha(a.trial/"candidate.npz"),
            "all_changed_face_pairs_independently_verified":True,"nonoverlapping_changed_patches":len(records),
            "exact_postflip_coordinate_preservation":True,"exact_postrelocation_connectivity_preservation":True,
            "protected_faces":int(protected.sum()),"protected_vertices":int(locked.sum()),
            "all_original_protected_rows_and_vertices_unchanged":True,
            "independent_quad_correspondence_bound_mm":phase_a,"all_vertex_displacements_max_mm":phase_b,
            "composed_complete_surface_correspondence_bound_mm":phase_a+phase_b,
            "bound_scope":"Both directions through common projected quad subdivisions, then unchanged-face barycentric vertex correspondence; double precision, not interval arithmetic or metrology",
            "bad_faces_before":bad_before,"bad_faces_after":bad_after,
            "bad_face_reduction_fraction":1-bad_after/bad_before,"quality_reduction_gate_passed":bad_after<=bad_before*.5,
            "forced_face_ceiling_below_0p01_before":int((before**(2/3)<.01).sum()),
            "forced_face_ceiling_below_0p01_after":int((after**(2/3)<.01).sum()),
            "minimum_face_quality_before":float(before.min()),"minimum_face_quality_after":float(after.min()),
            "source_volume_mm3":source_volume,"candidate_volume_mm3":candidate_volume,"relative_volume_change":relative,
            "preservation_checks_passed":True,"native_geometry_check_pending":True,"accepted_for_meshing":False,
            "controls":{"known_twisted_quad":True,"forged_bound_refused":True,"overlapping_patches_refused":True},
            "physical_acceptance":False,"manufacturing_qualified":False,"seconds":time.monotonic()-started}
    with (a.output/"report.json").open("x") as stream:stream.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__=="__main__":main()
