"""Independently inspect acquired-edge identity, exclusions and exhaustive pair coverage."""
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
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    with np.load(path, allow_pickle=False) as data:
        return {key:data[key] for key in data.files}


def original_key(mesh, edge, owner, raw):
    assert mesh['inferred_surface_kind'][owner] == 0
    original = int(mesh['original_face_ids'][owner]); assert 0 <= original < len(raw['triangles'])
    source_nodes = raw['triangles'][original]; source_points = raw['vertices'][source_nodes]
    lookup = {tuple(point):int(node) for point,node in zip(source_points,source_nodes)}
    assert len(lookup) == 3
    face = mesh['triangles'][owner]; points = mesh['points'][face]
    recovered = [lookup[tuple(point)] for point in points]
    assert any(recovered == list(np.roll(source_nodes, rotation)) for rotation in range(3))
    directed = [(int(a),int(b)) for a,b in zip(face,np.roll(face,-1))]
    assert directed.count(tuple(map(int,edge))) == 1
    a, b = [lookup[tuple(mesh['points'][node])] for node in edge]
    assert (a,b) in list(zip(map(int,source_nodes),map(int,np.roll(source_nodes,-1))))
    normal = np.cross(source_points[1]-source_points[0], source_points[2]-source_points[0])
    length = np.linalg.norm(normal); assert length > 0
    return (original,a,b), normal/length


def pair_key(keys, a, b):
    left, right = tuple(map(int,keys[a])), tuple(map(int,keys[b]))
    assert min(left+right) >= 0
    return min(left,right)+max(left,right)


