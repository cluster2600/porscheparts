#!/usr/bin/env python3
"""Assess one Foundation 13 hypothesis case without granting fan-curve approval."""
import argparse
import json
import math
from pathlib import Path
import re
import statistics

from run_reconstruction import fresh, save, sha


def history(path, columns):
    rows = []
    for line in Path(path).read_text().splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        row = [float(x) for x in line.replace('(', ' ').replace(')', ' ').split()]
        if len(row) != columns or not all(math.isfinite(x) for x in row):
            raise ValueError('Complete finite Foundation 13 history required')
        rows.append(row)
    if len(rows) < 2 or any(b[0] <= a[0] for a, b in zip(rows, rows[1:])):
        raise ValueError('Unique increasing history required')
    return rows


def assess(case):
    case = Path(case).resolve()
    metadata = json.loads((case / 'case-metadata.json').read_text())
    job = json.loads((case / 'execution.json').read_text())
    if (metadata['solver_family'] != 'OpenFOAM_Foundation_13' or job['exit'] != 0 or job['stop_reason'] is not None
            or job['input_files_unchanged'] is not True or job['input_receipt_sha256'] != sha(case / 'case-metadata.json')
            or metadata['classification'] != 'conditional_square_duct_not_935_installation'
            or metadata['scale_verified'] is not False or metadata['axis_verified'] is not False):
        raise ValueError('Completed Foundation 13 execution required')
    required = {'system/controlDict', 'system/fvSolution', 'system/fvSchemes', 'constant/MRFProperties',
                'constant/physicalProperties', 'constant/momentumTransport', 'constant/triSurface/rotor.obj',
                '0/U', '0/p', '0/k', '0/omega', '0/nut'}
    if not required.issubset(metadata['prepared_input_sha256']):
        raise ValueError('Complete prepared input identity required')
    for name, expected in metadata['prepared_input_sha256'].items():
        if Path(name).is_absolute() or '..' in Path(name).parts or not (case / name).resolve().is_relative_to(case) or sha(case / name) != expected:
            raise ValueError('Prepared CFD input changed or escapes the case')
    logs = {name: (case / name).read_text() for name in ('log.foamRun', 'log.checkMesh')}
    if 'Mesh OK.' not in logs['log.checkMesh'] or 'FOAM FATAL' in logs['log.foamRun'] or not re.search(r'^End\s*$', logs['log.foamRun'], re.M):
        raise ValueError('Accepted mesh and completed solver logs required')
    forces = case / 'postProcessing/rotorForces/0/forces.dat'
    if not re.search(r'#\s*Time\s+forces\(pressure viscous\)\s+moments\(pressure viscous\)', forces.read_text()):
        raise ValueError('Foundation 13 non-porous force/moment header required')
    paths = {name: case / f'postProcessing/{name}/0/surfaceFieldValue.dat' for name in
             ('inletFlow', 'outletFlow', 'inletPressure', 'outletPressure')}
    rows = {name: history(path, 2 if name.endswith('Flow') else 3) for name, path in paths.items()}
    rows['forces'] = history(forces, 13)
    times = [row[0] for row in rows['inletFlow']]
    end = re.search(r'\bendTime\s+([0-9.]+)\s*;', (case / 'system/controlDict').read_text())
    if not end or times[-1] != float(end[1]) or any([r[0] for r in values] != times for values in rows.values()):
        raise ValueError('Synchronized histories reaching the prescribed final iteration required')
    q, rho, rpm = (metadata[k] for k in ('specified_volume_flow_m3_s', 'density_kg_m3_assumed', 'rotor_rpm_assumed'))
    if not all(type(x) in (float, int) and math.isfinite(x) for x in (q, rho, rpm)) or q <= 0 or rho <= 0 or rpm == 0:
        raise ValueError('Finite signed rpm and positive flow/density required')
    series = []
    for i, time in enumerate(times):
        pin, pout = rows['inletPressure'][i], rows['outletPressure'][i]
        if pin[2] < 0 or pout[2] < 0:
            raise ValueError('Negative squared velocity')
        qi, qo = rows['inletFlow'][i][1], rows['outletFlow'][i][1]
        torque = -(rows['forces'][i][9] + rows['forces'][i][12])
        series.append({'iteration': time, 'total_pressure_rise_Pa': rho * (pout[1] - pin[1] + (pout[2] - pin[2]) / 2),
                       'resisting_torque_z_Nm': torque, 'shaft_power_W': torque * rpm * math.pi / 30,
                       'mass_imbalance_relative': abs(qi + qo) / q,
                       'imposed_flow_relative_error': max(abs(qi + q), abs(qo - q)) / q})
    windows = [[r for r in series if times[-1] - high < r['iteration'] <= times[-1] - low]
               for low, high in ((0, 100), (100, 200))]
    if any(len(w) != 10 or w[-1]['iteration'] - w[0]['iteration'] != 90 for w in windows):
        raise ValueError('Two complete 100-iteration windows sampled every 10 required')
    metrics = {}
    for key in ('total_pressure_rise_Pa', 'resisting_torque_z_Nm', 'shaft_power_W'):
        mean, previous = (statistics.mean(r[key] for r in w) for w in windows)
        spread = (max(r[key] for r in windows[0]) - min(r[key] for r in windows[0])) / max(abs(mean), 1e-30)
        drift = abs(mean - previous) / max(abs(mean), abs(previous), 1e-30)
        metrics[key] = {'final_window_mean': mean, 'peak_to_peak_relative': spread,
                        'successive_window_mean_relative_change': drift, 'stationarity_pass': spread < .01 and drift < .01}
    mass_error = max(r['mass_imbalance_relative'] for r in windows[0])
    flow_error = max(r['imposed_flow_relative_error'] for r in windows[0])
    extended = case / 'log.checkMesh.allGeometry'
    strict_mesh_pass = extended.is_file() and 'Mesh OK.' in extended.read_text()
    stationarity = all(m['stationarity_pass'] for m in metrics.values())
    return {'classification': metadata['classification'], 'solver_family': metadata['solver_family'],
            'metadata_sha256': sha(case / 'case-metadata.json'), 'execution_sha256': sha(case / 'execution.json'),
            'geometry_sha256': metadata['geometry_sha256'], 'source_sha256': sha(__file__),
            'result_sha256': {str(p.relative_to(case)): sha(p) for p in [*paths.values(), forces, *(case / n for n in logs)]},
            'rotor_rpm_assumed': rpm, 'flow_m3_s_imposed_not_predicted': q, 'metrics': metrics,
            'maximum_final_window_mass_imbalance_relative': mass_error,
            'maximum_imposed_flow_relative_error': flow_error,
            'extended_geometry_mesh_check_pass': strict_mesh_pass,
            'all_geometry_log_sha256': sha(extended) if extended.is_file() else None,
            'single_mesh_pilot_pass': strict_mesh_pass and mass_error < .001 and flow_error < .001 and stationarity,
            'three_mesh_convergence_established': False, 'accepted_for_935_fan_curve': False,
            'scale_verified': False, 'axis_verified': False, 'physical_validation': False,
            'manufacturing_authorized': False, 'series': series}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    report = assess(args.case)
    save(fresh(args.output) / 'assessment.json', report)
    print('Conditional single-mesh pilot pass:', report['single_mesh_pilot_pass'])
