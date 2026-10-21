#!/usr/bin/env python3
"""One bounded, assumed-reference arithmetic study; no solver or child process."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from fractions import Fraction

INPUT = Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993/work/962-engineering/material-assumed-reference-proposal-001/proposal.json')
INPUT_SHA = 'e3f8aee9be38df911b489101fe5e3361df142e1bd70a434326dafba91b04c1eb'
PYTHON = Path('/Users/maxime/.codex/worktrees/962-watercooled-head/3dprinting993/work/962-head/check-venv/bin/python')
PYTHON_SHA = '1699bf8aa705a8bb71613bef5cdd7d7c8c9d9a188a841f41679aa9b5830b8f60'
STRAINS = ('0', '0.0005', '0.001', '0.002', '0.004')
OUT = Path(__file__).resolve().parent


def pin(path):
    data = path.read_bytes()
    return {'path': str(path), 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def ratio(value):
    with localcontext() as context:
        context.prec = 50
        decimal = str(Decimal(value.numerator) / Decimal(value.denominator))
    return {'numerator': value.numerator, 'denominator': value.denominator,
            'decimal_50_significant_digits': decimal}


def write_new(path, text):
    with path.open('x', encoding='utf-8', newline='') as stream:
        stream.write(text)


def main():
    signal.alarm(20)
    start = time.monotonic_ns()
    start_utc = datetime.now(timezone.utc).isoformat()
    source = Path(__file__).resolve()
    before = [pin(source), pin(INPUT), pin(PYTHON)]
    if before[1]['sha256'] != INPUT_SHA or before[1]['bytes'] != 7545:
        raise ValueError('Input identity mismatch')
    if before[2]['sha256'] != PYTHON_SHA or before[2]['bytes'] != 49968:
        raise ValueError('Selected Python identity mismatch')
    if not os.path.samefile(sys.executable, PYTHON):
        raise ValueError('Unexpected executable')
    if not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
        raise ValueError('Required -B -I -S isolation flags absent')
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        if os.environ.get(name) != '1':
            raise ValueError('Required one-thread setting absent: ' + name)
    proposal = json.loads(INPUT.read_text(encoding='utf-8'))
    reference = proposal['published_model_input_reference']
    rows = reference['published_rows']
    expected = [(20, 69, 195), (100, 67, 150), (200, 62, 105), (300, 53, 70), (400, 41, 30)]
    if [(r['temperature'], r['elastic_modulus'], r['yield_parameter']) for r in rows] != expected:
        raise ValueError('Unexpected five-row reference table')
    points, crossings = [], []
    for row in rows:
        modulus = Fraction(row['elastic_modulus']) * 1000
        parameter = Fraction(row['yield_parameter'])
        crossing = parameter / modulus
        crossings.append({'temperature_C': row['temperature'],
                          'elastic_trial_parameter_crossing_strain': ratio(crossing)})
        for strain_text in STRAINS:
            strain = Fraction(Decimal(strain_text))
            trial = modulus * strain
            stress_decimal = str(Decimal(trial.numerator) / Decimal(trial.denominator))
            points.append({'temperature_C': row['temperature'],
                           'reference_E_MPa': int(modulus),
                           'published_scalar_parameter_MPa': int(parameter),
                           'assumed_mechanical_strain': strain_text,
                           'elastic_trial_stress_MPa': stress_decimal,
                           'trial_to_scalar_parameter_ratio': ratio(trial / parameter),
                           'elastic_trial_exceeds_scalar_parameter': trial > parameter})
    report = {
        'schema': '962-assumed-reference-prescribed-strain-study/v1',
        'status': 'COMPLETE_25_POINT_ASSUMED_REFERENCE_ARITHMETIC_ONLY',
        'qualification': False, 'production_alloy': None, 'qualified_material_card': None,
        'head_strength_acceptance': False, 'phase5_complete': False,
        'input': before[1], 'reference_source': reference['source'],
        'reference_classification': reference['classification'],
        'assumptions': {
            'temperature_C': [r['temperature'] for r in rows],
            'mechanical_strains': list(STRAINS),
            'idealization': 'Uniform temperature; homogeneous one-dimensional uniaxial small-strain elastic trial; free lateral contraction and zero transverse stress.',
            'strain_origin': 'Declared independent mechanical-strain demand; not a measured or computed head strain, thermal expansion, pressure or restraint load.',
            'formula_MPa': 'elastic_trial_stress = E_GPa * 1000 * assumed_mechanical_strain',
            'crossing_formula': 'published_scalar_parameter_MPa / reference_E_MPa',
            'interpretation': 'Scalar reference-parameter comparison only. Exceedance does not predict yield, failure, plastic flow, post-yield stress, life or a validated material law.',
            'interpolation_extrapolation_fitting': False,
            'arithmetic': 'Fractions are exact; decimal ratios are rounded to 50 significant digits with Decimal ROUND_HALF_EVEN. Exact fractions are authoritative.'
        },
        'property_table_heat_state': reference['property_table_heat_state'],
        'property_table_orientation': reference['property_table_orientation'],
        'missing_constitutive_and_measurement_data': reference['missing_properties'],
        'missing_lifetime_and_LPBF_properties': proposal['missing_lifetime_and_LPBF_properties'],
        'thermal_strain': None, 'plastic_response': None,
        'Materials_2023': 'Separate measured thermal lead; no observations used or blended here.',
        'crossings': crossings, 'points': points,
        'operations': {'solver': False, 'child_process': False, 'geometry_or_scientific_body_read': False,
                       'card_change': False, 'PUB_Git_change': False}
    }
    csv_buffer = io.StringIO(newline='')
    writer = csv.writer(csv_buffer, lineterminator='\n')
    writer.writerow(['temperature_C', 'reference_E_MPa', 'published_scalar_parameter_MPa',
                     'assumed_mechanical_strain', 'elastic_trial_stress_MPa',
                     'trial_ratio_numerator', 'trial_ratio_denominator', 'trial_ratio_decimal_50_digits',
                     'elastic_trial_exceeds_scalar_parameter'])
    for point in points:
        value = point['trial_to_scalar_parameter_ratio']
        writer.writerow([point['temperature_C'], point['reference_E_MPa'], point['published_scalar_parameter_MPa'],
                         point['assumed_mechanical_strain'], point['elastic_trial_stress_MPa'], value['numerator'],
                         value['denominator'], value['decimal_50_significant_digits'],
                         str(point['elastic_trial_exceeds_scalar_parameter']).lower()])
    write_new(OUT / 'results.json', json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    write_new(OUT / 'results.csv', csv_buffer.getvalue())
    after = [pin(source), pin(INPUT), pin(PYTHON)]
    if before != after:
        raise ValueError('Source/input/selected-runtime identity changed across calculation')
    receipt = {
        'status': report['status'], 'qualification': False,
        'started_utc': start_utc, 'finished_utc': datetime.now(timezone.utc).isoformat(),
        'elapsed_monotonic_ns': time.monotonic_ns() - start,
        'point_count': len(points), 'crossing_count': len(crossings),
        'pins_before': before, 'pins_after': after,
        'outputs': [pin(OUT / 'results.json'), pin(OUT / 'results.csv')],
        'runtime': {'sys_executable': sys.executable, 'selected_realpath': str(PYTHON.resolve()),
                    'version': sys.version, 'implementation': sys.implementation.name,
                    'flags': str(sys.flags), 'thread_environment': {name: os.environ[name] for name in
                        ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS')},
                    'stdlib_only': True, 'full_runtime_or_ABI_qualification': False},
        'process_limit': '20-second in-process SIGALRM; no child process or thread pool is created.'
    }
    print(json.dumps(receipt, indent=2, ensure_ascii=False), flush=True)
    signal.alarm(0)


if __name__ == '__main__':
    main()
