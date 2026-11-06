"""Read-only source-frontier pairing census; no vertices or faces are constructed."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from scipy.spatial import cKDTree


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def load(path):
    with np.load(path,allow_pickle=False) as data:return {k:data[k] for k in data.files}


def triangle_alignment(points,triangles,normal):
    p=points[triangles];cross=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]);length=np.linalg.norm(cross,axis=1)
    dot=np.full(len(triangles),-np.inf);keep=length>0
    dot[keep]=np.sum(cross[keep]*normal[keep],axis=1)/length[keep]
    return dot


def qualify(points,edges,normals,pairs,limits):
    """Return strict stage refusals, eligible pairs, and both signed-diagonal flags."""
    if not len(pairs):return {},np.empty(0,dtype=np.int64),np.empty((0,2),dtype=bool),np.empty(0)
    a,b=edges[pairs[:,0]].T;c,d=edges[pairs[:,1]].T
    tangent=points[edges[:,1]]-points[edges[:,0]];length=np.linalg.norm(tangent,axis=1);assert np.all(length>0)
    tangent/=length[:,None];alive=np.ones(len(pairs),dtype=bool);reasons={}
    def refuse(name,ok):
        reasons[name]=int(np.count_nonzero(alive&~ok));alive[:]&=ok
    distinct=(a!=c)&(a!=d)&(b!=c)&(b!=d)
    for x,y in ((a,c),(a,d),(b,c),(b,d)):distinct&=np.any(points[x]!=points[y],axis=1)
    refuse('shared_vertex_or_coordinate',distinct)
    cross_squared=np.maximum(np.sum((points[a]-points[d])**2,axis=1),np.sum((points[b]-points[c])**2,axis=1))
    refuse('cross_endpoint_support_distance',cross_squared<=limits['maximum_cross_endpoint_distance_nominal_mm']**2)
    refuse('directed_tangent_alignment',np.sum(tangent[pairs[:,0]]*tangent[pairs[:,1]],axis=1)<=limits['maximum_tangent_dot'])
    ni,nj=normals[pairs[:,0]],normals[pairs[:,1]]
    refuse('acquired_owner_normal_alignment',np.sum(ni*nj,axis=1)>=limits['minimum_owner_normal_dot'])
    first=np.c_[b,a,d];second=np.c_[b,d,c];other_first=np.c_[b,a,c];other_second=np.c_[a,d,c]
    bound=limits['minimum_signed_bridge_triangle_normal_dot']
    flags=np.c_[(triangle_alignment(points,first,ni)>=bound)&(triangle_alignment(points,second,nj)>=bound),
                (triangle_alignment(points,other_first,ni)>=bound)&(triangle_alignment(points,other_second,nj)>=bound)]
    refuse('no_forward_nondegenerate_quad_diagonal',np.any(flags,axis=1))
    reasons['eligible']=int(np.count_nonzero(alive))
    return reasons,np.flatnonzero(alive),flags[alive],cross_squared[alive]


def mutual_unique(pairs,scores,edge_count,tolerance):
    best=np.full(edge_count,-1,dtype=np.int64);ambiguous=np.zeros(edge_count,dtype=bool)
    if not len(pairs):return np.empty(0,dtype=np.int64),best,ambiguous
    edge=np.r_[pairs[:,0],pairs[:,1]];other=np.r_[pairs[:,1],pairs[:,0]];score=np.r_[scores,scores]
    order=np.lexsort((other,score,edge));ordered=edge[order]
    first=np.r_[0,np.flatnonzero(ordered[1:]!=ordered[:-1])+1];degree=np.diff(np.r_[first,len(order)])
    ids=ordered[first];best[ids]=other[order[first]]
    multiple=degree>1;where=first[multiple]
    ambiguous[ids[multiple]]=np.abs(score[order[where+1]]-score[order[where]])<=tolerance
    keep=(best[pairs[:,0]]==pairs[:,1])&(best[pairs[:,1]]==pairs[:,0])&~ambiguous[pairs[:,0]]&~ambiguous[pairs[:,1]]
    return np.flatnonzero(keep),best,ambiguous


def enumerate_same_curve_pairs(midpoint,edge_curve,scope,limits):
    radius=limits['midpoint_search_radius_nominal_mm'];guard=limits['spatial_search_arithmetic_guard_nominal_mm']
    all_tree=cKDTree(midpoint[scope]);global_envelope=(int(all_tree.count_neighbors(all_tree,radius+guard))-len(scope))//2
    broad=[];same_envelope=0
    for curve in np.unique(edge_curve[scope]):
        ids=scope[edge_curve[scope]==curve];tree=cKDTree(midpoint[ids]);count=(int(tree.count_neighbors(tree,radius+guard))-len(ids))//2
        same_envelope+=count;assert same_envelope<=limits['maximum_same_curve_search_pairs'],'registered_pair_resource_limit'
        pairs=tree.query_pairs(radius+guard,output_type='ndarray')
        if len(pairs):
            pairs=ids[pairs];distance=np.sum((midpoint[pairs[:,0]]-midpoint[pairs[:,1]])**2,axis=1)
            broad.append(pairs[distance<=radius**2])
    pairs=np.concatenate(broad) if broad else np.empty((0,2),dtype=np.int64)
    pairs=np.sort(pairs,axis=1);pairs=pairs[np.lexsort((pairs[:,1],pairs[:,0]))]
    assert not len(pairs) or np.all(edge_curve[pairs[:,0]]==edge_curve[pairs[:,1]])
    return pairs,global_envelope,same_envelope


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('job','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();job=json.loads(args.job.read_text());started=time.monotonic()
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    proof=json.loads(Path(job['topology_proof']).read_text());assert proof['mesh_sha256']==sha(job['mesh']) and proof['full_used_vertex_manifold']
    global_proof=json.loads(Path(job['global_proof']).read_text());assert global_proof['mesh_sha256']==proof['mesh_sha256'] and global_proof['source_preserving_surface_checks_passed']
    mesh=load(job['mesh']);boundary=load(job['boundaries']);source=load(job['source_arrays']);v=mesh['points'];edges=boundary['boundary_local_nodes']
    review=json.loads(Path(job['review']).read_text());decisions={x['curve']:x for x in json.loads(Path(job['prior_admission_decisions']).read_text())}
    edge_curve=np.full(len(edges),-1,dtype=np.int64);scope=[];curves=[]
    for row in review:
        curve=row['curve'];a,b=boundary['cycle_offsets'][curve:curve+2];ids=boundary['cycle_boundary_edge_ids'][a:b];edge_curve[ids]=curve
        if set(row['edge_origin_counts'])=={'1'} and not decisions[row['parent_boundary_curve_id']]['experimental_trial_admitted']:
            assert np.all(boundary['edge_origin_kind'][ids]==1);scope.extend(map(int,ids));curves.append(curve)
    assert np.all(edge_curve>=0);scope=np.array(sorted(scope),dtype=np.int64)
    assert len(curves)==612 and len(scope)==91318
    owners=boundary['boundary_face_rows'][scope];assert np.all(mesh['inferred_surface_kind'][owners]==0)
    source_faces=mesh['original_face_ids'][owners];assert np.all(source_faces>=0)
    target_nodes=np.unique(edges[scope]);global_nodes=mesh['global_node_ids'][target_nodes]
    assert np.all(global_nodes<len(source['vertices'])) and np.array_equal(v[target_nodes],source['vertices'][global_nodes])
    p=source['vertices'][source['triangles'][source_faces]];normal=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]);normal/=np.linalg.norm(normal,axis=1)[:,None]
    full_normals=np.zeros((len(edges),3));full_normals[scope]=normal
    midpoint=v[edges].mean(axis=1);limits=job['limits']
    pairs,global_envelope,same_envelope=enumerate_same_curve_pairs(midpoint,edge_curve,scope,limits)
    reasons,accepted,diagonals,scores=qualify(v,edges,full_normals,pairs,limits);eligible=pairs[accepted]
    selected,best,ambiguous=mutual_unique(eligible,scores,len(edges),limits['squared_gap_score_ambiguity_tolerance'])
    assert len(np.unique(eligible[selected]))==2*len(selected)
    args.output.mkdir(mode=0o700,exist_ok=False)
    np.savez_compressed(args.output/'private-frontier-pair-census.npz',scope_edge_ids=scope,edge_curve_ids=edge_curve,
                        same_curve_radius_pairs=pairs,eligible_pair_edge_ids=eligible,eligible_pair_diagonal_flags=diagonals,eligible_pair_scores_squared=scores,
                        selected_eligible_pair_indices=selected,selected_pair_edge_ids=eligible[selected],selected_pair_curve_ids=edge_curve[eligible[selected,0]],
                        unique_best_neighbor_edge_ids=best,ambiguous_edge_ids=np.flatnonzero(ambiguous))
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    result=dict(source_sha256=sha(__file__),job_sha256=sha(args.job),mesh_sha256=sha(job['mesh']),
                complete_parent_walks=len(review),complete_parent_boundary_edges=len(edges),target_source_walks=len(curves),target_source_edges=len(scope),
                global_search_envelope_pairs=global_envelope,same_curve_search_envelope_pairs=same_envelope,
                other_curve_search_envelope_pairs_excluded=global_envelope-same_envelope,exact_same_curve_radius_pairs=len(pairs),
                ordered_stage_counts=reasons,eligible_pairs=len(eligible),ambiguous_candidate_edges=int(np.count_nonzero(ambiguous)),
                selected_unique_mutual_pairs=len(selected),selected_source_walks=len(set(map(int,edge_curve[eligible[selected,0]]))),
                both_diagonals_forward_pairs=int(np.count_nonzero(diagonals[selected].all(axis=1))),
                selected_cross_endpoint_width_nominal_mm=dict(minimum=float(np.sqrt(scores[selected]).min()),median=float(np.median(np.sqrt(scores[selected]))),maximum=float(np.sqrt(scores[selected]).max())) if len(selected) else None,
                geometry_modified=False,pairs_are_hypotheses_not_proven_scan_damage=True,constructor_admission_not_yet_granted=True,
                physical_classifications_accepted=0,full_bare_head_created=False,manufacturing_authorized=False,seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if not isinstance(v,(dict,list))}),flush=True)


if __name__=='__main__':main()
