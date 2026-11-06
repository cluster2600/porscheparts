"""Measure both whole-source directions and explicitly probe every inferred patch."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def load(path):
    with np.load(path,allow_pickle=False) as data:return {key:data[key] for key in data.files}


def samples(vertices,faces,count,seed):
    rng = np.random.default_rng(seed)
    p = vertices[faces];areas = np.linalg.norm(np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]),axis=1)
    assert np.isfinite(areas).all() and areas.sum()>0
    ids = rng.choice(len(faces),size=count,p=areas/areas.sum())
    r,s = np.sqrt(rng.random(count)),rng.random(count)
    points = (1-r[:,None])*p[ids,0]+(r*(1-s))[:,None]*p[ids,1]+(r*s)[:,None]*p[ids,2]
    return points,ids


def query(points,vertices,faces):
    import igl
    squared,ids,closest = igl.point_mesh_squared_distance(np.ascontiguousarray(points,dtype=np.float64),
        np.ascontiguousarray(vertices,dtype=np.float64),np.ascontiguousarray(faces,dtype=np.int64))
    squared,ids,closest = np.asarray(squared),np.asarray(ids),np.asarray(closest)
    assert squared.shape==(len(points),) and ids.shape==(len(points),) and closest.shape==points.shape
    assert np.isfinite(squared).all() and np.all(squared>=0) and np.isfinite(closest).all()
    assert np.all(ids>=0) and np.all(ids<len(faces))
    return np.sqrt(squared),ids,closest


def stats(distance):
    assert len(distance)>0
    return dict(points=len(distance),minimum_nominal_mm=float(distance.min()),median_nominal_mm=float(np.median(distance)),
                p90_nominal_mm=float(np.quantile(distance,.9)),p95_nominal_mm=float(np.quantile(distance,.95)),
                p99_nominal_mm=float(np.quantile(distance,.99)),sampled_maximum_nominal_mm=float(distance.max()),
                coverage_at_nominal_mm={str(t):float(np.mean(distance<=t)) for t in (.05,.1,.25,.5)},
                sampled_error_is_not_Hausdorff_or_physical_accuracy=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job','mesh','global-proof','fan-proof','source-boundaries','source-excluded','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args();job = json.loads(args.job.read_text());started = time.monotonic()
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    proof = json.loads(args.global_proof.read_text());assert proof['mesh_sha256']==sha(args.mesh) and proof['source_preserving_surface_checks_passed']
    fan = json.loads(args.fan_proof.read_text());assert fan['mesh_sha256']==sha(args.mesh) and fan['all_used_vertex_fan_counts_unchanged']
    import igl
    assert Path(igl.__file__).resolve().is_relative_to(Path(job['igl_addon']).resolve())
    v = np.array([[0.,0.,0.],[2.,0.,0.],[0.,2.,0.]]);f = np.array([[0,1,2]])
    d,i,c = query(np.array([[.25,.25,0.],[.25,.25,2.],[2.,2.,0.]]),v,f)
    assert np.allclose(d,[0.,2.,np.sqrt(2.)],atol=1e-14,rtol=0) and np.all(i==0)
    assert np.allclose(c,[[.25,.25,0.],[.25,.25,0.],[1.,1.,0.]],atol=1e-14,rtol=0)
    args.output.mkdir(mode=0o700,exist_ok=False);source = load(job['arrays']);base = load(job['retained']);candidate = load(args.mesh)
    sv,sf = source['vertices'],source['triangles'];cv,cf = candidate['points'],candidate['triangles']
    assert np.array_equal(cv,base['points']) and np.array_equal(cf[:len(base['triangles'])],base['triangles'])
    assert sha(args.source_boundaries)=='dcdb28a642cac24dfd7279508d6605ee0e8c2f363dede4985e3fe55012e959f2'
    assert sha(args.source_excluded)=='b1fbeb39ce958aff980ccdc60d98915ac87a9a3eaf549365f98a42c2381ee77e'
    original_boundary = np.unique(np.load(args.source_boundaries,allow_pickle=False));excluded = np.load(args.source_excluded,allow_pickle=False)
    cross = np.cross(sv[sf[:,1]]-sv[sf[:,0]],sv[sf[:,2]]-sv[sf[:,0]])
    valid = np.any(cross!=0,axis=1);assert np.array_equal(np.flatnonzero(~valid),excluded) and len(excluded)==8
    valid_ids = np.flatnonzero(valid);raw_faces = sf[valid]
    source_sample,source_sample_ids = samples(sv,raw_faces,100000,93529)
    q = np.flatnonzero((load(job['roles'])['original_face_roles']==-2)&valid)
    rng = np.random.default_rng(93531);q_ids = np.repeat(q,100)
    r,s = np.sqrt(rng.random(len(q_ids))),rng.random(len(q_ids));p = sv[sf[q_ids]]
    q_points = (1-r[:,None])*p[:,0]+(r*(1-s))[:,None]*p[:,1]+(r*s)[:,None]*p[:,2]
    source_queries = np.r_[source_sample,sv[original_boundary],q_points]
    before,before_ids,before_closest = query(source_queries,base['points'],base['triangles'])
    after,after_ids,after_closest = query(source_queries,cv,cf)
    assert np.all(after<=before+1e-8),'Adding source-preserving patches increased measured source distance'
    candidate_sample,candidate_sample_ids = samples(cv,cf,100000,93530)
    old_boundary = load(job['boundaries']);remaining = load(args.fan_proof.parent/'private-used-vertex-fans-and-boundaries.npz')['remaining_original_boundary_edge_ids']
    remaining_global_nodes = np.unique(old_boundary['boundary_global_nodes'][remaining]);local_nodes = np.searchsorted(candidate['global_node_ids'],remaining_global_nodes)
    assert np.array_equal(candidate['global_node_ids'][local_nodes],remaining_global_nodes)
    patch_points = [];patch_labels = [];patch_row_ids = []
    for curve in sorted(set(map(int,candidate['source_patch_curve_ids']))-{-1}):
        ids = np.flatnonzero(candidate['source_patch_curve_ids']==curve)
        points,which = samples(cv,cf[ids],1000,93600+curve)
        probes = np.r_[points,cv[cf[ids]].mean(axis=1),cv[np.unique(cf[ids])]]
        patch_points.append(probes);patch_labels.extend([curve]*len(probes));patch_row_ids.append(ids[which])
    inferred = np.concatenate(patch_points);candidate_queries = np.r_[candidate_sample,cv[local_nodes],inferred]
    reverse,reverse_ids,reverse_closest = query(candidate_queries,sv,raw_faces)
    a,b = 100000,100000+len(original_boundary);c,d = 100000,100000+len(local_nodes)
    per_patch = []
    labels = np.array(patch_labels,dtype=np.int32)
    for curve in np.unique(labels):per_patch.append(dict(curve=int(curve),**stats(reverse[d:][labels==curve])))
    np.savez_compressed(args.output/'private-source-distance-witnesses.npz',source_query_points=source_queries,
                        source_random_face_ids=valid_ids[source_sample_ids],source_boundary_vertex_ids=original_boundary,
                        quarantine_probe_face_ids=q_ids,base_distances=before,base_nearest_faces=before_ids,base_nearest_points=before_closest,
                        candidate_distances=after,candidate_nearest_faces=after_ids,candidate_nearest_points=after_closest)
    np.savez_compressed(args.output/'private-candidate-distance-witnesses.npz',candidate_query_points=candidate_queries,
                        candidate_random_face_ids=candidate_sample_ids,candidate_boundary_vertex_ids=local_nodes,
                        inferred_probe_curve_ids=labels,distances=reverse,nearest_original_faces=valid_ids[reverse_ids],nearest_original_points=reverse_closest)
    result = dict(source_sha256=sha(__file__),job_sha256=sha(args.job),candidate_sha256=sha(args.mesh),
                  controls=dict(literal_on_surface_and_offset_distances=True,known_closest_points=True),random_samples_each_surface=100000,
                  seeds=dict(source=93529,candidate=93530,quarantine=93531,inferred='93600 + source curve index'),
                  original_zero_area_faces_excluded_from_distance_target=len(excluded),all_original_boundary_vertices=len(original_boundary),
                  source_random_to_base=stats(before[:a]),source_random_to_candidate=stats(after[:a]),
                  original_boundary_vertices_to_candidate=stats(after[a:b]),quarantined_face_probes_to_base=stats(before[b:]),
                  quarantined_face_probes_to_candidate=stats(after[b:]),candidate_random_to_original=stats(reverse[:c]),
                  candidate_boundary_vertices_to_original=stats(reverse[c:d]),all_inferred_patch_probes_to_original=stats(reverse[d:]),
                  private_per_patch_deviations=per_patch,source_distances_do_not_increase_pointwise=True,
                  original_component_exclusions_are_still_hypotheses=True,missing_surfaces_have_no_measured_ground_truth=True,
                  physical_calibration_or_tolerance_verified=False,full_bare_head_created=False,manufacturing_authorized=False,
                  seconds=time.monotonic()-started)
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    assert sha(args.mesh)==proof['mesh_sha256']
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(source_to_candidate_sampled_maximum_nominal_mm=result['source_random_to_candidate']['sampled_maximum_nominal_mm'],
                         candidate_to_source_sampled_maximum_nominal_mm=result['candidate_random_to_original']['sampled_maximum_nominal_mm'],
                         all_inferred_probe_maximum_nominal_mm=result['all_inferred_patch_probes_to_original']['sampled_maximum_nominal_mm'],
                         seconds=result['seconds'])),flush=True)


if __name__=='__main__':main()
