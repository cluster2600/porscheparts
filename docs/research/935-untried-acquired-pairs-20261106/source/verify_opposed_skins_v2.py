"""Independent scalar/exhaustive replay of an opposed-skin read-only hypothesis audit."""
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


def inspect_pair(points,edges,normals,left,right,limits):
    a,b=map(int,edges[left]);c,d=map(int,edges[right]);nodes=[a,b,c,d]
    if len(set(nodes))!=4 or len({tuple(points[node]) for node in nodes})!=4:
        return 'shared_vertex_or_coordinate',None
    gaps=[points[d]-points[a],points[c]-points[b],points[b]-points[c],points[a]-points[d]]
    lengths=[np.linalg.norm(gap) for gap in gaps]
    score=max(lengths[0]**2,lengths[1]**2)
    if max(lengths)>limits['maximum_cross_endpoint_distance_nominal_mm']:
        return 'cross_endpoint_support_distance',None
    first=points[b]-points[a];second=points[d]-points[c]
    first/=np.linalg.norm(first);second/=np.linalg.norm(second)
    if np.dot(first,second)>limits['maximum_tangent_dot']:
        return 'directed_tangent_alignment',None
    nl,nr=normals[left],normals[right]
    if np.dot(nl,nr)>limits['maximum_opposed_skin_normal_dot']:
        return 'acquired_owner_normals_not_opposed',None
    for gap,length,normal in zip(gaps,lengths,(nl,nl,nr,nr)):
        if length==0 or np.dot(gap/length,normal)>limits['maximum_material_side_gap_dot']:
            return 'gap_is_not_towards_material_side_of_both_skins',None
    bl,br=np.cross(first,nl),np.cross(second,nr)
    bl/=np.linalg.norm(bl);br/=np.linalg.norm(br)
    if np.dot(bl,br)<limits['minimum_outward_binormal_dot']:
        return 'edge_outward_binormals_incompatible',None
    flags=[]
    for patch in (((b,a,d),(b,d,c)),((b,a,c),(a,d,c))):
        good=True
        for triangle,normal in zip(patch,(bl,br)):
            x,y,z=points[list(triangle)];cross=np.cross(y-x,z-x);length=np.linalg.norm(cross)
            good &= length>0 and np.dot(cross/length,normal)>=limits['minimum_forward_wall_normal_dot']
        flags.append(bool(good))
    if not any(flags):return 'no_forward_nonzero_wall_diagonal',None
    return 'eligible',(flags,score)


