"""Attribute every pruned boundary and independently account for all omitted-face edges."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def load(path):
    with np.load(path,allow_pickle=False) as data:return {k:data[k] for k in data.files}


def boundary_after_omission(before,removed_faces):
    result=Counter(map(tuple,before.tolist()))
    for face in removed_faces:
        for a,b in zip(face,np.roll(face,-1)):
            a,b=int(a),int(b)
            if result[(a,b)]:result[(a,b)]-=1
            else:result[(b,a)]+=1
    return +result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('job','constructed','verified','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();job=json.loads(args.job.read_text());started=time.monotonic()
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    proof=json.loads((args.verified/'report.json').read_text());assert proof['candidate_sha256']==sha(args.constructed/'candidate.npz')
    assert proof['complete_source_omission_mask_verified'] and proof['all_retained_coordinates_triangles_and_provenance_exact']
    base=load(job['mesh']);data=load(args.constructed/'candidate.npz');witness=load(args.verified/'private-verified-mask-and-fans.npz')
    old=load(job['boundary_source']);removed=witness['removed_parent_face_rows'];kept=witness['retained_parent_face_rows'];edges=witness['boundary_local_nodes']
    assert boundary_after_omission(old['boundary_local_nodes'],base['triangles'][removed])==Counter(map(tuple,edges.tolist()))
    spec=importlib.util.spec_from_file_location('frozen_source_boundary_cycles',job['cycle_source']);helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    cycles=helper.fans_and_cycles(data['triangles'],len(data['points']));assert np.array_equal(cycles['boundary'],edges)
    all_edges,order,first,_,uses=helper.table(data['triangles'],len(data['points']))
    paired=first[uses==2];a=order[paired]//3;b=order[paired+1]//3
    graph=coo_matrix((np.ones(2*len(a),dtype=np.int8),(np.r_[a,b],np.r_[b,a])),shape=(len(data['triangles']),len(data['triangles']))).tocsr()
    component_count,components=connected_components(graph,directed=False);component_sizes=np.bincount(components)
    nv=len(data['points']);old_edges=old['boundary_local_nodes'];old_code=old_edges[:,0]*nv+old_edges[:,1];code=edges[:,0]*nv+edges[:,1]
    order=np.argsort(old_code);where=np.searchsorted(old_code[order],code);present=where<len(order)
    present[present]&=old_code[order[where[present]]]==code[present]
    previous=np.full(len(edges),-1,dtype=np.int64);previous[present]=order[where[present]]
    assert np.array_equal(kept[cycles['owners'][present]],old['boundary_face_rows'][previous[present]])
    origin=np.full(len(edges),5,dtype=np.int8);origin[present]=old['edge_origin_kind'][previous[present]]
    raw=np.full(len(edges),-1,dtype=np.int64);raw[present]=old['raw_original_curve_ids'][previous[present]]
    missing_owner={(int(a),int(b)):int(row) for row in removed for a,b in zip(base['triangles'][row],np.roll(base['triangles'][row],-1))}
    omitted_owner=np.full(len(edges),-1,dtype=np.int64)
    for i in np.flatnonzero(~present):
        a,b=map(int,edges[i]);assert (b,a) in missing_owner
        omitted_owner[i]=missing_owner[(b,a)]
    reviews=[]
    for index,(a,b) in enumerate(zip(cycles['offsets'][:-1],cycles['offsets'][1:])):
        ids=cycles['cycle_edges'][a:b];stats,_,_=helper.geometry(data['points'][edges[ids,0]])
        reviews.append(dict(curve=index,edges=len(ids),**stats,edge_origin_counts={str(int(k)):int(np.count_nonzero(origin[ids]==k)) for k in np.unique(origin[ids])},
                            source_raw_curve_ids=sorted(set(map(int,raw[ids]))-{-1}),physical_classification='unreviewed',closure_authorized=False))
    args.output.mkdir(mode=0o700,exist_ok=False)
    np.savez_compressed(args.output/'private-boundary-origins-and-fans.npz',boundary_local_nodes=edges,boundary_global_nodes=data['global_node_ids'][edges],boundary_face_rows=cycles['owners'],
                        cycle_offsets=cycles['offsets'],cycle_boundary_edge_ids=cycles['cycle_edges'],from_fan_labels=cycles['from_fans'],to_fan_labels=cycles['to_fans'],
                        edge_origin_kind=origin,raw_original_curve_ids=raw,previous_contact_boundary_edge_ids=previous,omitted_parent_face_owner=omitted_owner)
    np.save(args.output/'private-face-component-labels.npy',components)
    (args.output/'private-curve-review.json').write_text(json.dumps(reviews,indent=2)+'\n')
    old_gone=~np.isin(old_code,code);omitted_tri=base['points'][base['triangles'][removed]]
    total_area=float(np.linalg.norm(np.cross(omitted_tri[:,1]-omitted_tri[:,0],omitted_tri[:,2]-omitted_tri[:,0]),axis=1).sum()/2)
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    report=dict(source_sha256=sha(__file__),job_sha256=sha(args.job),candidate_sha256=sha(args.constructed/'candidate.npz'),
                before_boundary_edges=len(old_edges),after_boundary_edges=len(edges),old_boundary_edges_no_longer_open=int(old_gone.sum()),
                newly_exposed_omission_boundary_edges=int(np.count_nonzero(~present)),boundary_walks=len(reviews),
                all_boundary_change_edges_independently_rejoined=True,new_boundary_owners_rejoined_to_omitted_facets=True,
                complete_edge_origin_counts={str(int(k)):int(np.count_nonzero(origin==k)) for k in np.unique(origin)},
                complete_walk_origin_combinations=dict(Counter('+'.join(sorted(row['edge_origin_counts'])) for row in reviews)),
                omitted_facet_surface_kind_counts={str(int(k)):int(np.count_nonzero(base['inferred_surface_kind'][removed]==k)) for k in np.unique(base['inferred_surface_kind'][removed])},
                total_omitted_area_nominal_mm2=total_area,omissions_are_not_measured_missing_surfaces=True,
                connected_surface_components=int(component_count),largest_component_facets=int(component_sizes.max()),single_facet_components=int(np.count_nonzero(component_sizes==1)),
                component_selection_or_anatomy_accepted=False,
                all_physical_roles_unreviewed=True,full_bare_head_created=False,manufacturing_authorized=False,seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)


if __name__=='__main__':main()
