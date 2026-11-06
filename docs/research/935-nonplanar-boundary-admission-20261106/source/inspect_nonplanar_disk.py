"""Actual exported-disk, full native geometry and sampled source-support checks."""
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def check_disk(nodes, patch):
    assert len(patch) == len(nodes)-2 and len(set(nodes)) == len(nodes)
    assert set(map(int, patch.ravel())) == set(map(int, nodes))
    directed, owners = defaultdict(list), defaultdict(list)
    for index, triangle in enumerate(patch):
        assert len(set(triangle)) == 3
        for a, b in zip(triangle, np.roll(triangle, -1)):
            key = tuple(sorted((int(a), int(b))))
            directed[key].append((int(a), int(b)))
            owners[key].append(index)
    assert all(len(v) in (1, 2) for v in directed.values())
    rim = {tuple(map(int, x)) for x in zip(np.roll(nodes, -1), nodes)}
    assert {v[0] for v in directed.values() if len(v) == 1} == rim
    assert all(v[0] == v[1][::-1] for v in directed.values() if len(v) == 2)
    assert len(nodes)-len(directed)+len(patch) == 1
    graph = defaultdict(set)
    for incident in owners.values():
        if len(incident) == 2:
            a, b = incident
            graph[a].add(b)
            graph[b].add(a)
    seen, pending = set(), [0]
    while pending:
        face = pending.pop()
        if face not in seen:
            seen.add(face)
            pending.extend(graph[face]-seen)
    assert len(seen) == len(patch)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('job', 'constructed', 'output'):
        parser.add_argument('--'+key, required=True, type=Path)
    args = parser.parse_args()
    began = time.monotonic()
    job = json.loads(args.job.read_text())
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    construction = json.loads((args.constructed/'report.json').read_text())
    assert construction['source_sha256'] == sha(job['constructor_source'])
    assert construction['job_sha256'] == sha(args.job)
    assert construction['candidate_sha256'] == sha(args.constructed/'candidate.npz')
    assert construction['obj_sha256'] == sha(args.constructed/'candidate.obj')
    assert construction['patch_sha256'] == sha(args.constructed/'private-patch.npz')
    parent, body, patch_data = [dict(np.load(p, allow_pickle=False)) for p in
                               (job['mesh'], args.constructed/'candidate.npz', args.constructed/'private-patch.npz')]
    old_count = len(parent['triangles'])
    assert set(body) == set(parent) | {'source_nonplanar_cap_curve_ids', 'nonplanar_cap_immediate_parent_face_rows'}
    patch = body['triangles'][old_count:]
    nodes = patch_data['parent_boundary_nodes']
    walk = int(patch_data['parent_boundary_walk'])
    assert np.array_equal(patch, patch_data['triangles'])
    for key, values in parent.items():
        actual = body[key] if key in ('points', 'global_node_ids') else body[key][:len(values)]
        assert np.array_equal(values, actual), key
    assert np.array_equal(body['points'], parent['points'])
    for key in set(parent)-{'points', 'triangles', 'global_node_ids'}:
        expected = 10 if key == 'inferred_surface_kind' else 70000000+walk if key == 'source_patch_curve_ids' else -1
        assert np.all(body[key][old_count:] == expected)
    assert np.all(body['source_nonplanar_cap_curve_ids'][:old_count] == -1)
    assert np.all(body['source_nonplanar_cap_curve_ids'][old_count:] == walk)
    assert np.array_equal(body['nonplanar_cap_immediate_parent_face_rows'][:old_count], np.arange(old_count))
    assert np.all(body['nonplanar_cap_immediate_parent_face_rows'][old_count:] == -1)
    border = dict(np.load(job['boundaries'], allow_pickle=False))
    a, b = border['offsets'][walk:walk+2]
    edge_ids = border['cycle_edges'][a:b]
    assert np.array_equal(nodes, border['boundary'][edge_ids, 0])
    check_disk(nodes, patch)
    scalar = module(job['necessary_checker'], 'independent_nonplanar_source_checker')
    raw = dict(np.load(job['source_arrays'], allow_pickle=False))
    acquired, _ = scalar.recover_owners(parent, border, raw, edge_ids)
    legal, _ = scalar.triangle_replay(parent['points'][nodes], acquired)
    lookup = {int(node):i for i, node in enumerate(nodes)}
    assert all(tuple(sorted(lookup[int(v)] for v in face)) in set(map(tuple, legal)) for face in patch)
    # check_disk owns orientation; the Fraction predicate owns acquired-border alignment.
    reader = module(job['obj_reader'], 'frozen_disk_OBJ_reader')
    read_points, read_faces = reader.read_obj(args.constructed/'candidate.obj')
    assert np.array_equal(read_points, body['points']) and np.array_equal(read_faces, body['triangles'])
    del read_points, read_faces, acquired, parent
    args.output.mkdir(mode=0o700, exist_ok=False)
    detector = module(job['intersection_helper'], 'frozen_nonplanar_intersections')
    pairs, coplanar, excluded = detector.detect(body['points'], body['triangles'])
    np.savez_compressed(args.output/'private-native-intersections.npz', pairs=pairs, coplanar=coplanar, zero_area_faces=excluded)
    failures = []
    if len(pairs) or len(excluded):
        failures.append('whole_native_intersection_or_zero_area')
    if not failures:
        fans_helper = module(job['fan_helper'], 'frozen_nonplanar_fans')
        fans, boundary = fans_helper.vertex_fans(body['triangles'], len(body['points']))
        assert np.all(fans[fans > 0] == 1)
        canonical = np.sort(body['triangles'], axis=1)
        order = np.lexsort(canonical.T[::-1])
        assert not np.any(np.all(canonical[order[1:]] == canonical[order[:-1]], axis=1))
        keep = np.ones(len(border['boundary']), dtype=bool)
        keep[edge_ids] = False
        expected = set(map(tuple, border['boundary'][keep]))
        assert set(map(tuple, boundary)) == expected and len(boundary) == len(expected)
        unused = int(np.count_nonzero(fans == 0))
        del fans, canonical, order
        distances = module(job['distance_helper'], 'frozen_nonplanar_distances')
        weight = np.array([(i/16, j/16, (16-i-j)/16) for i in range(17) for j in range(17-i)])
        queries = np.einsum('ij,fjk->fik', weight, body['points'][patch]).reshape(-1, 3)
        added_distances, ids, closest = distances.query(queries, raw['vertices'], raw['triangles'])
        maximum = float(added_distances.max())
        np.savez_compressed(args.output/'private-cap-distance-witnesses.npz', query_points=queries,
                            distances=added_distances, nearest_original_faces=ids, nearest_original_points=closest)
        if maximum > .25:
            failures.append('complete_patch_sampled_support_exceeds_0.25_nominal_mm')
        if not failures:
            prior = dict(np.load(job['parent_distances'], allow_pickle=False))
            source, _, _ = distances.query(prior['source_query_points'], body['points'], body['triangles'])
            omitted, _, _ = distances.query(prior['omitted_query_points'], body['points'], body['triangles'])
            assert np.all(source <= prior['source_distances']+1e-8)
            assert np.all(omitted <= prior['omitted_distances']+1e-8)
            np.savez_compressed(args.output/'private-retained-cohort-distances.npz',
                                source_query_points=prior['source_query_points'], source_distances=source,
                                omitted_query_points=prior['omitted_query_points'], omitted_distances=omitted)
    result = dict(source_sha256=sha(__file__), job_sha256=sha(args.job),
                  mesh_sha256=sha(args.constructed/'candidate.npz'), obj_sha256=sha(args.constructed/'candidate.obj'),
                  all_parent_points_faces_and_provenance_preserved=True, exact_NPZ_OBJ_readback=True,
                  complete_disk_perimeter_topology_and_Fraction_boundary_normals_passed=True,
                  whole_mesh_intersection_pairs=len(pairs), zero_area_faces=len(excluded),
                  native_vertex_fans_and_duplicate_checks_passed=not len(pairs) and not len(excluded),
                  unused_vertices=unused if not len(pairs) and not len(excluded) else None,
                  added_triangles=len(patch), closed_parent_edges=len(nodes),
                  remaining_boundary_edges=len(border['boundary'])-len(nodes) if not len(pairs) and not len(excluded) else None,
                  added_degree16_probe_count=len(queries) if not len(pairs) and not len(excluded) else 0,
                  added_sampled_maximum_nominal_mm=maximum if not len(pairs) and not len(excluded) else None,
                  previous_source_and_omission_distances_nonincreasing_pointwise=not failures,
                  candidate_surface_study_accepted=not failures, rejection_reasons=failures,
                  sampled_distances_are_not_Hausdorff_or_physical_tolerances=True,
                  closed_volume=False, physical_acceptance=False, manufacturing_authorized=False,
                  seconds=time.monotonic()-began)
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    (args.output/'report.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
