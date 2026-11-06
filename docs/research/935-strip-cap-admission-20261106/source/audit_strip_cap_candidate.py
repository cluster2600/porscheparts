"""Audit full cap candidates, unchanged source ancestry and both sampled directions."""
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
        return {key:data[key] for key in data.files}


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job', 'mesh', 'intersection-proof', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args(); job = json.loads(args.job.read_text()); started = time.monotonic()
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    before = sha(args.mesh); proof = json.loads(args.intersection_proof.read_text())
    assert proof['mesh_sha256'] == before and proof['source_sha256'] == '3e0b239ca4993388f32563092c78d97065cc1fb0753c68a2def3d631feda7976'
    base, data, boundary, raw = map(load, (job['mesh'], args.mesh, job['boundaries'], job['source_arrays']))
    v, f = data['points'], data['triangles']; n, nv = len(base['triangles']), len(v); labels = data['source_strip_cap_curve_ids']
    assert np.array_equal(v, base['points']) and np.array_equal(f[:n], base['triangles'])
    assert np.array_equal(data['global_node_ids'], base['global_node_ids'])
    assert np.all(labels[:n] == -1) and np.all(labels[n:] >= 0)
    for key, values in base.items():
        if key in ('points', 'triangles', 'global_node_ids'):
            continue
        assert np.array_equal(values, data[key][:n])
        if key == 'inferred_surface_kind':
            assert np.all(data[key][n:] == 5)
        elif key == 'source_patch_curve_ids':
            assert np.array_equal(data[key][n:], 40000000+labels[n:])
        else:
            assert np.all(data[key][n:] == -1), key
    assert np.array_equal(data['strip_cap_immediate_parent_face_rows'][:n], np.arange(n))
    assert np.all(data['strip_cap_immediate_parent_face_rows'][n:] == -1)
    reader = module(job['patch_checker'], 'frozen_cap_obj_reader')
    ov, of = reader.read_obj(args.mesh.with_suffix('.obj'))
    assert np.array_equal(ov, v) and np.array_equal(of, f)
    local = json.loads((Path(job['local_checks'])/'report.json').read_text())
    expected = {row['curve']:row for row in local['private_patch_results'] if row['accepted']}
    closed = []
    for curve in np.unique(labels[n:]):
        assert int(curve) in expected
        path = Path(job['local_checks'])/('private-patch-'+str(curve).zfill(4)+'.npz')
        assert sha(path) == expected[int(curve)]['private_patch_sha256']
        assert np.array_equal(f[labels == curve], load(path)['triangles'])
        a, b = boundary['offsets'][curve:curve+2]; closed.extend(map(int, boundary['cycle_edges'][a:b]))
    rejected = set(); pairs = np.load(args.intersection_proof.parent/'private-intersecting-face-pairs.npy', allow_pickle=False)
    excluded = np.load(args.intersection_proof.parent/'private-excluded-zero-cross-faces.npy', allow_pickle=False)
    assert len(pairs) == proof['full_mesh_intersection_pairs']
    for pair in pairs:
        ids = set(map(int, labels[pair]))-{-1}; assert ids
        rejected.update(ids)
    for face in excluded:
        assert labels[face] >= 0; rejected.add(int(labels[face]))
    topology = module(job['boundary_helper'], 'frozen_cap_boundary_topology')
    fan_helper = module(job['fan_helper'], 'frozen_cap_complete_vertex_fans')
    edges, order, first, codes, uses = topology.table(f, nv)
    bad = uses > 2; paired = np.flatnonzero(uses == 2)
    bad[paired] |= np.any(edges[order[first[paired]]] != edges[order[first[paired]+1]][:, ::-1], axis=1)
    for i in np.flatnonzero(bad):
        ids = set(map(int, labels[order[first[i]:first[i]+uses[i]]//3]))-{-1}; assert ids
        rejected.update(ids)
    canonical = np.sort(f, axis=1); assert nv**3 < 2**63
    face_codes = (canonical[:, 0]*nv+canonical[:, 1])*nv+canonical[:, 2]
    fo = np.argsort(face_codes); fs = np.r_[0, np.flatnonzero(face_codes[fo][1:] != face_codes[fo][:-1])+1]
    counts = np.diff(np.r_[fs, len(f)])
    for i in np.flatnonzero(counts > 1):
        ids = set(map(int, labels[fo[fs[i]:fs[i]+counts[i]]]))-{-1}; assert ids
        rejected.update(ids)
    fan_counts = None; new_boundary = None; reviews = []; nonmanifold = None
    if not bad.any() and not np.any(counts > 1):
        fan_counts, _ = fan_helper.vertex_fans(f, nv)
        bad_nodes = np.flatnonzero(fan_counts > 1); nonmanifold = len(bad_nodes)
        for node in bad_nodes:
            ids = set(map(int, labels[np.any(f == node, axis=1)]))-{-1}; assert ids
            rejected.update(ids)
        if not nonmanifold:
            new_boundary = topology.fans_and_cycles(f, nv)
            old_edges = boundary['boundary']; old_code = old_edges.min(axis=1)*nv+old_edges.max(axis=1)
            old_order = np.argsort(old_code); old_sorted = old_code[old_order]
            current = new_boundary['boundary']; current_code = current.min(axis=1)*nv+current.max(axis=1)
            pos = np.searchsorted(old_sorted, current_code)
            assert np.all(pos < len(old_sorted)) and np.array_equal(old_sorted[pos], current_code)
            old_ids = old_order[pos]
            assert np.array_equal(current, old_edges[old_ids])
            assert np.array_equal(new_boundary['owners'], boundary['owners'][old_ids])
            missing = np.ones(len(old_edges), dtype=bool); missing[old_ids] = False
            assert np.array_equal(np.flatnonzero(missing), np.array(sorted(closed), dtype=np.int64))
            new_boundary.update(edge_origin_kind=boundary['edge_origin_kind'][old_ids], parent_boundary_edge_ids=old_ids,
                                all_used_vertex_fans=fan_counts)
            for curve in range(len(new_boundary['offsets'])-1):
                a, b = new_boundary['offsets'][curve:curve+2]; ids = new_boundary['cycle_edges'][a:b]
                descriptor, _, _ = topology.geometry(v[current[ids, 0]])
                reviews.append(dict(curve=curve, edges=len(ids), **descriptor,
                                    edge_origin_counts=dict(Counter(map(str, new_boundary['edge_origin_kind'][ids]))),
                                    physical_classification='unreviewed', closure_authorized=False))
    distance = module(job['distance_source'], 'frozen_cap_distances')
    literal = np.array([[0., 0., 0.], [2., 0., 0.], [0., 2., 0.]])
    d, _, _ = distance.query(np.array([[.25, .25, 2.], [2., 2., 0.]]), literal, np.array([[0, 1, 2]]))
    assert np.allclose(d, [2., np.sqrt(2.)], rtol=0, atol=1e-14)
    degree = job['sample_triangle_grid_order']
    weights = np.array([(a/degree, b/degree, 1-(a+b)/degree) for a in range(degree+1) for b in range(degree+1-a)])
    added_points = np.einsum('ij,fjk->fik', weights, v[f[n:]]).reshape(-1, 3)
    sv, sf = raw['vertices'], raw['triangles']; cross = np.cross(sv[sf[:, 1]]-sv[sf[:, 0]], sv[sf[:, 2]]-sv[sf[:, 0]])
    valid = np.any(cross != 0, axis=1); assert np.count_nonzero(~valid) == 8
    added_distance, nearest, closest = distance.query(added_points, sv, sf[valid])
    patch_labels = np.repeat(labels[n:], len(weights)); support = []
    for curve in np.unique(patch_labels):
        maximum = float(added_distance[patch_labels == curve].max()); refused = maximum > job['max_sampled_added_surface_distance_nominal_mm']
        support.append(dict(curve=int(curve), sampled_maximum_nominal_mm=maximum, refused=bool(refused)))
        if refused:
            rejected.add(int(curve))
    previous = load(job['previous_witness'])
    source_distance, _, _ = distance.query(previous['source_query_points'], v, f)
    omission_distance, _, _ = distance.query(previous['omitted_query_points'], v, f)
    assert np.all(source_distance <= previous['source_distances']+1e-8)
    assert np.all(omission_distance <= previous['omitted_distances']+1e-8)
    random, _ = distance.samples(v, f, 100000, 96500)
    reverse, _, _ = distance.query(random, sv, sf[valid])
    graph_edges = np.r_[f[:, [0, 1]], f[:, [1, 2]]]
    graph = coo_matrix((np.ones(len(graph_edges), dtype=np.int8), (graph_edges[:, 0], graph_edges[:, 1])), shape=(nv, nv)).tocsr()
    _, components = connected_components(graph, directed=False); sizes = np.bincount(components[f[:, 0]])
    args.output.mkdir(mode=0o700, exist_ok=False)
    if new_boundary is not None:
        np.savez_compressed(args.output/'private-boundaries-and-fans.npz', **new_boundary)
        (args.output/'private-curve-review.json').write_text(json.dumps(reviews, indent=2)+'\n')
    np.savez_compressed(args.output/'private-distance-witnesses.npz', source_query_points=previous['source_query_points'], source_distances=source_distance,
                        omitted_query_points=previous['omitted_query_points'], omitted_distances=omission_distance,
                        added_query_points=added_points, added_distances=added_distance, added_probe_curve_ids=patch_labels,
                        added_nearest_original_faces=np.flatnonzero(valid)[nearest], added_nearest_original_points=closest,
                        random_query_points=random, random_distances=reverse)
    (args.output/'private-cap-support.json').write_text(json.dumps(support, indent=2)+'\n')
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    assert sha(args.mesh) == before
    report = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), mesh_sha256=before, parent_mesh_sha256=sha(job['mesh']),
                  obj_sha256=sha(args.mesh.with_suffix('.obj')), exact_OBJ_NPZ_parent_and_provenance_preserved=True,
                  retained_caps=len(np.unique(labels[n:])), added_triangles=len(f)-n,
                  intersection_pairs=len(pairs), zero_area_faces=len(excluded), duplicate_face_groups=int(np.count_nonzero(counts > 1)),
                  edge_incidence_or_winding_conflicts=int(bad.sum()), nonmanifold_used_vertices=nonmanifold,
                  unused_vertices=int(np.count_nonzero(fan_counts == 0)) if fan_counts is not None else None,
                  only_selected_complete_walks_closed=new_boundary is not None, closed_parent_boundary_edges=len(closed),
                  remaining_boundary_edges=int(np.count_nonzero(uses == 1)), remaining_boundary_walks=len(reviews) if new_boundary is not None else None,
                  remaining_edge_origin_counts=dict(Counter(map(str, new_boundary['edge_origin_kind']))) if new_boundary is not None else None,
                  connected_surface_components=int(np.count_nonzero(sizes)), largest_component_facets=int(sizes.max()), single_facet_components=int(np.count_nonzero(sizes == 1)),
                  new_cap_probe_count=len(added_distance), new_cap_sampled_maximum_nominal_mm=float(added_distance.max()) if len(added_distance) else None,
                  support_refused_caps=sum(row['refused'] for row in support), source_probe_count=len(source_distance), omission_probe_count=len(omission_distance),
                  previous_source_and_omission_distances_nonincreasing_pointwise=True, source_to_candidate=distance.stats(source_distance), random_candidate_to_source=distance.stats(reverse),
                  rejected_strip_cap_curve_ids=sorted(rejected), surface_study_checks_passed=not rejected,
                  missing_surface_ground_truth_available=False, sampled_distances_are_not_Hausdorff_or_physical_tolerances=True,
                  closed_volume=not np.any(uses == 1), full_bare_head_created=False, physical_acceptance=False, manufacturing_authorized=False,
                  seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if not isinstance(v, (dict, list))}), flush=True)


if __name__ == '__main__':
    main()
