"""Recheck both raw-scan distance directions and explicitly probe every new bridge."""
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
    for name in ('job','mesh','topology-proof','distance-source','previous-distance-witness','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();job=json.loads(args.job.read_text());started=time.monotonic()
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    proof=json.loads(args.topology_proof.read_text());assert proof['mesh_sha256']==sha(args.mesh) and proof['exact_whole_boundary_change_mask_verified']
    assert sha(args.distance_source)=='8e4f401c4c76ca4cafa28979a0b2bdaf80c77049acbac2dc2a610b490720e570'
    spec=importlib.util.spec_from_file_location('frozen_distance_sampling',args.distance_source)
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    v=np.array([[0.,0.,0.],[2.,0.,0.],[0.,2.,0.]])
    d,_,c=helper.query(np.array([[.25,.25,0.],[.25,.25,2.],[2.,2.,0.]]),v,np.array([[0,1,2]]))
    assert np.allclose(d,[0.,2.,np.sqrt(2.)],atol=1e-14,rtol=0) and np.allclose(c[-1],[1.,1.,0.],atol=1e-14,rtol=0)
    old_job=json.loads(Path(job['predicate_job']).read_text());raw=load(old_job['arrays']);mesh=load(args.mesh);base=load(job['mesh'])
    v,f=mesh['points'],mesh['triangles'];sv,sf=raw['vertices'],raw['triangles'];n=len(base['triangles'])
    assert np.array_equal(v,base['points']) and np.array_equal(f[:n],base['triangles'])
    cross=np.cross(sv[sf[:,1]]-sv[sf[:,0]],sv[sf[:,2]]-sv[sf[:,0]]);valid=np.any(cross!=0,axis=1);assert np.count_nonzero(~valid)==8
    source=load(args.previous_distance_witness);old=source['candidate_distances'];queries=source['source_query_points']
    after,source_nearest_faces,source_nearest_points=helper.query(queries,v,f)
    assert np.all(after<=old+1e-8),'source_distance_increased_after_additive_bridge'
    samples,sample_ids=helper.samples(v,f,100000,93540)
    boundary=load(args.topology_proof.parent/'private-contact-boundaries-and-fans.npz')['boundary_local_nodes'];boundary_nodes=np.unique(boundary)
    bridges=[];labels=[]
    for contact in sorted(set(map(int,mesh['source_contact_vertex_ids'][n:]))):
        rows=np.flatnonzero(mesh['source_contact_vertex_ids']==contact);points,_=helper.samples(v,f[rows],1000,93541+contact)
        probes=np.r_[points,v[f[rows]].mean(axis=1),v[np.unique(f[rows])]];bridges.append(probes);labels.extend([contact]*len(probes))
    bridge_probes=np.concatenate(bridges);reverse_queries=np.r_[samples,v[boundary_nodes],bridge_probes]
    reverse,ids,closest=helper.query(reverse_queries,sv,sf[valid]);b=100000+len(boundary_nodes)
    args.output.mkdir(mode=0o700,exist_ok=False)
    np.savez_compressed(args.output/'private-distance-witnesses.npz',source_query_points=queries,source_distances=after,
                        source_nearest_faces=source_nearest_faces,source_nearest_points=source_nearest_points,
                        candidate_query_points=reverse_queries,candidate_distances=reverse,candidate_random_face_ids=sample_ids,
                        candidate_nearest_original_faces=np.flatnonzero(valid)[ids],candidate_nearest_original_points=closest,
                        bridge_probe_contact_ids=np.array(labels,dtype=np.int64),boundary_vertex_ids=boundary_nodes)
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    result=dict(source_sha256=sha(__file__),job_sha256=sha(args.job),mesh_sha256=sha(args.mesh),
                previous_distance_witness_sha256=sha(args.previous_distance_witness),distance_control_passed=True,
                source_probe_count=len(queries),source_random_to_candidate=helper.stats(after[:100000]),
                original_boundary_vertices_to_candidate=helper.stats(after[100000:199876]),
                quarantined_face_probes_to_candidate=helper.stats(after[199876:]),candidate_random_to_original=helper.stats(reverse[:100000]),
                candidate_boundary_vertices_to_original=helper.stats(reverse[100000:b]),all_new_bridge_probes_to_original=helper.stats(reverse[b:]),
                source_distances_do_not_increase_pointwise=True,all_previous_geometry_and_patch_distance_witnesses_remain_applicable=True,
                missing_surfaces_have_no_measured_ground_truth=True,physical_calibration_or_tolerance_verified=False,
                full_bare_head_created=False,manufacturing_authorized=False,seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(source_to_candidate_sampled_maximum_nominal_mm=result['source_random_to_candidate']['sampled_maximum_nominal_mm'],
                         bridge_to_source_sampled_maximum_nominal_mm=result['all_new_bridge_probes_to_original']['sampled_maximum_nominal_mm'],seconds=result['seconds'])),flush=True)


if __name__=='__main__':main()
