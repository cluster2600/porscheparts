"""Inspect every used vertex and reattribute all boundaries after inferred contact bridges."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def load(path):
    with np.load(path,allow_pickle=False) as data:return {k:data[k] for k in data.files}


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


def changed_boundary(before,added):
    expected=Counter(map(tuple,before.tolist()))
    for face in added:
        for a,b in zip(face,np.roll(face,-1)):
            a,b=int(a),int(b)
            if expected[(b,a)]:expected[(b,a)]-=1
            else:expected[(a,b)]+=1
    return +expected


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('job','mesh','global-proof','assembly-proof','cycle-source','boundary-origins','boundary-witness','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();job=json.loads(args.job.read_text());started=time.monotonic()
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    proof=json.loads(args.global_proof.read_text());assembly=json.loads(args.assembly_proof.read_text())
    assert proof['mesh_sha256']==assembly['candidate_NPZ_sha256']==sha(args.mesh) and proof['source_preserving_surface_checks_passed']
    assert proof['source_sha256']=='da24015af3fd8578f0bcd47e7d51f04c11905ee4738463aeae66c9491d42cd25'
    assert assembly['source_sha256']=='c5824c4142d06c0a938568b6d3b74ae7cd1a88cc9801c6a820d8dda9b1c6d86f'
    fan_count=module(job['fan_source'],'frozen_full_used_vertex_inspector').vertex_fans
    cycle=module(args.cycle_source,'frozen_surface_fan_cycle_audit')
    base=load(job['mesh']);data=load(args.mesh);n=len(base['triangles']);count=len(data['points'])
    assert np.array_equal(data['points'],base['points']) and np.array_equal(data['triangles'][:n],base['triangles'])
    before,old_edges=fan_count(base['triangles'],count);after,new_edges=fan_count(data['triangles'],count)
    selected=np.array(sorted(set(map(int,data['source_contact_vertex_ids'][n:]))),dtype=np.int64)
    keep=np.ones(count,dtype=bool);keep[selected]=False
    assert np.array_equal(before,load(job['fan_witness'])['candidate_face_fans'])
    assert np.all(before[selected]>1) and np.all(after[selected]==1) and np.array_equal(before[keep],after[keep])
    assert changed_boundary(old_edges,data['triangles'][n:])==Counter(map(tuple,new_edges.tolist()))
    origins=load(args.boundary_origins);old_ids=load(args.boundary_witness)['remaining_original_boundary_edge_ids']
    assert np.array_equal(base['global_node_ids'][old_edges],origins['boundary_global_nodes'][old_ids])
    current=cycle.fans_and_cycles(data['triangles'],count);assert np.array_equal(current['boundary'],new_edges)
    global_edges=data['global_node_ids'][new_edges];old_global=base['global_node_ids'][old_edges];radix=int(base['global_node_ids'].max())+1
    old_code=old_global[:,0]*radix+old_global[:,1];new_code=global_edges[:,0]*radix+global_edges[:,1]
    order=np.argsort(old_code);where=np.searchsorted(old_code[order],new_code);present=where<len(order)
    present[present]&=old_code[order[where[present]]]==new_code[present]
    previous=np.full(len(new_edges),-1,dtype=np.int64);previous[present]=old_ids[order[where[present]]]
    kind=np.full(len(new_edges),4,dtype=np.int8);kind[present]=origins['edge_origin_kind'][previous[present]]
    new_owner=data['source_contact_vertex_ids'][current['owners'][~present]];assert np.all(new_owner>=0)
    raw_curve=np.full(len(new_edges),-1,dtype=np.int64);raw_curve[present]=origins['raw_original_curve_ids'][previous[present]]
    contact_owner=np.full(len(new_edges),-1,dtype=np.int64);contact_owner[~present]=new_owner
    review=[]
    for index,(a,b) in enumerate(zip(current['offsets'][:-1],current['offsets'][1:])):
        ids=current['cycle_edges'][a:b];stats,_,_=cycle.geometry(data['points'][new_edges[ids,0]])
        review.append(dict(curve=index,edges=len(ids),**stats,edge_origin_counts={str(int(k)):int(np.count_nonzero(kind[ids]==k)) for k in np.unique(kind[ids])},
                           source_raw_curve_ids=sorted(set(map(int,raw_curve[ids]))-{-1}),physical_classification='unreviewed',closure_authorized=False))
    removed=np.flatnonzero(~np.isin(old_code,new_code))
    args.output.mkdir(mode=0o700,exist_ok=False)
    np.savez_compressed(args.output/'private-contact-boundaries-and-fans.npz',base_face_fans=before,candidate_face_fans=after,
                        boundary_local_nodes=new_edges,boundary_global_nodes=global_edges,boundary_face_rows=current['owners'],
                        from_fan_labels=current['from_fans'],to_fan_labels=current['to_fans'],cycle_offsets=current['offsets'],cycle_boundary_edge_ids=current['cycle_edges'],
                        edge_origin_kind=kind,previous_retained_boundary_edge_ids=previous,raw_original_curve_ids=raw_curve,inferred_contact_owner=contact_owner)
    (args.output/'private-curve-review.json').write_text(json.dumps(review,indent=2)+'\n')
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    result=dict(source_sha256=sha(__file__),job_sha256=sha(args.job),mesh_sha256=sha(args.mesh),
                base_nonmanifold_used_vertices=int(np.count_nonzero(before>1)),candidate_nonmanifold_used_vertices=int(np.count_nonzero(after>1)),
                exactly_selected_contacts_joined=len(selected),all_other_vertex_fan_counts_unchanged=True,
                base_boundary_edges=len(old_edges),candidate_boundary_edges=len(new_edges),candidate_boundary_walks=len(review),
                removed_previous_boundary_edges=len(removed),new_inferred_bridge_boundary_edges=int(np.count_nonzero(~present)),
                complete_boundary_origin_counts={str(int(k)):int(np.count_nonzero(kind==k)) for k in np.unique(kind)},
                removed_boundary_origin_counts={str(int(k)):int(np.count_nonzero(origins['edge_origin_kind'][old_ids[removed]]==k)) for k in np.unique(origins['edge_origin_kind'][old_ids[removed]])},
                exact_whole_boundary_change_mask_verified=True,all_original_coordinates_and_base_faces_unchanged=True,
                index_duplicates_created=False,closed_volume=False,full_used_vertex_manifold=not np.any(after>1),
                conservative_surface_workflow_fully_admitted=False,full_bare_head_created=False,
                physical_acceptance=False,manufacturing_authorized=False,seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)


if __name__=='__main__':main()
