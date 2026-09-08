#!/usr/bin/env python3
"""Normalisation analytique du banc; ne calcule aucun débit de culasse."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def ideal_mass_flux(p0, temperature, downstream_pressure, gas_constant=287.05, gamma=1.4):
    """Flux isentropique 1D, en kg/(m² s), amont total et aval statique.

    Il s'agit uniquement du dénominateur conventionnel de CdA. Le col idéal
    est étranglé au rapport critique; ni les pertes ni le débit CAO ne sont résolus.
    """
    values = (p0, temperature, downstream_pressure, gas_constant, gamma)
    if not all(math.isfinite(value) for value in values):
        raise ValueError('Inputs must be finite')
    if min(p0, temperature, gas_constant) <= 0 or not 0 < downstream_pressure <= p0 or gamma <= 1:
        raise ValueError('Require p0,T,R>0, 0<p_downstream<=p0 and gamma>1')
    critical_ratio = (2 / (gamma + 1)) ** (gamma / (gamma - 1))
    ratio = max(downstream_pressure / p0, critical_ratio)
    # expm1 avoids cancellation as pressure drop tends to zero.
    difference = ratio ** (2 / gamma) * -math.expm1((gamma - 1) / gamma * math.log(ratio))
    flux = p0 / math.sqrt(gas_constant * temperature) * math.sqrt(2 * gamma / (gamma - 1) * difference)
    ideal_mach = math.sqrt(2 / (gamma - 1) * math.expm1(-(gamma - 1) / gamma * math.log(ratio)))
    return flux, ideal_mach, downstream_pressure / p0 <= critical_ratio


def reference_report(policy):
    inputs = policy['inputs']
    drop = inputs['pressure_drop_inH2O_conventional'] * inputs['Pa_per_inH2O_conventional']
    pressure = inputs['inlet_total_pressure_Pa'] - drop
    flux, mach, choked = ideal_mass_flux(
        inputs['inlet_total_pressure_Pa'], inputs['inlet_total_temperature_K'], pressure,
        inputs['air_gas_constant_J_kg_K'], inputs['air_gamma_for_reference_normalization'])
    area = inputs['intake_valve_count'] * math.pi * (inputs['reference_throat_diameter_mm'] / 1000) ** 2 / 4
    return {
        'schema': 'm64-flowbench-analytical-reference/v1',
        'status': 'analytical_normalization_only_not_head_flow',
        'pressure_drop_Pa': drop,
        'outlet_static_pressure_Pa': pressure,
        'reference_total_throat_area_m2': area,
        'ideal_isentropic_mass_flux_kg_m2_s': flux,
        'ideal_reference_Mach': mach,
        'ideal_reference_choked': choked,
        'effective_flow_area_formula': 'measured_or_solved_mass_flow_kg_s / ideal_isentropic_mass_flux_kg_m2_s',
        'throat_reference_Cd_formula': 'effective_flow_area_m2 / reference_total_throat_area_m2',
        'head_mass_flow_kg_s': None,
        'head_discharge_coefficient': None,
        'CFD_executed': False,
        'physical_correlation': False,
        'manufacturing_authorized': False,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy', type=Path, default=Path(__file__).with_name('intake-flowbench-pilot.json'))
    args = parser.parse_args()
    data = args.policy.read_bytes()
    result = reference_report(json.loads(data))
    result['policy_sha256'] = hashlib.sha256(data).hexdigest()
    result['source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    print(json.dumps(result, indent=2, allow_nan=False))
