"""Measure every inferred acquired-gap patch and preserve both source/omission distance witnesses."""
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


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('job','mesh','previous-witness','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();job=json.loads(args.job.read_text());started=time.monotonic()
    for row in job['inputs']:assert sha(row['path'])==row['sha256']
    spec=importlib.util.spec_from_file_location('frozen_exact_distance_helpers',job['distance_source']);helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    literal=np.array([[0.,0.,0.],[2.,0.,0.],[0.,2.,0.]])
    d,_,c=helper.query(np.array([[.25,.25,0.],[.25,.25,2.],[2.,2.,0.]]),literal,np.array([[0,1,2]]))
    assert np.allclose(d,[0.,2.,np.sqrt(2.)],atol=1e-14,rtol=0) and np.allclose(c[-1],[1.,1.,0.],atol=1e-14,rtol=0)
    base=load(job['retained']);mesh=load(args.mesh);previous=load(args.previous_witness)
    v,f=mesh['points'],mesh['triangles'];n=len(base['triangles'])
    assert np.array_equal(v,base['points']) and np.array_equal(f[:n],base['triangles'])
    assert np.all(mesh['source_acquisition_curve_ids'][:n]==-1)
    raw_job=json.loads(Path(job['predicate_job']).read_text());raw=load(raw_job['arrays']);sv,sf=raw['vertices'],raw['triangles']
    cross=np.cross(sv[sf[:,1]]-sv[sf[:,0]],sv[sf[:,2]]-sv[sf[:,0]]);valid=np.any(cross!=0,axis=1);assert np.count_nonzero(~valid)==8
    source_points=previous['source_query_points'];forward,forward_ids,forward_nearest=helper.query(source_points,v,f)
    assert np.all(forward<=previous['source_distances']+1e-8),'additive_caps_increased_source_distance'
    omitted_points=previous['omitted_query_points'];omitted,omitted_ids,omitted_nearest=helper.query(omitted_points,v,f)
    assert np.all(omitted<=previous['omitted_distances']+1e-8),'additive_caps_increased_omission_distance'
    random,random_rows=helper.samples(v,f,100000,94000)
    boundary=load(job['boundaries']);parent_boundary_nodes=np.unique(boundary['boundary_local_nodes'])
    labels=[];patches=[]
    for curve in sorted(set(map(int,mesh['source_acquisition_curve_ids'][n:]))):
        rows=np.flatnonzero(mesh['source_acquisition_curve_ids']==curve);points,_=helper.samples(v,f[rows],1000,94001+curve)
        probes=np.r_[points,v[f[rows]].mean(axis=1),v[np.unique(f[rows])]]
        patches.append(probes);labels.extend([curve]*len(probes))
    cap_points=np.concatenate(patches) if patches else np.empty((0,3),dtype=np.float64)
    old_inferred_count=len(previous['retained_inferred_facet_rows']);old_inferred=previous['reverse_query_points'][-old_inferred_count:]
    reverse_points=np.r_[random,v[parent_boundary_nodes],cap_points,old_inferred]
    reverse,reverse_ids,reverse_nearest=helper.query(reverse_points,sv,sf[valid])
    a=100000+len(parent_boundary_nodes);b=a+len(cap_points);cap_distance=reverse[a:b];patch_labels=np.array(labels,dtype=np.int64)
    per_patch=[];rejected=[];limit=job['experimental_max_sampled_added_cap_distance_to_raw_source_nominal_mm']
    for curve in np.unique(patch_labels):
        stats=helper.stats(cap_distance[patch_labels==curve]);refused=stats['sampled_maximum_nominal_mm']>limit
        per_patch.append(dict(curve=int(curve),**stats,rejected_by_fixed_source_support_bound=bool(refused)))
        if refused:rejected.append(int(curve))
    args.output.mkdir(mode=0o700,exist_ok=False)
    np.savez_compressed(args.output/'private-distance-witnesses.npz',source_query_points=source_points,source_distances=forward,source_nearest_faces=forward_ids,source_nearest_points=forward_nearest,
                        omitted_query_points=omitted_points,omitted_distances=omitted,omitted_nearest_faces=omitted_ids,omitted_nearest_points=omitted_nearest,
                        reverse_query_points=reverse_points,reverse_distances=reverse,reverse_nearest_original_faces=np.flatnonzero(valid)[reverse_ids],reverse_nearest_original_points=reverse_nearest,
                        reverse_random_face_rows=random_rows,parent_boundary_vertex_ids=parent_boundary_nodes,cap_probe_curve_ids=patch_labels)
    for row in job['inputs']:assert sha(row['path'])==row['sha256']
    result=dict(source_sha256=sha(__file__),job_sha256=sha(args.job),mesh_sha256=sha(args.mesh),previous_witness_sha256=sha(args.previous_witness),
                literal_distance_controls_passed=True,source_random_to_candidate=helper.stats(forward[:100000]),original_source_boundary_vertices_to_candidate=helper.stats(forward[100000:199876]),
                original_quarantine_source_probes_to_candidate=helper.stats(forward[199876:]),all_previous_omitted_facet_probes_to_candidate=helper.stats(omitted),
                candidate_random_to_raw_source=helper.stats(reverse[:100000]),all_parent_boundary_vertices_to_raw_source=helper.stats(reverse[100000:a]),
                all_new_cap_probes_to_raw_source=helper.stats(cap_distance) if len(cap_distance) else None,unchanged_previous_inferred_probes_to_raw_source=helper.stats(reverse[b:]),
                private_per_patch_source_support_distances=per_patch,rejected_acquisition_curve_ids=rejected,
                experimental_added_cap_support_distance_limit_nominal_mm=limit,source_and_omission_distances_do_not_increase_pointwise=True,
                no_added_patch_exceeds_sampled_study_bound=not rejected,missing_cap_surfaces_have_no_measured_ground_truth=True,
                sampled_errors_are_not_Hausdorff_or_physical_tolerances=True,full_bare_head_created=False,manufacturing_authorized=False,seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(patches_probed=len(per_patch),patches_rejected=len(rejected),sampled_cap_maximum_nominal_mm=float(cap_distance.max()) if len(cap_distance) else None,seconds=result['seconds'])),flush=True)


if __name__=='__main__':main()
