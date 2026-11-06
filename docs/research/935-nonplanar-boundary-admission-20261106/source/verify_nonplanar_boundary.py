"""Independent Fraction and recursive-disk replay; no producer imports."""
import argparse
from collections import Counter
from fractions import Fraction
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def vector(a, b, c):
    u = [b[k]-a[k] for k in range(3)]
    v = [c[k]-a[k] for k in range(3)]
    return [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]


def triangle_replay(points, owners):
    p = [[Fraction(float(x)) for x in row] for row in points]
    acquired = [[[Fraction(float(x)) for x in point] for point in tri] for tri in owners]
    normals = [vector(*triangle) for triangle in acquired]
    assert all(any(n) for n in normals)
    threshold_squared = Fraction(float(.8))**2
    n = len(p)
    legal = []
    rim = np.zeros((n, n), dtype=np.uint8)
    for a in range(n-2):
        for b in range(a+1, n-1):
            for c in range(b+1, n):
                direction = vector(p[c], p[b], p[a])
                magnitude = sum(x*x for x in direction)
                if magnitude == 0:
                    continue
                # A reversed cap border must oppose an actual consecutive source edge.
                actual = []
                for u, v, third in ((a, c, b), (c, b, a), (b, a, c)):
                    if (v+1) % n == u:
                        dot = sum(x*y for x, y in zip(direction, normals[v]))
                        good = dot > 0 and dot**2 >= threshold_squared*magnitude*sum(x*x for x in normals[v])
                        actual.append(bool(good))
                        rim[v, third] = good
                if all(actual):
                    legal.append((a, b, c))
    return np.asarray(legal, dtype=np.int64).reshape(-1, 3), rim


def recursive_count(size, triangles):
    accepted = frozenset(map(tuple, triangles))
    @lru_cache(None)
    def visit(sequence):
        if len(sequence) == 2:
            return 1
        total = 0
        for pivot in range(1, len(sequence)-1):
            key = (sequence[0], sequence[pivot], sequence[-1])
            if key in accepted:
                total += visit(sequence[:pivot+1])*visit(sequence[pivot:])
        return total
    return visit(tuple(range(size)))


def recover_owners(mesh, border, raw, edges):
    result, keys = [], []
    for e in edges:
        face = int(border['owners'][e])
        assert mesh['inferred_surface_kind'][face] == 0 and border['edge_origin_kind'][e] == 1
        source_face = int(mesh['original_face_ids'][face])
        assert 0 <= source_face < len(raw['triangles'])
        original = list(map(int, raw['triangles'][source_face]))
        coordinates = raw['vertices'][original]
        lookup = {tuple(p):node for p, node in zip(coordinates, original)}
        assert len(lookup) == 3
        observed = [lookup[tuple(mesh['points'][node])] for node in mesh['triangles'][face]]
        assert observed in [original[s:]+original[:s] for s in range(3)]
        a, b = map(int, border['boundary'][e])
        ids = mesh['triangles'][face].tolist()
        assert (a, b) in list(zip(ids, ids[1:]+ids[:1]))
        ra, rb = [lookup[tuple(mesh['points'][node])] for node in (a, b)]
        assert (ra, rb) in list(zip(original, original[1:]+original[:1]))
        result.append(coordinates)
        keys.append((source_face, ra, rb))
    return np.asarray(result), np.asarray(keys, dtype=np.int64)


def independent_scope(mesh, border):
    choices, bins = [], Counter()
    seen = set()
    for walk, (begin, end) in enumerate(zip(border['offsets'][:-1], border['offsets'][1:])):
        ids = list(map(int, border['cycle_edges'][begin:end]))
        assert not seen.intersection(ids)
        seen.update(ids)
        pairs = border['boundary'][ids]
        assert all(pairs[i, 1] == pairs[(i+1) % len(ids), 0] for i in range(len(ids)))
        if set(map(int, border['edge_origin_kind'][ids])) != {1}:
            bins['mixed_or_nonacquired'] += 1
        elif not 3 <= len(ids) <= 128:
            bins['outside_edge_count_scope'] += 1
        else:
            p = mesh['points'][pairs[:, 0]]
            if len(set(map(tuple, p))) != len(p):
                bins['repeated_coordinate'] += 1
                continue
            spread = [max(p[:, k])-min(p[:, k]) for k in range(3)]
            if sum(x*x for x in spread) > 9:
                bins['outside_diagonal_scope'] += 1
                continue
            exact = [[Fraction(float(x)) for x in row] for row in p]
            if not any(any(vector(exact[0], exact[1], q)) for q in exact[2:]):
                bins['rank_below_two'] += 1
                continue
            centre = np.array([sum(p[:, k])/len(p) for k in range(3)])
            centred = p-centre
            values, axes = np.linalg.eigh(centred.T@centred)
            if values[1]-values[0] <= 1e-10*values[-1]:
                bins['plane_not_numerically_unique'] += 1
                continue
            residual = max(abs(float(np.dot(point, axes[:, 0]))) for point in centred)
            assert abs(residual-.25) > 1e-10, 'uncertain_nonplanar_scope_boundary'
            if residual > .25:
                choices.append((walk, np.asarray(ids), residual))
                bins['pure_acquired_compact_nonplanar'] += 1
            else:
                bins['compact_planar_outside_new_scope'] += 1
    assert seen == set(range(len(border['boundary'])))
    return choices, dict(bins)


