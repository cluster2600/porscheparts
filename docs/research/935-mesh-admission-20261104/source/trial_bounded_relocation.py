"""One fixed-connectivity tangent relocation pass on the frozen study envelope."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


SOLID_HASH = 'fa2f082be38f50fcd8e00b8f384d9824a22bf1d7fcba6aa88472a10c82a4831a'
MASK_HASH = 'f9172eabbabd4ea979c93b47afa72f3952feb325daf5c95045c3a5ca6b43b6e2'
INSPECTOR_HASH = '3e7917f938055267516032069c833481d5fd0bcad4078778f81a8ec84edb65b4'
HELPER_HASH = '57a29abf66e66f59e5eb8926fdf0dd75a3880e57928f9d28dd587a27d7d96c92'
BOUND = .0099
THRESHOLD = .01


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def quality(points):
    a, b = points[..., 1, :] - points[..., 0, :], points[..., 2, :] - points[..., 0, :]
    return 2*np.sqrt(3)*np.linalg.norm(np.cross(a, b), axis=-1) / np.sum(a*a+b*b+(a-b)**2, axis=-1)


def gradient_at_first(points):
    a, b, c = points[:, 0], points[:, 1], points[:, 2]
    cross = np.cross(b-a, c-a)
    area2 = np.linalg.norm(cross, axis=1)
    normal = cross/area2[:, None]
    denominator = np.sum((a-b)**2+(b-c)**2+(c-a)**2, axis=1)
    return (2*np.sqrt(3)/denominator)[:, None] * (
        np.cross(b-c, normal) - (area2/denominator)[:, None]*2*(2*a-b-c))


def locked_vertices(vertices, faces, protected):
    points = vertices[faces]
    cross = np.cross(points[:, 1]-points[:, 0], points[:, 2]-points[:, 0])
    lengths = np.linalg.norm(cross, axis=1)
    if np.any(lengths <= 0):
        raise ValueError('Degenerate parent refused')
    normal = cross/lengths[:, None]
    directed = np.concatenate((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]))
    keys = directed.min(1)*len(vertices)+directed.max(1)
    order = np.argsort(keys, kind='stable')
    ordered = keys[order]
    if len(ordered) % 2 or np.any(ordered[::2] != ordered[1::2]) or np.any(ordered[1:-1:2] == ordered[2::2]):
        raise ValueError('Closed two-face edge incidence required')
    winding = np.sign(directed[:, 1]-directed[:, 0])[order].reshape(-1, 2).sum(1)
    if np.any(winding):
        raise ValueError('Parent winding refused')
    pairs = np.tile(np.arange(len(faces)), 3)[order].reshape(-1, 2)
    protected_mask = np.zeros(len(faces), bool)
    protected_mask[protected] = True
    locked = protected_mask[pairs].any(1) | (
        np.einsum('ij,ij->i', normal[pairs[:, 0]], normal[pairs[:, 1]]) < np.cos(np.deg2rad(30)))
    locked_keys = ordered[::2][locked]
    mask = np.zeros(len(vertices), bool)
    mask[locked_keys//len(vertices)] = True
    mask[locked_keys % len(vertices)] = True
    return mask, int(locked.sum()), cross


def relocate(vertices, faces, locked, bound):
    """Deterministic single visit; two fixed step lengths, no connectivity edits."""
    result = vertices.copy()
    points = vertices[faces]
    cross = np.cross(points[:, 1]-points[:, 0], points[:, 2]-points[:, 0])
    initial = quality(points)
    current = initial.copy()
    vertex_normals = np.zeros_like(vertices)
    for i in range(3):
        np.add.at(vertex_normals, faces[:, i], cross)
    norm = np.linalg.norm(vertex_normals, axis=1)
    vertex_normals[norm > 0] /= norm[norm > 0, None]
    ids = faces.ravel()
    order = np.argsort(ids, kind='stable')
    offsets = np.concatenate(([0], np.cumsum(np.bincount(ids, minlength=len(vertices)))))
    incident = np.repeat(np.arange(len(faces)), 3)[order]
    bad = initial < THRESHOLD
    candidates = np.unique(faces[bad])
    candidates = candidates[~locked[candidates] & (norm[candidates] > 0)]
    vertex_minimum = np.ones(len(vertices))
    for i in range(3):
        np.minimum.at(vertex_minimum, faces[:, i], initial)
    candidates = candidates[np.lexsort((candidates, vertex_minimum[candidates]))]
    moved = []
    for vertex in candidates:
        rows = incident[offsets[vertex]:offsets[vertex+1]]
        oldq = current[rows]
        bad_local = oldq < THRESHOLD
        if not bad_local.any():
            continue
        patch = result[faces[rows]]
        columns = np.argmax(faces[rows] == vertex, axis=1)
        rotated = patch[np.arange(len(rows))[:, None], (columns[:, None]+np.arange(3)) % 3]
        gradients = gradient_at_first(rotated[bad_local])
        gradients -= (gradients@vertex_normals[vertex])[:, None]*vertex_normals[vertex]
        total = ((THRESHOLD-oldq[bad_local])[:, None]*gradients).sum(0)
        directions = np.concatenate((gradients, total[None, :]))
        lengths = np.linalg.norm(directions, axis=1)
        directions = directions[lengths > 1e-15]/lengths[lengths > 1e-15, None]
        if not len(directions):
            continue
        positions = vertices[vertex]+np.concatenate((bound*directions, .5*bound*directions))
        patches = np.broadcast_to(patch, (len(positions),)+patch.shape).copy()
        patches[:, np.arange(len(rows)), columns] = positions[:, None, :]
        newq = quality(patches)
        new_cross = np.cross(patches[:, :, 1]-patches[:, :, 0], patches[:, :, 2]-patches[:, :, 0])
        orientation = np.einsum('kij,ij->ki', new_cross, cross[rows]) > 0
        admissible = orientation.all(1)
        # No existing bad face may worsen; no previously good face may cross the gate.
        admissible &= (newq[:, bad_local] >= oldq[bad_local]-1e-12).all(1)
        admissible &= (newq[:, ~bad_local] >= THRESHOLD).all(1)
        old_deficit = np.sum(np.maximum(THRESHOLD-oldq, 0)**2)
        deficits = np.sum(np.maximum(THRESHOLD-newq, 0)**2, axis=1)
        admissible &= deficits < old_deficit-1e-16
        choices = np.flatnonzero(admissible)
        if not len(choices):
            continue
        bad_counts = (newq[choices] < THRESHOLD).sum(1)
        best = choices[np.lexsort((choices, deficits[choices], bad_counts))[0]]
        result[vertex] = positions[best]
        current[rows] = newq[best]
        moved.append(int(vertex))
    return result, np.asarray(moved, np.int64), len(candidates)


def controls():
    equilateral = np.array([[[0, 0, 0], [1, 0, 0], [.5, np.sqrt(3)/2, 0]]])
    triangle = np.array([[[.2, .3, .1], [1., 0, 0], [0, 1., 0]]])
    analytic = gradient_at_first(triangle)[0]
    numerical = []
    for axis in range(3):
        plus, minus = triangle.copy(), triangle.copy()
        plus[0, 0, axis] += 1e-6
        minus[0, 0, axis] -= 1e-6
        numerical.append(float((quality(plus)[0]-quality(minus)[0])/2e-6))
    vertices = np.array([[-1, 0, 0], [1, 0, 0], [1, 1, 0], [-1, 1, 0], [0, .001, 0.]])
    faces = np.array([[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]])
    lock = np.array([True, True, True, True, False])
    candidate, moved, count = relocate(vertices, faces, lock, BOUND)
    checks = {
        'equilateral_quality': bool(abs(quality(equilateral)[0]-1) < 1e-14),
        'analytic_gradient_matches_finite_difference': bool(np.max(np.abs(analytic-numerical)) < 1e-8),
        'skinny_fan_actually_changes': moved.tolist() == [4] and count == 1,
        'skinny_fan_clears_quality_gate': bool(np.all(quality(candidate[faces]) >= THRESHOLD)),
        'witness_locked_coordinates_exact': bool(np.array_equal(vertices[lock], candidate[lock])),
        'witness_motion_within_bound': bool(np.linalg.norm(candidate-vertices, axis=1).max() <= BOUND+1e-14),
        'witness_tangent_motion': bool(np.array_equal(vertices[:, 2], candidate[:, 2])),
    }
    if not all(checks.values()):
        raise ValueError('Relocation controls failed: '+json.dumps(checks))
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('solid', 'protected', 'inspector', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('Existing relocation output refused')
    helper_path = Path(__file__).with_name('trial_planar_flips.py')
    for path, expected in ((args.solid, SOLID_HASH), (args.protected, MASK_HASH),
                           (args.inspector, INSPECTOR_HASH), (helper_path, HELPER_HASH)):
        if sha(path) != expected:
            raise SystemExit('Registered input/runtime hash mismatch: '+path.name)
    spec = importlib.util.spec_from_file_location('retained_relocation_helpers', helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    args.output.mkdir(parents=True)
    save(args.output/'plan.json', {
        'input_sha256': SOLID_HASH, 'protection_sha256': MASK_HASH,
        'inspector_sha256': INSPECTOR_HASH, 'helper_sha256': HELPER_HASH,
        'source_sha256': sha(__file__), 'passes': 1,
        'candidate_vertex_bound_mm': BOUND, 'admission_bound_mm': .01,
        'relative_volume_change_limit': .0001, 'bad_triangle_reduction_min_fraction': .5,
        'fixed_connectivity': True, 'locked_edges': 'Protected-face edges and original dihedrals over 30 degrees; all endpoints fixed',
        'operator': 'Worst-first single visit; projected local quality gradients; full/half fixed bound; no worsening bad faces or new bad faces',
        'upstream_admission': 'Reconstructed assembly study only; inferred surfaces and missing specimen interfaces remain',
        'physical_acceptance': False, 'manufacturing_authorized': False})
    save(args.output/'controls.json', controls())
    with np.load(args.solid, allow_pickle=False) as data:
        used, inverse = np.unique(data['boundary'], return_inverse=True)
        vertices, faces = data['nodes'][used], inverse.reshape(-1, 3)
    protected = np.load(args.protected, allow_pickle=False)
    helper.write_off(args.output/'parent.off', vertices, faces)
    if not helper.inspect(args.inspector, args.output/'parent.off', args.output/'parent-native.json'):
        raise SystemExit('Parent native audit rejected; no vertex motion')
    locked, edges, cross = locked_vertices(vertices, faces, protected)
    before = helper.quality(vertices, faces)
    q = quality(vertices[faces])
    bad = q < THRESHOLD
    immobile_bad = int((bad & locked[faces].all(1)).sum())
    ceiling = 1-immobile_bad/int(bad.sum())
    save(args.output/'preflight.json', {'locked_edges': edges, 'locked_vertices': int(locked.sum()),
        'initial_bad_faces': int(bad.sum()), 'bad_faces_all_vertices_locked': immobile_bad,
        'maximum_possible_reduction_fraction_fixed_connectivity': ceiling})
    if ceiling < .5:
        raise SystemExit('Vertex-lock quality ceiling rejects operation')
    started = time.monotonic()
    candidate, moved, considered = relocate(vertices, faces, locked, BOUND)
    elapsed = time.monotonic()-started
    np.savez(args.output/'candidate.npz', vertices=candidate, triangles=faces)
    np.save(args.output/'moved-vertex-ids.npy', moved, allow_pickle=False)
    helper.write_off(args.output/'candidate.off', candidate, faces)
    native = helper.inspect(args.inspector, args.output/'candidate.off', args.output/'candidate-native.json')
    after = helper.quality(candidate, faces)
    displacement = np.linalg.norm(candidate-vertices, axis=1)
    candidate_cross = np.cross(candidate[faces[:, 1]]-candidate[faces[:, 0]], candidate[faces[:, 2]]-candidate[faces[:, 0]])
    reduction = 1-after['below_0p01']/before['below_0p01']
    checks = {'native_geometry': bool(native), 'locked_vertices_exact': bool(np.array_equal(vertices[locked], candidate[locked])),
        'bounded_motion': bool(displacement.max() <= .01),
        'positive_parent_normal_dot': bool(np.all(np.einsum('ij,ij->i', cross, candidate_cross) > 0)),
        'relative_volume': bool(abs(after['signed_volume_mm3']/before['signed_volume_mm3']-1) <= .0001),
        'quality_reduction': bool(reduction >= .5)}
    save(args.output/'assessment.json', {'before': before, 'after': after, 'moved_vertices': len(moved),
        'considered_vertices': considered, 'maximum_displacement_mm': float(displacement.max()),
        'bad_triangle_reduction_fraction': reduction, 'relocation_seconds': elapsed, 'checks': checks,
        'accepted_for_next_study_stage': all(checks.values()), 'independent_verification_pending': True,
        'physical_acceptance': False, 'manufacturing_authorized': False})
    print(json.dumps({'moved_vertices': len(moved), 'reduction': reduction, 'checks': checks}), flush=True)


if __name__ == '__main__':
    main()
