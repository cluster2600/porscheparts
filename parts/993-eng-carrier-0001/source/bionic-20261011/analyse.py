"""Conditional load, fatigue-demand and thermal verification from saved solves."""
import csv
import json
import sys
from pathlib import Path

import numpy as np

from simulate import eigenvalues, von_mises


def analyse(root):
    summary = {'scope': 'Provisional geometry and assumed loads; no manufacturing approval',
               'cases': [], 'linear_superposition': [], 'fatigue_demand': []}
    for path in sorted(root.glob('v*/mesh-*/*.json')):
        value = json.loads(path.read_text())
        if 'procedure' not in value:
            continue
        value.pop('eigenvalue_output', None)
        value['result_file'] = str(path.relative_to(root))
        if value['procedure'] in ('modal', 'buckling'):
            rows = eigenvalues(path.with_suffix('.dat').read_text(), value['procedure'])
            key = 'frequencies_Hz' if value['procedure'] == 'modal' else 'buckling_load_factors'
            value[key] = rows[:, 3 if value['procedure'] == 'modal' else 1].tolist()
        summary['cases'].append(value)
    folder = root/'v2/mesh-8'
    for support in ('rigid', 'spring-1000'):
        gpath = folder/f'gravity-{support}-static.npz'
        cpath = folder/f'combined-{support}-static.npz'
        gravity, combined = np.load(gpath), np.load(cpath)
        assert np.array_equal(gravity['tags'], combined['tags'])
        assert np.array_equal(gravity['element_ids'], combined['element_ids'])
        assert np.array_equal(gravity['xyz'], combined['xyz'])
        sg, sc = gravity['stress'], combined['stress']
        for name, a, b in [('shock_4000_N', 2, 0), ('stock_torque_540_Nm', -2*540/850, 540/850)]:
            u = a*gravity['displacement']+b*combined['displacement']
            s = a*sg+b*sc
            summary['linear_superposition'].append({'name': name, 'support': support,
                'derived_from': [str(gpath.relative_to(root)), str(cpath.relative_to(root))],
                'coefficients': [a, b], 'displacement_max_mm': float(np.linalg.norm(u, axis=1).max()),
                'integration_point_VM_max_MPa': float(von_mises(s).max())})
        for name, alternating in [('2000_N_to_4000_N_plus_850_Nm', (sc-sg)/2),
                                  ('2000_N_with_fully_reversed_850_Nm', sc-2*sg)]:
            amplitude = von_mises(alternating)
            summary['fatigue_demand'].append({'scenario': name, 'support': support,
                'maximum_equivalent_alternating_stress_MPa': float(amplitude.max()),
                'hotspot_element': int(gravity['element_ids'][amplitude.argmax()]),
                'fatigue_life_cycles': None, 'process_specific_SN_curve': None,
                'meaning': 'Elastic stress amplitude only, without a mean-stress correction, cycle count or damage/life claim.'})
    rows = []
    for size in (12, 10, 8):
        m = json.loads((root/f'v2/mesh-{size}/mesh.json').read_text())
        r = json.loads((root/f'v2/mesh-{size}/combined-rigid-static.json').read_text())
        rows.append({'nominal_size_mm': size, 'elements': m['C3D10_elements'],
                     'displacement_mm': r['displacement_max_mm'],
                     'peak_VM_MPa': r['integration_point_VM_max_MPa'],
                     'volume_error_fraction': m['volume_relative_error']})
    summary['refinement'] = rows
    summary['last_refinement_change'] = {
        key: rows[-1][key]/rows[-2][key]-1 for key in ('displacement_mm', 'peak_VM_MPa')}
    c = np.load(folder/'combined-rigid-static.npz')
    mesh = np.load(folder/'mesh.npz')
    summary['combined_joint_demands'] = {
        'central_site_forces_N': json.loads((folder/'combined-rigid-static.json').read_text())['bolt_group_forces_N'],
        'end_reactions_N': [c['reaction'][np.isin(c['fixed'], mesh[f'end{i}'])].sum(0).tolist() for i in range(2)],
        'joint_contact_preload_friction_modelled': False,
        'joint_capacity_or_slip_margin': None}
    p = root/'v2/mesh-12/thermal_gradient-rigid-warpage'
    data = np.load(p.with_suffix('.npz'))
    config = json.loads((root/'v2/study.json').read_text())
    xyz = data['xyz']; x, y, z = xyz.T
    a = config['material']['expansion_per_K']*50/config['geometry']['thickness_mm']
    u0 = a*np.c_[z*x, z*y, (z*z-x*x-y*y)/2]
    A, b = [], []
    boundary = p.with_suffix('.inp').read_text().split('*BOUNDARY\n')[1].split('*TEMPERATURE')[0]
    for line in boundary.strip().splitlines():
        node, first, last = map(int, line.split(','))
        idx = np.searchsorted(data['tags'], node); x, y, z = xyz[idx]
        block = np.c_[np.eye(3), [[0, z, -y], [-z, 0, x], [y, -x, 0]]]
        for dof in range(first-1, last):
            A.append(block[dof]); b.append(-u0[idx, dof])
    motion = np.linalg.solve(A, b)
    exact = u0+motion[:3]+np.cross(motion[3:], xyz)
    error = float(abs(exact-data['displacement']).max())
    assert error < 2e-5 and data['VM'].max() < 1e-4
    summary['thermal_verification'] = {
        'temperature_gradient_K_per_mm': 50/config['geometry']['thickness_mm'],
        'analytic_field': 'alpha*dT_dz*(z*x, z*y, (z*z-x*x-y*y)/2), plus rigid motion satisfying the same 3-2-1 restraint',
        'max_displacement_error_mm': error,
        'max_VM_MPa': float(data['VM'].max()), 'passed': True,
        'permanent_manufacturing_distortion_predicted': False}
    (root/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    with (root/'results.csv').open('w', newline='') as stream:
        columns = ['result_file', 'procedure', 'displacement_max_mm', 'integration_point_VM_max_MPa', 'seconds']
        writer = csv.DictWriter(stream, columns, extrasaction='ignore')
        writer.writeheader(); writer.writerows(summary['cases'])
    print(json.dumps({k: v for k, v in summary.items() if k != 'cases'}, indent=2))


if __name__ == '__main__':
    analyse(Path(sys.argv[1]))
