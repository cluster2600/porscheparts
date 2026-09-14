#!/usr/bin/env python3
"""Read a completed cold-flow pilot; mass checks are not CFD qualification."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table(text, columns):
    """Strict native function-object table, with no restarted/merged histories."""
    header = None
    rows = []
    for line in text.splitlines():
        if line.startswith('# Time'):
            header = line[1:].split()
        elif line.strip() and not line.startswith('#'):
            values = list(map(float, line.split()))
            if len(values) != len(columns) or not all(math.isfinite(v) for v in values):
                raise ValueError('invalid or nonfinite function-object row')
            if rows and values[0] <= rows[-1][0]:
                raise ValueError('duplicate or unordered function-object time')
            rows.append(values)
    if header != columns or not rows:
        raise ValueError('missing table or unexpected function-object columns')
    return rows


def mass_checks(series, window, criteria):
    """Conservative per-iteration balance plus the two preregistered means."""
    if isinstance(window, bool) or not isinstance(window, int) or window < 2:
        raise ValueError('statistical window must contain at least two iterations')
    if set(series) != {'inlet', 'receiver_outlet', 'walls'}:
        raise ValueError('all three boundary histories required')
    times = [row[0] for row in series['inlet']]
    if any([r[0] for r in rows] != times for rows in series.values()):
        raise ValueError('boundary time histories do not match')
    if times != list(range(len(times))):
        raise ValueError('complete unit-step history starting at zero required')
    if any(row[1] <= 0 for rows in series.values() for row in rows):
        raise ValueError('positive boundary areas required')
    if any(any(row[1] != rows[0][1] for row in rows) for rows in series.values()):
        raise ValueError('stationary pilot must retain boundary areas')
    count = len(times) - 1  # Time zero is the initial state, not an iteration.
    result = {'completed_iterations_in_tables': count, 'window_iterations': window,
              'sufficient_history': count >= 2 * window,
              'mass_checks_passed': False, 'convergence_demonstrated': False,
              'last_iteration_fluxes_kg_s': {p: rows[-1][2] for p, rows in series.items()}}
    if count < 2 * window:
        result['reason'] = 'insufficient_history_for_two_preregistered_windows'
        return result
    old = [r[2] for r in series['receiver_outlet'][-2*window:-window]]
    new = [r[2] for r in series['receiver_outlet'][-window:]]
    old_mean, mean = statistics.fmean(old), statistics.fmean(new)
    denominators = [max(abs(series['inlet'][i][2]), abs(series['receiver_outlet'][i][2]))
                    for i in range(len(times)-window, len(times))]
    if mean <= 0 or old_mean <= 0 or min(denominators) <= 0:
        result['reason'] = 'zero_or_reversed_mean_flow'
        return result
    balances = [abs(math.fsum(series[p][i][2] for p in series)) / denom
                for i, denom in zip(range(len(times)-window, len(times)), denominators)]
    change = abs(mean-old_mean) / abs(mean)
    expected_signs = all(row[2] < 0 for row in series['inlet'][-window:]) and min(new) > 0
    walls_impermeable = all(row[2] == 0 for row in series['walls'][-window:])
    result.update({
        'previous_window_outlet_mean_kg_s': old_mean,
        'last_window_outlet_mean_kg_s': mean,
        'maximum_relative_mass_imbalance_last_window': max(balances),
        'relative_outlet_mean_change': change,
        'relative_outlet_stddev_last_window': statistics.pstdev(new)/mean,
        'relative_outlet_peak_to_peak_last_window': (max(new)-min(new))/mean,
        'expected_inlet_outlet_signs': expected_signs,
        'prescribed_stationary_no_slip_wall_flux_zero': walls_impermeable,
        'mass_checks_passed': bool(expected_signs and walls_impermeable and
            max(balances) <= criteria['relative_mass_imbalance_max'] and
            change <= criteria['relative_mean_mass_flow_change_last_two_windows_max']),
        'stationarity_not_proven_by_equal_window_means': True,
    })
    return result


def audit(case, policy_path):
    case = case.resolve()
    hashes = {}
    def read(relative):
        path = (case / relative).resolve()
        if not path.is_relative_to(case):
            raise ValueError('case input escaped private package')
        hashes[relative] = sha(path)
        return path.read_text()
    manifest = json.loads(read('case-manifest.json'))
    execution = json.loads(read('execution-report.json'))
    policy_hash = sha(policy_path)
    policy = json.loads(policy_path.read_text())
    if (manifest.get('schema') != 'm64-openfoam-intake-case/v1' or
            execution.get('schema') != 'm64-openfoam-intake-execution/v1' or
            manifest.get('policy_sha256') != policy_hash or
            execution.get('case_manifest_sha256') != hashes['case-manifest.json'] or
            execution.get('purpose') != manifest.get('purpose') or
            manifest.get('purpose') not in ('head_pilot', 'synthetic_runtime_smoke')):
        raise ValueError('case, execution and policy provenance mismatch')
    if (execution.get('status') != 'solver_completed_not_convergence_or_performance_validation' or
            execution.get('solver_executed') is not True or
            execution.get('checkMesh_passed') is not True or execution.get('scale_applied') is not True):
        raise ValueError('completed solver and mesh pipeline required')
    stages = execution['stages']
    expected = ['gmshToFoam', 'transformPoints']
    if execution.get('poly_dual_requested'):
        expected.append('polyDualMesh')
    expected += ['createPatch', 'checkMesh', 'foamRun']
    if [s['name'] for s in stages] != expected:
        raise ValueError('unexpected execution stages')
    for stage in stages:
        relative = 'log.' + stage['name']
        log = read(relative)
        if stage['exit_code'] != 0 or stage['timed_out'] or hashes[relative] != stage['log_sha256']:
            raise ValueError('runtime exit or log provenance mismatch')
        if 'FOAM FATAL' in log or (stage['name'] == 'checkMesh' and 'Mesh OK.' not in log):
            raise ValueError('runtime log contradicts completed status')
    read('input.msh')
    if hashes['input.msh'] != manifest['mesh_sha256']:
        raise ValueError('input mesh changed')
    for name, expected_hash in manifest['file_sha256'].items():
        read(name)
        if hashes[name] != expected_hash:
            raise ValueError('prepared case file changed: ' + name)
    series = {p: table(read(f'postProcessing/massFlow_{p}/0/surfaceFieldValue.dat'),
                       ['Time', 'Area', 'orientedSum(phi)'])
              for p in ('inlet', 'receiver_outlet', 'walls')}
    result = mass_checks(series, manifest['statistical_window_iterations'],
                         policy['preregistered_exploratory_checks'])
    if result['completed_iterations_in_tables'] != manifest['steady_iterations']:
        raise ValueError('table history does not reach declared solver end')
    minima = table(read('postProcessing/scalarMinima/0/volFieldValue.dat'),
                   ['Time', 'min(p)', 'min(T)', 'min(k)', 'min(omega)'])
    if minima[-1][0] != manifest['steady_iterations']:
        raise ValueError('final scalar sample missing')
    scalar_positive = all(value > 0 for value in minima[-1][1:])
    unchanged = all(sha(case / name) == h for name, h in hashes.items()) and sha(policy_path) == policy_hash
    if not unchanged:
        raise ValueError('input changed during flow audit')
    return {'schema': 'm64-openfoam-intake-flow-audit/v1',
            'status': 'diagnostics_only_not_converged_head_CFD',
            'purpose': manifest['purpose'], 'input_sha256': hashes,
            'source_sha256': sha(Path(__file__)), 'policy_sha256': policy_hash,
            'mass_diagnostics': result,
            'final_scalar_minima': dict(zip(('p_Pa', 'T_K', 'k_m2_s2', 'omega_s_inverse'), minima[-1][1:])),
            'final_sampled_scalars_positive': scalar_positive,
            'sampled_positivity_does_not_exclude_between_sample_violations': True,
            'spatial_convergence_demonstrated': False, 'wall_resolution_qualified': False,
            'head_flow_qualified': False, 'physical_correlation': False,
            'engine_power_PS': None, 'manufacturing_authorized': False,
            'all_case_inputs_unchanged': unchanged}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case-dir', type=Path, required=True)
    parser.add_argument('--policy', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.case_dir, args.policy)
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'status': report['status'], 'purpose': report['purpose'],
                      'mass_checks_passed': report['mass_diagnostics']['mass_checks_passed']}))