def identity_controls():
    raw = dict(vertices=np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,0.],[1.,0.,0.],[0.,-1.,0.]]),
               triangles=np.array([[0,1,2],[4,3,5]]))
    mesh = dict(points=raw['vertices'], triangles=raw['triangles'], original_face_ids=np.array([0,1]), inferred_surface_kind=np.array([0,0]))
    first, _ = original_key(mesh,[0,1],0,raw); second, _ = original_key(mesh,[4,3],1,raw)
    assert first != second and np.array_equal(mesh['points'][[0,1]],mesh['points'][[3,4]])
    permutation = np.array([2,4,0,5,1,3]); inverse = np.argsort(permutation)
    remapped = dict(mesh,points=mesh['points'][permutation],triangles=inverse[mesh['triangles']])
    assert original_key(remapped,inverse[[0,1]],0,raw)[0] == first
    assert original_key(remapped,inverse[[4,3]],1,raw)[0] == second
    keys=np.array([first,second]); assert pair_key(keys,0,1)==pair_key(keys,1,0)
    assert pair_key(keys,0,1) in {pair_key(keys,1,0)}
    bad=dict(mesh,inferred_surface_kind=np.array([1,0]))
    try:
        original_key(bad,[0,1],0,raw)
    except AssertionError:
        pass
    else:
        raise AssertionError('inferred_owner_was_not_refused')
    return 5


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('job','census','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();started=time.monotonic();job=json.loads(args.job.read_text());before=sha(args.census)
    for row in job['inputs']:
        assert sha(row['path'])==row['sha256']
    proof=json.loads(Path(job['parent_proof']).read_text())
    assert proof['mesh_sha256']==sha(job['mesh']) and proof['surface_study_checks_passed']
    assert proof['intersection_pairs']==proof['nonmanifold_used_vertices']==0
    old_proof=json.loads(Path(job['prior_census_proof']).read_text())
    assert old_proof['census_independently_verified'] and old_proof['census_sha256']==sha(job['prior_census'])
    assert old_proof['mesh_sha256']==sha(job['prior_mesh'])
    mesh,boundary,raw,previous_mesh,previous_boundary,previous,census=map(load,(job['mesh'],job['boundaries'],job['source_arrays'],
        job['prior_mesh'],job['prior_boundaries'],job['prior_census'],args.census))
    spec=importlib.util.spec_from_file_location('frozen_independent_pair_inspection',job['independent_helper'])
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    identity_count=identity_controls();geometry_count=helper.controls(job['limits'])
    edges,owners=boundary['boundary'],boundary['owners'];curve_ids=np.full(len(edges),-1,dtype=np.int64);scope=[];scope_walks=[]
    sizes=np.diff(boundary['offsets'])
    for curve in range(len(sizes)):
        a,b=boundary['offsets'][curve:curve+2];ids=boundary['cycle_edges'][a:b];curve_ids[ids]=curve
        origins=set(map(int,boundary['edge_origin_kind'][ids]))
        if origins <= {1,6}:
            acquired=ids[boundary['edge_origin_kind'][ids]==1]
            if len(acquired):scope.extend(map(int,acquired));scope_walks.append(curve)
    scope=np.array(sorted(scope),dtype=np.int64)
    assert len(sizes)==1226 and len(edges)==96153 and len(scope_walks)==1192
    assert np.array_equal(scope,census['scope_edge_ids']) and np.array_equal(curve_ids,census['edge_curve_ids'])
    keys=np.full((len(edges),3),-1,dtype=np.int64);normals=np.zeros((len(edges),3))
    for edge in scope:keys[edge],normals[edge]=original_key(mesh,edges[edge],owners[edge],raw)
    assert np.array_equal(keys,census['source_edge_keys']) and len(np.unique(keys[scope],axis=0))==len(scope)
    prior_keys=np.full((len(previous_boundary['boundary_local_nodes']),3),-1,dtype=np.int64)
    for edge in np.unique(previous['selected_pair_edge_ids']):
        prior_keys[edge],_=original_key(previous_mesh,previous_boundary['boundary_local_nodes'][edge],previous_boundary['boundary_face_rows'][edge],raw)
    historical=[pair_key(prior_keys,a,b) for a,b in previous['selected_pair_edge_ids']]
    assert len(set(historical))==len(historical)==1315 and np.array_equal(historical,census['prior_attempted_pair_keys'])
    attempted=set(historical)
    broad=helper.exhaustive_pairs(mesh['points'][edges].mean(axis=1),curve_ids,scope,job['limits']['midpoint_search_radius_nominal_mm'],
                                  job['limits']['independent_pair_block_rows'],job['limits']['maximum_same_curve_search_pairs'])
    assert np.array_equal(broad,census['same_curve_radius_pairs'])
    prior_exclusions=[];small_exclusions=[];remaining=[]
    for row,(a,b) in enumerate(broad):
        if pair_key(keys,a,b) in attempted:
            prior_exclusions.append(row)
        elif sizes[curve_ids[a]] <= job['maximum_unchanged_whole_cap_edges_to_exclude']:
            small_exclusions.append(row)
        else:
            remaining.append((a,b))
    assert np.array_equal(prior_exclusions,census['prior_excluded_broad_indices'])
    assert np.array_equal(small_exclusions,census['unchanged_small_walk_excluded_broad_indices'])
    remaining=np.array(remaining,dtype=np.int64).reshape(-1,2)
    assert np.array_equal(remaining,census['evaluated_pair_edge_ids'])
    eligible=[];flags=[];scores=[];reasons=Counter()
    for a,b in remaining:
        reason,result=helper.inspect_pair(mesh['points'],edges,normals,a,b,job['limits']);reasons[reason]+=1
        if result is not None:
            eligible.append((a,b));flags.append(result[0]);scores.append(result[1])
    eligible=np.array(eligible,dtype=np.int64).reshape(-1,2);flags=np.array(flags,dtype=bool).reshape(-1,2)
    assert np.array_equal(eligible,census['eligible_pair_edge_ids']) and np.array_equal(flags,census['eligible_pair_diagonal_flags'])
    assert np.allclose(scores,census['eligible_pair_scores_squared'],rtol=0,atol=1e-15)
    selected,best,ambiguous=helper.reciprocal_unique(eligible,scores,job['limits']['squared_gap_score_ambiguity_tolerance'])
    assert np.array_equal(selected,census['selected_eligible_pair_indices'])
    assert np.array_equal(eligible[selected],census['selected_pair_edge_ids']) and np.array_equal(ambiguous,census['ambiguous_edge_ids'])
    for edge,other in best.items():assert census['unique_best_neighbor_edge_ids'][edge]==other
    assert len(np.unique(eligible[selected]))==2*len(selected)
    assert all(pair_key(keys,a,b) not in attempted for a,b in eligible[selected])
    for row in job['inputs']:
        assert sha(row['path'])==row['sha256']
    assert sha(args.census)==before;args.output.mkdir(mode=0o700,exist_ok=False)
    report=dict(source_sha256=sha(__file__),job_sha256=sha(args.job),census_sha256=before,mesh_sha256=sha(job['mesh']),
        independently_recovered_current_source_edges=len(scope),independently_recovered_prior_pair_identities=len(historical),
        exhaustive_same_walk_radius_pairs=len(broad),excluded_prior_attempts=len(prior_exclusions),excluded_unchanged_small_walk_pairs=len(small_exclusions),
        ordered_geometry_stage_counts=dict(reasons),eligible_pairs=len(eligible),selected_pairs=len(selected),
        identity_controls_passed=identity_count,geometric_controls_passed=geometry_count,producer_imported=False,spatial_tree_used=False,
        census_independently_verified=True,constructor_admission_is_only_for_bounded_hypothesis_trials=True,
        geometry_modified=False,physical_acceptance=False,manufacturing_authorized=False,seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)


if __name__=='__main__':
    main()
