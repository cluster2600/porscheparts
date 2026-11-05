"""Independent fixed-triangle relocation, lock, file and quality verification."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def face_data(vertices, faces):
    a, b, c = (vertices[faces[:, i]] for i in range(3))
    u, v = b-a, c-a
    # Explicit determinant components, separately implemented from the driver.
    cross = np.column_stack((u[:, 1]*v[:, 2]-u[:, 2]*v[:, 1],
                             u[:, 2]*v[:, 0]-u[:, 0]*v[:, 2],
                             u[:, 0]*v[:, 1]-u[:, 1]*v[:, 0]))
    area2 = np.sqrt(np.sum(cross**2, axis=1))
    perimeter_squared = np.sum((a-b)**2+(b-c)**2+(c-a)**2, axis=1)
    quality = np.sqrt(12.)*area2/perimeter_squared
    volume = np.sum(a[:, 0]*(b[:, 1]*c[:, 2]-b[:, 2]*c[:, 1]) +
                    a[:, 1]*(b[:, 2]*c[:, 0]-b[:, 0]*c[:, 2]) +
                    a[:, 2]*(b[:, 0]*c[:, 1]-b[:, 1]*c[:, 0]))/6
    return cross, quality, float(volume)


def derive_locks(vertices, faces, protected, cross):
    pairs = np.stack((faces, np.roll(faces, -1, axis=1)), axis=2).reshape(-1, 2)
    keys = pairs.min(1)*len(vertices)+pairs.max(1)
    order = np.argsort(keys, kind='stable')
    keys = keys[order]
    if len(keys) % 2 or np.any(keys[::2] != keys[1::2]) or np.any(keys[1:-1:2] == keys[2::2]):
        raise ValueError('Original edge incidence refused')
    winding = np.sign(pairs[:, 1]-pairs[:, 0])[order].reshape(-1, 2).sum(1)
    if np.any(winding):
        raise ValueError('Original winding refused')
    face_pairs = np.repeat(np.arange(len(faces)), 3)[order].reshape(-1, 2)
    normals = cross/np.sqrt((cross**2).sum(1))[:, None]
    cosine = (normals[face_pairs[:, 0]]*normals[face_pairs[:, 1]]).sum(1)
    protected_mask = np.zeros(len(faces), bool)
    protected_mask[protected] = True
    edges_locked = (cosine < np.sqrt(3)/2) | protected_mask[face_pairs].any(1)
    endpoints = pairs[order[::2]][edges_locked]
    locked = np.zeros(len(vertices), bool)
    locked[endpoints.ravel()] = True
    return locked, int(edges_locked.sum())


def validate_motion(original, candidate, faces, actual_faces, locked, limit=.01):
    if candidate.shape != original.shape or not np.isfinite(candidate).all():
        raise ValueError('Invalid vertex array')
    if not np.array_equal(faces, actual_faces):
        raise ValueError('Connectivity changed')
    if not np.array_equal(original[locked], candidate[locked]):
        raise ValueError('Locked coordinate changed')
    bound = float(np.linalg.norm(candidate-original, axis=1).max())
    if bound > limit:
        raise ValueError('Vertex displacement bound exceeded')
    oldcross, oldq, oldvolume = face_data(original, faces)
    newcross, newq, newvolume = face_data(candidate, faces)
    if np.any((oldcross*newcross).sum(1) <= 0):
        raise ValueError('Triangle orientation reversed or collapsed')
    return bound, oldq, newq, oldvolume, newvolume


def controls():
    vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0.]], float)
    faces = np.array([[0, 1, 2]])
    locked = np.array([True, False, False])
    checks = {}
    for name, reason in [('changed_connectivity', 'Connectivity changed'),
                         ('changed_locked_coordinate', 'Locked coordinate changed'),
                         ('excess_motion', 'Vertex displacement bound exceeded'),
                         ('reversed_triangle', 'Triangle orientation reversed')]:
        candidate, candidate_faces = vertices.copy(), faces.copy()
        limit = .01
        if name == 'changed_connectivity':
            candidate_faces = faces[:, ::-1]
        elif name == 'changed_locked_coordinate':
            candidate[0, 0] += .001
        elif name == 'excess_motion':
            candidate[1, 0] += .02
        else:
            candidate[[1, 2]] = candidate[[2, 1]]
            limit = 2.
        try:
            validate_motion(vertices, candidate, faces, candidate_faces, locked, limit)
        except ValueError as error:
            checks[name] = reason in str(error)
        else:
            checks[name] = False
    # A nonuniform vertex displacement is bounded everywhere by barycentric convexity.
    candidate = vertices+np.array([[0, 0, 0], [.003, -.002, .001], [-.004, 0, .002]])
    weights = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1], [.2, .3, .5]])
    maximum = np.linalg.norm(candidate-vertices, axis=1).max()
    checks['barycentric_sample_bound'] = bool(np.all(np.linalg.norm(weights@(candidate-vertices), axis=1) <= maximum+1e-15))
    if not all(checks.values()):
        raise ValueError('Independent relocation controls failed')
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('trial', 'solid', 'protected', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('Existing relocation verification refused')
    plan = json.loads((args.trial/'plan.json').read_text())
    if sha(args.solid) != plan['input_sha256'] or sha(args.protected) != plan['protection_sha256']:
        raise SystemExit('Frozen input mismatch')
    with np.load(args.solid, allow_pickle=False) as data:
        used, inverse = np.unique(data['boundary'], return_inverse=True)
        vertices, faces = data['nodes'][used], inverse.reshape(-1, 3)
    with np.load(args.trial/'candidate.npz', allow_pickle=False) as data:
        candidate, actual_faces = data['vertices'], data['triangles']
    protected = np.load(args.protected, allow_pickle=False)
    cross, _, _ = face_data(vertices, faces)
    locked, edge_count = derive_locks(vertices, faces, protected, cross)
    bound, oldq, newq, oldvolume, newvolume = validate_motion(vertices, candidate, faces, actual_faces, locked)
    import igl
    off_vertices, off_faces = igl.read_triangle_mesh(str(args.trial/'candidate.off'))
    if not np.array_equal(candidate, off_vertices) or not np.array_equal(faces, off_faces):
        raise ValueError('Actual native OFF differs from candidate NPZ')
    moved = np.flatnonzero(np.any(candidate != vertices, axis=1))
    declared = np.load(args.trial/'moved-vertex-ids.npy', allow_pickle=False)
    if not np.array_equal(moved, np.sort(declared)):
        raise ValueError('Changed-vertex provenance mismatch')
    parent_native = json.loads((args.trial/'parent-native.json').read_text())
    native = json.loads((args.trial/'candidate-native.json').read_text())
    before, after = int((oldq < .01).sum()), int((newq < .01).sum())
    reduction = 1-after/before
    checks = {'locked_coordinates_exact': bool(np.array_equal(candidate[locked], vertices[locked])),
        'protected_triangles_exact': bool(np.array_equal(candidate[faces[protected]], vertices[faces[protected]])),
        'same_connectivity': bool(np.array_equal(faces, actual_faces)), 'whole_surface_correspondence_bound': bound <= .01,
        'no_new_bad_triangles': bool(np.all(newq[oldq >= .01] >= .01)),
        'no_bad_triangle_worsened': bool(np.all(newq[oldq < .01] >= oldq[oldq < .01]-1e-10)),
        'native_parent_and_candidate_pass': all(
            item['exit_code'] == 0 and item['intersection_check_executed']
            and item['intersection_pairs'] == 0 and item['degenerate_faces'] == 0
            and item['closed'] and item['valid_polygon_mesh']
            and item['vertices'] == len(vertices) and item['faces'] == len(faces)
            for item in (parent_native, native)),
        'relative_volume': abs(newvolume/oldvolume-1) <= .0001,
        'bad_triangle_reduction_at_least_half': reduction >= .5}
    report = {'scope': 'Fixed-connectivity reconstructed assembly study, not acquired scan or accepted physical head',
        'locked_edges': edge_count, 'locked_vertices': int(locked.sum()), 'moved_vertices': len(moved),
        'before': {'bad_triangles': before, 'minimum_quality': float(oldq.min()), 'signed_volume_mm3': oldvolume},
        'after': {'bad_triangles': after, 'minimum_quality': float(newq.min()), 'signed_volume_mm3': newvolume},
        'maximum_vertex_displacement_mm': bound, 'bad_triangle_reduction_fraction': reduction,
        'surface_bound_proof': 'Same indexed triangle and barycentric coordinates; norm of weighted displacement <= weighted vertex norms <= maximum vertex norm; two directions use the same correspondence',
        'bound_limit': 'Double-precision coordinate bound; not interval certification, true specimen fidelity, surface-normal or thickness bound',
        'checks': checks, 'controls': controls(), 'accepted_for_volume_meshing': all(checks.values()),
        'candidate_npz_sha256': sha(args.trial/'candidate.npz'), 'native_off_sha256': sha(args.trial/'candidate.off'),
        'native_report_sha256': sha(args.trial/'candidate-native.json'), 'source_sha256': sha(__file__),
        'physical_acceptance': False, 'manufacturing_authorized': False}
    save(args.output, report)
    print(json.dumps({'checks': checks, 'reduction': reduction, 'moved_vertices': len(moved)}), flush=True)


if __name__ == '__main__':
    main()
