"""Independent bipartite coverage, scalar five-corner and three-edge selection replay."""
import argparse
from collections import Counter
import hashlib
import importlib.util
from itertools import product
import json
from pathlib import Path
import time

import numpy as np


PATTERNS = (((0,1,2),(0,2,3),(0,3,4)), ((0,1,3),(1,2,3),(0,3,4)),
    ((0,1,4),(1,2,3),(1,3,4)), ((0,1,4),(1,2,4),(2,3,4)),
    ((0,1,2),(0,2,4),(2,3,4)))


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


def all_convex_triangulations(vertices):
    if len(vertices) == 2:
        return [()]
    result = []
    for split in range(1, len(vertices)-1):
        for left in all_convex_triangulations(vertices[:split+1]):
            for right in all_convex_triangulations(vertices[split:]):
                result.append(left+right+((vertices[0], vertices[split], vertices[-1]),))
    return result


def inspect(points, edges, normals, triple):
    left, first, second = map(int, triple)
    a, b = map(int, edges[left]); c, d = map(int, edges[first]); dd, e = map(int, edges[second])
    if d != dd:
        return 'two_edges_not_directed_consecutive', None
    nodes = [a, b, c, d, e]
    if len(set(nodes)) != 5 or len(set(map(tuple, points[nodes]))) != 5:
        return 'not_five_distinct_source_corners', None
    delta = points[b]-points[a]
    fraction = min(1., max(0., float(np.dot(points[d]-points[a], delta)/np.dot(delta, delta))))
    middle = points[a]+fraction*delta
    gaps = [points[e]-points[a], points[c]-points[b], points[d]-middle]
    lengths = [float(np.linalg.norm(v)) for v in gaps]
    score = max(float(np.dot(v, v)) for v in gaps)
    if score > .25:
        return 'cross_endpoint_or_middle_support_distance', None
    tangents = [points[b]-points[a], points[d]-points[c], points[e]-points[d]]
    tangents = [t/np.linalg.norm(t) for t in tangents]
    if any(np.dot(tangents[0], t) > -.8 for t in tangents[1:]):
        return 'each_opposing_directed_tangent', None
    n = [normals[i] for i in (left, first, second)]
    polygon = points[[b, a, e, d, c]]
    results = []
    for cls in (0, 1):
        if np.dot(n[1], n[2]) < .8:
            results.append(('right_chain_acquired_owner_alignment', None)); continue
        owner_dots = [float(np.dot(n[0], v)) for v in n[1:]]
        good = all(v >= .8 for v in owner_dots) if cls == 0 else all(v <= -.8 for v in owner_dots)
        if not good:
            results.append(('acquired_owner_class', None)); continue
        if cls == 0:
            supports = n
        else:
            good = all(v > 0 for v in lengths)
            if good:
                normalized = [v/length for v, length in zip(gaps, lengths)]
                good &= all(np.dot(v, n[0]) <= -.8 for v in normalized)
                good &= all(np.dot(-normalized[i], n[j]) <= -.8 for i, j in ((1,1),(2,1),(2,2),(0,2)))
            if not good:
                results.append(('gap_not_towards_all_actual_material_sides', None)); continue
            supports = [np.cross(t, v) for t, v in zip(tangents, n)]
            if any(np.linalg.norm(v) == 0 for v in supports):
                results.append(('outward_binormals_incompatible', None)); continue
            supports = [v/np.linalg.norm(v) for v in supports]
            if any(np.dot(supports[i], supports[j]) < .8 for i, j in ((0,1),(0,2),(1,2))):
                results.append(('outward_binormals_incompatible', None)); continue
        flags = []
        for pattern in PATTERNS:
            good = True
            for tri in pattern:
                source_pairs = ((0,1),(4,3),(3,2))
                triangle_edges = {(min(a,b),max(a,b)) for a,b in zip(tri,tri[1:]+tri[:1])}
                attached = [i for i,(a,b) in enumerate(source_pairs) if (min(a,b),max(a,b)) in triangle_edges]
                if len(attached) != 1:
                    good = False; break
                x, y, z = polygon[list(tri)]
                normal = np.cross(y-x, z-x); size = np.linalg.norm(normal)
                if size == 0 or np.dot(normal/size, supports[attached[0]]) < .8:
                    good = False; break
            flags.append(good)
        if not any(flags):
            results.append(('no_nonzero_forward_pentagon_triangulation', None))
        else:
            results.append(('eligible', (flags, score)))
    assert not all(value is not None for _, value in results)
    return 'passed_common_geometry', results


