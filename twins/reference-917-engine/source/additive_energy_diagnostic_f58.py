#!/usr/bin/env python3
"""Instrument a pinned AlSi10Mg coupon's discrete energy equation, not a head."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil

PINNED = {
    'additiveFoam.C': '206016ec961e2da24fd33fb481f97c7f48f8b4851b8239e5e83ddb2cefb74914',
    'thermo/TEqn.H': '1f1058b95e0b64f99c3640180b3cda69e832d8e69ea026e261e7d9baa340d42b',
    'thermo/thermoScheme.H': '03b6c8f10ba5a2fff5974ae00f926f5ebd02c7e3fbff2f7f04892b48a5ddf7fd',
    'thermo/thermoSource.H': 'efab43bb4cd3f05b29eb326a2b2ead2508de43ff705bdf546ab7d58295a57b4f',
    'updateProperties.H': '98e6e85e1a8cd2c10ee385864280a88ff6649d45e51148eeee47fd55b136da2a',
}
FIELDS = ('time_s', 'dt_s', 'max_temperature_k', 'sensible_storage_w',
          'latent_storage_w', 'boundary_diffusion_in_w', 'laser_in_w',
          'advective_out_w', 'limiter_sink_w', 'equation_residual_w')
# Logs print 16 significant digits. The comparison covers rounding of the six
# terms and their cancellation; this is NOT a physical balance acceptance limit.
RESIDUAL_LOG_ABS_TOL_W = 1e-12
RESIDUAL_LOG_REL_TOL = 5e-15

# These are exactly the assembled explicit Euler terms, using lagged Cp/kappa.
# Sensible storage is NOT rho*Cp*T or a claim of calibrated physical enthalpy.
BEFORE = '''
        if (!explicitSolve || adjustTimeStep || mesh.changing())
        {
            FatalErrorInFunction << "F58 requires fixed-mesh explicit fixed-dt coupon"
                << abort(FatalError);
        }
        scalarField f58Tbefore(T.primitiveField());
        scalarField f58Abefore(alpha1.primitiveField());
        const scalar f58Diffusion = fvc::domainIntegrate(fvc::laplacian(kappa, T)).value();
        const scalar f58Laser = fvc::domainIntegrate(sources.qDot()).value();
        const scalar f58Advection = fvc::domainIntegrate(rho*Cp*fvc::div(phi, T)).value();
        scalar f58Limiter = 0.0;
'''
AFTER = '''
        const scalar f58Dt = runTime.deltaTValue();
        const scalar f58Sensible = gSum
        (
            rho.value()*Cp.primitiveField()*(T.primitiveField()-f58Tbefore)*mesh.V()
        )/f58Dt;
        const scalar f58Latent = -rho.value()*Lf.value()*gSum
        (
            (alpha1.primitiveField()-f58Abefore)*mesh.V()
        )/f58Dt;
        const scalar f58Residual = f58Sensible + f58Latent
            - f58Diffusion - f58Laser + f58Advection + f58Limiter;
        Info().precision(16);
        Info<< "F58_BALANCE " << runTime.value() << " " << f58Dt
            << " " << gMax(T.primitiveField())
            << " " << f58Sensible << " " << f58Latent
            << " " << f58Diffusion << " " << f58Laser
            << " " << f58Advection << " " << f58Limiter
            << " " << f58Residual << endl;
'''
LIMITER = '''
        // The last nonlinear iteration's actual implicit penalty, kept separate
        // from physical losses; do not hide an energy sink behind a capped Tmax.
        f58Limiter = fvc::domainIntegrate(rDeltaT*A*(T-Tmax)).value();
'''


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def hashes(root):
    return {str(p.relative_to(root)): digest(p)
            for p in sorted(root.rglob('*')) if p.is_file() and not p.is_symlink()}


def change_once(text, pattern, replacement):
    text, count = re.subn(pattern, replacement, text, flags=re.MULTILINE)
    if count != 1:
        raise ValueError('expected exactly one match: '+pattern)
    return text


def prepare(source, solver, output):
    if output.exists():
        raise FileExistsError(output)
    for name, expected in PINNED.items():
        if digest(solver/name) != expected:
            raise ValueError('solver source mismatch: '+name)
    solution = (source/'system/fvSolution').read_text()
    for pattern in (r'\bexplicitSolve\s+true;', r'\bnOuterCorrectors\s+0;',
                    r'\bTmax\s+3300\.0;'):
        if not re.search(pattern, solution):
            raise ValueError('unsupported coupon solution: '+pattern)
    heat = (source/'constant/heatSourceDict').read_text()
    if not re.search(r'\bmodel\s+Kelly;', heat):
        raise ValueError('expected original Kelly absorption, not calibrated alternative')
    transport = (source/'constant/transportProperties').read_text()
    if 'AlSi10Mg.cfg' not in transport:
        raise ValueError('expected AlSi10Mg coupon')
    if not (source/'constant/polyMesh/points').is_file():
        raise ValueError('source volume mesh absent')
    output.mkdir(parents=True)
    target = output/'solver'
    shutil.copytree(solver, target, symlinks=True)
    main = (target/'additiveFoam.C').read_text()
    marker = '        #include "thermo/TEqn.H"'
    if main.count(marker) != 1:
        raise ValueError('thermal equation include mismatch')
    (target/'additiveFoam.C').write_text(main.replace(marker, BEFORE+marker+'\n'+AFTER))
    equation = (target/'thermo/TEqn.H').read_text()
    marker = '        T.correctBoundaryConditions();'
    if equation.count(marker) != 1:
        raise ValueError('thermal boundary correction mismatch')
    (target/'thermo/TEqn.H').write_text(equation.replace(marker, LIMITER+marker))
    makefile = target/'Make/files'
    makefile.write_text(makefile.read_text().replace('$(FOAM_USER_APPBIN)/additiveFoam',
                                                   '$(FOAM_USER_APPBIN)/additiveFoamF58'))
    cases = {}
    for name, dt in (('dt', 1e-7), ('dt_half', 5e-8)):
        case = output/name
        case.mkdir()
        for folder in ('0', 'constant', 'system'):
            shutil.copytree(source/folder, case/folder)
        control = case/'system/controlDict'
        text = control.read_text()
        for pattern, replacement in (
            (r'^deltaT\s+[^;]+;', f'deltaT {dt:.12g};'),
            (r'^adjustTimeStep\s+[^;]+;', 'adjustTimeStep no;'),
            (r'^endTime\s+[^;]+;', 'endTime 0.00012;'),
            (r'^runTimeModifiable\s+[^;]+;', 'runTimeModifiable no;'),
        ):
            text = change_once(text, pattern, replacement)
        control.write_text(text)
        cases[name] = {'dt_s': dt, 'files_sha256': hashes(case)}
    report = {
        'schema': 'porsche-additive-energy-diagnostic-f58/v1',
        'classification': 'local_AlSi10Mg_coupon_discrete_energy_balance_not_M64_or_CP1',
        'source_case': str(source), 'solver_source': str(solver),
        'source_case_sha256': {folder: hashes(source/folder) for folder in ('0', 'constant', 'system')},
        'pinned_solver_source_sha256': PINNED, 'instrumented_solver_sha256': hashes(target),
        'cases': cases, 'columns': list(FIELDS),
        'balance_definition': 'sensible+latent=boundary_diffusion+laser-advection-limiter',
        'sensible_storage_definition': 'sum(rho*Cp_lagged*delta_T*V)/dt, exact discrete Euler term; not rho*Cp*T',
        'latent_storage_definition': '-sum(rho*Lf*delta_alpha_solid*V)/dt',
        'boundary_diffusion_definition': 'volume integral of the same conservative fvc::laplacian(kappa,T) used by solver; includes imposed thermal boundary fluxes',
        'not_modeled_or_qualified': ['evaporation loss not added', 'supplier absorption calibration',
                                   'full melt-flow hydrodynamics', 'full build distortion', 'M64 head'],
        'physics_changed_between_pair': False, 'temperature_limiter_k': 3300,
        'end_time_s': .00012, 'manufacturing_authorized': False,
    }
    (output/'manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


def evaluate(path, expected_dt):
    text = path.read_text()
    rows = []
    for line in text.splitlines():
        if line.startswith('F58_BALANCE '):
            values = tuple(map(float, line.split()[1:]))
            if len(values) != len(FIELDS) or not all(math.isfinite(v) for v in values):
                raise ValueError('invalid energy sample')
            rows.append(dict(zip(FIELDS, values)))
    if not rows:
        raise ValueError('missing instrumented energy samples')
    previous = 0.0
    residual_disagreements = []
    for row in rows:
        if not math.isclose(row['dt_s'], expected_dt, rel_tol=1e-10):
            raise ValueError('time step differs from paired contract')
        if not math.isclose(row['time_s']-previous, expected_dt, rel_tol=1e-7, abs_tol=1e-15):
            raise ValueError('time series incomplete or unordered')
        terms = (row['sensible_storage_w'], row['latent_storage_w'],
                 -row['boundary_diffusion_in_w'], -row['laser_in_w'],
                 row['advective_out_w'], row['limiter_sink_w'])
        recomputed = math.fsum(terms)
        difference = abs(recomputed-row['equation_residual_w'])
        tolerance = RESIDUAL_LOG_ABS_TOL_W + RESIDUAL_LOG_REL_TOL*math.fsum(abs(v) for v in terms)
        if difference > tolerance:
            raise ValueError('logged energy residual inconsistent with component columns')
        residual_disagreements.append(difference)
        # Every integral below uses the independently reconstructed residual.
        row['equation_residual_w'] = recomputed
        previous = row['time_s']
    complete = math.isclose(previous, .00012, rel_tol=0, abs_tol=1e-13)
    integrals = {key.removesuffix('_w')+'_j': math.fsum(row[key]*row['dt_s'] for row in rows)
                 for key in FIELDS if key.endswith('_w')}
    scale = max(abs(integrals['laser_in_j']), 1e-30)
    absolute_residual = math.fsum(abs(r['equation_residual_w'])*r['dt_s'] for r in rows)
    return {'samples': len(rows), 'time_series_complete': complete,
            'fatal_error_in_log': 'FOAM FATAL' in text,
            'solver_exit_code': None, 'solver_exit_status_verified': False,
            'final_time_s': previous, 'max_temperature_k': max(r['max_temperature_k'] for r in rows),
            'temperature_cap_hit': any(r['max_temperature_k'] >=3299 for r in rows),
            'integrated_terms': integrals,
            'absolute_residual_energy_j': absolute_residual,
            'relative_absolute_energy_residual': absolute_residual/scale,
            'residual_verification': {
                'method': 'independent_fsum_of_six_component_columns_before_integration',
                'log_precision_significant_digits': 16,
                'rounding_tolerance_formula': 'absolute_w + relative * sum(abs(component_w))',
                'rounding_tolerance_absolute_w': RESIDUAL_LOG_ABS_TOL_W,
                'rounding_tolerance_relative': RESIDUAL_LOG_REL_TOL,
                'max_logged_recomputed_difference_w': max(residual_disagreements),
                'all_logged_residuals_consistent': True,
            },
            'log_sha256': digest(path), 'manufacturing_authorized': False}


def compare(output):
    result = {name: evaluate(output/name/'energy-run.log', dt)
              for name, dt in (('dt', 1e-7), ('dt_half', 5e-8))}
    keys = ('sensible_storage_j', 'latent_storage_j', 'boundary_diffusion_in_j',
            'laser_in_j', 'advective_out_j', 'limiter_sink_j')
    differences = {key: abs(result['dt']['integrated_terms'][key]-result['dt_half']['integrated_terms'][key])
                   / max(abs(result['dt_half']['integrated_terms'][key]), 1e-30) for key in keys}
    prior = output/'energy-report.json'
    return {'schema': 'porsche-additive-energy-results-f58/v2', 'cases': result,
            'postprocessor_sha256': digest(Path(__file__)),
            'prior_report_sha256': digest(prior) if prior.is_file() else None,
            'relative_dt_pair_differences': differences,
            'classification': 'two_time_steps_local_AlSi10Mg_coupon_not_convergence_order_or_physical_validation',
            'manufacturing_authorized': False, 'M64_head_simulated': False,
            'supplier_recipe_calibrated': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('prepare', 'report'))
    p.add_argument('--source', type=Path)
    p.add_argument('--solver', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--report-path', type=Path, help='New receipt path; existing files are never overwritten')
    a = p.parse_args()
    if a.action == 'prepare':
        if a.source is None or a.solver is None:
            p.error('prepare requires --source and --solver')
        prepare(a.source, a.solver, a.output)
        print(json.dumps({'prepared': str(a.output), 'manufacturing_authorized': False}))
    else:
        report = compare(a.output)
        path = a.report_path if a.report_path is not None else a.output/'energy-report.json'
        with path.open('x') as stream:
            json.dump(report, stream, indent=2)
            stream.write('\n')
        print(json.dumps(report))


if __name__ == '__main__':
    main()
