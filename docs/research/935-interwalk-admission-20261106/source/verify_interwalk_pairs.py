"""Independent cell coverage, vertex components and scalar inter-walk admission."""
import argparse
from collections import Counter
import hashlib
import importlib.util
from itertools import product
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
    with np.load(path, allow_pickle=False) as arrays:
        return {name: arrays[name] for name in arrays.files}


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def cell_radius_pairs(midpoint, scope, radius, cap):
    """A power-of-two grid with a two-cell halo, followed by exact Float64 cut."""
    assert radius == .5 and np.all(np.isfinite(midpoint[scope]))
    assert np.max(np.abs(midpoint[scope]/radius), initial=0) < 2**50
    buckets = {}
    for edge, cell in zip(scope, np.floor(midpoint[scope]/radius).astype(np.int64)):
        buckets.setdefault(tuple(map(int, cell)), []).append(int(edge))
    result = []
    count = 0
    for cell in sorted(buckets):
        a = np.asarray(buckets[cell], dtype=np.int64)
        for offset in product(range(-2, 3), repeat=3):
            other = tuple(x+y for x, y in zip(cell, offset))
            if other < cell or other not in buckets:
                continue
            b = np.asarray(buckets[other], dtype=np.int64)
            for start in range(0, len(a), 128):
                aa = a[start:start+128]
                distance = np.sum((midpoint[aa, None]-midpoint[b][None, :])**2, axis=2)
                keep = distance <= radius**2
                if other == cell:
                    keep &= aa[:, None] < b[None, :]
                left, right = np.nonzero(keep)
                if len(left):
                    pairs = np.sort(np.column_stack((aa[left], b[right])), axis=1)
                    count += len(pairs)
                    assert count <= cap, 'independent_radius_pair_resource_limit'
                    result.append(pairs)
    pairs = np.concatenate(result) if result else np.empty((0, 2), dtype=np.int64)
    return pairs[np.lexsort((pairs[:, 1], pairs[:, 0]))]


