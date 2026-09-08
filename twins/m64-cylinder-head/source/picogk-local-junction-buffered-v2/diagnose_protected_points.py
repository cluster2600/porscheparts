#!/usr/bin/env python3
"""Localise le recouvrement masque/protection depuis le reçu, sans recalcul de champ."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(native_path, output):
    native = json.loads(native_path.read_text())
    digest = sha(native_path)
    if (native['schema'] != 'm64-picogk-local-junction-buffered-witness/v2'
            or native['voxel_world_units'] != .1 or native['private_head_processed'] is not False):
        raise ValueError('Only the fine synthetic witness receipt is in scope')
    low, high = native['inner_ROI_low'], native['inner_ROI_high']
    h = native['voxel_world_units']
    rows = []
    for example in native['SDF_comparison']['examples']:
        x, y, z = example['position_world_units']
        radial = math.hypot(x, z)
        inside = all(a <= q <= b for a, q, b in zip(low, (x, y, z), high))
        rows.append({
            'position_synthetic_world_units': [x, y, z],
            'radius_about_Y_world_units': radial,
            'distance_to_R10_Y0_ring_curve_world_units': math.hypot(radial - 10, y),
            'inside_inner_box': inside,
            'inside_declared_protection_band': abs(y) <= h / 2 and abs(radial - 10) <= h,
            'distance_to_nearest_inner_box_plane_world_units': min(
                min(q - a, b - q) for a, q, b in zip(low, (x, y, z), high)),
            'before_SDF_world_units': example['before'], 'after_SDF_world_units': example['after'],
            'zero_to_strict_negative': example['before'] == 0 and example['after'] < 0,
        })
    complete = (len(rows) == native['SDF_comparison']['protected_value_changes']
                and native['SDF_comparison']['outside_ROI_value_changes'] == 0)
    if not rows:
        raise ValueError('No failed points to diagnose')
    report = {
        'schema': 'm64-buffered-fine-protection-overlap-diagnostic/v1',
        'native_report_sha256': digest, 'source_sha256': sha(Path(__file__)),
        'coordinates_are_synthetic_not_private_scan': True,
        'reported_failed_points': rows,
        'all_reported_failed_points_inside_inner_box': all(row['inside_inner_box'] for row in rows),
        'all_reported_failed_points_in_protection_band': all(row['inside_declared_protection_band'] for row in rows),
        'all_failures_are_zero_to_strict_negative': all(row['zero_to_strict_negative'] for row in rows),
        'all_failed_protected_points_in_native_count_are_present': complete,
        'inner_box_XZ_corner_radius_world_units': math.hypot(high[0], high[2]),
        'box_mask_not_disjoint_from_protected_R10_ring': low[1] <= 0 <= high[1]
            and math.hypot(high[0], high[2]) > 10,
        'minimum_reported_ring_distance_world_units': min(row['distance_to_R10_Y0_ring_curve_world_units'] for row in rows),
        'maximum_reported_ring_distance_world_units': max(row['distance_to_R10_Y0_ring_curve_world_units'] for row in rows),
        'kernel_cause_of_SDF_delta_proved': False,
        'no_epsilon_or_guard_relaxation': True, 'no_geometry_or_field_recalculated': True,
        'new_mask_or_further_pass_executed': False,
        'manufacturing_authorized': False,
    }
    if sha(native_path) != digest:
        raise ValueError('Native receipt changed')
    with output.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'reported_failed_points'}, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.native_report, args.output)
