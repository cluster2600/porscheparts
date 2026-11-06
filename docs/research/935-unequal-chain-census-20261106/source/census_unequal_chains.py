"""Census one acquired edge opposite two actual consecutive acquired edges."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np
from scipy.spatial import cKDTree


PATTERNS = np.array([[[0,1,2],[0,2,3],[0,3,4]], [[0,1,3],[1,2,3],[0,3,4]],
    [[0,1,4],[1,2,3],[1,3,4]], [[0,1,4],[1,2,4],[2,3,4]],
    [[0,1,2],[0,2,4],[2,3,4]]], dtype=np.int64)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    with np.load(path, allow_pickle=False) as arrays:
        return {name: arrays[name] for name in arrays.files}


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def forward_flags(polygon, directions):
    flags = np.zeros((len(polygon), 5), dtype=bool)
    for i, pattern in enumerate(PATTERNS):
        xyz = polygon[:, pattern]
        cross = np.cross(xyz[:, :, 1]-xyz[:, :, 0], xyz[:, :, 2]-xyz[:, :, 0])
        length = np.linalg.norm(cross, axis=2)
        unit = np.zeros_like(cross)
        valid = length > 0
        unit[valid] = cross[valid]/length[valid, None]
        dots = np.einsum('mti,msi->mts', unit, directions)
        flags[:, i] = valid.all(axis=1) & (dots >= .8).all(axis=(1, 2))
    return flags


def qualify(points, edges, normals, triples):
    """Vector predicates at the frozen bounds; no native construction admission."""
    a, b = edges[triples[:, 0]].T
    c, d = edges[triples[:, 1]].T
    dd, e = edges[triples[:, 2]].T
    nodes = np.c_[a, b, c, d, e]
    alive = np.ones(len(triples), dtype=bool); common = Counter()
    def refuse(name, ok):
        common[name] = int(np.count_nonzero(alive & ~ok)); alive[:] &= ok
    refuse('two_edges_not_directed_consecutive', d == dd)
    distinct = np.ones(len(triples), dtype=bool)
    for i in range(5):
        for j in range(i+1, 5):
            distinct &= (nodes[:, i] != nodes[:, j]) & np.any(points[nodes[:, i]] != points[nodes[:, j]], axis=1)
    refuse('not_five_distinct_source_corners', distinct)
    p, q, r, s, t = (points[nodes[:, i]] for i in range(5))
    single = q-p
    length2 = np.sum(single**2, axis=1)
    parameter = np.zeros(len(triples)); good = length2 > 0
    parameter[good] = np.clip(np.sum((s-p)[good]*single[good], axis=1)/length2[good], 0, 1)
    projected = p+parameter[:, None]*single
    gaps = np.stack((t-p, r-q, s-projected), axis=1)
    lengths = np.linalg.norm(gaps, axis=2)
    scores = np.max(np.sum(gaps**2, axis=2), axis=1)
    refuse('cross_endpoint_or_middle_support_distance', scores <= .25)
    tangent = np.stack((single, s-r, t-s), axis=1)
    tl = np.linalg.norm(tangent, axis=2)
    unit = np.zeros_like(tangent); valid = tl > 0
    unit[valid] = tangent[valid]/tl[valid, None]
    tangent_ok = (tl > 0).all(axis=1)
    tangent_ok &= (np.sum(unit[:, 0]*unit[:, 1], axis=1) <= -.8)
    tangent_ok &= (np.sum(unit[:, 0]*unit[:, 2], axis=1) <= -.8)
    refuse('each_opposing_directed_tangent', tangent_ok)
    common['passed_common_geometry'] = int(alive.sum())
    positions = np.flatnonzero(alive)
    chosen = triples[positions]; n = normals[chosen]
    rr = np.sum(n[:, 1]*n[:, 2], axis=1)
    lr1 = np.sum(n[:, 0]*n[:, 1], axis=1); lr2 = np.sum(n[:, 0]*n[:, 2], axis=1)
    polygon = points[np.c_[b, a, e, d, c][positions]]
    eligible, classes, all_flags, all_scores = [], [], [], []
    counts = []
    for cls in (0, 1):
        mask = np.ones(len(positions), dtype=bool); reasons = Counter()
        def reject(name, ok):
            reasons[name] = int(np.count_nonzero(mask & ~ok)); mask[:] &= ok
        reject('right_chain_acquired_owner_alignment', rr >= .8)
        reject('acquired_owner_class', (lr1 >= .8)&(lr2 >= .8) if cls == 0 else (lr1 <= -.8)&(lr2 <= -.8))
        if cls == 0:
            directions = n
        else:
            local_gaps, local_lengths = gaps[positions], lengths[positions]
            normalized = np.zeros_like(local_gaps); nz = local_lengths > 0
            normalized[nz] = local_gaps[nz]/local_lengths[nz, None]
            side = np.all(local_lengths > 0, axis=1)
            side &= (np.einsum('mki,mi->mk', normalized, n[:, 0]) <= -.8).all(axis=1)
            for gap_index, owner_index in ((1, 1), (2, 1), (2, 2), (0, 2)):
                side &= (np.sum(-normalized[:, gap_index]*n[:, owner_index], axis=1) <= -.8)
            reject('gap_not_towards_all_actual_material_sides', side)
            directions = np.cross(unit[positions], n)
            norm = np.linalg.norm(directions, axis=2)
            usable = norm > 0; normalized_directions = np.zeros_like(directions)
            normalized_directions[usable] = directions[usable]/norm[usable, None]
            directions = normalized_directions
            compatible = usable.all(axis=1)
            for i, j in ((0, 1), (0, 2), (1, 2)):
                compatible &= np.sum(directions[:, i]*directions[:, j], axis=1) >= .8
            reject('outward_binormals_incompatible', compatible)
        flags = forward_flags(polygon, directions)
        reject('no_nonzero_forward_pentagon_triangulation', flags.any(axis=1))
        reasons['eligible'] = int(mask.sum()); counts.append(dict(reasons))
        eligible.extend(positions[mask]); classes.extend([cls]*int(mask.sum()))
        all_flags.extend(flags[mask]); all_scores.extend(scores[positions[mask]])
    indices = np.asarray(eligible, dtype=np.int64)
    assert len(np.unique(indices)) == len(indices), 'normal_classes_must_be_disjoint'
    order = np.argsort(indices)
    return dict(common), counts, triples[indices[order]], np.asarray(classes, dtype=np.int8)[order], \
        np.asarray(all_flags, dtype=bool).reshape(-1, 5)[order], np.asarray(all_scores)[order]


def unique_three_edge_selection(triples, scores, edge_count):
    incident = {}
    for candidate, edges in enumerate(triples):
        for edge in edges:
            incident.setdefault(int(edge), []).append(candidate)
    best = np.full(edge_count, -1, dtype=np.int64); ambiguous = []
    for edge, candidates in incident.items():
        candidates = sorted(candidates, key=lambda i: (scores[i], i))
        minimum = scores[candidates[0]]
        tied = [i for i in candidates if scores[i]-minimum <= 1e-12]
        if len(tied) == 1:
            best[edge] = tied[0]
        else:
            ambiguous.append(edge)
    selected = np.array([i for i, edges in enumerate(triples) if np.all(best[edges] == i)], dtype=np.int64)
    assert len(np.unique(triples[selected])) == 3*len(selected)
    return selected, best, np.array(sorted(ambiguous), dtype=np.int64)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args(); began = time.monotonic(); job = json.loads(args.job.read_text())
    assert job['schema'] == '935-unequal-chain-source-census-1'
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    proof = json.loads(Path(job['large_audit_proof']).read_text())
    assert proof['large_frontier_audit_independently_verified'] and proof['mesh_sha256'] == sha(job['mesh'])
    assert proof['source_sha256'] == sha(job['large_audit_inspector'])
    assert proof['ancestry_sha256'] == sha(job['large_ancestry'])
    mesh, border, raw, large, history = map(load, (job['mesh'], job['boundaries'], job['source_arrays'],
        job['large_ancestry'], job['atomic_history']))
    edges, owners = border['boundary'], border['owners']
    scope = np.sort(large['flat_edge_ids'][border['edge_origin_kind'][large['flat_edge_ids']] == 1])
    assert len(scope) == 68588
    successor = np.full(len(edges), -1, dtype=np.int64)
    for a, b in zip(border['offsets'][:-1], border['offsets'][1:]):
        ids = border['cycle_edges'][a:b]; successor[ids] = np.roll(ids, -1)
    present = np.zeros(len(edges), dtype=bool); present[scope] = True
    chains = np.c_[scope[present[successor[scope]]], successor[scope[present[successor[scope]]]]]
    identity = module(job['identity_producer'], 'chain_vector_raw_identity')
    keys = np.full((len(edges), 3), -1, dtype=np.int64); normals = np.zeros((len(edges), 3))
    keys[scope], normals[scope] = identity.source_edge_keys(mesh, edges, owners, raw, scope)
    lookup = np.full(len(edges), -1, dtype=np.int64); lookup[large['flat_edge_ids']] = np.arange(len(large['flat_edge_ids']))
    saved = large['edge_signatures'][lookup[scope]]
    assert np.array_equal(keys[scope], saved[:, [1, 5, 6]])
    assert np.allclose(normals[scope], large['actual_acquired_normals'][lookup[scope]], rtol=0, atol=1e-14)
    single_mid = mesh['points'][edges[scope]].mean(axis=1)
    chain_mid = (mesh['points'][edges[chains[:, 0], 0]]+mesh['points'][edges[chains[:, 1], 1]])/2
    left_tree, right_tree = cKDTree(single_mid), cKDTree(chain_mid)
    envelope = int(left_tree.count_neighbors(right_tree, .5+1e-12))
    assert envelope <= job['maximum_bipartite_radius_pairs']
    neighbors = left_tree.query_ball_tree(right_tree, .5+1e-12)
    chain_rows = np.concatenate([np.asarray(v, dtype=np.int64) for v in neighbors])
    left = np.repeat(scope, [len(v) for v in neighbors])
    triples = np.c_[left, chains[chain_rows]]
    delta = single_mid[np.repeat(np.arange(len(scope)), [len(v) for v in neighbors])]-chain_mid[chain_rows]
    triples = triples[np.sum(delta**2, axis=1) <= .25]
    triples = triples[np.lexsort((triples[:, 2], triples[:, 1], triples[:, 0]))]
    labels = large['face_component_ids'][owners]
    component_ok = (labels[triples[:, 0]] == labels[triples[:, 1]]) & (labels[triples[:, 1]] == labels[triples[:, 2]])
    evaluated = triples[component_ok]
    common = Counter(); class_counts = [Counter(), Counter()]
    eligible, classes, flags, scores = [], [], [], []
    for start in range(0, len(evaluated), 10000):
        c, cc, t, cls, f, score = qualify(mesh['points'], edges, normals, evaluated[start:start+10000])
        common.update(c)
        for i in (0, 1): class_counts[i].update(cc[i])
        eligible.append(t); classes.append(cls); flags.append(f); scores.append(score)
    eligible = np.concatenate(eligible) if eligible else np.empty((0, 3), dtype=np.int64)
    classes = np.concatenate(classes) if classes else np.empty(0, dtype=np.int8)
    flags = np.concatenate(flags) if flags else np.empty((0, 5), dtype=bool)
    scores = np.concatenate(scores) if scores else np.empty(0)
    selected, best, ambiguous = unique_three_edge_selection(eligible, scores, len(edges))
    assert history['raw_pair_keys'].shape == (1728, 6)
    assert len(np.unique(history['raw_pair_keys'], axis=0)) == 1728
    args.output.mkdir(mode=0o700, exist_ok=False)
    target = args.output/'private-unequal-chain-census.npz'
    np.savez_compressed(target, scope_edge_ids=scope, successor_edge_ids=successor, right_chain_edge_ids=chains,
        source_edge_keys=keys, bipartite_radius_triples=triples, component_excluded_indices=np.flatnonzero(~component_ok),
        evaluated_triples=evaluated, eligible_chain_edge_ids=eligible, eligible_classes=classes,
        eligible_triangulation_flags=flags, eligible_width_scores_squared=scores,
        selected_eligible_indices=selected, selected_chain_edge_ids=eligible[selected],
        eligible_raw_chain_keys=keys[eligible].reshape(-1, 9), selected_raw_chain_keys=keys[eligible[selected]].reshape(-1, 9),
        unique_best_candidate_by_edge=best, ambiguous_edge_ids=ambiguous)
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    report = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), mesh_sha256=sha(job['mesh']),
        census_sha256=sha(target), acquired_single_edges=len(scope), actual_two_edge_chains=len(chains),
        guarded_bipartite_envelope=envelope, exact_bipartite_radius_triples=len(triples),
        cross_component_triples_refused=int((~component_ok).sum()), evaluated_triples=len(evaluated),
        common_stage_counts=dict(common), class_stage_counts=list(map(dict, class_counts)),
        eligible_chains=len(eligible), selected_chains=len(selected), ambiguous_edges=len(ambiguous),
        selected_class_counts=dict(Counter(map(str, classes[selected]))),
        original_atomic_history_preserved=1728, five_corners_not_four_corner_retries=True,
        original_distance_and_angle_bounds_unchanged=True, native_constructor_not_admitted=True,
        geometry_modified=False, physical_acceptance=False, manufacturing_authorized=False,
        seconds=time.monotonic()-began)
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
