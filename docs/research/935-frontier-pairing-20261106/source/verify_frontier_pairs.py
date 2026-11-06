"""Independently inspect a read-only frontier census using blocked exhaustive pairs."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key] for key in data.files}


def exhaustive_pairs(centres, curve_ids, scope, radius, block_rows, maximum):
    """No spatial tree, constructor, producer selection, or expanded radius."""
    chunks = []
    count = 0
    for curve in np.unique(curve_ids[scope]):
        ids = scope[curve_ids[scope] == curve]
        coordinates = centres[ids]
        for start in range(0, len(ids), block_rows):
            stop = min(len(ids), start + block_rows)
            delta = coordinates[start:stop, None, :] - coordinates[None, :, :]
            squared = np.sum(delta * delta, axis=2)
            rows, columns = np.nonzero(squared <= radius * radius)
            rows += start
            keep = rows < columns
            pairs = np.column_stack((ids[rows[keep]], ids[columns[keep]]))
            count += len(pairs)
            assert count <= maximum, 'independent_pair_resource_limit'
            if len(pairs):
                chunks.append(pairs)
    result = np.concatenate(chunks) if chunks else np.empty((0, 2), dtype=np.int64)
    return result[np.lexsort((result[:, 1], result[:, 0]))]


def inspect_pair(points, edges, normals, first, second, limits):
    a, b = map(int, edges[first])
    c, d = map(int, edges[second])
    ids = [a, b, c, d]
    if len(set(ids)) != 4 or len({tuple(points[x]) for x in ids}) != 4:
        return 'shared_vertex_or_coordinate', None
    score = max(float(np.dot(points[a]-points[d], points[a]-points[d])),
                float(np.dot(points[b]-points[c], points[b]-points[c])))
    if score > limits['maximum_cross_endpoint_distance_nominal_mm'] ** 2:
        return 'cross_endpoint_support_distance', None
    left, right = points[b]-points[a], points[d]-points[c]
    if np.dot(left, right)/(np.linalg.norm(left)*np.linalg.norm(right)) > limits['maximum_tangent_dot']:
        return 'directed_tangent_alignment', None
    if np.dot(normals[first], normals[second]) < limits['minimum_owner_normal_dot']:
        return 'acquired_owner_normal_alignment', None
    flags = []
    for faces in (((b, a, d), (b, d, c)), ((b, a, c), (a, d, c))):
        good = True
        for triangle, owner in zip(faces, (first, second)):
            x, y, z = points[list(triangle)]
            normal = np.cross(y-x, z-x)
            length = np.linalg.norm(normal)
            good &= length > 0 and np.dot(normal, normals[owner])/length >= limits['minimum_signed_bridge_triangle_normal_dot']
        flags.append(bool(good))
    if not any(flags):
        return 'no_forward_nondegenerate_quad_diagonal', None
    return 'eligible', (flags, score)


def reciprocal_unique(pairs, scores, tolerance):
    neighbors = defaultdict(list)
    for index, ((a, b), score) in enumerate(zip(pairs, scores)):
        neighbors[int(a)].append((float(score), int(b), index))
        neighbors[int(b)].append((float(score), int(a), index))
    best, ambiguous = {}, []
    for edge, values in neighbors.items():
        values.sort()
        best[edge] = values[0][1]
        if len(values) > 1 and values[1][0]-values[0][0] <= tolerance:
            ambiguous.append(edge)
    ambiguous = set(ambiguous)
    selected = [index for index, (a, b) in enumerate(pairs)
                if a not in ambiguous and b not in ambiguous and best[a] == b and best[b] == a]
    return np.array(selected, dtype=np.int64), best, np.array(sorted(ambiguous), dtype=np.int64)


def controls(limits):
    normals = np.tile([0., 0., 1.], (2, 1))
    edges = np.array([[0, 1], [2, 3]])
    positive = np.array([[0., 0., 0.], [1., 0., 0.], [1., -.2, 0.], [0., -.2, 0.]])
    assert inspect_pair(positive, edges, normals, 0, 1, limits)[0] == 'eligible'
    above = positive.copy(); above[2:, 1] = .2
    assert inspect_pair(above, edges, normals, 0, 1, limits)[0] == 'no_forward_nondegenerate_quad_diagonal'
    wide = positive.copy(); wide[2:, 1] = -.6
    assert inspect_pair(wide, edges, normals, 0, 1, limits)[0] == 'cross_endpoint_support_distance'
    assert inspect_pair(positive, edges[:, ::-1], normals, 0, 1, limits)[0] == 'no_forward_nondegenerate_quad_diagonal'
    parallel = edges.copy(); parallel[1] = parallel[1, ::-1]
    assert inspect_pair(positive, parallel, normals, 0, 1, limits)[0] == 'directed_tangent_alignment'
    opposed = normals.copy(); opposed[1] *= -1
    assert inspect_pair(positive, edges, opposed, 0, 1, limits)[0] == 'acquired_owner_normal_alignment'
    coincident = positive.copy(); coincident[3] = coincident[0]
    assert inspect_pair(coincident, edges, normals, 0, 1, limits)[0] == 'shared_vertex_or_coordinate'
    centres = np.array([[0., 0., 0.], [0., .1, 0.], [0., .2, 0.]])
    assert exhaustive_pairs(centres, np.array([0, 0, 1]), np.arange(3), .5, 1, 3).tolist() == [[0, 1]]
    selected, _, ambiguous = reciprocal_unique(np.array([[0, 1], [0, 2]]), np.array([.1, .1]), 1e-12)
    assert not len(selected) and ambiguous.tolist() == [0]
    selected, _, ambiguous = reciprocal_unique(np.array([[0, 1], [0, 2]]), np.array([.1, .2]), 1e-12)
    assert selected.tolist() == [0] and not len(ambiguous)
    return 10


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job', 'census', 'output'):
        parser.add_argument('--'+name, required=True, type=Path)
    args = parser.parse_args(); started = time.monotonic()
    job = json.loads(args.job.read_text()); initial = sha(args.census)
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    data, boundary, source, census = map(load, (job['mesh'], job['boundaries'], job['source_arrays'], args.census))
    review = json.loads(Path(job['review']).read_text())
    old = {row['curve']: row for row in json.loads(Path(job['prior_admission_decisions']).read_text())}
    scope, curve_ids = [], np.full(len(boundary['boundary_local_nodes']), -1, dtype=np.int64)
    for row in review:
        a, b = boundary['cycle_offsets'][row['curve']:row['curve']+2]
        ids = boundary['cycle_boundary_edge_ids'][a:b]
        curve_ids[ids] = row['curve']
        if set(row['edge_origin_counts']) == {'1'} and not old[row['parent_boundary_curve_id']]['experimental_trial_admitted']:
            scope.extend(map(int, ids))
    scope = np.array(sorted(scope), dtype=np.int64)
    assert len(scope) == 91318 and len(np.unique(curve_ids[scope])) == 612
    assert np.array_equal(scope, census['scope_edge_ids']) and np.array_equal(curve_ids, census['edge_curve_ids'])
    edges, points = boundary['boundary_local_nodes'], data['points']
    owners = boundary['boundary_face_rows'][scope]
    assert np.all(data['inferred_surface_kind'][owners] == 0) and np.all(boundary['edge_origin_kind'][scope] == 1)
    nodes = np.unique(edges[scope]); raw_nodes = data['global_node_ids'][nodes]
    assert np.array_equal(points[nodes], source['vertices'][raw_nodes])
    raw_faces = source['triangles'][data['original_face_ids'][owners]]
    raw_points = source['vertices'][raw_faces]
    owner_normals = np.cross(raw_points[:, 1]-raw_points[:, 0], raw_points[:, 2]-raw_points[:, 0])
    owner_normals /= np.linalg.norm(owner_normals, axis=1)[:, None]
    normals = np.zeros((len(edges), 3)); normals[scope] = owner_normals
    limits = job['limits']; control_count = controls(limits)
    pairs = exhaustive_pairs(points[edges].mean(axis=1), curve_ids, scope,
                             limits['midpoint_search_radius_nominal_mm'], limits['independent_pair_block_rows'],
                             limits['maximum_same_curve_search_pairs'])
    assert np.array_equal(pairs, census['same_curve_radius_pairs'])
    reasons, eligible, flags, scores = Counter(), [], [], []
    for a, b in pairs:
        reason, result = inspect_pair(points, edges, normals, a, b, limits)
        reasons[reason] += 1
        if result is not None:
            eligible.append((a, b)); flags.append(result[0]); scores.append(result[1])
    eligible = np.array(eligible, dtype=np.int64).reshape(-1, 2)
    assert np.array_equal(eligible, census['eligible_pair_edge_ids'])
    assert np.array_equal(np.array(flags, dtype=bool), census['eligible_pair_diagonal_flags'])
    assert np.allclose(scores, census['eligible_pair_scores_squared'], rtol=0, atol=1e-15)
    selected, best, ambiguous = reciprocal_unique(eligible, scores, limits['squared_gap_score_ambiguity_tolerance'])
    assert np.array_equal(selected, census['selected_eligible_pair_indices'])
    assert np.array_equal(eligible[selected], census['selected_pair_edge_ids'])
    assert np.array_equal(ambiguous, census['ambiguous_edge_ids'])
    for edge, other in best.items():
        assert census['unique_best_neighbor_edge_ids'][edge] == other
    assert len(np.unique(eligible[selected])) == 2*len(selected)
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    assert sha(args.census) == initial
    args.output.mkdir(mode=0o700, exist_ok=False)
    report = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), census_sha256=initial,
                  mesh_sha256=sha(job['mesh']), independent_exhaustive_pairs=len(pairs),
                  eligible_pairs=len(eligible), selected_pairs=len(selected), selected_walks=len(np.unique(curve_ids[eligible[selected, 0]])),
                  ordered_stage_counts=dict(reasons), control_cases_passed=control_count,
                  producer_imported=False, spatial_index_used=False, census_independently_verified=True,
                  geometry_modified=False, physical_classifications_accepted=0, manufacturing_authorized=False,
                  seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
