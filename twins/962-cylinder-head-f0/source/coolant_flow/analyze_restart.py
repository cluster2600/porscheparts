"""Audit a stopped restart and report convergence separately from hydraulic diagnostics."""
import argparse
import importlib.util
import json
import math
from pathlib import Path
import re
import sys

from prepare_restart import sha, verify

FLOW = Path(__file__).resolve().parent.parent / 'flow4l/analyze_flow.py'
spec = importlib.util.spec_from_file_location('existing_flow_postprocessor', FLOW)
flow = importlib.util.module_from_spec(spec)
previous_bytecode = sys.dont_write_bytecode
try:
    # The existing analytical benchmark tree must stay free of generated files.
    sys.dont_write_bytecode = True
    spec.loader.exec_module(flow)
finally:
    sys.dont_write_bytecode = previous_bytecode
FLOAT = flow.benchmark.FLOAT_PATTERN


def iterations(text):
    records = []
    blocks = re.split(r'^Time = (' + FLOAT + r')(?:s)?\s*$', text, flags=re.MULTILINE)
    for time, body in zip(blocks[1::2], blocks[2::2]):
        if 'ExecutionTime =' not in body:
            continue
        first = {}
        for match in flow.benchmark.RESIDUAL_RE.finditer(body):
            first.setdefault(match['field'], float(match['initial']))
        if set(first) != {'Ux', 'Uy', 'Uz', 'p', 'k', 'omega'} or not all(
                math.isfinite(v) and v >= 0 for v in first.values()):
            raise ValueError('Incomplete or invalid completed iteration')
        records.append(dict(iteration=float(time), initial_residuals=first))
    if not records:
        raise ValueError('No completed iterations')
    if any(b['iteration'] <= a['iteration'] for a, b in zip(records, records[1:])):
        raise ValueError('Nonmonotonic iteration history')
    return records


def history(case, name):
    files = sorted((case / 'postProcessing' / name).glob('*/surfaceFieldValue.dat'))
    if len(files) != 1:
        raise ValueError('Expected one restart function history: ' + name)
    rows = [tuple(map(float, line.split())) for line in files[0].read_text().splitlines()
            if line.strip() and not line.lstrip().startswith('#')]
    if not rows or any(len(row) != 2 or not all(map(math.isfinite, row)) for row in rows):
        raise ValueError('Invalid surface history: ' + name)
    if any(b[0] <= a[0] for a, b in zip(rows, rows[1:])):
        raise ValueError('Nonmonotonic surface history: ' + name)
    return files[0], dict(rows)


def scalar_internal(path, cells, dimensions):
    import numpy as np
    text = path.read_text()
    if not re.search(r'dimensions\s*\[' + r'\s+'.join(map(str, dimensions)) + r'\s*\]', text):
        raise ValueError('Unexpected field dimensions: ' + path.name)
    match = re.search(r'internalField\s+nonuniform\s+List<scalar>\s+(\d+)\s*\((.*?)\)\s*;', text, re.DOTALL)
    if not match:
        raise ValueError('Expected a nonuniform scalar field: ' + path.name)
    values = np.asarray(match[2].split(), dtype=float)
    if len(values) != cells or int(match[1]) != cells or not np.isfinite(values).all():
        raise ValueError('Invalid scalar count or values: ' + path.name)
    return values


