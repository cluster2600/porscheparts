"""Replay complete two-class pairing with scalar/exhaustive raw-source checks."""
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


def combined_selection_controls(helper):
    pairs=np.array([[0,1],[0,2],[2,3]])
    selected,_,_=helper.reciprocal_unique(pairs,[.25,.04,.09],1e-12)
    assert selected.tolist()==[1]  # The opposed-class edge can compete with same-class edges.
    for delta in (0.,5e-13):
        selected,_,ambiguous=helper.reciprocal_unique(np.array([[0,1],[0,2]]),[1.,1.+delta],1e-12)
        assert len(selected)==0 and 0 in ambiguous
    selected,_,ambiguous=helper.reciprocal_unique(np.array([[0,1],[0,2]]),[1.,1.+2e-12],1e-12)
    assert selected.tolist()==[0] and len(ambiguous)==0
    return 4


def raw_key_valid(key,raw):
    face,a,b=map(int,key);assert 0<=face<len(raw['triangles'])
    corners=list(map(int,raw['triangles'][face]));assert (a,b) in list(zip(corners,corners[1:]+corners[:1]))
    p=raw['vertices'][corners];assert np.linalg.norm(np.cross(p[1]-p[0],p[2]-p[0]))>0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('job','census','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();started=time.monotonic();job=json.loads(args.job.read_text());before=sha(args.census)
    for row in job['inputs']:assert sha(row['path'])==row['sha256']
    proof=json.loads(Path(job['parent_proof']).read_text());assert proof['mesh_sha256']==sha(job['mesh']) and proof['surface_study_checks_passed']
    origin_proof=json.loads(Path(job['initial_opposed_proof']).read_text())
    assert origin_proof['census_independently_verified'] and origin_proof['census_sha256']==sha(job['initial_opposed_census'])
    mesh,boundary,raw,history,initial,census=map(load,(job['mesh'],job['boundaries'],job['source_arrays'],job['attempt_history'],job['initial_opposed_census'],args.census))
    identity=module(job['identity_inspector'],'scalar_continuation_raw_identity')
    same=module(job['same_class_inspector'],'scalar_continuation_same_class')
    opposed=module(job['opposed_class_inspector'],'scalar_continuation_opposed_class')
    primitive_controls=same.controls(job['limits']);opposed_controls=opposed.controls(job['limits'])
    identity_controls=identity.identity_controls();selection_controls=combined_selection_controls(same)
    first=[tuple(map(int,row)) for row in initial['prior_attempted_pair_keys']]
    first += [identity.pair_key(initial['source_edge_keys'],a,b) for a,b in initial['selected_pair_edge_ids']]
    assert len(first)==len(set(first))==1705
    suffix=[]
    if job.get('continuation_registry'):
        registry=load(job['continuation_registry']);registry_proof=json.loads(Path(job['registry_proof']).read_text())
        assert registry_proof['registry_independently_verified'] and registry_proof['registry_sha256']==sha(job['continuation_registry'])
        assert registry_proof['source_sha256']==sha(job['registry_inspector'])
        assert np.array_equal(registry['global_pair_ids'],np.arange(len(registry['raw_pair_keys'])))
        suffix=[tuple(map(int,row)) for row in registry['raw_pair_keys']]
        assert np.all(registry['birth_rounds']<job['round'])
    attempted=first+suffix;assert len(attempted)==len(set(attempted))
    assert np.array_equal(attempted,history['raw_pair_keys']) and np.array_equal(attempted,census['prior_attempted_pair_keys'])
    for key in attempted:raw_key_valid(key[:3],raw);raw_key_valid(key[3:],raw)
    attempt_set=set(attempted);edges,owners=boundary['boundary'],boundary['owners'];sizes=np.diff(boundary['offsets'])
    curve_ids=np.full(len(edges),-1,dtype=np.int64);scope=[];walks=[]
    for curve in range(len(sizes)):
        a,b=boundary['offsets'][curve:curve+2];ids=boundary['cycle_edges'][a:b];curve_ids[ids]=curve
        if set(map(int,boundary['edge_origin_kind'][ids]))<={1,6,7,8,9}:
            acquired=ids[boundary['edge_origin_kind'][ids]==1]
            if len(acquired):scope.extend(map(int,acquired));walks.append(curve)
    scope=np.asarray(sorted(scope),dtype=np.int64)
    assert np.array_equal(scope,census['scope_edge_ids']) and np.array_equal(curve_ids,census['edge_curve_ids'])
    keys=np.full((len(edges),3),-1,dtype=np.int64);normals=np.zeros((len(edges),3))
    for edge in scope:keys[edge],normals[edge]=identity.original_key(mesh,edges[edge],owners[edge],raw)
    assert np.array_equal(keys,census['source_edge_keys'])
    broad=same.exhaustive_pairs(mesh['points'][edges].mean(axis=1),curve_ids,scope,job['limits']['midpoint_search_radius_nominal_mm'],job['limits']['independent_pair_block_rows'],job['limits']['maximum_same_curve_search_pairs'])
    assert np.array_equal(broad,census['same_curve_radius_pairs'])
    seen=[];small=[];evaluated=[]
    for index,(a,b) in enumerate(broad):
        if identity.pair_key(keys,a,b) in attempt_set:seen.append(index)
        elif sizes[curve_ids[a]]<=4:small.append(index)
        else:evaluated.append((int(a),int(b)))
    evaluated=np.asarray(evaluated,dtype=np.int64).reshape(-1,2)
    assert np.array_equal(seen,census['prior_excluded_indices']) and np.array_equal(small,census['unchanged_small_walk_excluded_indices'])
    assert np.array_equal(evaluated,census['evaluated_pair_edge_ids'])
    eligible=[];classes=[];flags=[];scores=[];counts=[Counter(),Counter()]
    for a,b in evaluated:
        reason0,result0=same.inspect_pair(mesh['points'],edges,normals,a,b,job['limits'])
        reason1,result1=opposed.inspect_pair(mesh['points'],edges,normals,a,b,job['limits'])
        counts[0][reason0]+=1;counts[1][reason1]+=1;assert not (result0 is not None and result1 is not None)
        for cls,result in enumerate((result0,result1)):
            if result is not None:eligible.append((a,b));classes.append(cls);flags.append(result[0]);scores.append(result[1])
    eligible=np.asarray(eligible,dtype=np.int64).reshape(-1,2);flags=np.asarray(flags,dtype=bool).reshape(-1,2);classes=np.asarray(classes,dtype=np.int8)
    assert np.array_equal(eligible,census['eligible_pair_edge_ids']) and np.array_equal(classes,census['eligible_pair_classes'])
    assert np.array_equal(flags,census['eligible_pair_diagonal_flags']) and np.allclose(scores,census['eligible_pair_scores_squared'],rtol=0,atol=1e-15)
    selected,best,ambiguous=same.reciprocal_unique(eligible,scores,job['limits']['squared_gap_score_ambiguity_tolerance'])
    assert np.array_equal(selected,census['selected_eligible_pair_indices']) and np.array_equal(eligible[selected],census['selected_pair_edge_ids'])
    assert np.array_equal(classes[selected],census['selected_pair_classes']) and np.array_equal(curve_ids[eligible[selected,0]],census['selected_pair_curve_ids'])
    complete_best=np.full(len(edges),-1,dtype=np.int64)
    for edge,other in best.items():complete_best[edge]=other
    assert np.array_equal(complete_best,census['unique_best_neighbor_edge_ids']) and np.array_equal(ambiguous,census['ambiguous_edge_ids'])
    assert len(np.unique(eligible[selected]))==2*len(selected)
    halos=[];offsets=[0]
    for left,right in eligible[selected]:
        corners=edges[[left,right]].ravel();halo=np.flatnonzero(np.isin(mesh['triangles'],corners).any(axis=1))
        halos.extend(halo);offsets.append(len(halos))
    for row in job['inputs']:assert sha(row['path'])==row['sha256']
    assert sha(args.census)==before;args.output.mkdir(mode=0o700,exist_ok=False)
    target=args.output/'private-complete-selected-halos.npz';np.savez_compressed(target,halo_offsets=np.asarray(offsets,dtype=np.int64),halo_face_rows=np.asarray(halos,dtype=np.int64))
    report=dict(source_sha256=sha(__file__),job_sha256=sha(args.job),mesh_sha256=sha(job['mesh']),census_sha256=before,
        initial_raw_pair_history=1705,continuation_history_pairs=len(suffix),all_attempted_raw_pair_identities=len(attempted),all_historical_raw_facets_and_directed_corners_verified=True,
        source_scope_walks=len(walks),source_scope_edges=len(scope),exhaustive_same_walk_radius_pairs=len(broad),prior_attempts_excluded=len(seen),unchanged_small_cap_pairs_excluded=len(small),
        same_scalar_stage_counts=dict(counts[0]),opposed_scalar_stage_counts=dict(counts[1]),eligible_pairs=len(eligible),selected_pairs=len(selected),selected_class_counts=dict(Counter(map(str,classes[selected]))),
        same_class_controls_passed=primitive_controls,opposed_class_controls_passed=opposed_controls,raw_identity_controls_passed=identity_controls,combined_selection_controls_passed=selection_controls,
        complete_selected_incident_halos=len(selected),halo_sha256=sha(target),producer_imported=False,spatial_tree_used=False,census_independently_verified=True,
        geometry_modified=False,construction_admission_is_exploratory_only=True,physical_acceptance=False,manufacturing_authorized=False,seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)


if __name__=='__main__':
    main()