def grid_bipartite(left, right, cap):
    assert np.all(np.isfinite(left)) and np.all(np.isfinite(right))
    assert np.max(np.abs(left/.5), initial=0) < 2**50 and np.max(np.abs(right/.5), initial=0) < 2**50
    buckets_left, buckets_right = {}, {}
    for coords, buckets in ((left, buckets_left), (right, buckets_right)):
        for row, cell in enumerate(np.floor(coords/.5).astype(np.int64)):
            buckets.setdefault(tuple(map(int, cell)), []).append(row)
    output, total = [], 0
    for cell, ids in buckets_left.items():
        a = np.array(ids, dtype=np.int64)
        for delta in product(range(-2, 3), repeat=3):
            other = tuple(c+d for c, d in zip(cell, delta))
            if other not in buckets_right:
                continue
            b = np.array(buckets_right[other], dtype=np.int64)
            for start in range(0, len(a), 128):
                aa = a[start:start+128]
                squared = np.sum((left[aa, None]-right[b][None, :])**2, axis=2)
                i, j = np.nonzero(squared <= .25)
                if len(i):
                    output.append(np.c_[aa[i], b[j]]); total += len(i)
                    assert total <= cap
    pairs = np.concatenate(output) if output else np.empty((0, 2), dtype=np.int64)
    return pairs[np.lexsort((pairs[:, 1], pairs[:, 0]))]


def three_edge_selection(triples, scores, edge_count):
    best = np.full(edge_count, -1, dtype=np.int64); ambiguous = []
    scores = np.asarray(scores)
    edge_rows = np.asarray(triples, dtype=np.int64).reshape(-1)
    candidate_rows = np.repeat(np.arange(len(triples)), 3)
    order = np.argsort(edge_rows, kind='stable')
    sorted_edges, candidate_rows = edge_rows[order], candidate_rows[order]
    unique, starts = np.unique(sorted_edges, return_index=True)
    stops = np.r_[starts[1:], len(sorted_edges)]
    for edge, a, b in zip(unique, starts, stops):
        rows = candidate_rows[a:b]
        minimum = scores[rows].min()
        tied = rows[np.abs(scores[rows]-minimum) <= 1e-12]
        if len(tied) == 1: best[int(edge)] = int(tied[0])
        else: ambiguous.append(int(edge))
    selected = [i for i, triple in enumerate(triples) if all(best[int(e)] == i for e in triple)]
    assert len(set(int(e) for i in selected for e in triples[i])) == 3*len(selected)
    return np.array(selected, dtype=np.int64), best, np.array(ambiguous, dtype=np.int64)


