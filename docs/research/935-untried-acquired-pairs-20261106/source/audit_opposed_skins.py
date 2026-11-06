"""Read-only opposed-skin wall hypothesis census under explicit winding assumptions."""
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


def classify(points,edges,normals,pairs,limits,triangle_alignment):
    a,b=edges[pairs[:,0]].T;c,d=edges[pairs[:,1]].T
    tangent=points[edges[:,1]]-points[edges[:,0]]
    lengths=np.linalg.norm(tangent,axis=1);valid=lengths>0;tangent[valid]/=lengths[valid,None]
    alive=np.ones(len(pairs),dtype=bool);reasons={}
    def refuse(name,ok):
        reasons[name]=int(np.count_nonzero(alive&~ok));alive[:]&=ok
    distinct=(a!=c)&(a!=d)&(b!=c)&(b!=d)
    for x,y in ((a,c),(a,d),(b,c),(b,d)):
        distinct&=np.any(points[x]!=points[y],axis=1)
    refuse('shared_vertex_or_coordinate',distinct)
    gaps=np.stack((points[d]-points[a],points[c]-points[b],points[b]-points[c],points[a]-points[d]),axis=1)
    gap_lengths=np.linalg.norm(gaps,axis=2)
    scores=np.maximum(gap_lengths[:,0]**2,gap_lengths[:,1]**2)
    refuse('cross_endpoint_support_distance',scores<=limits['maximum_cross_endpoint_distance_nominal_mm']**2)
    refuse('directed_tangent_alignment',np.sum(tangent[pairs[:,0]]*tangent[pairs[:,1]],axis=1)<=limits['maximum_tangent_dot'])
    first,second=normals[pairs[:,0]],normals[pairs[:,1]]
    refuse('acquired_owner_normals_not_opposed',np.sum(first*second,axis=1)<=limits['maximum_opposed_skin_normal_dot'])
    directions=np.zeros_like(gaps);nonzero=gap_lengths>0;directions[nonzero]=gaps[nonzero]/gap_lengths[nonzero,None]
    gap_owners=np.stack((first,first,second,second),axis=1)
    side_dots=np.sum(directions*gap_owners,axis=2)
    refuse('gap_is_not_towards_material_side_of_both_skins',np.all(side_dots<=limits['maximum_material_side_gap_dot'],axis=1))
    binormal=np.cross(tangent,normals);length=np.linalg.norm(binormal,axis=1);valid=length>0;binormal[valid]/=length[valid,None]
    left,right=binormal[pairs[:,0]],binormal[pairs[:,1]]
    refuse('edge_outward_binormals_incompatible',np.sum(left*right,axis=1)>=limits['minimum_outward_binormal_dot'])
    bound=limits['minimum_forward_wall_normal_dot']
    flags=np.c_[(triangle_alignment(points,np.c_[b,a,d],left)>=bound)&(triangle_alignment(points,np.c_[b,d,c],right)>=bound),
                (triangle_alignment(points,np.c_[b,a,c],left)>=bound)&(triangle_alignment(points,np.c_[a,d,c],right)>=bound)]
    refuse('no_forward_nonzero_wall_diagonal',np.any(flags,axis=1))
    reasons['eligible']=int(alive.sum());indices=np.flatnonzero(alive)
    return reasons,indices,flags[indices],scores[indices]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('job','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();job=json.loads(args.job.read_text());started=time.monotonic()
    for row in job['inputs']:assert sha(row['path'])==row['sha256']
    proof=json.loads(Path(job['parent_proof']).read_text());assert proof['mesh_sha256']==sha(job['mesh']) and proof['surface_study_checks_passed']
    history_proof=json.loads(Path(job['attempt_history_proof']).read_text())
    assert history_proof['census_independently_verified'] and history_proof['census_sha256']==sha(job['attempt_history'])
    mesh,boundary,raw,history=map(load,(job['mesh'],job['boundaries'],job['source_arrays'],job['attempt_history']))
    identity=module(job['identity_helper'],'frozen_acquired_identity')
    geometry=module(job['geometry_helper'],'frozen_spatial_pair_helpers')
    old_attempted=np.r_[history['prior_attempted_pair_keys'],identity.canonical_pair_keys(history['source_edge_keys'],history['selected_pair_edge_ids'])]
    attempted={tuple(map(int,row)) for row in old_attempted};assert len(attempted)==1488
    edges,owners=boundary['boundary'],boundary['owners'];sizes=np.diff(boundary['offsets'])
    curves=np.full(len(edges),-1,dtype=np.int64);scope=[];walks=[]
    for curve in range(len(sizes)):
        a,b=boundary['offsets'][curve:curve+2];ids=boundary['cycle_edges'][a:b];curves[ids]=curve
        if set(map(int,boundary['edge_origin_kind'][ids])) <= {1,6,7}:
            acquired=ids[boundary['edge_origin_kind'][ids]==1]
            if len(acquired):scope.extend(map(int,acquired));walks.append(curve)
    scope=np.array(sorted(scope),dtype=np.int64)
    keys=np.full((len(edges),3),-1,dtype=np.int64);normals=np.zeros((len(edges),3))
    keys[scope],normals[scope]=identity.source_edge_keys(mesh,edges,owners,raw,scope)
    broad,global_count,same_count=geometry.enumerate_same_curve_pairs(mesh['points'][edges].mean(axis=1),curves,scope,job['limits'])
    pair_keys=identity.canonical_pair_keys(keys,broad)
    seen=np.array([tuple(map(int,key)) in attempted for key in pair_keys],dtype=bool)
    unchanged_small=(sizes[curves[broad[:,0]]]<=4)&~seen
    evaluate=broad[~seen&~unchanged_small]
    reasons,accepted,flags,scores=classify(mesh['points'],edges,normals,evaluate,job['limits'],geometry.triangle_alignment)
    eligible=evaluate[accepted]
    selected,best,ambiguous=geometry.mutual_unique(eligible,scores,len(edges),job['limits']['squared_gap_score_ambiguity_tolerance'])
    assert len(np.unique(eligible[selected]))==2*len(selected)
    args.output.mkdir(mode=0o700,exist_ok=False)
    np.savez_compressed(args.output/'private-opposed-skin-census.npz',scope_edge_ids=scope,edge_curve_ids=curves,source_edge_keys=keys,
        prior_attempted_pair_keys=old_attempted,same_curve_radius_pairs=broad,prior_excluded_indices=np.flatnonzero(seen),
        unchanged_small_walk_excluded_indices=np.flatnonzero(unchanged_small),evaluated_pair_edge_ids=evaluate,
        eligible_pair_edge_ids=eligible,eligible_pair_diagonal_flags=flags,eligible_pair_scores_squared=scores,
        selected_eligible_pair_indices=selected,selected_pair_edge_ids=eligible[selected],selected_pair_curve_ids=curves[eligible[selected,0]],
        unique_best_neighbor_edge_ids=best,ambiguous_edge_ids=np.flatnonzero(ambiguous))
    for row in job['inputs']:assert sha(row['path'])==row['sha256']
    result=dict(source_sha256=sha(__file__),job_sha256=sha(args.job),mesh_sha256=sha(job['mesh']),
        complete_walks=len(sizes),complete_boundary_edges=len(edges),acquired_scope_walks=len(walks),acquired_scope_edges=len(scope),
        prior_attempted_pairs=len(attempted),global_search_envelope_pairs=global_count,same_curve_search_envelope_pairs=same_count,
        exact_same_curve_radius_pairs=len(broad),prior_attempts_excluded=int(seen.sum()),unchanged_small_walk_pairs_excluded=int(unchanged_small.sum()),
        evaluated_pairs=len(evaluate),ordered_stage_counts=reasons,eligible_opposed_skin_pairs=len(eligible),selected_opposed_skin_pairs=len(selected),
        selected_walks=len(np.unique(curves[eligible[selected,0]])),ambiguous_edges=int(ambiguous.sum()),
        selected_cross_endpoint_width_nominal_mm=dict(minimum=float(np.sqrt(scores[selected]).min()),maximum=float(np.sqrt(scores[selected]).max())) if len(selected) else None,
        geometry_modified=False,scan_normals_assumed_outward_for_material_side_test=True,physical_orientation_not_certified=True,
        anatomical_or_material_classifications_accepted=0,constructor_admission_granted=False,manufacturing_authorized=False,seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)


if __name__=='__main__':main()
