"""Independently verify changed patches and reconstruct required feature edges."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()


def module(path):
    spec = importlib.util.spec_from_file_location("independent_patch_verifier",path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def features(vertices, faces, tags):
    # Interleaved edges and unique/inverse incidence, independent of producer masks.
    directed = faces[:,[[0,1],[1,2],[2,0]]].reshape(-1,2)
    edges, first, inverse, counts = np.unique(np.sort(directed,axis=1),axis=0,
        return_index=True,return_inverse=True,return_counts=True)
    assert np.all(counts == 2)
    assert not np.any(np.bincount(inverse, weights=np.sign(directed[:,1]-directed[:,0])))
    face_a = first//3
    # Face IDs and their sums are far below the exact binary64 integer bound.
    sums = np.bincount(inverse,weights=np.repeat(np.arange(len(faces)),3))
    assert np.array_equal(sums,sums.astype(np.int64))
    face_b = sums.astype(np.int64)-face_a
    xyz = vertices[faces]
    normal = np.cross(xyz[:,1]-xyz[:,0], xyz[:,2]-xyz[:,0])
    normal /= np.linalg.norm(normal,axis=1)[:,None]
    sine = np.linalg.norm(np.cross(normal[face_a],normal[face_b]),axis=1)
    cosine = np.einsum("ij,ij->i",normal[face_a],normal[face_b])
    angles = np.arctan2(sine,cosine)
    required = (angles > np.pi/6) | (tags[face_a] != tags[face_b])
    keys = edges[:,0]*len(vertices)+edges[:,1]
    return keys, edges[required], keys[required]


def measure(vertices, faces):
    quality = np.empty(len(faces)); volume = 0.; origin = vertices[0]
    for start in range(0,len(faces),100000):
        xyz = vertices[faces[start:start+100000]]
        edges = xyz-np.roll(xyz,1,axis=1)
        area = np.linalg.norm(np.cross(edges[:,0],-edges[:,1]),axis=1)
        quality[start:start+len(xyz)] = 2*np.sqrt(3)*area/np.sum(edges**2,axis=(1,2))
        points = xyz-origin
        volume += float(np.einsum("ij,ij->",points[:,0],np.cross(points[:,1],points[:,2]))/6)
    assert (quality > 0).all()
    return quality, volume


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("trial","parent","baseline","tags","parent-preservation","repository","output"):
        parser.add_argument("--"+name,type=Path,required=True)
    args = parser.parse_args(); args.output.mkdir(mode=0o700,exist_ok=False); started=time.monotonic()
    assert sha(args.parent) == "7adc8f931feac78eb6298e1415c8d49b7a92bced5dde5dbcc6bc3afd2e9e947f"
    assert sha(args.baseline) == "05159cdbf903729da5b8556d2ff2c2d29680a45c2b4bd42b34e031a122205594"
    assert sha(args.tags) == "877cf9c6638eb388755a378775428c7a5067409f166b3ea38d03b1837f2fae2f"
    plan=json.loads((args.trial/"plan.json").read_text())
    assert plan["passes"] == 1 and plan["per_patch_correspondence_limit_mm"] == .0029
    assert plan["forced_face_reduction_min_fraction"] == .5
    verifier_path=args.repository/"docs/research/935-mesh-admission-20261104/source/verify_bounded_quad_flips.py"
    verifier=module(verifier_path)
    # A known nonplanar flip and two deliberate provenance defects.
    points=np.array([[0,0,0],[1,1,.009],[0,1,0],[1,0,0]],float)
    original=np.array([[0,1,2],[1,0,3]]); replacement=np.array([[2,0,3],[3,1,2]])
    expected=.009/(2*np.sqrt(1+.009**2/2)); record=np.array([[0,1,0,1,2,3,expected,.5,.5]])
    assert abs(verifier.verify_patches(points,original,replacement,record)[0]-expected)<1e-12
    forged=record.copy(); forged[:,6]+=.001
    for bad in (forged,np.repeat(record,2,axis=0)):
        try: verifier.verify_patches(points,original,replacement,bad)
        except ValueError: pass
        else: raise AssertionError("Invalid provenance accepted")
    with np.load(args.parent,allow_pickle=False) as data: vertices,faces=data["vertices"],data["triangles"]
    with np.load(args.baseline,allow_pickle=False) as data: bv,bf=data["vertices"],data["triangles"]
    with np.load(args.trial/"candidate.npz",allow_pickle=False) as data: cv,cf=data["vertices"],data["triangles"]
    tags=np.load(args.tags,allow_pickle=False)
    assert np.array_equal(vertices,cv) and faces.shape == cf.shape
    with np.load(args.trial/"private-flip-provenance.npz",allow_pickle=False) as data: records=data["records"]
    bounds=verifier.verify_patches(vertices,faces,cf,records)
    assert not len(bounds) or bounds.max() <= .0029
    rows=records[:,:2].astype(np.int64); assert np.all(tags[rows[:,0]] == tags[rows[:,1]])
    before,volume_before=measure(vertices,faces); after,volume_after=measure(cv,cf)
    baseline_keys,baseline_edges,baseline_required=features(bv,bf,tags)
    assert np.array_equal(cv[np.unique(baseline_edges)],bv[np.unique(baseline_edges)])
    print("Baseline feature contract reconstructed",flush=True)
    del baseline_keys,bv,bf
    parent_keys,parent_edges,parent_required=features(vertices,faces,tags)
    required=np.union1d(baseline_required,parent_required)
    print("Parent feature contract reconstructed",flush=True)
    candidate_keys,_,_=features(cv,cf,tags)
    assert np.isin(required,candidate_keys,assume_unique=True).all()
    supplied=np.load(args.trial/"private-feature-edge-keys.npy",allow_pickle=False)
    assert np.isin(required,supplied,assume_unique=True).all()
    before_forced=int((before**(2/3)<.01).sum()); after_forced=int((after**(2/3)<.01).sum())
    relative=abs(volume_after/volume_before-1); assert relative <= .0001
    prior=json.loads(args.parent_preservation.read_text())
    assert prior["candidate_sha256"] == sha(args.parent) and prior["preservation_checks_passed"]
    bound=float(bounds.max()) if len(bounds) else 0.
    total=prior["composed_complete_surface_correspondence_bound_mm"]+bound; assert total <= .01
    result={"source_sha256":sha(Path(__file__)),"independent_quad_helper_sha256":sha(verifier_path),
            "plan_sha256":sha(args.trial/"plan.json"),"candidate_sha256":sha(args.trial/"candidate.npz"),
            "parent_sha256":sha(args.parent),"baseline_sha256":sha(args.baseline),
            "all_vertices_unchanged_exactly":True,"all_changed_patches_independently_verified":True,
            "nonoverlapping_patch_count":len(records),"all_changed_pairs_preserve_construction_tag":True,
            "baseline_required_feature_edges":len(baseline_required),"parent_required_feature_edges":len(parent_required),
            "required_feature_union":len(required),"all_required_edges_and_endpoints_preserved_exactly":True,
            "feature_masks_reconstructed_without_producer_mask":True,
            "independent_patch_bound_mm":bound,"cumulative_correspondence_bound_mm":total,
            "bound_scope":"Double-precision analytical bidirectional patch correspondence; not metrology",
            "before_forced_faces":before_forced,"after_forced_faces":after_forced,
            "forced_face_reduction_fraction":1-after_forced/before_forced,
            "forced_face_quality_gate_passed":after_forced<=before_forced*.5,
            "bad_faces_before":int((before<.01).sum()),"bad_faces_after":int((after<.01).sum()),
            "bad_face_count_not_increased":bool((after<.01).sum()<=(before<.01).sum()),
            "minimum_face_quality_before":float(before.min()),"minimum_face_quality_after":float(after.min()),
            "source_volume_mm3":volume_before,"candidate_volume_mm3":volume_after,"relative_volume_change":relative,
            "preservation_passed":True,"controls":{"known_quad":True,"forged_bound_refused":True,"overlap_refused":True},
            "accepted_for_meshing":False,"physics_admitted":False,"manufacturing_qualified":False,
            "seconds":time.monotonic()-started}
    with (args.output/"report.json").open("x") as stream: stream.write(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result),flush=True)


if __name__ == "__main__":
    main()