def controls():
    def canonical(pattern):
        return tuple(sorted(min(t[i:]+t[:i] for i in range(3)) for t in pattern))
    exhaustive = {canonical(p) for p in all_convex_triangulations(tuple(range(5)))}
    assert len(exhaustive) == 5 and exhaustive == {canonical(p) for p in PATTERNS}
    p = np.array([[0.,0.,.1],[1.2,0.,.1],[1.2,0.,-.1],[.6,0.,-.1],[0.,0.,-.1]])
    e = np.array([[0,1],[2,3],[3,4]]); n = np.array([[0.,0.,1.],[0.,0.,-1.],[0.,0.,-1.]])
    reason, result = inspect(p, e, n, [0,1,2])
    assert reason == 'passed_common_geometry' and result[1][0] == 'eligible' and sum(result[1][1][0]) == 3
    assert result[0][1] is None
    assert inspect(p, e, -n, [0,1,2])[1][1][1] is None
    reversed_edges = e[:, ::-1].copy()
    assert inspect(p, reversed_edges, -n, [0,2,1])[1][1][1] is None
    wrong = e.copy(); wrong[2] = [2,4]
    assert inspect(p, wrong, n, [0,1,2])[0] == 'two_edges_not_directed_consecutive'
    four = p.copy(); four[3] = four[0]
    assert inspect(four, e, n, [0,1,2])[0] == 'not_five_distinct_source_corners'
    # Same-facing planar missing strip; its support normal is -Z.
    planar = np.array([[0.,0.,0.],[1.2,0.,0.],[1.2,.2,0.],[.6,.2,0.],[0.,.2,0.]])
    same = np.tile([0.,0.,-1.], (3,1))
    assert inspect(planar, e, same, [0,1,2])[1][0][0] == 'eligible'
    # Material annular sector, with no triangle crossing the central bore.
    theta = np.deg2rad([30., 0., 0., 15., 30.])
    radius = np.array([2.2,2.2,2.,2.,2.])
    ring = np.c_[radius*np.cos(theta), radius*np.sin(theta), np.zeros(5)]
    directions = np.deg2rad([15.,7.5,22.5])
    annular_n = np.c_[np.cos(directions), np.sin(directions), np.zeros(3)]
    annular_n[1:] *= -1
    _, values = inspect(ring, e, annular_n, [0,1,2])
    assert values[1][0] == 'eligible'
    polygon = ring[[1,0,4,3,2]]
    for pattern, flag in zip(PATTERNS, values[1][1][0]):
        if flag:
            assert np.min(np.linalg.norm(polygon[np.asarray(pattern)].mean(axis=1)[:, :2], axis=1)) > 1.9
    curved = np.array([[0.,0.,0.],[1.2,0.,0.],[1.2,.2,0.],[.6,.2,.15],[0.,.2,0.]])
    curved_n = np.array([[0.,0.,-1.],[-.25,.05,-1.],[.25,.5,-1.]])
    curved_n /= np.linalg.norm(curved_n,axis=1)[:,None]
    assert np.allclose(np.sum((curved[e[:,1]]-curved[e[:,0]])*curved_n,axis=1),0.,atol=1e-15)
    _, local_values = inspect(curved,e,curved_n,[0,1,2])
    assert local_values[0][0] == 'eligible' and local_values[0][1][0][0]
    xyz = curved[[1,0,4,3,2]][list(PATTERNS[0][1])]
    tri_n = np.cross(xyz[1]-xyz[0],xyz[2]-xyz[0]);tri_n /= np.linalg.norm(tri_n)
    assert np.dot(tri_n,curved_n[0]) < .8 and np.dot(tri_n,curved_n[2]) >= .8
    # Ordered two-population radius coverage, including exact and nextafter cuts.
    left = np.array([[0.,0.,0.],[-.5,0.,0.]])
    right = np.array([[.5,0.,0.],[np.nextafter(.5,1.),0.,0.],[-1.,0.,0.]])
    expected = np.array([(a,b) for a in range(len(left)) for b in range(len(right))
                         if np.sum((left[a]-right[b])**2) <= .25])
    assert np.array_equal(grid_bipartite(left, right, 100), expected)
    triples = np.array([[0,1,2],[0,3,4],[5,6,7]])
    assert three_edge_selection(triples, [.1,.2,.1], 8)[0].tolist() == [0,2]
    assert three_edge_selection(triples, [.1,.1,.1], 8)[0].tolist() == [2]
    return dict(complete_pentagon_patterns=5, unequal_opposed_strip=True, same_facing_strip=True,
        void_and_global_reversal_refused=True, wrong_adjacency_and_four_corner_refused=True,
        annular_bore_preserved_by_source_predicate=True, independent_radius_boundary=True,
        three_edge_conflict_and_tie_selection=True, curved_local_acquired_border_control=True)


