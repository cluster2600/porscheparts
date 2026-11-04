"""Independently verify changed patches using scalar triple-product bounds."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def oriented(triangle):
    a, b, c = map(int, triangle)
    return min((a, b, c), (b, c, a), (c, a, b))


def verify_patches(vertices, original, candidate, records):
    integer = records[:, :6].astype(np.int64)
    if not np.array_equal(integer, records[:, :6]):
        raise ValueError('Nonintegral provenance refused')
    rows = integer[:, :2].ravel()
    if len(np.unique(rows)) != len(rows):
        raise ValueError('Overlapping changed patches refused')
    changed = np.flatnonzero(np.any(original != candidate, axis=1))
    if not np.array_equal(np.sort(rows), changed):
        raise ValueError('Undeclared changed face rows')
    bounds = []
    new_keys = set()
    for record, ids in zip(records, integer):
        ra, rb, a, b, c, d = map(int, ids)
        if oriented(original[ra]) != oriented([a, b, c]) or oriented(original[rb]) != oriented([b, a, d]):
            raise ValueError('Original quad provenance mismatch')
        if not np.array_equal(candidate[ra], [c, a, d]) or not np.array_equal(candidate[rb], [d, b, c]):
            raise ValueError('Replacement quad provenance mismatch')
        key = tuple(sorted((c, d)))
        if key in new_keys:
            raise ValueError('Duplicate replacement diagonal')
        new_keys.add(key)
        aa, bb, cc, dd = vertices[[a, b, c, d]]
        normal = np.cross(bb-aa, cc-aa) + np.cross(aa-bb, dd-bb)
        normal /= np.linalg.norm(normal)
        polygon = vertices[[c, a, d, b]]
        for i in range(4):
            first = polygon[(i+1) % 4] - polygon[i]
            second = polygon[(i+2) % 4] - polygon[(i+1) % 4]
            if np.dot(np.cross(first, second), normal) <= 0:
                raise ValueError('Nonconvex projected patch')
        cross = np.cross(bb-aa, dd-cc)
        denominator = float(np.dot(normal, cross))
        if not denominator:
            raise ValueError('Singular projected diagonals')
        bound = abs(float(np.dot(aa-cc, cross)) / denominator)
        if abs(bound-record[6]) > 1e-9 or bound > .01:
            raise ValueError('Analytic patch bound mismatch or exceeded')
        bounds.append(bound)
    return np.asarray(bounds)


def quality(vertices, faces):
    points = vertices[faces]
    edges = points - np.roll(points, 1, axis=1)
    area2 = np.linalg.norm(np.cross(edges[:, 0], -edges[:, 1]), axis=1)
    q = 2 * np.sqrt(3) * area2 / np.sum(edges**2, axis=(1, 2))
    volume = np.sum(np.einsum('ij,ij->i', points[:, 0], np.cross(points[:, 1], points[:, 2]))) / 6
    return {'bad_triangles': int((q < .01).sum()), 'minimum_quality': float(q.min()),
            'signed_volume_mm3': float(volume), 'zero_area_faces': int((area2 == 0).sum())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('trial', 'solid', 'protected', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('Existing quad assessment refused')
    plan = json.loads((args.trial/'plan.json').read_text())
    if sha(args.solid) != plan['input_sha256'] or sha(args.protected) != plan['protection_sha256']:
        raise SystemExit('Registered input changed')
    with np.load(args.solid, allow_pickle=False) as data:
        used, inverse = np.unique(data['boundary'], return_inverse=True)
        vertices, original = data['nodes'][used], inverse.reshape((-1, 3))
    with np.load(args.trial/'candidate.npz', allow_pickle=False) as data:
        actual_vertices, candidate = data['vertices'], data['triangles']
    with np.load(args.trial/'flip-provenance.npz', allow_pickle=False) as data:
        records = data['records']
    if not np.array_equal(vertices, actual_vertices) or candidate.shape != original.shape:
        raise ValueError('Vertex or face-array shape changed')
    protected = np.load(args.protected, allow_pickle=False)
    if not np.array_equal(original[protected], candidate[protected]):
        raise ValueError('Protected original triangles changed')
    bounds = verify_patches(vertices, original, candidate, records)
    refusals = {}
    if len(records) < 2:
        raise ValueError('Insufficient changed patches for registered negative controls')
    for name in ('forged_bound', 'overlapping_patches'):
        altered = records.copy()
        if name == 'forged_bound':
            altered[0, 6] += 1
            reason = 'Analytic patch bound mismatch'
        else:
            altered[1, :2] = altered[0, :2]
            reason = 'Overlapping changed patches'
        try:
            verify_patches(vertices, original, candidate, altered)
        except ValueError as error:
            refusals[name] = reason in str(error)
        else:
            refusals[name] = False
    if not all(refusals.values()):
        raise ValueError('Independent proof-refusal controls failed')
    # Verify the actual file fed to the native inspector, not only the NPZ candidate.
    import igl
    off_vertices, off_faces = igl.read_triangle_mesh(str(args.trial/'candidate.off'))
    if not np.array_equal(vertices, off_vertices) or not np.array_equal(candidate, off_faces):
        raise ValueError('Native OFF input differs from assessed NPZ')
    del off_vertices, off_faces
    directed = np.concatenate((candidate[:, [0, 1]], candidate[:, [1, 2]], candidate[:, [2, 0]]))
    keys = np.minimum(directed[:, 0], directed[:, 1])*len(vertices) + np.maximum(directed[:, 0], directed[:, 1])
    order = np.argsort(keys, kind='stable')
    ordered = keys[order]
    if len(ordered) % 2 or np.any(ordered[::2] != ordered[1::2]) or np.any(ordered[1:-1:2] == ordered[2::2]):
        raise ValueError('Candidate closed edge manifold failed')
    winding = np.sign(directed[:, 1]-directed[:, 0])[order].reshape((-1, 2)).sum(axis=1)
    if np.any(winding):
        raise ValueError('Candidate shared-edge winding failed')
    unique_edges = directed[order[::2]]
    graph = coo_matrix((np.ones(len(unique_edges), bool), (unique_edges[:, 0], unique_edges[:, 1])),
                       shape=(len(vertices), len(vertices))).tocsr()
    components = int(connected_components(graph, directed=False, return_labels=False))
    euler = len(vertices)-len(unique_edges)+len(candidate)
    before, after = quality(vertices, original), quality(vertices, candidate)
    native = json.loads((args.trial/'candidate-native.json').read_text())
    reduction = 1-after['bad_triangles']/before['bad_triangles']
    checks = {'unchanged_vertices': True, 'unchanged_protected_triangles': True,
              'disjoint_patch_bound_under_0p01mm': bool(len(bounds)) and bool(np.all(bounds <= .01)),
              'same_topology': components == 1 and euler == -1288,
              'no_zero_area_faces': after['zero_area_faces'] == 0,
              'native_no_intersections': native.get('intersection_pairs') == 0 and native.get('exit_code') == 0,
              'relative_volume': abs(after['signed_volume_mm3']/before['signed_volume_mm3']-1) <= .0001,
              'bad_triangle_reduction_at_least_half': reduction >= .5}
    args.output.mkdir(parents=True)
    report = {'before': before, 'after': after, 'flips': len(records),
              'maximum_independent_patch_bound_mm': float(bounds.max()),
              'components': components, 'euler_characteristic': euler,
              'protected_triangles': len(protected), 'refusal_controls': refusals,
              'bad_triangle_reduction_fraction': reduction, 'checks': checks,
              'accepted_for_volume_meshing': all(checks.values()),
              'native_input_sha256': sha(args.trial/'candidate.off'),
              'native_report_sha256': sha(args.trial/'candidate-native.json'),
              'source_sha256': sha(__file__), 'physical_acceptance': False,
              'manufacturing_authorized': False,
              'bound_scope': 'Double-precision analytic corresponding-point bound on convex, face-disjoint quads; not interval-arithmetic certification or scan-to-specimen metrology.'}
    with (args.output/'verification.json').open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
