#!/usr/bin/env python3
"""Convert the frozen 700 PS balance to Garrett's published flow convention.

This is a change of reporting reference, not compressor matching or CFD.
The 460 offset reproduces the rounded Fahrenheit equation in Rev G, page 15.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


BALANCE_SHA256 = 'db181428b99fdf23dea0cd7725e9b6ff3fa37dd6ec752eb2db9fd0f68c3a67ac'
PSI_PA = 6894.757293168
SOURCE_URL = ('https://www.garrettmotion.com/wp-content/uploads/2023/02/'
              '737639-34_781328_Speed_Sensor_Kit_Installation_Instructions_revG.pdf')
SOURCE_SHA256 = 'd000a6b0631e2431692b3bfd09c23d9018d01f00e5e612b61aef3afc9fa78a97'


def corrected_flow(actual_lb_min, inlet_temperature_k, inlet_absolute_pa):
    for value in (actual_lb_min, inlet_temperature_k, inlet_absolute_pa):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError('positive_finite_flow_temperature_absolute_pressure_required')
    inlet_f = (inlet_temperature_k - 273.15) * 9 / 5 + 32
    return actual_lb_min * math.sqrt((inlet_f + 460) / 545) / (inlet_absolute_pa / PSI_PA / 13.95)


def report(data):
    if hashlib.sha256(data).hexdigest() != BALANCE_SHA256:
        raise ValueError('frozen_700ps_balance_required')
    balance = json.loads(data)
    inputs, result = balance['base_inputs'], balance['base_result']
    flow = corrected_flow(result['air_per_turbo_lb_per_min'], inputs['compressor_inlet_temperature_k'],
                          (inputs['ambient_pressure_pa'] - inputs['inlet_pressure_loss_pa']))
    previous = result['corrected_air_per_turbo_lb_per_min_reporting_reference']
    return {
        'schema': 'm64-700ps-garrett-reference/v1',
        'status': 'reporting_reference_conversion_only_not_turbo_selection',
        'balance_sha256': BALANCE_SHA256,
        'source': {'url': SOURCE_URL, 'sha256': SOURCE_SHA256, 'printed_page': 15,
                   'equation': 'Wc = Wactual * sqrt((Tin_F + 460) / 545) / (Pin_psia / 13.95)',
                   'rounded_Fahrenheit_offset_used_as_published': True},
        'air_per_turbo_actual_lb_min': result['air_per_turbo_lb_per_min'],
        'air_per_turbo_corrected_project_reference_lb_min': previous,
        'air_per_turbo_corrected_garrett_revG_lb_min': flow,
        'reference_change_percent': (flow / previous - 1) * 100,
        'pressure_ratio_unchanged': result['compressor_pressure_ratio_required'],
        'thermodynamic_model_changed': False,
        'efficiency_read_from_map': None,
        'shaft_speed_read_from_map': None,
        'surge_choke_speed_margins_qualified': False,
        'borgwarner_numeric_reference_established': False,
        'performance_validated': False,
        'manufacturing_authorized': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = report(Path(__file__).with_name('700ps-balance-20260907.json').read_bytes())
    result['script_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with args.output.open('x') as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