def inspect_complete_boundary(mesh, border):
    triangles = mesh['triangles']
    edges = np.concatenate((triangles[:, :2], triangles[:, 1:], triangles[:, [2, 0]]))
    faces = np.tile(np.arange(len(triangles)), 3)
    codes = edges.min(axis=1)*len(mesh['points'])+edges.max(axis=1)
    order = np.argsort(codes, kind='stable')
    sorted_codes = codes[order]
    start = np.r_[0, np.flatnonzero(np.diff(sorted_codes))+1]
    uses = np.diff(np.r_[start, len(order)])
    assert np.all((uses == 1) | (uses == 2))
    pairs = start[uses == 2]
    assert np.array_equal(edges[order[pairs]], edges[order[pairs+1]][:, ::-1])
    rows = order[start[uses == 1]]
    saved = border['boundary']
    saved_codes = saved.min(axis=1)*len(mesh['points'])+saved.max(axis=1)
    saved_order = np.argsort(saved_codes)
    assert np.array_equal(edges[rows], saved[saved_order])
    assert np.array_equal(faces[rows], border['owners'][saved_order])
    return len(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('job', 'audit', 'output'):
        parser.add_argument('--'+key, required=True, type=Path)
    args = parser.parse_args()
    began = time.monotonic()
    job = json.loads(args.job.read_text())
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    assert job['policy'] == 'source_corner_only_nonplanar_disk_local_acquired_border_0.8_v1'
    peer = json.loads((args.audit/'report.json').read_text())
    assert peer['source_sha256'] == sha(job['producer_source'])
    assert peer['job_sha256'] == sha(args.job) and peer['mesh_sha256'] == sha(job['mesh'])
    assert peer['private_results_sha256'] == sha(args.audit/'private-walk-results.json')
    rows = json.loads((args.audit/'private-walk-results.json').read_text())
    mesh, border, raw = [dict(np.load(job[k], allow_pickle=False)) for k in ('mesh', 'boundaries', 'source_arrays')]
    proof = json.loads(Path(job['surface_proof']).read_text())
    assert proof['surface_study_checks_passed'] and proof['mesh_sha256'] == sha(job['mesh'])
    assert proof['source_sha256'] == sha(job['surface_inspector'])
    edges = inspect_complete_boundary(mesh, border)
    assert edges == proof['remaining_boundary_edges']
    selected, bins = independent_scope(mesh, border)
    assert bins == peer['scope_partition'] and len(rows) == len(selected)
    passed = empty = triples = 0
    for (walk, ids, residual), row in zip(selected, rows):
        assert row['walk'] == walk and row['edges'] == len(ids)
        assert abs(residual-row['plane_residual_nominal_mm']) < 1e-8
        file = args.audit/row['private_file']
        assert sha(file) == row['private_sha256']
        saved = dict(np.load(file, allow_pickle=False))
        nodes = border['boundary'][ids, 0]
        assert np.array_equal(saved['edge_ids'], ids) and np.array_equal(saved['nodes'], nodes)
        owners, keys = recover_owners(mesh, border, raw, ids)
        assert np.array_equal(keys, saved['raw_keys'])
        legal, rim = triangle_replay(mesh['points'][nodes], owners)
        assert np.array_equal(legal, saved['allowed_triangles'])
        assert np.array_equal(rim, saved['rim_third_corner_allowed'])
        ways = recursive_count(len(nodes), legal)
        assert str(ways) == row['combinatorial_disk_count']
        assert row['necessary_conditions_passed'] == (ways > 0)
        missing = sum(not any(r) for r in rim)
        assert row['empty_rim_edges'] == missing
        assert row['allowed_triangle_count'] == len(legal)
        count = len(nodes)*(len(nodes)-1)*(len(nodes)-2)//6
        assert row['possible_triangle_count'] == count
        passed += ways > 0
        empty += missing
        triples += count
    assert passed == peer['necessary_condition_passing_walks']
    assert empty == peer['empty_rim_edges'] and triples == peer['exact_corner_triples']
    args.output.mkdir(mode=0o700, exist_ok=False)
    result = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), mesh_sha256=sha(job['mesh']),
                  complete_boundary_edges_verified=edges, whole_walks=len(border['offsets'])-1,
                  scope_partition=bins, scoped_walks=len(selected), scoped_edges=sum(len(r[1]) for r in selected),
                  exact_fraction_corner_triples=triples, exact_binary64_alignment_threshold=True,
                  empty_rim_edges=empty, necessary_condition_passing_walks=int(passed),
                  producer_imported=False, independent_eigen_scope_and_recursive_disk_counts_verified=True,
                  nonplanar_boundary_necessary_conditions_independently_verified=True,
                  geometry_modified=False, construction_admitted=False, physical_acceptance=False,
                  manufacturing_authorized=False, seconds=time.monotonic()-began)
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    (args.output/'report.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
