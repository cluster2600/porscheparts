"""Inspect every used vertex and prove that only selected acquired boundaries were closed."""
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


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('job','mesh','global-proof','assembly-proof','before-fans','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();job=json.loads(args.job.read_text());started=time.monotonic()
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    global_proof=json.loads(args.global_proof.read_text());assembly=json.loads(args.assembly_proof.read_text());digest=sha(args.mesh)
    assert global_proof['mesh_sha256']==assembly['candidate_NPZ_sha256']==digest and assembly['mode']=='check'
    assert global_proof['job_sha256']==assembly['job_sha256']==sha(args.job)
    args.output.mkdir(mode=0o700,exist_ok=False)
    result=dict(source_sha256=sha(__file__),job_sha256=sha(args.job),mesh_sha256=digest,rejected_acquisition_curve_ids=[],
                geometry_evaluation_deferred_for_global_conflicts=not global_proof['source_preserving_surface_checks_passed'],
                full_bare_head_created=False,physical_acceptance=False,manufacturing_authorized=False)
    if global_proof['source_preserving_surface_checks_passed']:
        base=load(job['retained']);mesh=load(args.mesh);before=load(args.before_fans)['candidate_face_fans'];old=load(job['boundaries'])
        n=len(base['triangles']);assert np.array_equal(mesh['points'],base['points']) and np.array_equal(mesh['triangles'][:n],base['triangles'])
        fan_count=module(job['fan_source'],'frozen_whole_vertex_graph').vertex_fans
        counts,edges=fan_count(mesh['triangles'],len(mesh['points']));changed=np.flatnonzero(before!=counts)
        if len(changed):
            faces=mesh['triangles'][n:];involved=np.any(np.isin(faces,changed),axis=1)
            rejected=sorted(set(map(int,mesh['source_acquisition_curve_ids'][n:][involved])));assert rejected
            result.update(rejected_acquisition_curve_ids=rejected,all_used_vertex_fan_counts_unchanged=False,candidate_nonmanifold_used_vertices=int(np.count_nonzero(counts>1)))
        else:
            selected=set(map(int,mesh['source_acquisition_curve_ids'][n:]));assert -1 not in selected
            assert selected<=set(map(int,np.load(job['admission_ids'],allow_pickle=False)))
            keep=np.ones(len(old['boundary_local_nodes']),dtype=bool)
            for curve in sorted(selected):
                a,b=old['cycle_offsets'][curve:curve+2];ids=old['cycle_boundary_edge_ids'][a:b]
                assert np.all(old['edge_origin_kind'][ids]==1);keep[ids]=False
            assert np.array_equal(edges,old['boundary_local_nodes'][keep]),'unselected_or_nonacquired_boundary_changed'
            helper=module(job['cycle_source'],'frozen_directed_boundary_fans');cycles=helper.fans_and_cycles(mesh['triangles'],len(mesh['points']))
            assert np.array_equal(cycles['boundary'],edges) and np.array_equal(cycles['owners'],old['boundary_face_rows'][keep])
            old_curve=np.empty(len(keep),dtype=np.int64)
            for curve,(a,b) in enumerate(zip(old['cycle_offsets'][:-1],old['cycle_offsets'][1:])):old_curve[old['cycle_boundary_edge_ids'][a:b]]=curve
            origin=old['edge_origin_kind'][keep];raw=old['raw_original_curve_ids'][keep];ancestors=old_curve[keep];reviews=[]
            for curve,(a,b) in enumerate(zip(cycles['offsets'][:-1],cycles['offsets'][1:])):
                ids=cycles['cycle_edges'][a:b];parents=np.unique(ancestors[ids]);assert len(parents)==1
                stats,_,_=helper.geometry(mesh['points'][edges[ids,0]])
                reviews.append(dict(curve=curve,parent_boundary_curve_id=int(parents[0]),edges=len(ids),**stats,
                                    edge_origin_counts={str(int(k)):int(np.count_nonzero(origin[ids]==k)) for k in np.unique(origin[ids])},
                                    source_raw_curve_ids=sorted(set(map(int,raw[ids]))-{-1}),physical_classification='unreviewed',closure_authorized=False))
            assert len(reviews)==len(old['cycle_offsets'])-1-len(selected)
            _,order,first,_,uses=helper.table(mesh['triangles'],len(mesh['points']));paired=first[uses==2];a=order[paired]//3;b=order[paired+1]//3
            graph=coo_matrix((np.ones(2*len(a),dtype=np.int8),(np.r_[a,b],np.r_[b,a])),shape=(len(mesh['triangles']),len(mesh['triangles']))).tocsr()
            component_count,components=connected_components(graph,directed=False);sizes=np.bincount(components)
            np.savez_compressed(args.output/'private-boundaries-and-fans.npz',candidate_face_fans=counts,boundary_local_nodes=edges,boundary_global_nodes=mesh['global_node_ids'][edges],boundary_face_rows=cycles['owners'],
                                from_fan_labels=cycles['from_fans'],to_fan_labels=cycles['to_fans'],cycle_offsets=cycles['offsets'],cycle_boundary_edge_ids=cycles['cycle_edges'],
                                edge_origin_kind=origin,raw_original_curve_ids=raw,parent_boundary_edge_ids=np.flatnonzero(keep),
                                omitted_parent_face_owner=old['omitted_parent_face_owner'][keep])
            np.save(args.output/'private-face-component-labels.npy',components)
            (args.output/'private-curve-review.json').write_text(json.dumps(reviews,indent=2)+'\n')
            result.update(all_used_vertex_fan_counts_unchanged=True,candidate_nonmanifold_used_vertices=int(np.count_nonzero(counts>1)),
                          candidate_unreferenced_vertices=int(np.count_nonzero(counts==0)),full_used_vertex_manifold=not np.any(counts>1),
                          exactly_selected_acquisition_walks_closed=len(selected),remaining_boundary_walks=len(reviews),remaining_boundary_edges=len(edges),
                          all_unselected_boundary_edges_owners_origins_and_omission_ancestry_unchanged=True,
                          remaining_edge_origin_counts={str(int(k)):int(np.count_nonzero(origin==k)) for k in np.unique(origin)},
                          remaining_walk_origin_combinations=dict(Counter('+'.join(sorted(x['edge_origin_counts'])) for x in reviews)),
                          connected_surface_components=int(component_count),largest_component_facets=int(sizes.max()),single_facet_components=int(np.count_nonzero(sizes==1)),
                          component_selection_or_anatomy_accepted=False,closed_volume=not len(edges))
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    result['seconds']=time.monotonic()-started
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if not isinstance(v,(dict,list))}),flush=True)


if __name__=='__main__':main()
