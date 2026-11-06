"""Enumerate genuinely unattempted acquired pairs in one fixed two-class graph."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def load(path):
    with np.load(path,allow_pickle=False) as data:
        return {key:data[key] for key in data.files}


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


def combine(same_pairs,same_flags,same_scores,opposed_pairs,opposed_flags,opposed_scores):
    pairs=np.concatenate((same_pairs,opposed_pairs)).reshape(-1,2)
    classes=np.r_[np.zeros(len(same_pairs),dtype=np.int8),np.ones(len(opposed_pairs),dtype=np.int8)]
    flags=np.concatenate((same_flags,opposed_flags)).reshape(-1,2)
    scores=np.r_[same_scores,opposed_scores]
    order=np.lexsort((pairs[:,1],pairs[:,0]));pairs=pairs[order]
    assert len(np.unique(pairs,axis=0))==len(pairs),'geometric_classes_must_be_disjoint'
    return pairs,classes[order],flags[order],scores[order]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('job','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();job=json.loads(args.job.read_text());started=time.monotonic()
    assert job['schema']=='935-fixed-two-class-pairing-census-1'
    for row in job['inputs']:assert sha(row['path'])==row['sha256']
    proof=json.loads(Path(job['parent_proof']).read_text())
    assert proof['mesh_sha256']==sha(job['mesh']) and proof['surface_study_checks_passed']
    assert proof.get('intersection_pairs',proof.get('whole_mesh_intersection_pairs'))==0 and proof['nonmanifold_used_vertices']==0
    mesh,boundary,raw,history=map(load,(job['mesh'],job['boundaries'],job['source_arrays'],job['attempt_history']))
    identity=module(job['identity_producer'],'frozen_vector_raw_keys')
    same=module(job['same_class_producer'],'frozen_same_facing_class')
    opposed=module(job['opposed_class_producer'],'frozen_opposed_material_class')
    prior=history['raw_pair_keys'];prior_set=set(map(tuple,prior.tolist()));assert len(prior_set)==len(prior)
    edges,owners=boundary['boundary'],boundary['owners'];curve_sizes=np.diff(boundary['offsets'])
    curve_ids=np.full(len(edges),-1,dtype=np.int64);scope=[];walks=[]
    for curve in range(len(curve_sizes)):
        a,b=boundary['offsets'][curve:curve+2];ids=boundary['cycle_edges'][a:b];curve_ids[ids]=curve
        if set(map(int,boundary['edge_origin_kind'][ids])) <= {1,6,7,8,9}:
            acquired=ids[boundary['edge_origin_kind'][ids]==1]
            if len(acquired):scope.extend(map(int,acquired));walks.append(curve)
    scope=np.array(sorted(scope),dtype=np.int64);keys=np.full((len(edges),3),-1,dtype=np.int64);normals=np.zeros((len(edges),3))
    keys[scope],normals[scope]=identity.source_edge_keys(mesh,edges,owners,raw,scope)
    assert len(np.unique(keys[scope],axis=0))==len(scope)
    broad,global_envelope,same_envelope=same.enumerate_same_curve_pairs(mesh['points'][edges].mean(axis=1),curve_ids,scope,job['limits'])
    pair_keys=identity.canonical_pair_keys(keys,broad)
    attempted=np.array([tuple(map(int,row)) in prior_set for row in pair_keys],dtype=bool)
    small=(curve_sizes[curve_ids[broad[:,0]]]<=4)&~attempted
    evaluated=broad[~attempted&~small]
    reasons0,indices0,flags0,scores0=same.qualify(mesh['points'],edges,normals,evaluated,job['limits'])
    reasons1,indices1,flags1,scores1=opposed.classify(mesh['points'],edges,normals,evaluated,job['limits'],same.triangle_alignment)
    eligible,classes,flags,scores=combine(evaluated[indices0],flags0,scores0,evaluated[indices1],flags1,scores1)
    selected,best,ambiguous=same.mutual_unique(eligible,scores,len(edges),job['limits']['squared_gap_score_ambiguity_tolerance'])
    assert len(np.unique(eligible[selected]))==2*len(selected)
    assert not any(tuple(row) in prior_set for row in identity.canonical_pair_keys(keys,eligible[selected]).tolist())
    args.output.mkdir(mode=0o700,exist_ok=False);target=args.output/'private-continuation-pair-census.npz'
    np.savez_compressed(target,scope_edge_ids=scope,edge_curve_ids=curve_ids,source_edge_keys=keys,
        prior_attempted_pair_keys=prior,same_curve_radius_pairs=broad,prior_excluded_indices=np.flatnonzero(attempted),
        unchanged_small_walk_excluded_indices=np.flatnonzero(small),evaluated_pair_edge_ids=evaluated,
        eligible_pair_edge_ids=eligible,eligible_pair_classes=classes,eligible_pair_diagonal_flags=flags,eligible_pair_scores_squared=scores,
        selected_eligible_pair_indices=selected,selected_pair_edge_ids=eligible[selected],selected_pair_curve_ids=curve_ids[eligible[selected,0]],
        selected_pair_classes=classes[selected],unique_best_neighbor_edge_ids=best,ambiguous_edge_ids=np.flatnonzero(ambiguous))
    for row in job['inputs']:assert sha(row['path'])==row['sha256']
    result=dict(source_sha256=sha(__file__),job_sha256=sha(args.job),mesh_sha256=sha(job['mesh']),census_sha256=sha(target),
        complete_walks=len(curve_sizes),complete_boundary_edges=len(edges),source_scope_walks=len(walks),source_scope_edges=len(scope),
        prior_attempted_pairs=len(prior),global_search_envelope_pairs=global_envelope,same_walk_search_envelope_pairs=same_envelope,
        exact_same_walk_radius_pairs=len(broad),excluded_prior_attempted_pairs=int(attempted.sum()),excluded_unchanged_small_whole_cap_pairs=int(small.sum()),
        evaluated_untried_pairs=len(evaluated),same_facing_stage_counts=reasons0,opposed_material_stage_counts=reasons1,
        eligible_pairs=len(eligible),eligible_class_counts=dict(Counter(map(str,classes))),selected_pairs=len(selected),
        selected_class_counts=dict(Counter(map(str,classes[selected]))),selected_walks=len(np.unique(curve_ids[eligible[selected,0]])),
        ambiguous_edges=int(ambiguous.sum()),selected_width_nominal_mm=dict(minimum=float(np.sqrt(scores[selected]).min()),maximum=float(np.sqrt(scores[selected]).max())) if len(selected) else None,
        original_class_thresholds_unchanged=True,combined_graph_selection_is_a_new_versioned_policy=True,
        raw_normals_from_actual_acquired_owners_only=True,geometry_modified=False,constructor_admission_pending_independent_check=True,
        physical_acceptance=False,manufacturing_authorized=False,seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)


if __name__=='__main__':
    main()
