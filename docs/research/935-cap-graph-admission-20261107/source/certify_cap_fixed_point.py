"""Independently enumerate every edge of the unchanged cap proposal."""
import argparse
from collections import defaultdict
from fractions import Fraction as Q
import importlib.util
from itertools import permutations
import json
from pathlib import Path
import signal
import time

import numpy as np


def determinant(matrix):
    size = len(matrix)
    total = Q(0)
    for order in permutations(range(size)):
        term = Q(-1 if sum(order[i] > order[j] for i in range(size) for j in range(i+1, size)) % 2 else 1)
        for i in range(size):
            term *= matrix[i][order[i]]
        total += term
    return total


def controls():
    circle = [[Q(x), Q(y), Q(x*x+y*y), Q(1)] for x, y in [(0, 0), (1, 0), (1, 1), (0, 1)]]
    assert determinant(circle) == 0
    circle[-1] = [Q(1, 2), Q(1, 2), Q(1, 2), Q(1)]
    assert determinant(circle) == Q(1, 2)
    circle[0], circle[1] = circle[1], circle[0]
    assert determinant(circle) == -Q(1, 2)
    return {'literal_cocircular_zero': True, 'literal_inside_positive': True, 'row_swap_sign': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); job = json.loads(args.job.read_text())
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600); started = time.monotonic()
    spec = importlib.util.spec_from_file_location('cap_certificate_io', job['diagnostic'])
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    for item in job['inputs']:
        assert helper.sha(item['path']) == item['sha256']
    args.output.mkdir(mode=0o700, exist_ok=False); tested = controls()
    with np.load(job['proposal'], allow_pickle=False) as data:
        points, old, new = data['vertices'], data['old_triangles'], data['new_triangles']
        ids, source_rows, axes = data['source_node_ids'], data['source_face_rows'], data['projection_axes']
        asserted_protected = {tuple(map(int, e)) for e in data['protected_edges']}
    assert np.array_equal(old, new), 'This certificate only covers the unchanged proposal'
    with np.load(job['surface'], allow_pickle=False) as data:
        assert np.array_equal(data['vertices'][ids].view(np.uint64), points.view(np.uint64))
        assert np.array_equal(data['triangles'][source_rows], ids[old])
    with np.load(job['mapping'], allow_pickle=False) as data:
        mapping, retained = data['mapping'], data['used_source_vertices']
    inverse = np.full(len(mapping), -1, dtype=np.int64); inverse[retained] = np.arange(len(retained))
    original = np.load(job['features'], allow_pickle=False)
    marked = inverse[mapping[np.column_stack((original//len(mapping), original % len(mapping)))]]
    assert np.all(marked >= 0)
    local = {int(v): i for i, v in enumerate(ids)}
    protected = {tuple(sorted((local[int(a)], local[int(b)]))) for a, b in marked
                 if a != b and int(a) in local and int(b) in local}
    assert protected == asserted_protected
    projected = [[Q.from_float(float(x)) for x in p] for p in points[:, axes]]

    def area(triangle):
        return determinant([[*projected[v], Q(1)] for v in triangle])

    assert all(area(t) > 0 for t in old)
    owners = defaultdict(list)
    for row, triangle in enumerate(old):
        for k in range(3):
            owners[tuple(sorted(map(int, (triangle[k], triangle[(k+1) % 3]))))].append(row)
    assert all(len(rows) in (1, 2) for rows in owners.values())
    counts = dict(boundary=0, constrained_interior=0, nonconvex_interior=0,
                  convex_strictly_legal=0, convex_cocircular=0, strict_flips_available=0)
    private = []
    for edge, rows in sorted(owners.items()):
        if len(rows) == 1:
            counts['boundary'] += 1; continue
        if edge in protected:
            counts['constrained_interior'] += 1; continue
        a, b = edge; p, = set(map(int, old[rows[0]]))-set(edge); q, = set(map(int, old[rows[1]]))-set(edge)
        if area([a, b, p]) < 0:
            a, b = b, a
        assert area([a, b, p]) > 0 and area([b, a, q]) > 0
        convex = area([p, a, q]) > 0 and area([p, q, b]) > 0
        value = determinant([[*projected[v], sum(x*x for x in projected[v]), Q(1)] for v in (a, b, p, q)])
        if not convex:
            counts['nonconvex_interior'] += 1
        elif value < 0:
            counts['convex_strictly_legal'] += 1
        elif value == 0:
            counts['convex_cocircular'] += 1
        else:
            counts['strict_flips_available'] += 1
        private.append({'edge': edge, 'convex': convex, 'incircle_determinant': str(value)})
    assert counts['strict_flips_available'] == 0
    assert sum(counts.values()) == len(owners)
    ledger = args.output/'private-edge-certificate.json'; ledger.write_text(json.dumps(private, indent=2)+'\n')
    report = dict(schema='935-cap-fixed-point-certificate-1', source_sha256=helper.sha(__file__),
        job_sha256=helper.sha(args.job), controls=tested, edge_census=counts,
        cap_vertices=len(points), cap_triangles=len(old), edges=len(owners),
        every_source_coordinate_bit_preserved=True, every_source_triangle_preserved=True,
        mapped_feature_edges_independently_reconstructed=True, exact_graph_change_nominal_mm=0,
        private_edge_certificate_sha256=helper.sha(ledger), triangulations_with_additional_points_excluded=False,
        other_flip_criteria_excluded=False, complete_head_modified=False,
        physics_admitted=False, manufacturing_qualified=False, new_paid_compute_usd=0,
        seconds=time.monotonic()-started)
    for item in job['inputs']:
        assert helper.sha(item['path']) == item['sha256']
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    signal.alarm(0); print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
