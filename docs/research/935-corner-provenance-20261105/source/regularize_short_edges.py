"""One deterministic bounded numerical edge-contraction pass.

The exact feature graph may contract: its mapped curves receive the same
complete displacement bound as the surface. This is a separate study mesh,
never a physical feature classification or replacement printing master.
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


def save(path,value):
    with path.open("x") as stream:stream.write(json.dumps(value,indent=2)+"\n")


def module(path):
    spec=importlib.util.spec_from_file_location("frozen_triangle_quality",path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("mesh","tags","geometry-report","parent-preservation","provenance-report","repository","output"):
        parser.add_argument("--"+name,type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(mode=0o700,exist_ok=False);started=time.monotonic()
    expected="7adc8f931feac78eb6298e1415c8d49b7a92bced5dde5dbcc6bc3afd2e9e947f"
    assert sha(args.mesh)==expected
    assert sha(args.tags)=="877cf9c6638eb388755a378775428c7a5067409f166b3ea38d03b1837f2fae2f"
    admission=json.loads(args.geometry_report.read_text());prior=json.loads(args.parent_preservation.read_text())
    provenance=json.loads(args.provenance_report.read_text())
    assert admission["input_sha256"]==expected and admission["geometry_export_gate_passed"] and admission["intersection_pairs"]==0
    assert prior["candidate_sha256"]==expected and prior["preservation_checks_passed"]
    assert provenance["inputs_sha256"]["mesh"]==expected
    assert provenance["sector_faces"]["by_origin"]["inherited_parent_triangle"]==170
    helper_path=args.repository/"docs/research/935-mesh-admission-20261104/source/trial_bounded_quad_flips.py"
    helper=module(helper_path)
    plan={"source_sha256":sha(Path(__file__)),"input_sha256":expected,"tags_sha256":sha(args.tags),
          "geometry_report_sha256":sha(args.geometry_report),"parent_preservation_sha256":sha(args.parent_preservation),
          "provenance_report_sha256":sha(args.provenance_report),"quality_helper_sha256":sha(helper_path),
          "scope":"Bounded numerical feature regularization; graph contractions allowed and explicitly measured; not a print master",
          "upstream_verdict":"Hypothetical envelope; exact indexed acquired identity for limiting sectors unestablished; exact planar-sector shape floor incompatible",
          "passes":1,"initial_edge_candidates_only":True,"deterministic_current_topology_recheck":True,
          "maximum_original_vertex_displacement_mm":.0029,"cumulative_surface_limit_mm":.01,
          "prior_correspondence_bound_mm":prior["composed_complete_surface_correspondence_bound_mm"],
          "preserve_cap_plane_membership":True,"reject_normal_reversal":True,
          "forced_face_mean_ratio_bin":.01,"forced_face_reduction_min_fraction":.5,
          "bad_face_bin":.01,"bad_face_count_must_not_increase":True,"relative_volume_limit":.0001,
          "exact_feature_graph_required":False,"parameter_sweep":False,"new_paid_compute_usd":0,
          "physics_admitted":False,"manufacturing_qualified":False}
    assert plan["prior_correspondence_bound_mm"]+.0029<=.01
    save(args.output/"plan.json",plan)
    with np.load(args.mesh,allow_pickle=False) as d:v,original=d["vertices"],d["triangles"]
    tags=np.load(args.tags,allow_pickle=False);assert len(tags)==len(original)
    f=original.copy();q=helper.qvalues(v,f);initial_forced=q**(2/3)<.01
    assert initial_forced.sum()==633
    active=np.ones(len(f),bool);uf=np.arange(len(v));groups={};overrides={}
    order=np.argsort(f.ravel(),kind="stable")
    offsets=np.r_[0,np.cumsum(np.bincount(f.ravel(),minlength=len(v)))]
    cap=np.zeros(len(v),np.uint8)
    for tag in np.unique(tags[tags>0]):
        cap[np.unique(f[tags==tag])]|=np.uint8(1<<int(tag))
    def find(vertex):
        vertex=int(vertex)
        while uf[vertex]!=vertex:
            uf[vertex]=uf[uf[vertex]];vertex=int(uf[vertex])
        return vertex
    def star(vertex):
        if vertex in overrides:return np.array(sorted(overrides[vertex]),dtype=np.int64)
        rows=np.unique(order[offsets[vertex]:offsets[vertex+1]]//3)
        return rows[active[rows]]
    proposals=[];covered=np.zeros(len(f),bool)
    for source in np.unique(f[initial_forced]):
        rows=star(int(source));neighbours=np.unique(f[rows]);neighbours=neighbours[neighbours!=source]
        distance=np.linalg.norm(v[neighbours]-v[source],axis=1)
        eligible=(distance<=.0029)&((cap[neighbours]&cap[source])==cap[source])
        for target,length in zip(neighbours[eligible],distance[eligible]):
            proposals.append((float(length),int(source),int(target)))
        if eligible.any():covered[rows]=True
    proposals.sort()
    upper=int((covered&initial_forced).sum())
    save(args.output/"upstream-coverage.json",{"initial_directed_candidates":len(proposals),
         "optimistic_forced_faces_affected":upper,"required_improvements":317,
         "plane_membership_constraints_included":True,"ignores_all_other_rejections":True})
    if upper<317:
        save(args.output/"producer.json",{"terminal":"coverage_rejected_before_contractions","coverage_upper":upper,
             "quality_gate_passed":False,"geometry_modified":False,"accepted_for_meshing":False})
        print("Coverage rejected before contractions",upper,flush=True);return
    accepted=[];reasons={name:0 for name in ("retired_endpoint","not_edge","plane_membership","distance","link","normal","quality")}
    initial_bad=int((q<.01).sum());initial_minimum=float(q.min())
    for length,old_source,old_target in proposals:
        source,target=old_source,old_target
        if find(source)!=source or find(target)!=target:
            reasons["retired_endpoint"]+=1;continue
        sr,tr=star(source),star(target)
        common=np.intersect1d(sr,tr)
        if len(common)!=2:reasons["not_edge"]+=1;continue
        if (cap[source]&cap[target])!=cap[source]:reasons["plane_membership"]+=1;continue
        source_group=groups.get(source,[source]);target_group=groups.get(target,[target])
        if np.linalg.norm(v[np.array(source_group)]-v[target],axis=1).max()>.0029:
            reasons["distance"]+=1;continue
        ns=np.setdiff1d(np.unique(f[sr]),[source]);nt=np.setdiff1d(np.unique(f[tr]),[target])
        opposite=np.setdiff1d(np.unique(f[common]),[source,target])
        if len(opposite)!=2 or not np.array_equal(np.intersect1d(ns,nt),opposite):
            reasons["link"]+=1;continue
        before=f[sr].copy();after=before.copy();after[after==source]=target
        keep=(after[:,0]!=after[:,1])&(after[:,1]!=after[:,2])&(after[:,2]!=after[:,0])
        if int((~keep).sum())!=2 or not keep.any():reasons["link"]+=1;continue
        new=after[keep];old=before[keep]
        old_normal=np.cross(v[old[:,1]]-v[old[:,0]],v[old[:,2]]-v[old[:,0]])
        new_normal=np.cross(v[new[:,1]]-v[new[:,0]],v[new[:,2]]-v[new[:,0]])
        if np.any(np.einsum("ij,ij->i",old_normal,new_normal)<=0):reasons["normal"]+=1;continue
        new_q=helper.qvalues(v,new);old_q=q[sr]
        improvement=int((old_q**(2/3)<.01).sum())-int((new_q**(2/3)<.01).sum())
        if (improvement<1 or (new_q<.01).sum()>(old_q<.01).sum()
                or new_q.min()<old_q.min()*(1-1e-10)):
            reasons["quality"]+=1;continue
        # Update all affected stars before the next initial candidate is checked.
        old_vertices=np.unique(before)
        for vertex in old_vertices:
            current=set(map(int,star(int(vertex))))
            current.difference_update(map(int,sr));overrides[int(vertex)]=current
        kept_rows=sr[keep];dead=sr[~keep]
        f[kept_rows]=new;active[dead]=False;q[kept_rows]=new_q
        for row,face in zip(kept_rows,new):
            for vertex in face:overrides[int(vertex)].add(int(row))
        uf[source]=target;groups[target]=target_group+source_group;groups.pop(source,None)
        cap[target]|=cap[source]
        accepted.append((source,target,improvement,len(source_group),float(np.linalg.norm(v[np.array(source_group)]-v[target],axis=1).max())))
    mapping=np.arange(len(v))
    for source,_,_,_,_ in accepted:mapping[source]=find(source)
    mapped=mapping[original]
    keep=(mapped[:,0]!=mapped[:,1])&(mapped[:,1]!=mapped[:,2])&(mapped[:,2]!=mapped[:,0])
    assert np.array_equal(keep,active) and np.array_equal(mapped[keep],f[active])
    used=np.unique(mapped[keep]);old_to_new=np.full(len(v),-1,dtype=np.int64);old_to_new[used]=np.arange(len(used))
    candidate=old_to_new[mapped[keep]];vertices=v[used]
    final_q=helper.qvalues(vertices,candidate)
    displacement=np.linalg.norm(v-v[mapping],axis=1);assert displacement.max()<=.0029
    np.savez_compressed(args.output/"candidate.npz",vertices=vertices,triangles=candidate)
    np.save(args.output/"candidate-tags.npy",tags[keep])
    np.savez_compressed(args.output/"private-collapse-map.npz",mapping=mapping,used_source_vertices=used,
        surviving_source_face_ids=np.flatnonzero(keep),records=np.asarray(accepted,float).reshape(-1,5))
    after_forced=int((final_q**(2/3)<.01).sum());reduction=1-after_forced/int(initial_forced.sum())
    result={"terminal":"candidate_constructed","candidate_sha256":sha(args.output/"candidate.npz"),
            "contractions":len(accepted),"removed_triangles":int((~keep).sum()),"remaining_vertices":len(vertices),
            "remaining_triangles":len(candidate),"before_forced_faces":int(initial_forced.sum()),"after_forced_faces":after_forced,
            "forced_face_reduction_fraction":reduction,"quality_gate_passed":reduction>=.5,
            "bad_faces_before":initial_bad,"bad_faces_after":int((final_q<.01).sum()),
            "minimum_face_quality_before":initial_minimum,"minimum_face_quality_after":float(final_q.min()),
            "maximum_original_vertex_displacement_mm":float(displacement.max()),"rejections":reasons,
            "independent_proof_and_native_audit_pending":True,"accepted_for_meshing":False,
            "physics_admitted":False,"manufacturing_qualified":False,"seconds":time.monotonic()-started}
    save(args.output/"producer.json",result);print(json.dumps(result),flush=True)


if __name__=="__main__":main()
