"""Independently certify the complete collapse correspondence and cap constraints."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with path.open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()


def edge_keys(faces,count):
    return np.unique(np.concatenate([np.minimum(faces[:,i],faces[:,j])*count+
        np.maximum(faces[:,i],faces[:,j]) for i,j in ((0,1),(1,2),(2,0))]))


def cap_mask(count,faces,tags):
    result=np.zeros(count,np.uint8)
    for tag in np.unique(tags[tags>0]):result[np.unique(faces[tags==tag])]|=np.uint8(1<<int(tag))
    return result


def certify(v,f,tags,cv,cf,mapping,used,kept,candidate_tags,limit,feature_keys=None):
    assert mapping.shape==(len(v),) and mapping.dtype.kind in "iu"
    assert mapping.min()>=0 and mapping.max()<len(v)
    assert np.array_equal(mapping[mapping],mapping)
    assert np.array_equal(used,np.unique(used)) and np.array_equal(cv,v[used])
    inverse=np.full(len(v),-1,dtype=np.int64);inverse[used]=np.arange(len(used))
    assert np.all(inverse[mapping]>=0)
    mapped=inverse[mapping[f]]
    nondegenerate=(mapped[:,0]!=mapped[:,1])&(mapped[:,1]!=mapped[:,2])&(mapped[:,2]!=mapped[:,0])
    assert np.array_equal(kept,np.flatnonzero(nondegenerate))
    assert np.array_equal(cf,mapped[nondegenerate]) and np.array_equal(candidate_tags,tags[kept])
    distance=np.linalg.norm(v-v[mapping],axis=1);maximum=float(distance.max())
    assert maximum<=limit
    original_caps=cap_mask(len(v),f,tags)
    assert np.all((original_caps[mapping]&original_caps)==original_caps)
    keys=edge_keys(cf,len(cv))
    degenerate=mapped[~nondegenerate]
    low,high=degenerate.min(axis=1),degenerate.max(axis=1)
    segments=low!=high
    expected=low[segments]*len(cv)+high[segments]
    assert np.isin(expected,keys).all()
    result={"maximum_vertex_displacement_mm":maximum,"all_surviving_images_exact":True,
            "all_removed_face_images_in_candidate_skeleton":True,
            "cap_plane_memberships_preserved":True,"removed_faces":int((~nondegenerate).sum()),
            "preserved_vertex_coordinates_exact":True}
    if feature_keys is not None:
        original_edges=np.column_stack((feature_keys//len(v),feature_keys%len(v)))
        image=inverse[mapping[original_edges]]
        low,high=image.min(axis=1),image.max(axis=1);segments=low!=high
        assert np.isin(low[segments]*len(cv)+high[segments],keys).all()
        result.update(original_feature_edges=len(feature_keys),feature_edges_mapped_to_points=int((~segments).sum()),
            feature_vertex_coordinates_changed=int(np.any(v[np.unique(original_edges)]!=v[mapping[np.unique(original_edges)]] ,axis=1).sum()),
            every_marked_curve_image_in_candidate_skeleton=True,
            exact_feature_graph_preservation_claimed=False,
            marked_curve_bidirectional_correspondence_bound_mm=maximum)
    return result


def controls():
    v=np.array([[0.,0,0],[1.,0,0],[1.,1.,0],[0,1.,0],[.5,.5,1.]])
    f=np.array([[0,2,1],[0,3,2],[0,1,4],[1,2,4],[2,3,4],[3,0,4]])
    mapping=np.array([1,1,2,3,4]);used=np.array([1,2,3,4]);inverse=np.array([-1,0,1,2,3])
    image=inverse[mapping[f]]
    keep=np.flatnonzero((image[:,0]!=image[:,1])&(image[:,1]!=image[:,2])&(image[:,2]!=image[:,0]))
    cf=image[keep];tags=np.zeros(len(f),np.int8);features=edge_keys(f,len(v))
    certify(v,f,tags,v[used],cf,mapping,used,keep,tags[keep],1.,features)
    try:certify(v,f,tags,v[used],cf,mapping,used,keep,tags[keep],.9,features)
    except AssertionError:pass
    else:raise AssertionError("Understated displacement bound accepted")
    altered=cf.copy();altered[0]=altered[0,[0,2,1]]
    try:certify(v,f,tags,v[used],altered,mapping,used,keep,tags[keep],1.,features)
    except AssertionError:pass
    else:raise AssertionError("Altered image orientation accepted")
    cap_tags=tags.copy();cap_tags[-1]=1
    try:certify(v,f,cap_tags,v[used],cf,mapping,used,keep,cap_tags[keep],1.,features)
    except AssertionError:pass
    else:raise AssertionError("Cap membership violation accepted")
    return {"pyramid_contraction":True,"forged_bound_refused":True,"altered_face_refused":True,"cap_violation_refused":True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("trial","parent","tags","features","parent-preservation","feature-verifier","output"):
        parser.add_argument("--"+name,type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(mode=0o700,exist_ok=False);started=time.monotonic()
    assert sha(args.parent)=="7adc8f931feac78eb6298e1415c8d49b7a92bced5dde5dbcc6bc3afd2e9e947f"
    assert sha(args.tags)=="877cf9c6638eb388755a378775428c7a5067409f166b3ea38d03b1837f2fae2f"
    assert sha(args.features)=="e5087c3cd5c90208acb56adff830bb39edc58bb0d93362b9a57b5cbf944b70f3"
    plan=json.loads((args.trial/"plan.json").read_text())
    assert plan["maximum_original_vertex_displacement_mm"]==.0029
    assert plan["forced_face_reduction_min_fraction"]==.5 and not plan["exact_feature_graph_required"]
    test=controls()
    with np.load(args.parent,allow_pickle=False) as d:v,f=d["vertices"],d["triangles"]
    with np.load(args.trial/"candidate.npz",allow_pickle=False) as d:cv,cf=d["vertices"],d["triangles"]
    with np.load(args.trial/"private-collapse-map.npz",allow_pickle=False) as d:
        mapping,used,kept=d["mapping"],d["used_source_vertices"],d["surviving_source_face_ids"]
    tags=np.load(args.tags,allow_pickle=False);ct=np.load(args.trial/"candidate-tags.npy",allow_pickle=False)
    feature=np.load(args.features,allow_pickle=False)
    proof=certify(v,f,tags,cv,cf,mapping,used,kept,ct,.0029,feature)
    spec=importlib.util.spec_from_file_location("independent_triangle_measures",args.feature_verifier)
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    before,vol_before=helper.measure(v,f);after,vol_after=helper.measure(cv,cf)
    before_forced=int((before**(2/3)<.01).sum());after_forced=int((after**(2/3)<.01).sum())
    relative=abs(vol_after/vol_before-1);assert relative<=.0001
    prior=json.loads(args.parent_preservation.read_text());assert prior["candidate_sha256"]==sha(args.parent)
    total=prior["composed_complete_surface_correspondence_bound_mm"]+proof["maximum_vertex_displacement_mm"]
    assert total<=.01
    result={"source_sha256":sha(Path(__file__)),"plan_sha256":sha(args.trial/"plan.json"),
            "parent_sha256":sha(args.parent),"candidate_sha256":sha(args.trial/"candidate.npz"),
            "parent_preservation_sha256":sha(args.parent_preservation),"feature_contract_sha256":sha(args.features),
            "independent_measure_helper_sha256":sha(args.feature_verifier),**proof,
            "controls":test,"composed_complete_surface_correspondence_bound_mm":total,
            "bound_scope":"Continuous barycentric image of every source triangle; every nondegenerate image is a candidate face, every degenerate image is in its skeleton; surjective onto candidate. Stored-coordinate bound, not physical metrology.",
            "before_forced_faces":before_forced,"after_forced_faces":after_forced,
            "forced_face_reduction_fraction":1-after_forced/before_forced,
            "quality_gate_passed":after_forced<=before_forced*.5,
            "bad_faces_before":int((before<.01).sum()),"bad_faces_after":int((after<.01).sum()),
            "bad_face_count_not_increased":bool((after<.01).sum()<=(before<.01).sum()),
            "minimum_face_quality_before":float(before.min()),"minimum_face_quality_after":float(after.min()),
            "source_volume_mm3":vol_before,"candidate_volume_mm3":vol_after,"relative_volume_change":relative,
            "preservation_checks_passed":True,"native_geometry_pending":True,
            "accepted_for_meshing":False,"physics_admitted":False,"manufacturing_qualified":False,
            "seconds":time.monotonic()-started}
    (args.output/"report.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result),flush=True)


if __name__=="__main__":main()
