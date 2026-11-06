"""Inspect complete saved strip candidates, provenance, topology and sampled support."""
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
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key] for key in data.files}


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job', 'mesh', 'intersection-proof', 'output'):
        parser.add_argument('--'+name, required=True, type=Path)
    args = parser.parse_args(); started = time.monotonic(); job = json.loads(args.job.read_text())
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    mesh_hash = sha(args.mesh); intersection_proof = json.loads(args.intersection_proof.read_text())
    assert intersection_proof['mesh_sha256'] == mesh_hash
    assert intersection_proof['source_sha256'] == '3e0b239ca4993388f32563092c78d97065cc1fb0753c68a2def3d631feda7976'
    base, data, boundary, raw, census = map(load, (job['mesh'], args.mesh, job['boundaries'], job['source_arrays'], job['census']))
    v, f = data['points'], data['triangles']; n = len(base['triangles']); nv = len(v); labels = data['source_frontier_pair_ids']
    assert np.array_equal(v, base['points']) and np.array_equal(f[:n], base['triangles'])
    assert np.array_equal(data['global_node_ids'], base['global_node_ids'])
    assert np.all(labels[:n] == -1) and np.all(labels[n:] >= 0)
    for key, values in base.items():
        if key in ('points', 'triangles', 'global_node_ids'):
            continue
        assert np.array_equal(data[key][:n], values)
        if key == 'inferred_surface_kind':
            assert np.all(data[key][n:] == 4)
        elif key == 'source_patch_curve_ids':
            assert np.array_equal(data[key][n:], 30000000+labels[n:])
        else:
            assert np.all(data[key][n:] == -1), key
    assert np.array_equal(data['frontier_immediate_parent_face_rows'][:n], np.arange(n))
    assert np.all(data['frontier_immediate_parent_face_rows'][n:] == -1)
    reader = module(job['obj_reader'], 'strip_obj_reader')
    obj_vertices, obj_faces = reader.read_obj(args.mesh.with_suffix('.obj'))
    assert np.array_equal(obj_vertices, v) and np.array_equal(obj_faces, f)
    pairing = module(job['pair_inspector'], 'independent_strip_pairing')
    owner_rows = boundary['boundary_face_rows']; source_ids = base['original_face_ids'][owner_rows]
    normals = np.zeros((len(owner_rows), 3)); valid_owners = source_ids >= 0
    q = raw['vertices'][raw['triangles'][source_ids[valid_owners]]]
    cross = np.cross(q[:, 1]-q[:, 0], q[:, 2]-q[:, 0]); cross /= np.linalg.norm(cross, axis=1)[:, None]
    normals[valid_owners] = cross
    for pair_id in np.unique(labels[n:]):
        rows = np.flatnonzero(labels == pair_id); assert len(rows) == 2 and np.all(rows >= n)
        first, second = census['selected_pair_edge_ids'][pair_id]
        reason, _ = pairing.inspect_pair(v, boundary['boundary_local_nodes'], normals, first, second, job['limits'])
        assert reason == 'eligible'
        a, b = boundary['boundary_local_nodes'][first]; c, d = boundary['boundary_local_nodes'][second]
        assert np.array_equal(f[rows], [[b, a, d], [b, d, c]]) or np.array_equal(f[rows], [[b, a, c], [a, d, c]])
        assert np.all(data['source_frontier_parent_curve_ids'][rows] == census['selected_pair_curve_ids'][pair_id])
    rejected = set(); intersection_pairs = np.load(args.intersection_proof.parent/'private-intersecting-face-pairs.npy', allow_pickle=False)
    excluded = np.load(args.intersection_proof.parent/'private-excluded-zero-cross-faces.npy', allow_pickle=False)
    assert len(intersection_pairs) == intersection_proof['full_mesh_intersection_pairs']
    for pair in intersection_pairs:
        involved = set(map(int, labels[pair]))-{-1}; assert involved
        rejected.update(involved)
    for row in excluded:
        assert labels[row] >= 0; rejected.add(int(labels[row]))
    topology = module(job['boundary_helper'], 'strip_boundary_inspection')
    fan_helper = module(job['fan_helper'], 'strip_all_used_vertex_inspection')
    all_edges, order, first, codes, uses = topology.table(f, nv)
    bad = uses > 2; twice = np.flatnonzero(uses == 2)
    bad[twice] |= np.any(all_edges[order[first[twice]]] != all_edges[order[first[twice]+1]][:, ::-1], axis=1)
    for index in np.flatnonzero(bad):
        involved = set(map(int, labels[order[first[index]:first[index]+uses[index]]//3]))-{-1}; assert involved
        rejected.update(involved)
    canonical = np.sort(f, axis=1); assert nv**3 < 2**63
    fc = (canonical[:, 0]*nv+canonical[:, 1])*nv+canonical[:, 2]
    fo = np.argsort(fc, kind='stable'); starts = np.r_[0, np.flatnonzero(fc[fo][1:] != fc[fo][:-1])+1]
    counts = np.diff(np.r_[starts, len(f)])
    for index in np.flatnonzero(counts > 1):
        involved = set(map(int, labels[fo[starts[index]:starts[index]+counts[index]]]))-{-1}; assert involved
        rejected.update(involved)
    used_fans = None; nonmanifold = None; topology_data = None; origins = None; review = []; closed_old = None
    if not bad.any() and not np.any(counts > 1):
        used_fans, _ = fan_helper.vertex_fans(f, nv)
        bad_vertices = np.flatnonzero(used_fans > 1); nonmanifold = len(bad_vertices)
        for node in bad_vertices:
            involved = set(map(int, labels[np.any(f == node, axis=1)]))-{-1}; assert involved
            rejected.update(involved)
        if not nonmanifold:
            topology_data = topology.fans_and_cycles(f, nv)
            old_edges = boundary['boundary_local_nodes']; old_codes = old_edges.min(axis=1)*nv+old_edges.max(axis=1)
            old_order = np.argsort(old_codes); old_codes = old_codes[old_order]
            remaining = topology_data['boundary']; new_codes = remaining.min(axis=1)*nv+remaining.max(axis=1)
            positions = np.searchsorted(old_codes, new_codes); inherited = positions < len(old_codes)
            inherited[inherited] &= old_codes[positions[inherited]] == new_codes[inherited]
            origins = np.full(len(remaining), 6, dtype=np.int8); old_ids = np.full(len(remaining), -1, dtype=np.int64)
            old_ids[inherited] = old_order[positions[inherited]]
            assert np.array_equal(remaining[inherited], old_edges[old_ids[inherited]])
            assert np.array_equal(topology_data['owners'][inherited], boundary['boundary_face_rows'][old_ids[inherited]])
            origins[inherited] = boundary['edge_origin_kind'][old_ids[inherited]]
            missing = np.ones(len(old_edges), dtype=bool); missing[old_ids[inherited]] = False
            assert np.all(boundary['edge_origin_kind'][missing] == 1)
            new_face_edges = np.stack((f[n:, [0, 1]], f[n:, [1, 2]], f[n:, [2, 0]]), axis=1).reshape(-1, 2)
            reverse_new_codes = new_face_edges.min(axis=1)*nv+new_face_edges.max(axis=1)
            assert np.all(np.isin(old_codes[missing[old_order]], reverse_new_codes))
            closed_old = int(missing.sum())
            for curve in range(len(topology_data['offsets'])-1):
                a, b = topology_data['offsets'][curve:curve+2]; ids = topology_data['cycle_edges'][a:b]
                descriptor, _, _ = topology.geometry(v[remaining[ids, 0]])
                review.append(dict(curve=curve, edges=len(ids), **descriptor,
                                   edge_origin_counts=dict(Counter(map(str, origins[ids]))),
                                   parent_boundary_curve_ids=sorted(set(map(int, census['edge_curve_ids'][old_ids[ids][old_ids[ids] >= 0]]))),
                                   physical_classification='unreviewed', closure_authorized=False))
            topology_data.update(edge_origin_kind=origins, parent_boundary_edge_ids=old_ids, all_used_vertex_fans=used_fans)
    distance = module(job['distance_helper'], 'strip_distance_inspection')
    literal = np.array([[0., 0., 0.], [2., 0., 0.], [0., 2., 0.]])
    control_distance, _, _ = distance.query(np.array([[.25, .25, 2.], [2., 2., 0.]]), literal, np.array([[0, 1, 2]]))
    assert np.allclose(control_distance, [2., np.sqrt(2.)], rtol=0, atol=1e-14)
    degree = job['triangle_sample_grid_order']
    weights = np.array([(a/degree, b/degree, 1-(a+b)/degree) for a in range(degree+1) for b in range(degree+1-a)])
    assert len(weights) == (degree+1)*(degree+2)//2
    added_points = np.einsum('ij,fjk->fik', weights, v[f[n:]]).reshape(-1, 3)
    raw_cross = np.cross(raw['vertices'][raw['triangles'][:, 1]]-raw['vertices'][raw['triangles'][:, 0]], raw['vertices'][raw['triangles'][:, 2]]-raw['vertices'][raw['triangles'][:, 0]])
    valid = np.any(raw_cross != 0, axis=1); assert np.count_nonzero(~valid) == 8
    added_distances, nearest, closest = distance.query(added_points, raw['vertices'], raw['triangles'][valid])
    probe_labels = np.repeat(labels[n:], len(weights)); support = []
    for pair_id in np.unique(probe_labels):
        maximum = float(added_distances[probe_labels == pair_id].max())
        refused = maximum > job['maximum_added_patch_to_raw_sample_distance_nominal_mm']
        support.append(dict(pair=int(pair_id), sampled_maximum_nominal_mm=maximum, refused=bool(refused)))
        if refused:
            rejected.add(int(pair_id))
    previous = load(job['previous_distance_witness'])
    forward, _, _ = distance.query(previous['source_query_points'], v, f)
    omission, _, _ = distance.query(previous['omitted_query_points'], v, f)
    assert np.all(forward <= previous['source_distances']+1e-8)
    assert np.all(omission <= previous['omitted_distances']+1e-8)
    random, _ = distance.samples(v, f, 100000, 95201)
    reverse, _, _ = distance.query(random, raw['vertices'], raw['triangles'][valid])
    component_edges = np.r_[f[:, [0, 1]], f[:, [1, 2]]]
    graph = coo_matrix((np.ones(len(component_edges), dtype=np.int8), (component_edges[:, 0], component_edges[:, 1])), shape=(nv, nv)).tocsr()
    _, component_labels = connected_components(graph, directed=False)
    sizes = np.bincount(component_labels[f[:, 0]])
    args.output.mkdir(mode=0o700, exist_ok=False)
    if topology_data is not None:
        np.savez_compressed(args.output/'private-boundaries-and-fans.npz', **topology_data)
        (args.output/'private-curve-review.json').write_text(json.dumps(review, indent=2)+'\n')
    np.savez_compressed(args.output/'private-distance-witnesses.npz', source_query_points=previous['source_query_points'], source_distances=forward,
                        omitted_query_points=previous['omitted_query_points'], omitted_distances=omission,
                        added_query_points=added_points, added_distances=added_distances, added_probe_pair_ids=probe_labels,
                        added_nearest_original_faces=np.flatnonzero(valid)[nearest], added_nearest_original_points=closest,
                        random_query_points=random, random_distances=reverse)
    (args.output/'private-patch-support.json').write_text(json.dumps(support, indent=2)+'\n')
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    assert sha(args.mesh) == mesh_hash
    report = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), mesh_sha256=mesh_hash,
                  obj_sha256=sha(args.mesh.with_suffix('.obj')), npz_and_obj_exact_readback=True,
                  parent_vertices_faces_and_all_provenance_preserved=True,
                  whole_mesh_intersection_pairs=len(intersection_pairs), zero_area_faces=len(excluded),
                  edge_incidence_or_winding_conflicts=int(bad.sum()), duplicate_indexed_face_groups=int(np.count_nonzero(counts > 1)),
                  nonmanifold_used_vertices=nonmanifold, unused_vertices=int(np.count_nonzero(used_fans == 0)) if used_fans is not None else None,
                  added_strip_pairs=len(np.unique(labels[n:])), added_triangles=len(f)-n,
                  closed_acquired_parent_boundary_edges=closed_old,
                  remaining_boundary_edges=int(np.count_nonzero(uses == 1)), remaining_boundary_walks=len(review) if topology_data is not None else None,
                  remaining_edge_origin_counts=dict(Counter(map(str, origins))) if origins is not None else None,
                  connected_surface_components=int(np.count_nonzero(sizes)), largest_component_facets=int(sizes.max()), single_facet_components=int(np.count_nonzero(sizes == 1)),
                  added_probe_count=len(added_distances), added_sampled_maximum_nominal_mm=float(added_distances.max()) if len(added_distances) else None,
                  support_refused_pair_count=sum(row['refused'] for row in support), source_probe_count=len(forward), omission_probe_count=len(omission),
                  previous_source_and_omission_distances_nonincreasing_pointwise=True, random_candidate_to_raw=distance.stats(reverse),
                  rejected_frontier_pair_ids=sorted(rejected), surface_study_checks_passed=not rejected,
                  inferred_missing_surfaces_have_no_measured_ground_truth=True, sampled_distances_are_not_Hausdorff_or_physical_tolerances=True,
                  closed_volume=not np.any(uses == 1), full_bare_head_created=False, physical_acceptance=False, manufacturing_authorized=False,
                  seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if not isinstance(v, (dict, list))}), flush=True)


if __name__ == '__main__':
    main()
