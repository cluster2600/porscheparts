"""Verify actual tetrahedral incidence, preserved surface and study quality."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def canonical_oriented(faces):
    starts = np.argmin(faces, axis=1)
    rotated = faces[np.arange(len(faces))[:, None], (starts[:, None]+np.arange(3)) % 3]
    return rotated[np.lexsort((rotated[:, 2], rotated[:, 1], rotated[:, 0]))]


def boundary_of_tets(tets):
    oriented = tets[:, [[1, 2, 3], [0, 3, 2], [0, 1, 3], [0, 2, 1]]].reshape(-1, 3)
    keys = np.sort(oriented, axis=1)
    order = np.lexsort((keys[:, 2], keys[:, 1], keys[:, 0]))
    keys = keys[order]
    starts = np.flatnonzero(np.concatenate(([True], np.any(keys[1:] != keys[:-1], axis=1))))
    counts = np.diff(np.append(starts, len(keys)))
    if np.any((counts != 1) & (counts != 2)):
        raise ValueError('Nonmanifold tetrahedral face incidence')
    # Every paired interior face must cancel with the opposite orientation.
    inversions = ((oriented[:, 0] > oriented[:, 1]).astype(np.int8) +
                  (oriented[:, 0] > oriented[:, 2]).astype(np.int8) +
                  (oriented[:, 1] > oriented[:, 2]).astype(np.int8))
    signs = (1-2*(inversions % 2))[order]
    paired = starts[counts == 2]
    if np.any(signs[paired]+signs[paired+1]):
        raise ValueError('Interior face winding does not cancel')
    return oriented[order[starts[counts == 1]]], len(paired)


def controls():
    tet = np.array([[0, 1, 2, 3]])
    boundary, count = boundary_of_tets(tet)
    expected = np.array([[1, 2, 3], [0, 3, 2], [0, 1, 3], [0, 2, 1]])
    checks = {'one_tet_outward_boundary': count == 0 and np.array_equal(canonical_oriented(boundary), canonical_oriented(expected))}
    for name, cells, reason in [
        ('same_winding_interior_refused', np.vstack((tet, tet)), 'Interior face winding'),
        ('triple_face_refused', np.vstack((tet, tet, tet)), 'Nonmanifold tetrahedral face')]:
        try:
            boundary_of_tets(cells)
        except ValueError as error:
            checks[name] = reason in str(error)
        else:
            checks[name] = False
    pair = np.array([[0, 1, 2, 3], [0, 2, 1, 4]])
    external, paired = boundary_of_tets(pair)
    checks['two_tets_cancel_one_shared_face'] = paired == 1 and len(external) == 6
    checks['oriented_cycle_invariant'] = np.array_equal(canonical_oriented(expected), canonical_oriented(np.roll(expected, 1, axis=1)))
    checks['orientation_reversal_detected'] = not np.array_equal(canonical_oriented(expected), canonical_oriented(expected[:, ::-1]))
    if not all(checks.values()):
        raise ValueError('Tetrahedral incidence controls failed')
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('mesh', 'surface', 'surface-verification', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('Existing tetrahedral verification refused')
    admission = json.loads(args.surface_verification.read_text())
    if not admission['accepted_for_volume_meshing'] or sha(args.surface) != admission['candidate_npz_sha256']:
        raise SystemExit('Surface admission mismatch')
    helper_path = Path(__file__).with_name('audit_retained_meshes.py')
    if sha(helper_path) != 'c1d93c8018e03c628cda261c16304b0dca26eb575967953e828e9a16cb9f610c':
        raise SystemExit('Retained metric helper hash mismatch')
    spec = importlib.util.spec_from_file_location('retained_tetra_metrics', helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    metric_controls = helper.controls()
    incidence_controls = controls()
    audit = helper.audit(args.mesh)
    with np.load(args.surface, allow_pickle=False) as data:
        vertices, faces = data['vertices'], data['triangles']
    with np.load(args.mesh, allow_pickle=False) as data:
        nodes, tets, declared = data['nodes'], data['tets'], data['boundary']
    if not np.array_equal(nodes[:len(vertices)], vertices):
        raise ValueError('Original boundary coordinates or node mapping changed')
    if not np.array_equal(canonical_oriented(declared), canonical_oriented(faces)):
        raise ValueError('Declared mesh surface differs from admitted oriented surface')
    exterior, paired = boundary_of_tets(tets)
    if not np.array_equal(canonical_oriented(exterior), canonical_oriented(faces)):
        raise ValueError('Actual tetrahedral boundary differs from admitted surface')
    p = vertices[faces]
    surface_volume = float(np.einsum('ij,ij->i', p[:, 0], np.cross(p[:, 1], p[:, 2])).sum()/6)
    relative_volume_error = abs(audit['signed_volume_mm3']/surface_volume-1)
    checks = {'original_surface_coordinates_exact': True, 'declared_oriented_surface_exact': True,
        'actual_tetrahedral_oriented_surface_exact': True, 'interior_faces_cancel': True,
        'all_nodes_used': len(np.unique(tets)) == len(nodes),
        'all_tetrahedra_positive': audit['nonpositive_tetrahedra'] == 0,
        'surface_volume_agreement': relative_volume_error < 1e-8}
    report = {'scope': 'Face-incidence-checked study-volume mesh; not a physical head or engineering-quality acceptance',
        'source_sha256': sha(__file__), 'metric_helper_sha256': sha(helper_path),
        'surface_sha256': sha(args.surface), 'surface_verification_sha256': sha(args.surface_verification),
        'metric_controls': metric_controls, 'incidence_controls': incidence_controls,
        'mesh_audit': audit, 'interior_paired_faces': paired,
        'surface_volume_mm3': surface_volume, 'relative_surface_volume_error': relative_volume_error,
        'checks': checks, 'study_mesh_geometry_passed': all(checks.values()),
        'physics_admitted': False, 'physical_acceptance': False, 'manufacturing_authorized': False,
        'remaining_limit': 'Poor-quality cells, convergence and specimen/material/load/process requirements remain; diagnostic bins are not engineering allowables'}
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'checks': checks, 'tetrahedra': len(tets), 'diagnostic_bins': audit['diagnostic_bins']}), flush=True)


if __name__ == '__main__':
    main()
