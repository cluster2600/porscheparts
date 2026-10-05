#!/usr/bin/env python3
"""Compare independent holdout observations; never promotes a validated twin."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re

from build_system_twin import finite, nonnegative, ROOT

OUTPUT_UNITS = {
    'input_rpm': 'rpm', 'rotor_rpm': 'rpm', 'tip_speed_m_s': 'm/s',
    'blade_passing_frequency_hz': 'Hz', 'rotor_kinetic_energy_j': 'J',
    'rotor_acceleration_torque_nm': 'N*m', 'unbalance_force_amplitude_n': 'N',
    'rotor_inertia_reflected_to_input_kg_m2': 'kg*m2', 'volume_flow_m3_s': 'm3/s',
    'total_pressure_rise_pa': 'Pa', 'fan_shaft_power_w': 'W', 'total_efficiency': '1',
    'branch_volume_flow_m3_s': 'm3/s', 'parallel_pressure_loss_pa': 'Pa',
    'series_pressure_loss_pa': 'Pa', 'mass_balance_residual_m3_s': 'm3/s',
    'pressure_balance_residual_pa': 'Pa', 'mass_flow_kg_s': 'kg/s',
    'steady_fan_torque_nm': 'N*m', 'steady_drive_input_power_w': 'W',
    'steady_drive_loss_w': 'W', 'steady_drive_input_torque_nm': 'N*m',
    'belt_tension_difference_n': 'N', 'steady_solid_temperature_deg_c': 'degC',
    'solid_temperature_after_step_deg_c': 'degC', 'air_outlet_temperature_after_step_deg_c': 'degC',
    'thermal_time_constant_s': 's', 'steady_air_temperature_rise_k': 'K',
    'transient_heat_to_air_w': 'W',
}


def compare(predictions, rows):
    results = []
    for row in rows:
        if row['dataset_role'] != 'holdout':
            raise ValueError('Calibration rows cannot establish holdout correlation')
        if row['model_case_sha256'] != predictions['case_sha256']:
            raise ValueError('Observation refers to another model case')
        for key in ('measurement_sha256', 'predeclared_tolerance_sha256'):
            if not re.fullmatch(r'[0-9a-f]{64}', row[key]):
                raise ValueError('Pinned measurement and predeclared tolerance required')
        if row['measurement_sha256'] in predictions['input_evidence_sha256']:
            raise ValueError('Holdout artifact was already used as a model input')
        keys = row['quantity_path'].split('.')
        metric = keys[-2] if keys[-1].isdigit() else keys[-1]
        if row['unit'] != OUTPUT_UNITS[metric]:
            raise ValueError('Observation unit differs from prediction unit')
        value = predictions['models'][keys[0]]['values']
        if value is None:
            raise ValueError('Prediction is blocked; no numeric comparison allowed')
        for key in keys[1:]:
            value = value[int(key)] if isinstance(value, list) else value[key]
        value = finite(value)
        observed = finite(float(row['observed']))
        # Report uncertainty as declared; the reduced model does not propagate it.
        u_obs = nonnegative(float(row['observed_standard_uncertainty']))
        u_model = nonnegative(float(row['prediction_standard_uncertainty']))
        tolerance = nonnegative(float(row['acceptance_absolute_error']))
        residual = value - observed
        results.append({'sample_id': row['sample_id'], 'quantity_path': row['quantity_path'],
                        'predicted': value, 'observed': observed, 'residual': residual,
                        'observed_standard_uncertainty': u_obs, 'prediction_standard_uncertainty': u_model,
                        'absolute_error_within_declared_tolerance': abs(residual) <= tolerance})
    return {'status': 'numerical_comparison_only' if results else 'blocked_no_holdout',
            'samples': results, 'all_declared_tolerances_met': all(r['absolute_error_within_declared_tolerance'] for r in results) if results else False,
            'threshold_order_and_artifact_contents_independently_reviewed': False,
            'physical_correlation_approved': False, 'digital_twin_validated': False,
            'manufacturing_release_allowed': False}


def build(prediction_path, observations_path, output):
    output = output.resolve()
    if output.exists() or (output.is_relative_to(ROOT) and not output.is_relative_to(ROOT / 'work')):
        raise ValueError('Use a new private output directory')
    data = json.loads(prediction_path.read_text())
    with observations_path.open(newline='') as source:
        result = compare(data, list(csv.DictReader(source)))
    result['predictions_sha256'] = hashlib.sha256(prediction_path.read_bytes()).hexdigest()
    result['observations_sha256'] = hashlib.sha256(observations_path.read_bytes()).hexdigest()
    text = json.dumps(result, indent=2, allow_nan=False) + '\n'
    output.mkdir(parents=True, mode=0o700)
    p = output / 'holdout-comparison.json'
    p.write_text(text)
    p.chmod(0o600)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--predictions', type=Path, required=True)
    parser.add_argument('--observations', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = build(args.predictions, args.observations, args.output)
    print(f"Holdout comparison: {len(result['samples'])} rows; physical correlation remains unapproved")
