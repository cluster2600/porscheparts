"""Exact necessary conditions for a source-corner-only nonplanar disk hypothesis.

This does not construct a patch or admit intersections, support or physical roles.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def lattice(points):
    ratios = [[float(x).as_integer_ratio() for x in row] for row in points]
    denominator = max(q for row in ratios for _, q in row)
    return [tuple(p * (denominator // q) for p, q in row) for row in ratios]


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def normal(a, b, c):
    return cross(tuple(y-x for x, y in zip(a, b)), tuple(y-x for x, y in zip(a, c)))


def alignment(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    aa, bb = sum(x*x for x in a), sum(x*x for x in b)
    numerator, denominator = float(.8).as_integer_ratio()
    return bool(aa and bb and dot > 0 and dot*dot*denominator**2 >= numerator**2*aa*bb)


def allowed_triangles(points, owner_triangles):
    """Enumerate every nonzero reversed triangle, testing each owned rim edge."""
    n = len(points)
    integer = lattice(np.concatenate((points, owner_triangles.reshape(-1, 3))))
    rim, owner = integer[:n], integer[n:]
    normals = [normal(*owner[3*i:3*i+3]) for i in range(n)]
    assert all(any(v for v in item) for item in normals)
    allowed = []
    rim_candidates = np.zeros((n, n), dtype=np.uint8)
    for i in range(n-2):
        for k in range(i+1, n-1):
            for j in range(k+1, n):
                direction = normal(rim[i], rim[j], rim[k])
                if not any(direction):
                    continue
                borders = []
                if k == i+1:
                    borders.append((i, j))
                if j == k+1:
                    borders.append((k, i))
                if i == 0 and j == n-1:
                    borders.append((j, k))
                decisions = [alignment(direction, normals[edge]) for edge, _ in borders]
                for (edge, third), valid in zip(borders, decisions):
                    rim_candidates[edge, third] = valid
                if all(decisions):
                    allowed.append((i, k, j))
    return np.asarray(allowed, dtype=np.int64).reshape(-1, 3), rim_candidates


def disk_count(size, allowed):
    """Count all combinatorial polygon disks; geometric embedding is separate."""
    legal = set(map(tuple, allowed))
    counts = [[0]*size for _ in range(size)]
    for i in range(size-1):
        counts[i][i+1] = 1
    for width in range(2, size):
        for i in range(size-width):
            j = i+width
            counts[i][j] = sum(counts[i][k]*counts[k][j] for k in range(i+1, j)
                               if (i, k, j) in legal)
    return counts[0][-1]


def raw_owners(mesh, border, raw, edge_ids):
    triangles = []
    keys = []
    for edge_id in edge_ids:
        owner = int(border['owners'][edge_id])
        assert border['edge_origin_kind'][edge_id] == 1
        assert mesh['inferred_surface_kind'][owner] == 0
        original = int(mesh['original_face_ids'][owner])
        assert 0 <= original < len(raw['triangles'])
        source_ids = raw['triangles'][original]
        source = raw['vertices'][source_ids]
        ids = mesh['triangles'][owner]
        coordinates = mesh['points'][ids]
        assert any(np.array_equal(coordinates, np.roll(source, s, axis=0)) for s in range(3))
        a, b = map(int, border['boundary'][edge_id])
        assert (a, b) in list(zip(ids, np.roll(ids, -1)))
        source_a = [int(v) for v, p in zip(source_ids, source) if np.array_equal(p, mesh['points'][a])]
        source_b = [int(v) for v, p in zip(source_ids, source) if np.array_equal(p, mesh['points'][b])]
        assert len(source_a) == len(source_b) == 1
        assert (source_a[0], source_b[0]) in list(zip(source_ids, np.roll(source_ids, -1)))
        triangles.append(source)
        keys.append((original, source_a[0], source_b[0]))
    return np.asarray(triangles), np.asarray(keys, dtype=np.int64)


def select_walks(mesh, border):
    selected, counts = [], Counter()
    assert np.array_equal(np.sort(border['cycle_edges']), np.arange(len(border['boundary'])))
    for walk in range(len(border['offsets'])-1):
        a, b = border['offsets'][walk:walk+2]
        ids = border['cycle_edges'][a:b]
        edges = border['boundary'][ids]
        assert np.array_equal(edges[:, 1], np.roll(edges[:, 0], -1))
        if not np.all(border['edge_origin_kind'][ids] == 1):
            counts['mixed_or_nonacquired'] += 1
            continue
        if not 3 <= len(ids) <= 128:
            counts['outside_edge_count_scope'] += 1
            continue
        points = mesh['points'][edges[:, 0]]
        if len(np.unique(points, axis=0)) != len(points):
            counts['repeated_coordinate'] += 1
            continue
        if np.dot(np.ptp(points, axis=0), np.ptp(points, axis=0)) > 9:
            counts['outside_diagonal_scope'] += 1
            continue
        exact = lattice(points)
        first = tuple(exact[1][k]-exact[0][k] for k in range(3))
        if not any(any(cross(first, tuple(p[k]-exact[0][k] for k in range(3)))) for p in exact[2:]):
            counts['rank_below_two'] += 1
            continue
        centred = points-points.mean(axis=0)
        _, singular, axes = np.linalg.svd(centred, full_matrices=False)
        spectrum = np.r_[singular**2, np.zeros(max(0, 3-len(singular)))]
        if spectrum[1]-spectrum[2] <= 1e-10*spectrum[0]:
            counts['plane_not_numerically_unique'] += 1
            continue
        residual = float(np.abs(centred@axes[-1]).max())
        assert abs(residual-.25) > 1e-10, 'uncertain_nonplanar_scope_boundary'
        if residual <= .25:
            counts['compact_planar_outside_new_scope'] += 1
            continue
        selected.append((walk, ids, residual))
        counts['pure_acquired_compact_nonplanar'] += 1
    assert sum(counts.values()) == len(border['offsets'])-1
    return selected, dict(counts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job', 'output'):
        parser.add_argument('--'+name, required=True, type=Path)
    args = parser.parse_args()
    began = time.monotonic()
    job = json.loads(args.job.read_text())
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    assert job['policy'] == 'source_corner_only_nonplanar_disk_local_acquired_border_0.8_v1'
    proof = json.loads(Path(job['surface_proof']).read_text())
    assert proof['surface_study_checks_passed'] and proof['mesh_sha256'] == sha(job['mesh'])
    assert proof['source_sha256'] == sha(job['surface_inspector'])
    mesh, border, raw = [dict(np.load(job[k], allow_pickle=False)) for k in ('mesh', 'boundaries', 'source_arrays')]
    assert len(border['boundary']) == proof['remaining_boundary_edges']
    assert len(border['offsets'])-1 == proof['remaining_boundary_walks']
    selected, counts = select_walks(mesh, border)
    args.output.mkdir(mode=0o700, exist_ok=False)
    rows = []
    for walk, edge_ids, residual in selected:
        nodes = border['boundary'][edge_ids, 0]
        owners, raw_keys = raw_owners(mesh, border, raw, edge_ids)
        allowed, rim = allowed_triangles(mesh['points'][nodes], owners)
        ways = disk_count(len(nodes), allowed)
        target = args.output/('private-walk-'+str(walk).zfill(4)+'.npz')
        np.savez_compressed(target, edge_ids=edge_ids, nodes=nodes, raw_keys=raw_keys,
                            allowed_triangles=allowed, rim_third_corner_allowed=rim)
        rows.append(dict(walk=int(walk), edges=len(nodes), plane_residual_nominal_mm=residual,
                         possible_triangle_count=len(nodes)*(len(nodes)-1)*(len(nodes)-2)//6,
                         allowed_triangle_count=len(allowed), empty_rim_edges=int(np.count_nonzero(~rim.any(axis=1))),
                         combinatorial_disk_count=str(ways), necessary_conditions_passed=ways>0,
                         private_file=target.name, private_sha256=sha(target)))
    (args.output/'private-walk-results.json').write_text(json.dumps(rows, indent=2)+'\n')
    result = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), mesh_sha256=sha(job['mesh']),
                  private_results_sha256=sha(args.output/'private-walk-results.json'),
                  scope_partition=counts, whole_walks=len(border['offsets'])-1,
                  scoped_walks=len(rows), scoped_edges=sum(r['edges'] for r in rows),
                  exact_corner_triples=sum(r['possible_triangle_count'] for r in rows),
                  empty_rim_edges=sum(r['empty_rim_edges'] for r in rows),
                  necessary_condition_passing_walks=sum(r['necessary_conditions_passed'] for r in rows),
                  exact_binary64_alignment_threshold=True, new_coordinates_allowed=False,
                  projected_planarity_not_required_by_this_new_hypothesis=True,
                  old_planar_cap_policy_unchanged=True, independent_verification_pending=True,
                  geometry_modified=False, construction_admitted=False, physical_acceptance=False,
                  manufacturing_authorized=False, seconds=time.monotonic()-began)
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    (args.output/'report.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
