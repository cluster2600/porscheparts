#!/usr/bin/env python3
"""Bound one rigid 935 rotor revolution against the retained drive and shroud."""
import argparse
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import time

import numpy as np

from review_surface_contacts import DTYPE, fixtures, load, model, query, sha

SAMPLES = 240
ROUNDING_MARGIN = 1e-4  # Native scan units; numerical reserve, not metrology.


def between_sample_motion(radius, count):
    if not math.isfinite(radius) or radius <= 0 or type(count) is not int or count < 3:
        raise ValueError('Finite radius and at least three phases required')
    return 2 * radius * math.sin(math.pi / (2 * count))


def moving_fixture():
    import fcl
    face = np.array([[0, 1, 2]], dtype=np.int32)
    moving = model(np.array([[1., 0, 0], [2., 0, 0], [1., 1, 0]]), face)
    fixed = model(np.array([[-.5, 1.1, 0], [-.5, 1.3, 0], [-.3, 1.1, 0]]), face)
    before = query(moving, fixed)
    moving.setTransform(fcl.Transform(np.array([[0., -1, 0], [1., 0, 0], [0, 0, 1.]])))
    after = query(moving, fixed)
    moving.setTransform(fcl.Transform(np.eye(3)))
    if before['surface_crossing'] or not after['surface_crossing'] or query(moving, fixed) != before:
        raise ValueError('FCL rigid-transform fixture failed')


def run(native, receipt_sha, output):
    import fcl
    native, output = Path(native), Path(output)
    if output.exists() or output.is_symlink() or not output.parent.is_dir() or sha(native / 'receipt.json') != receipt_sha:
        raise ValueError('Pinned assembly receipt and fresh output required')
    receipt = json.loads((native / 'receipt.json').read_text())
    case = json.loads((native / 'case.json').read_text())
    if (receipt['target'] != '935' or receipt['engine_cylinders'] != 6
            or receipt['scale_verified'] is not False
            or receipt['manufacturing_authorized'] is not False
            or case['shroud']['origin_mm'] != [0, 0, 0]
            or receipt['engine_context_family'] != '935_six_cylinder_packaging_hypothesis_not_exact_engine'):
        raise ValueError('Uncalibrated, Z-axis 935 inspection case required')
    rows = {row['id']: row for row in receipt['components']}
    if len(receipt['components']) != 4 or set(rows) != {
            'engine_context', 'drive_observed', 'rotor_candidate', 'provisional_shroud'}:
        raise ValueError('Expected four component identities')
    controls = fixtures()
    moving_fixture()
    started = time.monotonic()
    objects = {}
    for name in ('rotor_candidate', 'drive_observed', 'provisional_shroud'):
        row = rows[name]
        if Path(row['file']).name != row['file'] or sha(native / row['file']) != row['sha256']:
            raise ValueError('Component changed')
        objects[name] = load(native / row['file'], row['triangles'])
    rotor = np.memmap(native / rows['rotor_candidate']['file'], mode='r', dtype=DTYPE,
                      offset=84, shape=(rows['rotor_candidate']['triangles'],))['vertices']
    radius = 0.
    for start in range(0, len(rotor), 100000):
        xy = np.asarray(rotor[start:start + 100000, :, :2], dtype=np.float64)
        radius = max(radius, float(np.sqrt(np.sum(xy * xy, axis=-1)).max()))
    motion = between_sample_motion(radius, SAMPLES)
    phases = {name: [] for name in ('drive_observed', 'provisional_shroud')}
    for index in range(SAMPLES):
        angle = 2 * math.pi * index / SAMPLES
        c, s = math.cos(angle), math.sin(angle)
        rotation = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.]])
        objects['rotor_candidate'].setTransform(fcl.Transform(rotation))
        for name in phases:
            phases[name].append({'phase_index': index, 'angle_deg': 360 * index / SAMPLES,
                                 **query(objects['rotor_candidate'], objects[name])})
    summary = {}
    for name, rows_for_pair in phases.items():
        collisions = [row for row in rows_for_pair if row['surface_crossing']]
        distances = [row['minimum_surface_distance_native_units'] for row in rows_for_pair
                     if not row['surface_crossing']]
        minimum = min(distances) if distances else None
        summary[name] = {
            'sampled_collision_count': len(collisions),
            'minimum_sampled_distance_native_units': minimum,
            'maximum_between_sample_motion_native_units': motion,
            'lower_bound_distance_native_units': minimum - motion - ROUNDING_MARGIN
            if minimum is not None and not collisions else None,
            'rigid_surface_sweep_separated': not collisions and minimum > motion + ROUNDING_MARGIN,
        }
    if sha(native / 'receipt.json') != receipt_sha or any(
            sha(native / rows[name]['file']) != rows[name]['sha256'] for name in objects):
        raise ValueError('Inputs changed during sweep')
    report = {
        'schema': '935-rigid-rotor-sweep-v1', 'native_receipt_sha256': receipt_sha,
        'source_sha256': sha(__file__), 'component_sha256': {name: rows[name]['sha256'] for name in objects},
        'samples_per_revolution': SAMPLES,
        'axis': {'origin_native_units': [0, 0, 0], 'direction': [0, 0, 1]},
        'maximum_rotor_radius_native_units': radius,
        'rounding_margin_native_units': ROUNDING_MARGIN,
        'certificate': 'distance is 1-Lipschitz in rotor Hausdorff motion; nearest-sample displacement <= 2R sin(pi/(2N))',
        'fixtures': controls, 'moving_fixture_passed': True,
        'summary': summary, 'phases': phases, 'elapsed_s': time.monotonic() - started,
        'python_fcl_version': importlib.metadata.version('python-fcl'),
        'numpy_version': np.__version__, 'architecture': platform.machine(),
        'source_coordinate_unit': 'uncalibrated_scan_unit', 'scale_verified': False,
        'axis_verified_on_historical_935': False, 'rotor_drive_mount_defined': False,
        'solid_containment_checked': False, 'thermal_or_elastic_changes_checked': False,
        'manufacturing_authorized': False,
    }
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('native', type=Path)
    parser.add_argument('receipt_sha256')
    parser.add_argument('new_report', type=Path)
    args = parser.parse_args()
    run(args.native, args.receipt_sha256, args.new_report)
