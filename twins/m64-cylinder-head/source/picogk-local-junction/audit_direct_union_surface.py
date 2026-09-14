#!/usr/bin/env python3
"""Separate exact-face counter-audit; never changes the direct witness STL."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np
from audit_surface_topology import (audit_arrays, exact_zero_area_mask,
                                    load_binary_stl, sha, write_private_new_json)


def oriented_face_multiset(triangles):
    # Numerical coordinate equality, including +0 == -0; cyclic rotations only.
    # Reversing the winding does NOT make an identical oriented face.
    return Counter(min(tuple(map(tuple, face)), tuple(map(tuple, np.roll(face, 1, axis=0))),
                       tuple(map(tuple, np.roll(face, 2, axis=0)))) for face in triangles)


def roi_difference(before, after, low, high):
    old, new = oriented_face_multiset(before), oriented_face_multiset(after)
    rows = {}
    for name, difference in (('removed', old - new), ('added', new - old)):
        if difference:
            faces = np.asarray(list(difference), dtype=np.float64)
            inside = np.all((faces >= low) & (faces <= high), axis=(1, 2))
            outside_count = sum(count for fits, count in zip(inside, difference.values()) if not fits)
            bounds = [faces.min(axis=(0, 1)).tolist(), faces.max(axis=(0, 1)).tolist()]
        else:
            outside_count, bounds = 0, None
        rows[name] = {'unmatched_oriented_faces': sum(difference.values()),
                      'unmatched_faces_not_entirely_contained_in_ROI': outside_count,
                      'unmatched_face_bounds': bounds}
    rows['all_changed_triangle_supports_inside_convex_ROI'] = all(
        rows[name]['unmatched_faces_not_entirely_contained_in_ROI'] == 0 for name in ('removed', 'added'))
    rows['failure_is_not_itself_a_measure_of_continuous_shape_displacement'] = True
    rows['underlying_SDF_or_BRep_invariance_proved'] = False
    return rows


def normalize_exact_zero(triangles):
    vertices = triangles.reshape(-1, 3)
    faces = np.arange(len(vertices)).reshape(-1, 3)
    zero = exact_zero_area_mask(vertices, faces)
    retained = triangles[~zero]
    return retained, {
        'removed_face_indices_zero_based': np.flatnonzero(zero).tolist(),
        'removed_exact_dyadic_zero_area_faces': int(zero.sum()),
        'nonzero_faces_removed': 0, 'vertex_displacement': 0,
        'retained_oriented_triangles_sha256': hashlib.sha256(
            np.asarray(retained, dtype='<f8').tobytes()).hexdigest(),
        'derived_mesh_written': False,
        'topology': audit_arrays(retained.reshape(-1, 3), np.arange(retained.size // 3).reshape(-1, 3)),
    }


def run(directory, output):
    native_path = directory / 'run-report.json'
    native = json.loads(native_path.read_text())
    if (native['schema'] != 'm64-picogk-local-junction-direct-union-witness/v1' or
            native['voxel_scan_units'] != 0.2 or native['private_head_processed'] is not False):
        raise ValueError('Only the recorded 0.2 direct synthetic witness is accepted')
    native_sha, source_sha = sha(native_path), sha(Path(__file__))
    originals, normalized, rows = {}, {}, {}
    for name in ('before', 'after', 'added'):
        originals[name], digest = load_binary_stl(directory / (name + '.stl'))
        if digest != native['exports'][name]['sha256']:
            raise ValueError('Source STL changed from native report')
        normalized[name], row = normalize_exact_zero(originals[name])
        rows[name] = {'source_STL_sha256': digest, **row}
    # Exact synthetic mask in the executed program, not an inferred head ROI.
    roi = roi_difference(normalized['before'], normalized['after'], (-8, -3, -8), (8, 3, 8))
    if (native_sha != sha(native_path) or source_sha != sha(Path(__file__)) or
            any(sha(directory / (name + '.stl')) != row['source_STL_sha256'] for name, row in rows.items())):
        raise ValueError('An input or source changed during the audit')
    report = {
        'schema': 'm64-picogk-direct-union-exact-surface-counter-audit/v1',
        'native_report_sha256': native_sha, 'source_sha256': source_sha,
        'topology_auditor_sha256': sha(Path(__file__).with_name('audit_surface_topology.py')),
        'numpy_version': np.__version__, 'normalized_in_memory_only': rows,
        'ROI_low': [-8, -3, -8], 'ROI_high': [8, 3, 8], 'normalized_mesh_ROI_check': roi,
        'original_raw_rejection_overridden': False,
        'normalization_is_not_physical_validation': True,
        'private_head_processed': False, 'finer_resolution_executed': False,
        'manufacturing_authorized': False,
    }
    write_private_new_json(output, report)
    print(json.dumps({'output': str(output), 'normalized_combinatorial_screens': {
        name: row['topology']['closed_oriented_combinatorial_surface_screen_pass'] for name, row in rows.items()},
        'ROI': roi}, indent=2))
    return 0 if roi['all_changed_triangle_supports_inside_convex_ROI'] and all(
        row['topology']['closed_oriented_combinatorial_surface_screen_pass'] for row in rows.values()) else 3


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.directory, args.output))
