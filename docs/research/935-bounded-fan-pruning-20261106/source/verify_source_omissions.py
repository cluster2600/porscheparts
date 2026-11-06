"""Independently replay every bounded omission and inspect the complete saved candidate."""
import argparse
from collections import defaultdict
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


def independent_groups(faces,vertex,parents):
    assert np.all(np.sum(faces==vertex,axis=1)==1)
    owners=defaultdict(list)
    for row,face in enumerate(faces):
        for other in face[face!=vertex]:owners[int(other)].append(row)
    left=[];right=[]
    for rows in owners.values():
        assert len(rows)<=2
        if len(rows)==2:left.extend(rows);right.extend(rows[::-1])
    graph=coo_matrix((np.ones(len(left),dtype=np.int8),(left,right)),shape=(len(faces),len(faces))).tocsr()
    count,labels=connected_components(graph,directed=False)
    return sorted([sorted(map(int,parents[labels==i])) for i in range(count)])


def replay(points,faces,journal,limits,fan_count):
    parents=np.arange(len(faces),dtype=np.int64)
    p=points[faces];areas=np.linalg.norm(np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]),axis=1)/2
    assert np.all(areas>0)
    assert len(journal)<=limits['max_rounds']
    for ordinal,round_record in enumerate(journal):
        current=faces[parents];counts,_=fan_count(current,len(points));targets=np.flatnonzero(counts>1)
        assert round_record['round']==ordinal and round_record['current_face_count']==len(parents)
        assert round_record['nonmanifold_contacts']==len(targets)
        assert [x['contact_vertex'] for x in round_record['private_contacts']]==targets.tolist()
        incident=np.flatnonzero(np.any(np.isin(current,targets),axis=1));requested=set()
        for contact in round_record['private_contacts']:
            vertex=contact['contact_vertex'];rows=incident[np.any(current[incident]==vertex,axis=1)]
            groups=independent_groups(current[rows],vertex,parents[rows]);record=contact['groups']
            assert groups==[x['parent_face_rows'] for x in record],'nonmaximal_or_forged_source_fan_partition'
            computed=[]
            for group,row in zip(groups,record):
                ids=np.array(group,dtype=np.int64);area=float(areas[ids].sum())
                diagonal=float(np.linalg.norm(np.ptp(points[faces[ids]].reshape(-1,3),axis=0)))
                assert row['facets']==len(ids) and np.isclose(row['area_nominal_mm2'],area,rtol=1e-12,atol=1e-15)
                assert np.isclose(row['bounds_diagonal_nominal_mm'],diagonal,rtol=1e-12,atol=1e-15)
                computed.append((area,diagonal,len(ids)))
            retain=min(range(len(groups)),key=lambda i:(-computed[i][0],groups[i][0]))
            assert retain==contact['retained_group'],'largest_source_fan_not_retained'
            admitted=all(area<=limits['max_area_per_removed_fan_nominal_mm2'] and diagonal<=limits['max_diagonal_nominal_mm'] and size<=limits['max_facets_per_removed_fan']
                         for i,(area,diagonal,size) in enumerate(computed) if i!=retain)
            assert admitted==contact['removal_admitted'],'omission_bound_not_enforced'
            if admitted:
                for i,group in enumerate(groups):
                    if i!=retain:requested.update(group)
        assert sorted(requested)==round_record['requested_parent_face_rows'],'incomplete_or_out_of_mask_omission'
        permitted=len(faces)-len(parents)+len(requested)<=limits['max_total_removed_facets']
        assert permitted==round_record['total_removal_limit_passed']
        if permitted:parents=parents[~np.isin(parents,np.array(sorted(requested),dtype=np.int64))]
    return parents


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('job','constructed','intersection-proof','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();job=json.loads(args.job.read_text());started=time.monotonic()
    for row in job['inputs']:assert sha(row['path'])==row['sha256']
    produced=json.loads((args.constructed/'report.json').read_text());assert produced['job_sha256']==sha(args.job)
    proof=json.loads(args.intersection_proof.read_text());assert proof['mesh_sha256']==sha(args.constructed/'candidate.npz')==produced['candidate_NPZ_sha256']
    assert proof['job_sha256']==sha(job['predicate_job']) and proof['source_sha256']=='3e0b239ca4993388f32563092c78d97065cc1fb0753c68a2def3d631feda7976'
    assert proof['full_mesh_intersection_pairs']==proof['predicate_excluded_zero_cross_faces']==0
    fan_count=module(job['fan_source'],'frozen_all_used_vertex_inspector').vertex_fans
    base=load(job['mesh']);data=load(args.constructed/'candidate.npz');mask=load(args.constructed/'private-omission-mask.npz')
    journal=json.loads((args.constructed/'private-round-journal.json').read_text());keep=replay(base['points'],base['triangles'],journal,job['limits'],fan_count)
    assert np.array_equal(keep,mask['retained_parent_face_rows']) and np.array_equal(keep,data['parent_face_rows'])
    omitted=np.setdiff1d(np.arange(len(base['triangles']),dtype=np.int64),keep,assume_unique=True)
    assert np.array_equal(omitted,mask['removed_parent_face_rows'])
    assert set(data)==set(base)|{'parent_face_rows'}
    for key,value in base.items():
        expected=value if key in ('points','global_node_ids') else value[keep]
        assert np.array_equal(data[key],expected),'retained_geometry_or_provenance_changed:'+key
    for key,parent in [('omitted_source_face_ids','original_face_ids'),('omitted_source_fragment_indices','source_fragment_indices'),('omitted_surface_kinds','inferred_surface_kind')]:
        assert np.array_equal(mask[key],base[parent][omitted])
    reader=module(job['obj_reader'],'frozen_independent_OBJ_reader')
    actual_points,actual_faces=reader.read_obj(args.constructed/'candidate.obj')
    assert np.array_equal(actual_points,data['points']) and np.array_equal(actual_faces,data['triangles'])
    assert sha(args.constructed/'candidate.obj')==produced['candidate_OBJ_sha256']
    counts,boundary=fan_count(data['triangles'],len(data['points']))
    before,_=fan_count(base['triangles'],len(base['points']))
    canonical=np.sort(data['triangles'],axis=1);nv=len(data['points']);assert nv**3<2**63
    codes=(canonical[:,0]*nv+canonical[:,1])*nv+canonical[:,2];assert len(np.unique(codes))==len(codes)
    converged=not np.any(counts>1);assert converged==produced['convergence_reached']
    args.output.mkdir(mode=0o700,exist_ok=False)
    np.savez_compressed(args.output/'private-verified-mask-and-fans.npz',retained_parent_face_rows=keep,removed_parent_face_rows=omitted,
                        candidate_face_fans=counts,boundary_local_nodes=boundary)
    for row in job['inputs']:assert sha(row['path'])==row['sha256']
    report=dict(source_sha256=sha(__file__),job_sha256=sha(args.job),candidate_sha256=sha(args.constructed/'candidate.npz'),
                independently_replayed_rounds=len(journal),all_bounded_fan_decisions_verified=True,complete_source_omission_mask_verified=True,
                all_retained_coordinates_triangles_and_provenance_exact=True,actual_saved_OBJ_readback_exact=True,
                removed_triangles=len(omitted),retained_triangles=len(keep),base_nonmanifold_used_vertices=int(np.count_nonzero(before>1)),
                candidate_nonmanifold_used_vertices=int(np.count_nonzero(counts>1)),base_unreferenced_vertices=int(np.count_nonzero(before==0)),
                candidate_unreferenced_vertices=int(np.count_nonzero(counts==0)),open_boundary_edges=len(boundary),
                duplicate_faces=0,intersection_pairs=0,excluded_degenerate_faces=0,edge_incidence_and_winding_verified=True,
                full_used_vertex_manifold=converged,conservative_surface_topology_admitted=converged,
                physical_accuracy_or_omission_validity_verified=False,full_bare_head_created=False,closed_volume=not len(boundary),
                physical_acceptance=False,manufacturing_authorized=False,seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)


if __name__=='__main__':main()