def vertex_components(faces, vertex_count, boundary):
    """Independent primal graph; no face-dual producer or helper is imported."""
    directed = np.concatenate((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]))
    graph = coo_matrix((np.ones(len(directed), dtype=np.int8), (directed[:, 0], directed[:, 1])),
                       shape=(vertex_count, vertex_count)).tocsr()
    _, vertex_labels = connected_components(graph, directed=False)
    original = vertex_labels[faces[:, 0]]
    assert np.all(vertex_labels[faces] == original[:, None])
    unique, first = np.unique(original, return_index=True)
    order = np.argsort(first)
    remap = np.full(int(vertex_labels.max())+1, -1, dtype=np.int64)
    remap[unique[order]] = np.arange(len(unique))
    labels = remap[original]
    vertex_labels = remap[vertex_labels]
    count = len(unique)
    canonical = directed.min(axis=1)*vertex_count+directed.max(axis=1)
    edge_codes, uses = np.unique(canonical, return_counts=True)
    assert np.all((uses == 1) | (uses == 2))
    vertex_counts = np.bincount(vertex_labels[np.unique(faces)], minlength=count)
    edge_counts = np.bincount(vertex_labels[edge_codes//vertex_count], minlength=count)
    face_counts = np.bincount(labels, minlength=count)
    boundary_counts = np.zeros(count, dtype=np.int64)
    for start, stop in zip(boundary['offsets'][:-1], boundary['offsets'][1:]):
        ids = boundary['cycle_edges'][start:stop]
        values = set(map(int, labels[boundary['owners'][ids]]))
        assert len(values) == 1
        boundary_counts[values.pop()] += 1
    chi = vertex_counts-edge_counts+face_counts
    twice = 2-boundary_counts-chi
    assert np.all(twice >= 0) and np.all(twice % 2 == 0)
    return labels, np.column_stack((vertex_counts, edge_counts, face_counts,
                                   boundary_counts, chi, twice//2))


def scope_reason(left, right, walks, components):
    if walks[left] == walks[right]:
        return 'same_walk'
    if components[left] != components[right]:
        return 'separate_components'
    return 'different_walks_same_component'


def fixture_boundary(faces):
    """Small literal-control boundary; deliberately no production helper."""
    owners = {}
    for row, tri in enumerate(faces):
        for a, b in zip(tri, np.roll(tri, -1)):
            owners.setdefault(tuple(sorted((int(a), int(b)))), []).append((int(a), int(b), row))
    values = [v[0] for v in owners.values() if len(v) == 1]
    edges = np.array([v[:2] for v in values], dtype=np.int64).reshape(-1, 2)
    owner = np.array([v[2] for v in values], dtype=np.int64)
    outgoing = {int(a): i for i, (a, _) in enumerate(edges)}
    assert len(outgoing) == len(edges)
    remaining = set(range(len(edges)))
    flat, offsets = [], [0]
    while remaining:
        current = first = min(remaining)
        while current in remaining:
            remaining.remove(current)
            flat.append(current)
            current = outgoing[int(edges[current, 1])]
        assert current == first
        offsets.append(len(flat))
    return dict(boundary=edges, owners=owner, cycle_edges=np.array(flat), offsets=np.array(offsets))


def controls(limits, scalar):
    # A U-shaped annular material wall, joined below with two distinct top rims.
    n = 16
    theta = np.arange(n)*2*np.pi/n
    rings = [np.c_[radius*np.cos(theta), radius*np.sin(theta), np.full(n, z)]
             for radius, z in ((1., 0.), (1., 1.), (.8, 0.), (.8, 1.))]
    points = np.concatenate(rings)
    faces = []
    for i in range(n):
        j = (i+1) % n
        faces.extend(((i, j, n+j), (i, n+j, n+i),
                      (2*n+i, 3*n+j, 2*n+j), (2*n+i, 3*n+i, 3*n+j),
                      (i, 2*n+j, j), (i, 2*n+i, 2*n+j)))
    faces = np.array(faces, dtype=np.int64)
    boundary = fixture_boundary(faces)
    labels, cert = vertex_components(faces, len(points), boundary)
    assert cert.tolist() == [[64, 160, 96, 2, 0, 0]]
    edges = boundary['boundary']
    walks = np.empty(len(edges), dtype=np.int64)
    for curve, (a, b) in enumerate(zip(boundary['offsets'][:-1], boundary['offsets'][1:])):
        walks[boundary['cycle_edges'][a:b]] = curve
    xyz = points[faces[boundary['owners']]]
    normals = np.cross(xyz[:, 1]-xyz[:, 0], xyz[:, 2]-xyz[:, 0])
    normals /= np.linalg.norm(normals, axis=1)[:, None]
    eligible = []
    for a in range(len(edges)):
        for b in range(a+1, len(edges)):
            if scope_reason(a, b, walks, labels[boundary['owners']]) == 'different_walks_same_component':
                reason, value = scalar.inspect_pair(points, edges, normals, a, b, limits)
                if value is not None:
                    eligible.append((a, b, value))
    assert len(eligible) == n
    a, b, value = eligible[0]
    assert value[0] == [True, True]
    assert scope_reason(a, b, walks, np.arange(len(edges))) == 'separate_components'
    assert scope_reason(a, a, walks, labels[boundary['owners']]) == 'same_walk'
    assert scalar.inspect_pair(points, edges, -normals, a, b, limits)[1] is None
    assert scalar.inspect_pair(points, edges[:, ::-1], -normals, a, b, limits)[1] is None
    assert scalar.inspect_pair(points, np.where(np.arange(len(edges))[:, None] == b,
                               edges[:, ::-1], edges), normals, a, b, limits)[1] is None
    aa, bb = edges[a]
    cc, dd = edges[b]
    patch = np.array([[bb, aa, dd], [bb, dd, cc]])
    full = np.concatenate((faces, patch))
    _, after = vertex_components(full, len(points), fixture_boundary(full))
    assert after.tolist() == [[64, 163, 98, 1, -1, 1]]
    assert np.min(np.linalg.norm(points[patch].mean(axis=1)[:, :2], axis=1)) > .7
    # Independent cell coverage versus complete literal enumeration, including boundaries.
    mid = np.array([[0., 0., 0.], [.5, 0., 0.], [np.nextafter(.5, 1.), 0., 0.],
                    [-.5, 0., 0.], [-1., 0., 0.], [30., 20., -10.]])
    expected = np.array([(a, b) for a in range(len(mid)) for b in range(a+1, len(mid))
                         if np.dot(mid[a]-mid[b], mid[a]-mid[b]) <= .25], dtype=np.int64)
    assert np.array_equal(cell_radius_pairs(mid, np.arange(len(mid)), .5, 100), expected)
    return dict(annular_opposed_pairs=n, component_fusion_refused=True,
        same_walk_refused=True, void_side_refused=True, global_reversal_refused=True,
        wrong_border_direction_refused=True, single_band_Euler_boundary_genus_verified=True,
        central_opening_preserved=True, independent_radius_boundary_control=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job', 'census', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    began = time.monotonic()
    job = json.loads(args.job.read_text())
    assert job['schema'] == '935-interwalk-source-admission-1'
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    mesh, boundary, raw, history, census = map(load, (job['mesh'], job['boundaries'],
        job['source_arrays'], job['attempt_history'], args.census))
    identity = module(job['identity_inspector'], 'interwalk_scalar_raw_identity')
    scalar = module(job['opposed_class_inspector'], 'interwalk_scalar_material')
    selection = module(job['selection_inspector'], 'interwalk_scalar_selection')
    history_checker = module(job['history_inspector'], 'interwalk_historical_corners')
    control_results = controls(job['limits'], scalar)
    identity_controls = identity.identity_controls()
    opposed_controls = scalar.controls(job['limits'])
    proof = json.loads(Path(job['parent_proof']).read_text())
    terminal = json.loads(Path(job['terminal_proof']).read_text())
    registry_proof = json.loads(Path(job['registry_proof']).read_text())
    assert proof['mesh_sha256'] == sha(job['mesh']) and proof['surface_study_checks_passed']
    assert terminal['final_mesh_sha256'] == sha(job['mesh'])
    assert terminal['last_full_geometric_proof_sha256'] == sha(job['parent_proof'])
    assert terminal['fixed_two_class_graph_exhausted_for_unchanged_geometry']
    assert registry_proof['registry_independently_verified']
    assert registry_proof['registry_sha256'] == sha(job['registry'])
    assert registry_proof['source_sha256'] == sha(job['registry_inspector'])
    prior = [tuple(map(int, row)) for row in history['raw_pair_keys']]
    assert len(prior) == len(set(prior)) == terminal['attempted_raw_pairs'] == 1714
    old_history = load(job['previous_attempt_history'])['raw_pair_keys']
    registry = load(job['registry'])
    assert np.array_equal(history['raw_pair_keys'][:1705], old_history)
    assert np.array_equal(history['raw_pair_keys'][1705:], registry['raw_pair_keys'])
    for key in prior:
        history_checker.raw_key_valid(key[:3], raw)
        history_checker.raw_key_valid(key[3:], raw)
    labels, certificate = vertex_components(mesh['triangles'], len(mesh['points']), boundary)
    assert np.array_equal(labels, census['face_component_ids'])
    assert np.array_equal(certificate, census['component_V_E_F_B_chi_genus'])
    edges, owners = boundary['boundary'], boundary['owners']
    walks = np.full(len(edges), -1, dtype=np.int64)
    scope = []
    for curve, (start, stop) in enumerate(zip(boundary['offsets'][:-1], boundary['offsets'][1:])):
        ids = boundary['cycle_edges'][start:stop]
        walks[ids] = curve
        if set(map(int, boundary['edge_origin_kind'][ids])) <= {1, 6, 7, 8, 9}:
            scope.extend(int(e) for e in ids if boundary['edge_origin_kind'][e] == 1)
    scope = np.array(sorted(scope), dtype=np.int64)
    assert np.array_equal(scope, census['scope_edge_ids']) and np.array_equal(walks, census['edge_curve_ids'])
    keys = np.full((len(edges), 3), -1, dtype=np.int64)
    normals = np.zeros((len(edges), 3))
    for edge in scope:
        keys[edge], normals[edge] = identity.original_key(mesh, edges[edge], owners[edge], raw)
    assert np.array_equal(keys, census['source_edge_keys'])
    all_pairs = cell_radius_pairs(mesh['points'][edges].mean(axis=1), scope,
        job['limits']['midpoint_search_radius_nominal_mm'], job['limits']['maximum_same_curve_search_pairs'])
    assert np.array_equal(all_pairs, census['global_radius_pairs'])
    cross = all_pairs[walks[all_pairs[:, 0]] != walks[all_pairs[:, 1]]]
    assert np.array_equal(cross, census['different_walk_radius_pairs'])
    components = labels[owners]
    rejected, candidates = [], []
    for i, (a, b) in enumerate(cross):
        if scope_reason(a, b, walks, components) == 'separate_components':
            rejected.append(i)
        else:
            candidates.append((a, b))
    assert np.array_equal(rejected, census['different_component_excluded_indices'])
    evaluated, attempted = [], []
    attempted_set = set(prior)
    for i, (a, b) in enumerate(candidates):
        if identity.pair_key(keys, a, b) in attempted_set:
            attempted.append(i)
        else:
            evaluated.append((a, b))
    evaluated = np.asarray(evaluated, dtype=np.int64).reshape(-1, 2)
    assert np.array_equal(attempted, census['prior_excluded_indices'])
    assert np.array_equal(evaluated, census['evaluated_pair_edge_ids'])
    eligible, flags, scores, reasons = [], [], [], Counter()
    for a, b in evaluated:
        reason, value = scalar.inspect_pair(mesh['points'], edges, normals, a, b, job['limits'])
        reasons[reason] += 1
        if value is not None:
            eligible.append((a, b)); flags.append(value[0]); scores.append(value[1])
    eligible = np.asarray(eligible, dtype=np.int64).reshape(-1, 2)
    assert np.array_equal(eligible, census['eligible_pair_edge_ids'])
    assert np.array_equal(np.asarray(flags, dtype=bool).reshape(-1, 2), census['eligible_pair_diagonal_flags'])
    assert np.allclose(scores, census['eligible_pair_scores_squared'], rtol=0, atol=1e-15)
    selected, best, ambiguous = selection.reciprocal_unique(eligible, scores,
                                  job['limits']['squared_gap_score_ambiguity_tolerance'])
    assert np.array_equal(selected, census['selected_eligible_pair_indices'])
    assert np.array_equal(eligible[selected], census['selected_pair_edge_ids'])
    assert np.array_equal(walks[eligible[selected]], census['selected_pair_walk_ids'])
    assert np.array_equal(components[eligible[selected, 0]], census['selected_pair_component_ids'])
    complete_best = np.full(len(edges), -1, dtype=np.int64)
    for edge, other in best.items():
        complete_best[edge] = other
    assert np.array_equal(complete_best, census['unique_best_neighbor_edge_ids'])
    assert np.array_equal(ambiguous, census['ambiguous_edge_ids'])
    halos, offsets = [], [0]
    for left, right in eligible[selected]:
        corners = edges[[left, right]].ravel()
        halo = np.flatnonzero(np.isin(mesh['triangles'], corners).any(axis=1))
        halos.extend(halo); offsets.append(len(halos))
    args.output.mkdir(mode=0o700, exist_ok=False)
    target = args.output/'private-complete-interwalk-halos.npz'
    np.savez_compressed(target, halo_offsets=np.array(offsets), halo_face_rows=np.array(halos, dtype=np.int64))
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    report = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), mesh_sha256=sha(job['mesh']),
        census_sha256=sha(args.census), complete_halo_sha256=sha(target),
        source_scope_edges=len(scope), source_scope_walks=len(np.unique(walks[scope])),
        independently_complete_global_radius_pairs=len(all_pairs),
        different_walk_radius_pairs=len(cross), separate_component_pairs_refused=len(rejected),
        historical_attempts_excluded=len(attempted), evaluated_unattempted_pairs=len(evaluated),
        scalar_stage_counts=dict(reasons), eligible_pairs=len(eligible), selected_pairs=len(selected),
        independent_vertex_component_certificates=certificate.tolist(),
        annular_scope_and_radius_controls=control_results, raw_identity_controls_passed=identity_controls,
        opposed_scalar_controls_passed=opposed_controls, complete_selected_incident_halos=len(selected),
        producer_imported=False, spatial_tree_used=False, census_independently_verified=True,
        geometry_modified=False, physical_acceptance=False, manufacturing_authorized=False,
        construction_pending_native_mask_topology_admission=True, seconds=time.monotonic()-began)
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
