"""Audit acquired material-side pairs on different walks of one component."""
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
from scipy.spatial import cKDTree


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    with np.load(path, allow_pickle=False) as arrays:
        return {name: arrays[name] for name in arrays.files}


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def surface_components(faces, vertex_count, boundary, topology):
    """Face-dual components, exact V/E/F/B/chi/genus; no anatomical labels."""
    edges, order, first, _, uses = topology.table(faces, vertex_count)
    assert np.all((uses == 1) | (uses == 2))
    shared = first[uses == 2]
    assert np.array_equal(edges[order[shared]], edges[order[shared+1]][:, ::-1])
    a, b = order[shared]//3, order[shared+1]//3
    graph = coo_matrix((np.ones(len(a), dtype=np.int8), (a, b)),
                       shape=(len(faces), len(faces))).tocsr()
    count, labels = connected_components(graph, directed=False)
    actual = order[first[uses == 1]]
    assert np.array_equal(edges[actual], boundary['boundary'])
    assert np.array_equal(actual//3, boundary['owners'])
    face_counts = np.bincount(labels, minlength=count)
    edge_counts = np.bincount(labels[order[first]//3], minlength=count)
    codes = labels[:, None].astype(np.int64)*vertex_count+faces
    vertex_counts = np.bincount(np.unique(codes)//vertex_count, minlength=count)
    walk_components = []
    edge_components = labels[boundary['owners']]
    for start, stop in zip(boundary['offsets'][:-1], boundary['offsets'][1:]):
        ids = boundary['cycle_edges'][start:stop]
        unique = np.unique(edge_components[ids])
        assert len(unique) == 1
        walk_components.append(int(unique[0]))
    boundaries = np.bincount(walk_components, minlength=count)
    chi = vertex_counts-edge_counts+face_counts
    twice_genus = 2-boundaries-chi
    assert np.all(twice_genus >= 0) and np.all(twice_genus % 2 == 0)
    return labels, np.column_stack((vertex_counts, edge_counts, face_counts,
                                   boundaries, chi, twice_genus//2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    job = json.loads(args.job.read_text())
    assert job['schema'] == '935-interwalk-source-admission-1'
    began = time.monotonic()
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    proof = json.loads(Path(job['parent_proof']).read_text())
    assert proof['mesh_sha256'] == sha(job['mesh']) and proof['surface_study_checks_passed']
    assert proof['whole_mesh_intersection_pairs'] == proof['nonmanifold_used_vertices'] == 0
    terminal = json.loads(Path(job['terminal_proof']).read_text())
    assert terminal['fixed_two_class_graph_exhausted_for_unchanged_geometry']
    assert terminal['final_mesh_sha256'] == sha(job['mesh'])
    assert terminal['last_full_geometric_proof_sha256'] == sha(job['parent_proof'])
    mesh, boundary, raw, history = map(load, (job['mesh'], job['boundaries'],
                                            job['source_arrays'], job['attempt_history']))
    identity = module(job['identity_producer'], 'interwalk_raw_vector')
    same = module(job['same_class_producer'], 'interwalk_triangle_and_selection')
    opposed = module(job['opposed_class_producer'], 'interwalk_opposed_vector')
    topology = module(job['topology_helper'], 'interwalk_dual_topology')
    labels, certificate = surface_components(mesh['triangles'], len(mesh['points']), boundary, topology)
    edges, owners = boundary['boundary'], boundary['owners']
    curve_ids = np.full(len(edges), -1, dtype=np.int64)
    scope = []
    for curve, (start, stop) in enumerate(zip(boundary['offsets'][:-1], boundary['offsets'][1:])):
        ids = boundary['cycle_edges'][start:stop]
        curve_ids[ids] = curve
        if set(map(int, boundary['edge_origin_kind'][ids])) <= {1, 6, 7, 8, 9}:
            scope.extend(ids[boundary['edge_origin_kind'][ids] == 1])
    scope = np.sort(np.asarray(scope, dtype=np.int64))
    assert np.all(curve_ids >= 0)
    keys = np.full((len(edges), 3), -1, dtype=np.int64)
    normals = np.zeros((len(edges), 3))
    keys[scope], normals[scope] = identity.source_edge_keys(mesh, edges, owners, raw, scope)
    assert len(np.unique(keys[scope], axis=0)) == len(scope)
    midpoint = mesh['points'][edges].mean(axis=1)
    limits = job['limits']
    tree = cKDTree(midpoint[scope])
    envelope = tree.query_pairs(limits['midpoint_search_radius_nominal_mm']+
                               limits['spatial_search_arithmetic_guard_nominal_mm'], output_type='ndarray')
    assert len(envelope) <= limits['maximum_same_curve_search_pairs']
    all_pairs = np.sort(scope[envelope], axis=1)
    all_pairs = all_pairs[np.sum((midpoint[all_pairs[:, 0]]-midpoint[all_pairs[:, 1]])**2, axis=1)
                          <= limits['midpoint_search_radius_nominal_mm']**2]
    all_pairs = all_pairs[np.lexsort((all_pairs[:, 1], all_pairs[:, 0]))]
    cross = all_pairs[curve_ids[all_pairs[:, 0]] != curve_ids[all_pairs[:, 1]]]
    component_ids = labels[owners]
    same_component = component_ids[cross[:, 0]] == component_ids[cross[:, 1]]
    candidates = cross[same_component]
    prior = history['raw_pair_keys']
    prior_set = set(map(tuple, prior.tolist()))
    assert len(prior_set) == len(prior) == 1714
    pair_keys = identity.canonical_pair_keys(keys, candidates)
    attempted = np.array([tuple(row) in prior_set for row in pair_keys], dtype=bool)
    evaluated = candidates[~attempted]
    reasons, indices, flags, scores = opposed.classify(mesh['points'], edges, normals, evaluated,
                                                       limits, same.triangle_alignment)
    eligible = evaluated[indices]
    selected, best, ambiguous = same.mutual_unique(eligible, scores, len(edges),
                         limits['squared_gap_score_ambiguity_tolerance'])
    assert len(np.unique(eligible[selected])) == 2*len(selected)
    args.output.mkdir(mode=0o700, exist_ok=False)
    target = args.output/'private-interwalk-census.npz'
    np.savez_compressed(target, scope_edge_ids=scope, edge_curve_ids=curve_ids,
        face_component_ids=labels, component_V_E_F_B_chi_genus=certificate,
        source_edge_keys=keys, global_radius_pairs=all_pairs, different_walk_radius_pairs=cross,
        different_component_excluded_indices=np.flatnonzero(~same_component),
        prior_excluded_indices=np.flatnonzero(attempted), evaluated_pair_edge_ids=evaluated,
        eligible_pair_edge_ids=eligible, eligible_pair_diagonal_flags=flags,
        eligible_pair_scores_squared=scores, selected_eligible_pair_indices=selected,
        selected_pair_edge_ids=eligible[selected], selected_pair_walk_ids=curve_ids[eligible[selected]],
        selected_pair_component_ids=component_ids[eligible[selected, 0]],
        unique_best_neighbor_edge_ids=best, ambiguous_edge_ids=np.flatnonzero(ambiguous))
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    report = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), mesh_sha256=sha(job['mesh']),
        census_sha256=sha(target), source_scope_edges=len(scope), source_scope_walks=len(np.unique(curve_ids[scope])),
        global_search_envelope_pairs=len(envelope), exact_global_radius_pairs=len(all_pairs),
        exact_different_walk_radius_pairs=len(cross), separate_component_pairs_refused=int((~same_component).sum()),
        same_component_different_walk_pairs=len(candidates), historical_attempts_excluded=int(attempted.sum()),
        evaluated_unattempted_pairs=len(evaluated), material_side_stage_counts=reasons,
        eligible_pairs=len(eligible), selected_pairs=len(selected), ambiguous_edges=int(ambiguous.sum()),
        component_certificates=certificate.tolist(),
        selected_width_nominal_mm=dict(minimum=float(np.sqrt(scores[selected]).min()),
                                      maximum=float(np.sqrt(scores[selected]).max())) if len(selected) else None,
        raw_owner_normals_only=True, geometry_modified=False, physical_acceptance=False,
        construction_pending_independent_admission=True, manufacturing_authorized=False,
        seconds=time.monotonic()-began)
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
