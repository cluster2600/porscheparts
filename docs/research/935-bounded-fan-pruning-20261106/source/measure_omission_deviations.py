"""Measure every omitted facet, every retained inferred facet and both whole-scan directions."""
import argparse
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


def facet_probes(points,faces,rows,seed):
    queries=[];labels=[]
    for row in rows:
        triangle=points[faces[row]];rng=np.random.default_rng(seed+int(row))
        r,s=np.sqrt(rng.random(1000)),rng.random(1000)
        sample=(1-r[:,None])*triangle[0]+(r*(1-s))[:,None]*triangle[1]+(r*s)[:,None]*triangle[2]
        probes=np.r_[sample,triangle.mean(axis=0)[None,:],triangle]
        queries.append(probes);labels.extend([int(row)]*len(probes))
    return np.concatenate(queries),np.array(labels,dtype=np.int64)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('job','constructed','verified','previous-source-witness','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();job=json.loads(args.job.read_text());started=time.monotonic()
    for row in job['inputs']:assert sha(row['path'])==row['sha256']
    verified=json.loads((args.verified/'report.json').read_text());assert verified['candidate_sha256']==sha(args.constructed/'candidate.npz')
    assert verified['complete_source_omission_mask_verified'] and verified['all_retained_coordinates_triangles_and_provenance_exact']
    spec=importlib.util.spec_from_file_location('frozen_both_direction_distances',job['distance_source']);helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    literal=np.array([[0.,0.,0.],[2.,0.,0.],[0.,2.,0.]])
    d,_,closest=helper.query(np.array([[.25,.25,0.],[.25,.25,2.],[2.,2.,0.]]),literal,np.array([[0,1,2]]))
    assert np.allclose(d,[0.,2.,np.sqrt(2.)],rtol=0,atol=1e-14) and np.allclose(closest[-1],[1.,1.,0.],rtol=0,atol=1e-14)
    base=load(job['mesh']);mesh=load(args.constructed/'candidate.npz');mask=load(args.verified/'private-verified-mask-and-fans.npz')
    source_job=json.loads(Path(job['predicate_job']).read_text());source=load(source_job['arrays']);sv,sf=source['vertices'],source['triangles']
    cross=np.cross(sv[sf[:,1]]-sv[sf[:,0]],sv[sf[:,2]]-sv[sf[:,0]]);valid=np.any(cross!=0,axis=1);assert np.count_nonzero(~valid)==8
    previous=load(args.previous_source_witness);source_points=previous['source_query_points'];old=previous['source_distances']
    v,f=mesh['points'],mesh['triangles'];forward,forward_ids,forward_nearest=helper.query(source_points,v,f)
    omitted_points,omitted_labels=facet_probes(base['points'],base['triangles'],mask['removed_parent_face_rows'],93800)
    omitted,omitted_ids,omitted_nearest=helper.query(omitted_points,v,f)
    random,random_rows=helper.samples(v,f,100000,93801);boundary_nodes=np.unique(mask['boundary_local_nodes'])
    inferred_rows=np.flatnonzero(mesh['inferred_surface_kind']>0);inferred_points,inferred_labels=facet_probes(v,f,inferred_rows,93802)
    reverse_points=np.r_[random,v[boundary_nodes],inferred_points];reverse,reverse_ids,reverse_nearest=helper.query(reverse_points,sv,sf[valid]);b=100000+len(boundary_nodes)
    increase=np.maximum(forward-old,0);limit=job['limits']['max_sampled_omission_distance_nominal_mm']
    checks=bool(omitted.max()<=limit and increase.max()<=limit+1e-8)
    args.output.mkdir(mode=0o700,exist_ok=False)
    np.savez_compressed(args.output/'private-omission-distance-witnesses.npz',omitted_query_points=omitted_points,omitted_parent_face_rows=omitted_labels,
                        omitted_distances=omitted,omitted_nearest_retained_faces=omitted_ids,omitted_nearest_points=omitted_nearest,
                        source_query_points=source_points,source_distances=forward,source_nearest_faces=forward_ids,source_nearest_points=forward_nearest,
                        reverse_query_points=reverse_points,reverse_distances=reverse,reverse_nearest_original_faces=np.flatnonzero(valid)[reverse_ids],reverse_nearest_original_points=reverse_nearest,
                        reverse_random_face_rows=random_rows,reverse_boundary_vertex_ids=boundary_nodes,retained_inferred_facet_rows=inferred_labels)
    for row in job['inputs']:assert sha(row['path'])==row['sha256']
    result=dict(source_sha256=sha(__file__),job_sha256=sha(args.job),candidate_sha256=sha(args.constructed/'candidate.npz'),
                previous_source_witness_sha256=sha(args.previous_source_witness),literal_distance_controls_passed=True,
                all_omitted_facet_probes_to_retained_candidate=helper.stats(omitted),omitted_facets_probed=len(mask['removed_parent_face_rows']),
                raw_source_random_to_candidate=helper.stats(forward[:100000]),raw_original_boundary_vertices_to_candidate=helper.stats(forward[100000:199876]),
                quarantined_source_facet_probes_to_candidate=helper.stats(forward[199876:]),maximum_sampled_source_distance_increase_nominal_mm=float(increase.max()),
                candidate_random_to_raw_source=helper.stats(reverse[:100000]),candidate_boundary_vertices_to_raw_source=helper.stats(reverse[100000:b]),
                every_retained_inferred_facet_probes_to_raw_source=helper.stats(reverse[b:]),retained_inferred_facets_probed=len(inferred_rows),
                experimental_omission_probe_limit_nominal_mm=limit,geometry_study_deviation_checks_passed=checks,
                limits_are_not_physical_tolerances=True,sampled_errors_are_not_Hausdorff_bounds=True,
                full_bare_head_created=False,physical_accuracy_verified=False,manufacturing_authorized=False,seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(omitted_facet_sampled_maximum_nominal_mm=float(omitted.max()),maximum_sampled_source_distance_increase_nominal_mm=float(increase.max()),geometry_study_deviation_checks_passed=checks,seconds=result['seconds'])),flush=True)
    if not checks:raise SystemExit(2)


if __name__=='__main__':main()
