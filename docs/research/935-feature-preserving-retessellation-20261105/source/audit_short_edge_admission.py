"""Audit whether one bounded free-vertex edge-collapse pass can meet the target.

This is a coverage upper bound, not a collapse proposal or geometry edit.
It retains the original conditioned input after the failed quad-flip trial.
"""
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


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("parent","baseline","tags","feature-verifier","output"):
        parser.add_argument("--"+name,type=Path,required=True)
    args=parser.parse_args(); args.output.mkdir(mode=0o700,exist_ok=False); started=time.monotonic()
    assert sha(args.parent)=="7adc8f931feac78eb6298e1415c8d49b7a92bced5dde5dbcc6bc3afd2e9e947f"
    assert sha(args.baseline)=="05159cdbf903729da5b8556d2ff2c2d29680a45c2b4bd42b34e031a122205594"
    assert sha(args.tags)=="877cf9c6638eb388755a378775428c7a5067409f166b3ea38d03b1837f2fae2f"
    policy={"scope":"Upstream feasibility audit only; no collapse or mesh execution",
            "parent_sha256":sha(args.parent),"baseline_sha256":sha(args.baseline),
            "tags_sha256":sha(args.tags),"source_sha256":sha(Path(__file__)),
            "feature_verifier_sha256":sha(args.feature_verifier),
            "one_pass_initial_edge_set_only":True,"source_vertex_must_not_touch_required_feature":True,
            "maximum_endpoint_displacement_mm":.0029,"forced_face_target_reduction_fraction":.5,
            "parameter_sweep":False,"geometry_modified":False,"new_paid_compute_usd":0}
    (args.output/"plan.json").write_text(json.dumps(policy,indent=2)+"\n")
    spec=importlib.util.spec_from_file_location("independent_feature_contract",args.feature_verifier)
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    with np.load(args.parent,allow_pickle=False) as data:v,f=data["vertices"],data["triangles"]
    with np.load(args.baseline,allow_pickle=False) as data:bv,bf=data["vertices"],data["triangles"]
    tags=np.load(args.tags,allow_pickle=False)
    _,_,baseline_features=helper.features(bv,bf,tags)
    del bv,bf
    _,_,parent_features=helper.features(v,f,tags)
    required=np.union1d(baseline_features,parent_features)
    np.save(args.output/"private-required-feature-keys.npy",required)
    feature_vertices=np.zeros(len(v),bool)
    feature_vertices[required//len(v)]=True;feature_vertices[required%len(v)]=True
    q,_=helper.measure(v,f);forced=q**(2/3)<.01; assert forced.sum()==633
    fixed_per_face=feature_vertices[f].sum(axis=1)
    bad_ids=np.flatnonzero(forced)
    free_vertices=np.unique(f[forced]);free_vertices=free_vertices[~feature_vertices[free_vertices]]
    # Vertex stars from the complete initial triangulation, not only bad faces.
    order=np.argsort(f.ravel(),kind="stable")
    offsets=np.r_[0,np.cumsum(np.bincount(f.ravel(),minlength=len(v)))]
    covered=np.zeros(len(f),bool); sources=[]; directed_candidates=0
    for vertex in free_vertices:
        rows=np.unique(order[offsets[vertex]:offsets[vertex+1]]//3)
        neighbours=np.unique(f[rows]);neighbours=neighbours[neighbours!=vertex]
        distance=np.linalg.norm(v[neighbours]-v[vertex],axis=1)
        eligible=neighbours[distance<=.0029]
        if len(eligible):
            directed_candidates+=len(eligible);sources.append(vertex);covered[rows]=True
    maximum_affected=int((covered&forced).sum())
    # A collapse can change a face only when that face contains its removed vertex.
    # Ignoring link, geometry and disjointness tests makes this an optimistic bound.
    result={"source_sha256":sha(Path(__file__)),"parent_sha256":sha(args.parent),
            "feature_verifier_sha256":sha(args.feature_verifier),
            "required_feature_edges":len(required),"required_feature_vertices":int(feature_vertices.sum()),
            "forced_faces":len(bad_ids),"forced_retained_skin":int((forced&(tags==0)).sum()),
            "forced_assumed_caps":int((forced&(tags>0)).sum()),
            "fixed_vertices_per_forced_face":{str(k):int((fixed_per_face[forced]==k).sum()) for k in range(4)},
            "free_vertices_on_forced_faces":len(free_vertices),"eligible_source_vertices":len(sources),
            "eligible_directed_short_edges":int(directed_candidates),
            "optimistic_maximum_forced_faces_affected":maximum_affected,
            "optimistic_maximum_reduction_fraction":maximum_affected/len(bad_ids),
            "required_faces_to_improve":int(np.ceil(.5*len(bad_ids))),
            "coverage_cannot_meet_target":bool(maximum_affected<np.ceil(.5*len(bad_ids))),
            "upper_bound_scope":"One pass using initial mesh edges, removing only vertices outside the required feature set, each to an existing adjacent vertex within 0.0029 mm; ignores all other rejection conditions",
            "geometry_modified":False,"collapse_quality_proved":False,
            "physics_admitted":False,"manufacturing_qualified":False,
            "seconds":time.monotonic()-started}
    np.save(args.output/"private-eligible-source-vertices.npy",np.asarray(sources,dtype=np.int64))
    (args.output/"report.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result),flush=True)


if __name__=="__main__":
    main()