def analyze(case, output):
    import numpy as np
    if output.exists():
        raise ValueError('Audit output must be new')
    inputs = json.loads((case / 'case-report.json').read_text())
    verify(case, inputs['case_hashes'])
    mesh = json.loads((case / 'mesh-report.json').read_text())
    verify(case, mesh['source_hashes'])
    if mesh['cells'] != inputs['cells'] or mesh['status'] != 'mesh_numerical_gate_passed_not_physical_validation':
        raise ValueError('Missing admitted mesh')
    text = (case / 'log.parallelFoam').read_text()
    records = iterations(text)
    last = records[-1]
    saved = flow.benchmark.latest_time_dir(case)
    saved_time = float(saved.name)
    tables = {name: history(case, name) for name in
              ('inletFlux', 'outletFlux', 'inletPressure', 'outletPressure')}
    if any(saved_time not in values for _, values in tables.values()):
        raise ValueError('Saved fields have no matching function samples')
    q, rho, cells = inputs['flow_m3_s'], inputs['water_density_kg_m3'], inputs['cells']
    if not (math.isfinite(q) and q > 0 and math.isfinite(rho) and rho > 0):
        raise ValueError('Invalid operating assumptions')
    boundary = (case / 'constant/polyMesh/boundary').read_text()
    flux = {}
    for name in ('inlet', 'outlet'):
        patch = re.search(r'\b' + name + r'\s*\{([^}]+)\}', boundary)
        count = int(re.search(r'nFaces\s+(\d+)\s*;', patch[1])[1])
        flux[name] = flow.patch_flux(saved / 'phi', name, count)
        if not math.isclose(flux[name], tables[name + 'Flux'][1][saved_time], rel_tol=1e-10, abs_tol=1e-14):
            raise ValueError('Saved patch flux differs from native function history')
    p = scalar_internal(saved / 'p', cells, [0, 2, -2, 0, 0, 0, 0])
    k = scalar_internal(saved / 'k', cells, [0, 2, -2, 0, 0, 0, 0])
    omega = scalar_internal(saved / 'omega', cells, [0, 0, -1, 0, 0, 0, 0])
    nut = scalar_internal(saved / 'nut', cells, [0, 2, -1, 0, 0, 0, 0])
    u_text = (saved / 'U').read_text()
    if not re.search(r'dimensions\s*\[0\s+1\s+-1\s+0\s+0\s+0\s+0\]', u_text):
        raise ValueError('Unexpected velocity dimensions')
    u = np.asarray(flow.benchmark.read_vector_field(saved / 'U', cells))
    if u.shape != (cells, 3) or not np.isfinite(u).all():
        raise ValueError('Invalid velocity count or values')
    dp = (tables['inletPressure'][1][saved_time] - tables['outletPressure'][1][saved_time]) * rho
    window = [t for t in tables['inletPressure'][1] if t <= saved_time][-100:]
    if any(t not in values for _, values in tables.values() for t in window):
        raise ValueError('Function history timestamps differ')
    drops = [(tables['inletPressure'][1][t] - tables['outletPressure'][1][t]) * rho for t in window]
    spread = (max(drops) - min(drops)) / abs(sum(drops) / len(drops)) if sum(drops) else None
    imbalance = abs(flux['inlet'] + flux['outlet']) / q
    inlet_error = abs(-flux['inlet'] - q) / q
    exit_path = case / 'solver-exit-code.txt'
    exit_code = int(exit_path.read_text()) if exit_path.exists() else None
    native_converged = 'SIMPLE solution converged' in text
    ended = bool(re.search(r'^End\s*$', text, re.MULTILINE))
    residuals_pass = max(last['initial_residuals'].values()) <= inputs['residual_target']
    checkpoint_matches = saved_time == last['iteration']
    positive_turbulence = bool(k.min() >= 0 and omega.min() > 0 and nut.min() >= 0)
    passed = bool(exit_code == 0 and native_converged and ended and residuals_pass
        and checkpoint_matches and imbalance < 1e-5 and inlet_error < 1e-6
        and dp > 0 and len(window) == 100 and spread is not None and spread < .001
        and positive_turbulence)
    report = dict(status='audited_isothermal_restart_not_physical_validation',
        cells=cells, saved_iteration=saved_time, last_completed_iteration=last['iteration'],
        solver_exit_code=exit_code, native_convergence_marker=native_converged,
        native_End_marker=ended, first_solve_initial_residuals=last['initial_residuals'],
        residual_target=inputs['residual_target'], residual_target_satisfied=residuals_pass,
        saved_fields_match_last_completed_iteration=checkpoint_matches,
        flow_m3_s=q, density_kg_m3=rho, inlet_flux_m3_s=flux['inlet'],
        outlet_flux_m3_s=flux['outlet'], relative_flow_imbalance=imbalance,
        relative_inlet_flow_error=inlet_error,
        provisional_pressure_drop_pa=dp, provisional_hydraulic_power_w=dp * q,
        pressure_is_static_area_average_not_total_pressure=True,
        pressure_window_iterations=len(window), pressure_relative_range=spread,
        pressure_relative_range_target=.001,
        maximum_cell_speed_m_s=float(np.linalg.norm(u, axis=1).max()),
        positive_turbulence_fields=positive_turbulence,
        internal_kinematic_pressure_range_m2_s2=[float(p.min()), float(p.max())],
        numerical_flow_screen_passed=passed,
        spatial_discretization='first-order bounded upwind; no grid convergence study',
        non_orthogonal_correction_limiter=inputs.get('non_orthogonal_correction_limiter', 1),
        hydraulic_performance_validated=False, thermal_performance_validated=False,
        manufacturing_authorized=False,
        source_hashes={str(p.name): sha(p) for p in (Path(__file__),
            Path(__file__).with_name('prepare_restart.py'), FLOW,
            flow.SOURCE / 'build_flow_case.py',
            flow.ROOT / 'outils/benchmarks/openfoam-poiseuille-f25/analyze_results.py',
            flow.ROOT / 'outils/benchmarks/openfoam-poiseuille-f25/generate_cases.py')},
        case_report_sha256=sha(case / 'case-report.json'),
        mesh_report_sha256=sha(case / 'mesh-report.json'),
        log_hashes={p.name: sha(p) for p in sorted(case.glob('log.*'))},
        final_field_hashes={name: sha(saved / name) for name in ('U', 'p', 'phi', 'k', 'omega', 'nut')},
        history_hashes={str(path.relative_to(case)): sha(path) for path, _ in tables.values()})
    output.mkdir(parents=True)
    (output / 'residual-history.json').write_text(json.dumps(records, indent=2, allow_nan=False) + '\n')
    report['residual_history_sha256'] = sha(output / 'residual-history.json')
    (output / 'flow-report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(json.dumps(analyze(args.case.resolve(), args.output.resolve()), indent=2))
