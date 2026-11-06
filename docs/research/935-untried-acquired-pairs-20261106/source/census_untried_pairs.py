"""Read-only acquired-edge census with immutable source identities and prior exclusions."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


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


def source_edge_keys(mesh, edges, owners, raw, ids):
    """Recover directed raw corner IDs from each actual acquired owning facet."""
    body_faces = mesh['triangles'][owners[ids]]
    source_faces = mesh['original_face_ids'][owners[ids]]
    assert np.all(mesh['inferred_surface_kind'][owners[ids]] == 0)
    assert np.all((source_faces >= 0)&(source_faces < len(raw['triangles'])))
    source_nodes = raw['triangles'][source_faces]
    body_points, original_points = mesh['points'][body_faces], raw['vertices'][source_nodes]
    matches = np.all(body_points[:, :, None, :] == original_points[:, None, :, :], axis=3)
    assert np.all(matches.sum(axis=2) == 1) and np.all(matches.sum(axis=1) == 1)
    permutation = matches.argmax(axis=2)
    assert np.all((np.roll(permutation, -1, axis=1)-permutation)%3 == 1)
    starts = body_faces == edges[ids, 0, None]; ends = body_faces == edges[ids, 1, None]
    assert np.all(starts.sum(axis=1) == 1) and np.all(ends.sum(axis=1) == 1)
    a, b = starts.argmax(axis=1), ends.argmax(axis=1); assert np.all((b-a)%3 == 1)
    rows = np.arange(len(ids)); raw_a = source_nodes[rows, permutation[rows, a]]; raw_b = source_nodes[rows, permutation[rows, b]]
    assert np.array_equal(mesh['points'][edges[ids, 0]], raw['vertices'][raw_a])
    assert np.array_equal(mesh['points'][edges[ids, 1]], raw['vertices'][raw_b])
    cross = np.cross(original_points[:, 1]-original_points[:, 0], original_points[:, 2]-original_points[:, 0])
    length = np.linalg.norm(cross, axis=1); assert np.all(length > 0)
    return np.column_stack((source_faces, raw_a, raw_b)), cross/length[:, None]


def canonical_pair_keys(edge_keys, pairs):
    result = np.empty((len(pairs), 6), dtype=np.int64)
    for row, (a, b) in enumerate(pairs):
        left, right = tuple(map(int, edge_keys[a])), tuple(map(int, edge_keys[b]))
        assert min(left+right) >= 0
        result[row] = left+right if left < right else right+left
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args(); job = json.loads(args.job.read_text()); started = time.monotonic()
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    proof = json.loads(Path(job['parent_proof']).read_text())
    assert proof['mesh_sha256'] == sha(job['mesh']) and proof['surface_study_checks_passed']
    assert proof['intersection_pairs'] == proof['nonmanifold_used_vertices'] == 0
    old_proof = json.loads(Path(job['prior_census_proof']).read_text())
    assert old_proof['census_independently_verified'] and old_proof['census_sha256'] == sha(job['prior_census'])
    mesh, boundary, raw, prior_mesh, prior_boundary, prior = map(load, (job['mesh'], job['boundaries'], job['source_arrays'],
                                                                    job['prior_mesh'], job['prior_boundaries'], job['prior_census']))
    assert len(boundary['offsets'])-1 == 1226 and len(boundary['boundary']) == 96153
    assert len(prior['selected_pair_edge_ids']) == old_proof['selected_pairs'] == 1315
    helper = module(job['census_helper'], 'frozen_pair_geometry')
    edges, owners = boundary['boundary'], boundary['owners']; curve_ids = np.full(len(edges), -1, dtype=np.int64)
    curve_sizes = np.diff(boundary['offsets']); scope = []; scope_walks = []; origin_names = {}
    for curve in range(len(curve_sizes)):
        a, b = boundary['offsets'][curve:curve+2]; ids = boundary['cycle_edges'][a:b]
        curve_ids[ids] = curve; origins = set(map(int, boundary['edge_origin_kind'][ids]))
        origin_names[curve] = '+'.join(map(str, sorted(origins)))
        if origins <= {1, 6}:
            acquired = ids[boundary['edge_origin_kind'][ids] == 1]
            if len(acquired):
                scope.extend(map(int, acquired)); scope_walks.append(curve)
    scope = np.array(sorted(scope), dtype=np.int64); assert len(scope_walks) == 1192
    keys = np.full((len(edges), 3), -1, dtype=np.int64); normals = np.zeros((len(edges), 3))
    keys[scope], normals[scope] = source_edge_keys(mesh, edges, owners, raw, scope)
    assert len(np.unique(keys[scope], axis=0)) == len(scope)
    prior_ids = np.unique(prior['selected_pair_edge_ids'])
    old_keys = np.full((len(prior_boundary['boundary_local_nodes']), 3), -1, dtype=np.int64)
    old_keys[prior_ids], _ = source_edge_keys(prior_mesh, prior_boundary['boundary_local_nodes'], prior_boundary['boundary_face_rows'], raw, prior_ids)
    prior_keys = canonical_pair_keys(old_keys, prior['selected_pair_edge_ids'])
    prior_set = {tuple(map(int, row)) for row in prior_keys}; assert len(prior_set) == 1315
    midpoint = mesh['points'][edges].mean(axis=1)
    broad, global_envelope, same_envelope = helper.enumerate_same_curve_pairs(midpoint, curve_ids, scope, job['limits'])
    pair_keys = canonical_pair_keys(keys, broad)
    was_attempted = np.array([tuple(map(int, key)) in prior_set for key in pair_keys], dtype=bool)
    # A four-corner whole-loop fill is an unchanged, already assessed cap input.
    small = curve_sizes[curve_ids[broad[:, 0]]] <= job['maximum_unchanged_whole_cap_edges_to_exclude']
    small &= ~was_attempted
    evaluated = broad[~was_attempted&~small]
    reasons, accepted, flags, scores = helper.qualify(mesh['points'], edges, normals, evaluated, job['limits'])
    eligible = evaluated[accepted]
    selected, best, ambiguous = helper.mutual_unique(eligible, scores, len(edges), job['limits']['squared_gap_score_ambiguity_tolerance'])
    assert len(np.unique(eligible[selected])) == 2*len(selected)
    assert not any(tuple(map(int, key)) in prior_set for key in canonical_pair_keys(keys, eligible[selected]))
    args.output.mkdir(mode=0o700, exist_ok=False)
    np.savez_compressed(args.output/'private-untried-pair-census.npz', scope_edge_ids=scope, edge_curve_ids=curve_ids,
                        source_edge_keys=keys, prior_attempted_pair_keys=prior_keys,
                        same_curve_radius_pairs=broad, prior_excluded_broad_indices=np.flatnonzero(was_attempted),
                        unchanged_small_walk_excluded_broad_indices=np.flatnonzero(small), evaluated_pair_edge_ids=evaluated,
                        eligible_pair_edge_ids=eligible, eligible_pair_diagonal_flags=flags, eligible_pair_scores_squared=scores,
                        selected_eligible_pair_indices=selected, selected_pair_edge_ids=eligible[selected],
                        selected_pair_curve_ids=curve_ids[eligible[selected, 0]], unique_best_neighbor_edge_ids=best,
                        ambiguous_edge_ids=np.flatnonzero(ambiguous))
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    report = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), mesh_sha256=sha(job['mesh']),
                  complete_current_walks=len(curve_sizes), complete_current_boundary_edges=len(edges),
                  source_scope_walks=len(scope_walks), source_scope_edges=len(scope), prior_attempted_pairs=len(prior_set),
                  global_search_envelope_pairs=global_envelope, same_curve_search_envelope_pairs=same_envelope,
                  exact_same_curve_radius_pairs=len(broad), prior_attempted_broad_pairs_excluded=int(was_attempted.sum()),
                  unchanged_small_walk_broad_pairs_excluded=int(small.sum()), evaluated_untried_pairs=len(evaluated),
                  ordered_geometry_stage_counts=reasons, eligible_untried_pairs=len(eligible), selected_untried_pairs=len(selected),
                  selected_walks=len(np.unique(curve_ids[eligible[selected, 0]])),
                  selected_walk_origin_combinations=dict(Counter(origin_names[int(curve)] for curve in curve_ids[eligible[selected, 0]])),
                  selected_width_nominal_mm=dict(minimum=float(np.sqrt(scores[selected]).min()), maximum=float(np.sqrt(scores[selected]).max())) if len(selected) else None,
                  ambiguous_candidate_edges=int(ambiguous.sum()), source_identity_uses_original_owner_and_directed_raw_corners=True,
                  geometry_modified=False, constructor_admission_pending_independent_check=True,
                  physical_classifications_accepted=0, manufacturing_authorized=False, seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n'); print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