def complete_halos(faces, selected, edges, vertex_count):
    wanted = np.unique(edges[selected].ravel())
    mask = np.zeros(vertex_count, dtype=bool); mask[wanted] = True
    rows, columns = np.nonzero(mask[faces])
    vertices = faces[rows, columns]
    order = np.argsort(vertices, kind='stable'); vertices, rows = vertices[order], rows[order]
    unique, starts = np.unique(vertices, return_index=True)
    ends = np.r_[starts[1:], len(vertices)]
    index = {int(v): rows[a:b] for v,a,b in zip(unique, starts, ends)}
    flat, offsets = [], [0]
    for triple in selected:
        corners = np.unique(edges[triple].ravel()); assert len(corners) == 5
        halo = np.unique(np.concatenate([index[int(v)] for v in corners]))
        flat.extend(halo); offsets.append(len(flat))
    return np.asarray(offsets, dtype=np.int64), np.asarray(flat, dtype=np.int64)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job', 'census', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args(); began = time.monotonic(); job = json.loads(args.job.read_text())
    for row in job['inputs']: assert sha(row['path']) == row['sha256']
    assert job['alignment_policy'] == 'each_triangle_owns_one_actual_acquired_border'
    control = controls()
    mesh, border, raw, large, saved, history = map(load, (job['mesh'], job['boundaries'], job['source_arrays'],
        job['large_ancestry'], args.census, job['atomic_history']))
    peer = json.loads(Path(job['large_audit_proof']).read_text())
    assert peer['large_frontier_audit_independently_verified'] and peer['mesh_sha256'] == sha(job['mesh'])
    assert peer['source_sha256'] == sha(job['large_audit_inspector']) and peer['ancestry_sha256'] == sha(job['large_ancestry'])
    edges, owners = border['boundary'], border['owners']
    scope, successor = [], np.full(len(edges), -1, dtype=np.int64)
    for a,b in zip(border['offsets'][:-1], border['offsets'][1:]):
        ids = border['cycle_edges'][a:b]; successor[ids] = np.roll(ids, -1)
        origins = set(map(int, border['edge_origin_kind'][ids]))
        if len(ids) > 128 and 1 in origins and origins <= {1,6,7,8,9}:
            scope.extend(int(i) for i in ids if border['edge_origin_kind'][i] == 1)
    scope = np.array(sorted(scope), dtype=np.int64)
    assert np.array_equal(scope, saved['scope_edge_ids']) and np.array_equal(successor, saved['successor_edge_ids'])
    present = set(map(int, scope))
    chains = np.array([(int(i),int(successor[i])) for i in scope if successor[i] in present], dtype=np.int64)
    assert np.array_equal(chains, saved['right_chain_edge_ids'])
    identity = module(job['identity_inspector'], 'scalar_chain_raw_identity')
    keys = np.full((len(edges),3), -1, dtype=np.int64); normals = np.zeros((len(edges),3))
    for edge in scope: keys[edge], normals[edge] = identity.original_key(mesh, edges[edge], owners[edge], raw)
    assert np.array_equal(keys, saved['source_edge_keys'])
    component = module(job['dual_component_source'], 'chain_dual_components')
    topology = module(job['boundary_helper'], 'chain_actual_edge_table')
    labels, certificate = component.surface_components(mesh['triangles'], len(mesh['points']), border, topology)
    assert np.array_equal(labels, large['face_component_ids'])
    assert np.array_equal(certificate, large['component_V_E_F_B_chi_genus'])
    left_mid = mesh['points'][edges[scope]].mean(axis=1)
    right_mid = (mesh['points'][edges[chains[:,0],0]]+mesh['points'][edges[chains[:,1],1]])/2
    coverage = grid_bipartite(left_mid, right_mid, job['maximum_bipartite_radius_pairs'])
    triples = np.c_[scope[coverage[:,0]], chains[coverage[:,1]]]
    triples = triples[np.lexsort((triples[:,2],triples[:,1],triples[:,0]))]
    assert np.array_equal(triples, saved['bipartite_radius_triples'])
    edge_labels = labels[owners]
    excluded = [i for i,t in enumerate(triples) if len(set(map(int,edge_labels[t]))) != 1]
    assert np.array_equal(excluded, saved['component_excluded_indices'])
    keep = np.ones(len(triples), dtype=bool); keep[excluded] = False
    evaluated = triples[keep]; assert np.array_equal(evaluated, saved['evaluated_triples'])
    common, class_counts = Counter(), [Counter(),Counter()]
    eligible, classes, flags, scores = [], [], [], []
    for triple in evaluated:
        reason, results = inspect(mesh['points'], edges, normals, triple); common[reason] += 1
        if results is not None:
            for cls, (reason, value) in enumerate(results):
                class_counts[cls][reason] += 1
                if value is not None:
                    eligible.append(triple); classes.append(cls); flags.append(value[0]); scores.append(value[1])
    eligible = np.asarray(eligible,dtype=np.int64).reshape(-1,3)
    flags = np.asarray(flags,dtype=bool).reshape(-1,5); classes=np.asarray(classes,dtype=np.int8)
    assert np.array_equal(eligible,saved['eligible_chain_edge_ids']) and np.array_equal(classes,saved['eligible_classes'])
    assert np.array_equal(flags,saved['eligible_triangulation_flags'])
    assert np.allclose(scores,saved['eligible_width_scores_squared'],rtol=0,atol=1e-15)
    selected,best,ambiguous=three_edge_selection(eligible,scores,len(edges))
    assert np.array_equal(selected,saved['selected_eligible_indices'])
    assert np.array_equal(eligible[selected],saved['selected_chain_edge_ids'])
    assert np.array_equal(best,saved['unique_best_candidate_by_edge']) and np.array_equal(ambiguous,saved['ambiguous_edge_ids'])
    assert np.array_equal(keys[eligible].reshape(-1,9),saved['eligible_raw_chain_keys'])
    assert np.array_equal(keys[eligible[selected]].reshape(-1,9),saved['selected_raw_chain_keys'])
    assert history['raw_pair_keys'].shape == (1728,6) and len(np.unique(history['raw_pair_keys'],axis=0))==1728
    offsets,halos=complete_halos(mesh['triangles'],eligible[selected],edges,len(mesh['points']))
    args.output.mkdir(mode=0o700,exist_ok=False)
    target=args.output/'private-complete-five-corner-halos.npz'
    np.savez_compressed(target,halo_offsets=offsets,halo_face_rows=halos)
    for row in job['inputs']:assert sha(row['path'])==row['sha256']
    result=dict(source_sha256=sha(__file__),job_sha256=sha(args.job),mesh_sha256=sha(job['mesh']),
        census_sha256=sha(args.census),complete_halos_sha256=sha(target),acquired_single_edges=len(scope),
        actual_two_edge_chains=len(chains),independently_complete_bipartite_radius_triples=len(triples),
        cross_component_triples_refused=len(excluded),evaluated_triples=len(evaluated),
        scalar_common_stage_counts=dict(common),scalar_class_stage_counts=list(map(dict,class_counts)),
        eligible_chains=len(eligible),selected_chains=len(selected),complete_selected_halos=len(selected),
        selected_class_counts=dict(Counter(map(str,classes[selected]))),controls=control,
        scalar_raw_identity_controls_passed=identity.identity_controls(),atomic_history_preserved=1728,
        five_corner_chain_identities_verified=True,all_three_edge_selection_and_ties_verified=True,
        producer_imported=False,spatial_tree_used=False,census_independently_verified=True,
        native_constructor_not_yet_admitted=True,geometry_modified=False,
        physical_acceptance=False,manufacturing_authorized=False,seconds=time.monotonic()-began)
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)


if __name__=='__main__':main()
