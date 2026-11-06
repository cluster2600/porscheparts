"""Screen every current walk; admit only bounded acquired-source gap experiments."""
import argparse
from collections import Counter
from fractions import Fraction
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


def exact_projection(points,simple):
    p=[tuple(Fraction.from_float(float(x)) for x in point) for point in points]
    area=[sum(a[(j+1)%3]*b[(j+2)%3]-a[(j+2)%3]*b[(j+1)%3] for a,b in zip(p,p[1:]+p[:1])) for j in range(3)]
    drop=max(range(3),key=lambda j:abs(area[j]))
    if not area[drop]:return False,drop
    axes=[i for i in range(3) if i!=drop]
    return simple([tuple(point[i] for i in axes) for point in p]),drop


def screen(points,adjacent_normals,simple,limits):
    centred=points-points.mean(axis=0);_,singular,axes=np.linalg.svd(centred,full_matrices=False)
    rank=int(np.count_nonzero(singular>singular.max()*max(points.shape)*np.finfo(float).eps))
    normal=axes[-1];residual=float(np.abs(centred@normal).max());diagonal=float(np.linalg.norm(np.ptp(points,axis=0)))
    alignment=float(np.quantile(np.abs(adjacent_normals@normal),.1));reasons=[]
    if not limits['min_edges']<=len(points)<=limits['max_edges']:reasons.append('edge_count')
    if rank<2:reasons.append('rank_below_two')
    if diagonal>limits['max_diagonal_nominal_mm']:reasons.append('diagonal')
    if residual>limits['max_plane_residual_nominal_mm']:reasons.append('planarity')
    if alignment<limits['minimum_adjacent_normal_absolute_p10']:reasons.append('adjacent_normal_alignment')
    if len(np.unique(points,axis=0))!=len(points):reasons.append('repeated_source_coordinate')
    # The exact quadratic polygon predicate is bounded independently of rejected large loops.
    exact=None;drop=None
    if not reasons:exact,drop=exact_projection(points,simple)
    if exact is False:reasons.append('non_simple_or_zero_exact_projection')
    return reasons,dict(rank=rank,diagonal_nominal_mm=diagonal,maximum_plane_residual_nominal_mm=residual,
                        adjacent_normal_absolute_alignment_p10=alignment,exact_projection_checked=exact is not None,
                        exact_simple_projection=exact,dropped_projection_axis=drop)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('job','constructed','verified','boundaries','deviations','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();job=json.loads(args.job.read_text());started=time.monotonic()
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    proof=json.loads((args.verified/'report.json').read_text());distance=json.loads((args.deviations/'report.json').read_text())
    boundary_report=json.loads((args.boundaries/'report.json').read_text());mesh_path=args.constructed/'candidate.npz';digest=sha(mesh_path)
    assert proof['candidate_sha256']==distance['candidate_sha256']==boundary_report['candidate_sha256']==digest
    assert proof['conservative_surface_topology_admitted'] and distance['geometry_study_deviation_checks_passed']
    mesh=load(mesh_path);data=load(args.boundaries/'private-boundary-origins-and-fans.npz');v,f=mesh['points'],mesh['triangles']
    spec=importlib.util.spec_from_file_location('frozen_exact_polygon_inspector',job['obj_reader']);checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
    old_job=json.loads(Path(job['predicate_job']).read_text());source=load(old_job['arrays']);pairs=np.load(old_job['intersection_pairs'],allow_pickle=False)
    involved_vertices=np.unique(source['triangles'][np.unique(pairs)])
    normal=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]);length=np.linalg.norm(normal,axis=1);assert np.all(length>0);normal/=length[:,None]
    limits=dict(min_edges=3,max_edges=128,max_diagonal_nominal_mm=3.,max_plane_residual_nominal_mm=.25,minimum_adjacent_normal_absolute_p10=.8)
    records=[]
    for index,(a,b) in enumerate(zip(data['cycle_offsets'][:-1],data['cycle_offsets'][1:])):
        ids=data['cycle_boundary_edge_ids'][a:b];edges=data['boundary_local_nodes'][ids];owners=data['boundary_face_rows'][ids]
        reasons=[];stats={};kinds=set(map(int,data['edge_origin_kind'][ids]));global_ids=mesh['global_node_ids'][edges[:,0]]
        if kinds!={1}:reasons.append('not_acquisition_only')
        else:
            assert np.array_equal(edges[:,1],np.roll(edges[:,0],-1))
            if np.any(global_ids>=len(source['vertices'])):reasons.append('constructed_node_on_acquisition_walk')
            else:assert np.array_equal(v[edges[:,0]],source['vertices'][global_ids])
            if np.any(mesh['inferred_surface_kind'][owners]!=0):reasons.append('inferred_owner_on_acquisition_walk')
            if np.any(np.isin(global_ids,involved_vertices)):reasons.append('original_intersection_vertex_contact')
            geometric,stats=screen(v[edges[:,0]],normal[owners],checker.simple_projection,limits);reasons.extend(geometric)
        records.append(dict(curve=index,boundary_edges=len(ids),edge_origins=sorted(kinds),experimental_trial_admitted=not reasons,
                            reasons=reasons,**stats,physical_classification_accepted=False,closure_authorized=False))
    args.output.mkdir(mode=0o700,exist_ok=False)
    (args.output/'private-all-walk-decisions.json').write_text(json.dumps(records,indent=2)+'\n')
    np.save(args.output/'private-admitted-acquisition-curve-ids.npy',np.array([x['curve'] for x in records if x['experimental_trial_admitted']],dtype=np.int64))
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    result=dict(source_sha256=sha(__file__),job_sha256=sha(args.job),candidate_sha256=digest,complete_walk_denominator=len(records),
                acquired_only_walks=sum(x['edge_origins']==[1] for x in records),experimental_trials_admitted=sum(x['experimental_trial_admitted'] for x in records),
                all_rejection_reason_counts=dict(Counter(reason for row in records for reason in row['reasons'])),experimental_limits=limits,
                whole_topology_and_omission_deviations_checked_before_admission=True,geometry_modified=False,
                trial_inputs_or_native_constructor_not_yet_executed=True,physical_classifications_accepted=0,
                full_bare_head_created=False,manufacturing_authorized=False,seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)


if __name__=='__main__':main()
