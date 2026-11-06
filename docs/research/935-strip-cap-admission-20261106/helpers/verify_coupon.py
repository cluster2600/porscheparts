"""Independently measure exported STL against the predeclared JSON contract.

No OpenSCAD source or model metadata is used to derive measured dimensions.
Lengths are digital STL-coordinate checks, not physical manufacturing tolerances.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import trimesh


def verify(stl_path: Path, contract_path: Path):
    contract = json.loads(contract_path.read_text())
    mesh = trimesh.load_mesh(stl_path, process=True)
    tolerance = contract['digital_length_tolerance_mm']
    checks = []

    def test(name, passed, measured=None, expected=None):
        checks.append({'name': name, 'passed': bool(passed),
                       'measured': measured, 'expected': expected})

    def near(name, measured, expected):
        measured = np.asarray(measured, dtype=float)
        expected = np.asarray(expected, dtype=float)
        test(name, measured.shape == expected.shape and
             np.all(np.abs(measured - expected) <= tolerance),
             measured.tolist(), expected.tolist())

    test('finite_vertices', np.isfinite(mesh.vertices).all())
    test('closed_edges', mesh.is_watertight)
    test('consistent_winding', mesh.is_winding_consistent)
    test('positive_volume', mesh.volume > 0, float(mesh.volume))
    test('nondegenerate_triangles', np.all(mesh.area_faces > 1e-12),
         float(mesh.area_faces.min()))
    components = len(mesh.split(only_watertight=False))
    test('connected_components', components == contract['expected_components'],
         components, contract['expected_components'])
    test('surface_topology', mesh.euler_number == contract['expected_euler_number'],
         int(mesh.euler_number), contract['expected_euler_number'])
    near('overall_bounds_mm', mesh.bounds, contract['overall_bounds_mm'])

    for z in [0.1, 2.0, 3.9]:
        section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        loops = [] if section is None else section.discrete
        test(f'base_section_{z}_loop_count', len(loops) == 4, len(loops), 4)
        if len(loops) != 4:
            continue
        loops.sort(key=lambda points: np.ptp(points[:, :2], axis=0).prod(), reverse=True)
        outer = loops[0][:, :2]
        near(f'base_section_{z}_outer_bounds_mm',
             [outer.min(axis=0), outer.max(axis=0)], [[0, 0], [60, 40]])
        holes = sorted(loops[1:], key=lambda points: points[:, 0].min())
        for i, (points, hole) in enumerate(zip(holes, contract['holes'])):
            xy = points[:, :2]
            lo, hi = xy.min(axis=0), xy.max(axis=0)
            near(f'hole_{i}_center_z{z}_mm', (lo + hi) / 2, hole['center_mm'])
            near(f'hole_{i}_diameters_xy_z{z}_mm', hi - lo,
                 [hole['diameter_mm']] * 2)
            radial_error = float(np.max(np.abs(np.linalg.norm(
                xy - hole['center_mm'], axis=1) - hole['diameter_mm'] / 2)))
            test(f'hole_{i}_radial_chord_error_z{z}_mm',
                 radial_error <= contract['maximum_circle_chord_error_mm'],
                 radial_error, contract['maximum_circle_chord_error_mm'])

    for z in [4.1, 9.0, 14.9]:
        section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        loops = [] if section is None else section.discrete
        test(f'fin_section_{z}_loop_count', len(loops) == 5, len(loops), 5)
        if len(loops) != 5:
            continue
        loops.sort(key=lambda points: points[:, 0].min())
        for i, (points, fin) in enumerate(zip(loops, contract['fins'])):
            xy = points[:, :2]
            near(f'fin_{i}_bounds_z{z}_mm', [xy.min(axis=0), xy.max(axis=0)],
                 [[fin['x_mm'], 22], [fin['x_mm'] + fin['width_mm'], 36]])
    for i, fin in enumerate(contract['fins']):
        v = mesh.vertices
        selected = v[(v[:, 0] >= fin['x_mm'] - tolerance) &
                     (v[:, 0] <= fin['x_mm'] + fin['width_mm'] + tolerance) &
                     (v[:, 1] >= 22 - tolerance) & (v[:, 1] <= 36 + tolerance) &
                     (v[:, 2] >= 4 - tolerance)]
        test(f'fin_{i}_vertices_present', len(selected) > 0)
        if len(selected):
            near(f'fin_{i}_height_bounds_mm',
                 [selected[:, 2].min(), selected[:, 2].max()], [4, 15])
    analytic_volume = 60 * 40 * 4 - sum(
        math.pi * (h['diameter_mm'] / 2) ** 2 * 4 for h in contract['holes']) + sum(
        f['width_mm'] * 14 * 11 for f in contract['fins'])
    volume_error = abs(float(mesh.volume) - analytic_volume) / analytic_volume
    test('analytic_volume_relative_error',
         volume_error <= contract['maximum_relative_volume_error'],
         volume_error, contract['maximum_relative_volume_error'])
    return {'schema_version': 1, 'units': 'mm', 'stl_sha256': hashlib.sha256(stl_path.read_bytes()).hexdigest(),
            'contract_sha256': hashlib.sha256(contract_path.read_bytes()).hexdigest(),
            'vertices': len(mesh.vertices), 'triangles': len(mesh.faces),
            'analytic_volume_mm3': analytic_volume, 'measured_volume_mm3': float(mesh.volume),
            'checks': checks, 'all_checks_passed': all(c['passed'] for c in checks),
            'physical_dimensions_measured': False, 'manufacturing_qualified': False,
            'whole_mesh_self_intersection_test_performed': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('stl', type=Path)
    parser.add_argument('--contract', type=Path, default=Path(__file__).with_name('contract.json'))
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.stl, args.contract)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'passed': report['all_checks_passed'], 'checks': len(report['checks']),
                      'failed': [c['name'] for c in report['checks'] if not c['passed']],
                      'volume_mm3': report['measured_volume_mm3']}))
    raise SystemExit(0 if report['all_checks_passed'] else 1)
