"""One non-overlapping quad-flip pass with an analytic surface-distance bound."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def qvalues(vertices, faces):
    p = vertices[faces]
    a, b = p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]
    return 2 * np.sqrt(3) * np.linalg.norm(np.cross(a, b), axis=1) / np.sum(a*a + b*b + (a-b)**2, axis=1)


def certificate(points):
    # Old diagonal a--b, old oriented faces abc and bad; new faces cad and dbc.
    a, b, c, d = points
    e, h = b-a, d-c
    normal = np.cross(b-a, c-a) + np.cross(a-b, d-b)
    scale = max(np.linalg.norm(e), np.linalg.norm(h))
    if not scale or np.linalg.norm(normal) < 1e-12 * scale**2:
        return None
    normal /= np.linalg.norm(normal)
    x = e / np.linalg.norm(e)
    y = np.cross(normal, x)
    y /= np.linalg.norm(y)
    matrix = np.array([[e@x, -h@x], [e@y, -h@y]])
    if abs(np.linalg.det(matrix)) < 1e-12 * scale**2:
        return None
    t, s = np.linalg.solve(matrix, np.array([(c-a)@x, (c-a)@y]))
    if not (1e-8 < t < 1-1e-8 and 1e-8 < s < 1-1e-8):
        return None
    # All four constituent projected triangles must have consistent nonzero orientation.
    for triangle in (points[[0, 1, 2]], points[[1, 0, 3]], points[[2, 0, 3]], points[[3, 1, 2]]):
        if np.dot(np.cross(triangle[1]-triangle[0], triangle[2]-triangle[0]), normal) <= 1e-12 * scale**2:
            return None
    delta = a + t*e - (c + s*h)
    if np.linalg.norm(np.cross(delta, normal)) > 1e-10 * scale:
        return None
    return float(np.linalg.norm(delta)), float(t), float(s)


def controls():
    checks = {}
    for height in (0., .01, .2):
        p = np.array([[0, 0, 0], [1, 1, height], [0, 1, 0], [1, 0, 0]], float)
        result = certificate(p)
        expected = height / (2 * np.sqrt(1 + height**2 / 2))
        checks[f'known_twist_{height:g}'] = result is not None and abs(result[0]-expected) < 1e-12
    p = np.array([[0, 0, 0], [1, 1, 0], [.4, .4, 0], [1, 0, 0]], float)
    checks['degenerate_chart_refused'] = certificate(p) is None
    concave = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [-.2, -.1, 0]], float)
    checks['concave_chart_refused'] = certificate(concave) is None
    planar = np.array([[0, 0, 0], [2, 1, 0], [2, 0, 0], [0, .1, 0]], float)
    old = qvalues(planar, np.array([[0, 1, 2], [1, 0, 3]]))
    new = qvalues(planar, np.array([[2, 0, 3], [3, 1, 2]]))
    # Reverse both orientations for this coordinate arrangement to exercise a positive chart.
    if certificate(planar) is None:
        planar = planar[[1, 0, 2, 3]]
    checks['planar_flip_has_zero_distance_bound'] = certificate(planar) is not None and certificate(planar)[0] < 1e-12
    checks['asymmetric_quad_quality_improves'] = new.min() > old.min()
    if not all(checks.values()):
        raise ValueError('Quad-bound controls failed: ' + json.dumps(checks))
    return {name: bool(value) for name, value in checks.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('solid', 'protected', 'inspector', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('Existing quad-flip trial refused')
    if sha(args.solid) != 'fa2f082be38f50fcd8e00b8f384d9824a22bf1d7fcba6aa88472a10c82a4831a':
        raise SystemExit('Frozen study solid mismatch')
    if sha(args.protected) != 'f9172eabbabd4ea979c93b47afa72f3952feb325daf5c95045c3a5ca6b43b6e2':
        raise SystemExit('Frozen protection mask mismatch')
    helper_path = Path(__file__).with_name('trial_planar_flips.py')
    spec = importlib.util.spec_from_file_location('retained_mesh_helpers', helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    args.output.mkdir(parents=True)
    plan = {'input_sha256': sha(args.solid), 'protection_sha256': sha(args.protected),
            'source_sha256': sha(__file__), 'helper_sha256': sha(helper_path),
            'inspector_sha256': sha(args.inspector), 'passes': 1,
            'selection': 'Only edges incident to quality<0.01 faces; deterministic maximal disjoint face-pair selection',
            'candidate_bound_limit_mm': .0099, 'admission_bound_limit_mm': .01,
            'relative_volume_change_limit': .0001, 'bad_triangle_reduction_min_fraction': .5,
            'identical_vertices_and_protected_face_rows': True,
            'upstream_admission': 'Closed reconstructed assembly study only; inferred surfaces and unknown physical interfaces persist',
            'physical_acceptance': False, 'manufacturing_authorized': False}
    save(args.output/'plan.json', plan)
    save(args.output/'controls.json', controls())
    with np.load(args.solid, allow_pickle=False) as data:
        used, inverse = np.unique(data['boundary'], return_inverse=True)
        vertices, faces = data['nodes'][used], inverse.reshape((-1, 3))
    protected_ids = np.load(args.protected, allow_pickle=False)
    protected = np.zeros(len(faces), bool)
    protected[protected_ids] = True
    helper.write_off(args.output/'parent.off', vertices, faces)
    if not helper.inspect(args.inspector, args.output/'parent.off', args.output/'parent-native.json'):
        raise SystemExit('Parent native audit rejected; no flips executed')
    quality = qvalues(vertices, faces)
    before = helper.quality(vertices, faces)
    started = time.monotonic()
    edges = np.sort(np.concatenate((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]])), axis=1)
    keys = edges[:, 0] * len(vertices) + edges[:, 1]
    order = np.argsort(keys, kind='stable')
    ordered = keys[order]
    if len(ordered) % 2 or np.any(ordered[::2] != ordered[1::2]) or np.any(ordered[1:-1:2] == ordered[2::2]):
        raise SystemExit('Parent does not have exactly two faces per edge')
    unique_keys = ordered[::2]
    pairs = (order.reshape((-1, 2)) % len(faces))
    eligible = ((quality[pairs] < .01).any(axis=1) & ~protected[pairs].any(axis=1))
    candidates = []
    for position in np.flatnonzero(eligible):
        row_a, row_b = map(int, pairs[position])
        a, b = map(int, edges[order[position*2]])
        first, second = faces[row_a], faces[row_b]
        i = int(np.flatnonzero(first == a)[0])
        if first[(i+1) % 3] != b:
            a, b = b, a
        j = int(np.flatnonzero(second == b)[0])
        if second[(j+1) % 3] != a:
            raise ValueError('Parent has inconsistent shared-edge winding')
        c = int(first[(first != a) & (first != b)][0])
        d = int(second[(second != a) & (second != b)][0])
        new_key = min(c, d)*len(vertices) + max(c, d)
        location = np.searchsorted(unique_keys, new_key)
        if c == d or (location < len(unique_keys) and unique_keys[location] == new_key):
            continue
        bound = certificate(vertices[[a, b, c, d]])
        if bound is None or bound[0] > .0099:
            continue
        replacement = np.array([[c, a, d], [d, b, c]])
        new_q = qvalues(vertices, replacement)
        old_q = quality[[row_a, row_b]]
        improvement = int((old_q < .01).sum()) - int((new_q < .01).sum())
        if improvement < 1 or new_q.min() <= old_q.min()*(1+1e-6):
            continue
        candidates.append((improvement, float(new_q.min()-old_q.min()), row_a, row_b,
                           a, b, c, d, bound[0], bound[1], bound[2], new_key))
    candidates.sort(key=lambda item: (-item[0], -item[1], item[2], item[3]))
    touched = np.zeros(len(faces), bool)
    new_edges = set()
    output = faces.copy()
    accepted = []
    for item in candidates:
        _, _, row_a, row_b, a, b, c, d, bound, t, s, new_key = item
        if touched[row_a] or touched[row_b] or new_key in new_edges:
            continue
        output[row_a], output[row_b] = [c, a, d], [d, b, c]
        touched[[row_a, row_b]] = True
        new_edges.add(new_key)
        accepted.append([row_a, row_b, a, b, c, d, bound, t, s])
    np.savez_compressed(args.output/'candidate.npz', vertices=vertices, triangles=output)
    np.savez_compressed(args.output/'flip-provenance.npz', records=np.asarray(accepted, float).reshape((-1, 9)))
    helper.write_off(args.output/'candidate.off', vertices, output)
    native = helper.inspect(args.inspector, args.output/'candidate.off', args.output/'candidate-native.json')
    after = helper.quality(vertices, output)
    reduction = 1-after['below_0p01']/before['below_0p01']
    checks = {'native_geometry': native, 'protected_rows_exact': bool(np.array_equal(output[protected_ids], faces[protected_ids])),
              'same_face_count': len(output) == len(faces), 'quality_reduction': reduction >= .5,
              'relative_volume': abs(after['signed_volume_mm3']/before['signed_volume_mm3']-1) <= .0001,
              'all_disjoint_patch_bounds': bool(accepted) and max(row[6] for row in accepted) <= .01}
    save(args.output/'assessment.json', {'before': before, 'after': after,
         'eligible_edges': int(eligible.sum()), 'qualified_candidates': len(candidates),
         'flips': len(accepted), 'changed_rows': int(touched.sum()), 'bad_triangle_reduction_fraction': reduction,
         'maximum_patch_bound_mm': max((row[6] for row in accepted), default=0),
         'processing_seconds': time.monotonic()-started, 'checks': checks,
         'accepted_for_next_study_stage': False,
         'independent_verification_pending': True, 'physical_acceptance': False, 'manufacturing_authorized': False})
    print(json.dumps({'flips': len(accepted), 'bad_triangles_before': before['below_0p01'],
                      'bad_triangles_after': after['below_0p01'], 'checks': checks}), flush=True)


if __name__ == '__main__':
    main()