def controls(limits):
    points=np.array([[0.,0.,.1],[.2,0.,.1],[.2,0.,-.1],[0.,0.,-.1]])
    edges=np.array([[0,1],[2,3]]);normals=np.array([[0.,0.,1.],[0.,0.,-1.]])
    reason,result=inspect_pair(points,edges,normals,0,1,limits)
    assert reason=='eligible' and result[0]==[True,True]
    volume=abs(float(np.dot(points[1]-points[0],np.cross(points[2]-points[0],points[3]-points[0]))))/6
    assert volume==0
    assert inspect_pair(points,edges,-normals,0,1,limits)[0]=='gap_is_not_towards_material_side_of_both_skins'
    assert inspect_pair(points,edges[:,::-1],-normals,0,1,limits)[0]=='gap_is_not_towards_material_side_of_both_skins'
    same=normals.copy();same[1]=same[0]
    assert inspect_pair(points,edges,same,0,1,limits)[0]=='acquired_owner_normals_not_opposed'
    wide=points.copy();wide[2:,2]=-.6
    assert inspect_pair(wide,edges,normals,0,1,limits)[0]=='cross_endpoint_support_distance'
    parallel=edges.copy();parallel[1]=parallel[1,::-1]
    assert inspect_pair(points,parallel,normals,0,1,limits)[0]=='directed_tangent_alignment'
    coincident=points.copy();coincident[3]=coincident[0]
    assert inspect_pair(coincident,edges,normals,0,1,limits)[0]=='shared_vertex_or_coordinate'
    return 8


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('job','census','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();job=json.loads(args.job.read_text());started=time.monotonic();before=sha(args.census)
    for row in job['inputs']:assert sha(row['path'])==row['sha256']
    proof=json.loads(Path(job['parent_proof']).read_text());assert proof['mesh_sha256']==sha(job['mesh']) and proof['surface_study_checks_passed']
    history_proof=json.loads(Path(job['attempt_history_proof']).read_text())
    assert history_proof['census_independently_verified'] and history_proof['census_sha256']==sha(job['attempt_history'])
    mesh,boundary,raw,history,census=map(load,(job['mesh'],job['boundaries'],job['source_arrays'],job['attempt_history'],args.census))
    identity=module(job['identity_inspector'],'frozen_scalar_raw_identity')
    helper=module(job['independent_geometry_helper'],'frozen_exhaustive_pairs')
    control_count=controls(job['limits']);identity_count=identity.identity_controls()
    historical=[tuple(map(int,row)) for row in history['prior_attempted_pair_keys']]
    historical += [identity.pair_key(history['source_edge_keys'],a,b) for a,b in history['selected_pair_edge_ids']]
    assert len(set(historical))==len(historical)==1488 and np.array_equal(historical,census['prior_attempted_pair_keys'])
    attempted=set(historical);edges,owners=boundary['boundary'],boundary['owners'];sizes=np.diff(boundary['offsets'])
    curve_ids=np.full(len(edges),-1,dtype=np.int64);scope=[];walks=[]
    for curve in range(len(sizes)):
        a,b=boundary['offsets'][curve:curve+2];ids=boundary['cycle_edges'][a:b];curve_ids[ids]=curve
        if set(map(int,boundary['edge_origin_kind'][ids])) <= {1,6,7}:
            acquired=ids[boundary['edge_origin_kind'][ids]==1]
            if len(acquired):scope.extend(map(int,acquired));walks.append(curve)
    scope=np.array(sorted(scope),dtype=np.int64)
    assert np.array_equal(scope,census['scope_edge_ids']) and np.array_equal(curve_ids,census['edge_curve_ids'])
    keys=np.full((len(edges),3),-1,dtype=np.int64);normals=np.zeros((len(edges),3))
    for edge in scope:keys[edge],normals[edge]=identity.original_key(mesh,edges[edge],owners[edge],raw)
    assert np.array_equal(keys,census['source_edge_keys'])
    broad=helper.exhaustive_pairs(mesh['points'][edges].mean(axis=1),curve_ids,scope,job['limits']['midpoint_search_radius_nominal_mm'],
        job['limits']['independent_pair_block_rows'],job['limits']['maximum_same_curve_search_pairs'])
    assert np.array_equal(broad,census['same_curve_radius_pairs'])
    seen=[];small=[];evaluated=[]
    for index,(a,b) in enumerate(broad):
        if identity.pair_key(keys,a,b) in attempted:seen.append(index)
        elif sizes[curve_ids[a]]<=4:small.append(index)
        else:evaluated.append((a,b))
    assert np.array_equal(seen,census['prior_excluded_indices']) and np.array_equal(small,census['unchanged_small_walk_excluded_indices'])
    evaluated=np.array(evaluated,dtype=np.int64).reshape(-1,2);assert np.array_equal(evaluated,census['evaluated_pair_edge_ids'])
    reasons=Counter();eligible=[];flags=[];scores=[]
    for a,b in evaluated:
        reason,result=inspect_pair(mesh['points'],edges,normals,a,b,job['limits']);reasons[reason]+=1
        if result is not None:eligible.append((a,b));flags.append(result[0]);scores.append(result[1])
    eligible=np.array(eligible,dtype=np.int64).reshape(-1,2);flags=np.array(flags,dtype=bool).reshape(-1,2)
    assert np.array_equal(eligible,census['eligible_pair_edge_ids']) and np.array_equal(flags,census['eligible_pair_diagonal_flags'])
    assert np.allclose(scores,census['eligible_pair_scores_squared'],rtol=0,atol=1e-15)
    selected,best,ambiguous=helper.reciprocal_unique(eligible,scores,job['limits']['squared_gap_score_ambiguity_tolerance'])
    assert np.array_equal(selected,census['selected_eligible_pair_indices']) and np.array_equal(eligible[selected],census['selected_pair_edge_ids'])
    assert np.array_equal(ambiguous,census['ambiguous_edge_ids'])
    for edge,other in best.items():assert census['unique_best_neighbor_edge_ids'][edge]==other
    assert len(np.unique(eligible[selected]))==2*len(selected)
    for row in job['inputs']:assert sha(row['path'])==row['sha256']
    assert sha(args.census)==before;args.output.mkdir(mode=0o700,exist_ok=False)
    result=dict(source_sha256=sha(__file__),job_sha256=sha(args.job),census_sha256=before,mesh_sha256=sha(job['mesh']),
        acquired_scope_edges=len(scope),complete_walks=len(sizes),exhaustive_radius_pairs=len(broad),previous_pair_identities=len(historical),
        excluded_prior_attempts=len(seen),excluded_small_whole_loop_pairs=len(small),ordered_stage_counts=dict(reasons),
        eligible_opposed_skin_pairs=len(eligible),selected_opposed_skin_pairs=len(selected),opposed_skin_controls_passed=control_count,
        raw_identity_controls_passed=identity_count,producer_imported=False,spatial_tree_used=False,census_independently_verified=True,
        geometry_modified=False,physical_normals_orientation_certified=False,physical_anatomy_accepted=False,
        constructor_admission_granted=False,manufacturing_authorized=False,seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)


if __name__=='__main__':main()
