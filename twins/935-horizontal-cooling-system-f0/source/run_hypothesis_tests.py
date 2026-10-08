#!/usr/bin/env python3
"""Run conditional system loads and an independent rotating-annulus witness."""
import argparse
import importlib.util
import itertools
import json
import math
from pathlib import Path
import shutil

import build_system_twin as twin

STUDY = Path(__file__).resolve().parents[1]
CARDS = STUDY / 'vast-omniverse-screen/materials.json'
SPEC = importlib.util.spec_from_file_location('existing_ccx_screen', STUDY / 'vast-omniverse-screen/source/run_campaign.py')
CCX = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CCX)
ASSUMPTIONS = {
    'annulus_inner_radius_m': 0.020, 'annulus_outer_radius_m': 0.1375,
    'annulus_thickness_m': 0.004, 'blade_count': 9,
    'blade_volume_each_m3': 6e-6, 'blade_lumped_radius_m': 0.100,
    'rotor_rpm': [3000, 6000, 8500, 11000], 'stop_time_s': [0.1, 1.0],
    'network_resistance_multiplier': [0.5, 2.0], 'residual_unbalance_kg_m': 1e-5,
    'gear_speed_ratio': 1.0, 'drive_efficiency': 0.95, 'pulley_pitch_radius_m': 0.05,
    'gear_pitch_diameter_m': 0.04, 'shaft_diameter_m': 0.016,
    'air_density_kg_m3': 1.15, 'air_cp_J_kgK': 1005,
    'map_reference_rpm': 6000, 'map_Q_dp_eta': [[0, 1200, 0.4], [0.6, 1050, 0.65], [1.2, 650, 0.55], [1.8, 0, 0.2]],
    'common_resistance_Pa_s2_m6': 100, 'zone_resistance_Pa_s2_m6': 15000,
    'leak_resistance_Pa_s2_m6': 50000, 'zone_heat_load_W': 3000,
    'zone_UA_W_K': 150, 'zone_capacity_J_K': 8000,
    'inlet_degC': 25, 'initial_zone_degC': 100, 'thermal_step_s': 60,
}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def annulus(card, rpm, radius=None):
    """Free radial boundaries, constant thickness, isotropic plane-stress solution."""
    a, b, t = (twin.positive(ASSUMPTIONS[k]) for k in
               ('annulus_inner_radius_m', 'annulus_outer_radius_m', 'annulus_thickness_m'))
    if a >= b:
        raise ValueError('Inner radius must be smaller than outer radius')
    rho = twin.positive(card['density_g_cm3']) * 1000
    young = twin.positive(card['young_modulus_GPa']) * 1e9
    nu = 0.33  # common screening assumption from the existing material cards
    omega = twin.nonnegative(rpm) * math.pi / 30
    mass = math.pi * (b*b - a*a) * t * rho
    r = a if radius is None else twin.positive(radius)
    if not a <= r <= b:
        raise ValueError('Evaluation radius outside annulus')
    coefficient = (3 + nu) * rho * omega**2 / 8
    radial = coefficient * (a*a + b*b - r*r - a*a*b*b/(r*r))
    hoop = coefficient * (a*a + b*b + a*a*b*b/(r*r) - (1 + 3*nu)/(3 + nu)*r*r)
    return {'mass_kg': mass, 'inertia_kg_m2': mass*(a*a+b*b)/2,
            'radial_stress_pa': radial, 'hoop_stress_pa': hoop,
            'von_mises_pa': math.sqrt(radial**2 + hoop**2 - radial*hoop),
            'radial_displacement_m': r*(hoop - nu*radial)/young}


def make_case(card, rpm, stop, resistance):
    """All physical values below are scenario assumptions, not specimen evidence."""
    disk = annulus(card, rpm)
    rho = card['density_g_cm3'] * 1000
    blade_mass = ASSUMPTIONS['blade_count'] * ASSUMPTIONS['blade_volume_each_m3'] * rho
    mass = disk['mass_kg'] + blade_mass
    inertia = disk['inertia_kg_m2'] + blade_mass * ASSUMPTIONS['blade_lumped_radius_m']**2
    case = json.loads((STUDY / 'operating-case.template.json').read_text())
    case.update(id=f"H-{card['id']}-n{rpm}-stop{stop}-R{resistance}", purpose='hypothesis_screen')
    case['evidence'] = [{'id': 'H-SYSTEM', 'kind': 'assumption', 'sha256': None,
        'locator': 'docs/research/935-horizontal-cooling/HYPOTHESIS_TESTS.md',
        'rejection_test': 'Replace assumed geometry, material coupons, fan map, network, braking and balance with independent measurements'}]
    def record(name, value):
        return {'value': value, 'unit': twin.UNITS[name], 'uncertainty': 0, 'evidence_ids': ['H-SYSTEM']}
    speed_scale = rpm / ASSUMPTIONS['map_reference_rpm']
    # ponytail: affinity-scaled assumed maps only; use accepted CFD/bench maps for specimen predictions.
    fan_map = [[q*speed_scale, p*speed_scale**2, eta] for q, p, eta in ASSUMPTIONS['map_Q_dp_eta']]
    values = dict(engine_rpm=rpm, belt_speed_ratio=1, belt_slip_fraction=0,
        gear_speed_ratio=ASSUMPTIONS['gear_speed_ratio'], rotor_diameter=2*ASSUMPTIONS['annulus_outer_radius_m'],
        blade_count=ASSUMPTIONS['blade_count'], rotor_inertia=inertia, rotor_acceleration=-rpm*math.pi/30/twin.positive(stop),
        residual_unbalance=ASSUMPTIONS['residual_unbalance_kg_m'], air_density=ASSUMPTIONS['air_density_kg_m3'],
        air_cp=ASSUMPTIONS['air_cp_J_kgK'], branch_inlet_temperature=ASSUMPTIONS['inlet_degC'],
        common_resistance=ASSUMPTIONS['common_resistance_Pa_s2_m6']*resistance,
        drive_efficiency=ASSUMPTIONS['drive_efficiency'], input_pulley_pitch_radius=ASSUMPTIONS['pulley_pitch_radius_m'],
        thermal_step=ASSUMPTIONS['thermal_step_s'], map_rotor_rpm=rpm, map_air_density=ASSUMPTIONS['air_density_kg_m3'])
    for name, value in values.items():
        case['parameters'][name] = record(name, value)
    case['parameters']['fan_map'] = record('fan_map', fan_map)
    case['parameters']['fan_map']['uncertainty'] = [[0, 0, 0] for _ in fan_map]
    case.update(pressure_basis='total_to_total', pressure_stations=['assumed_inlet_total', 'assumed_outlet_total'],
                air_topology_confirmed=True, air_topology_evidence_ids=['H-SYSTEM'])
    case['branches'] = []
    for index in range(7):
        leakage = index == 6
        params = {'resistance': record('resistance', resistance*ASSUMPTIONS[
            'leak_resistance_Pa_s2_m6' if leakage else 'zone_resistance_Pa_s2_m6'])}
        if not leakage:
            for name, key in [('solid_heat_load', 'zone_heat_load_W'), ('ua', 'zone_UA_W_K'),
                              ('thermal_capacity', 'zone_capacity_J_K'), ('initial_temperature', 'initial_zone_degC')]:
                params[name] = record(name, ASSUMPTIONS[key])
        case['branches'].append({'id': f'assumed-{index}', 'role': 'leakage' if leakage else 'cooled_zone', 'parameters': params})
    case['scope_exclusions'] += ['scan_derived_geometry', 'measured_fan_map', 'material_part_allowables']
    return case, mass


def annulus_deck(card, radial_elements, rpm):
    """CAX8 half-thickness mesh in r/y; midplane axial symmetry, free radial edges."""
    if isinstance(radial_elements, bool) or not isinstance(radial_elements, int) or radial_elements < 2:
        raise ValueError('At least two radial elements required')
    annulus(card, rpm)  # validate dimensions and material units before preparing a deck
    a, b, t = (ASSUMPTIONS[k]*1000 for k in
               ('annulus_inner_radius_m', 'annulus_outer_radius_m', 'annulus_thickness_m'))
    nodes = {}
    lines = ['*NODE,NSET=NALL']
    for j in range(5):  # two quadratic elements over half the thickness
        for i in range(2*radial_elements+1):
            if i % 2 and j % 2:
                continue
            node = len(nodes)+1
            nodes[i, j] = node
            lines.append(f'{node},{a+(b-a)*i/(2*radial_elements):.12g},{t*j/8:.12g},0')
    lines += ['*ELEMENT,TYPE=CAX8,ELSET=ROTOR']
    for j, i in itertools.product(range(2), range(radial_elements)):
        x, y = 2*i, 2*j
        order = [(x,y),(x+2,y),(x+2,y+2),(x,y+2),(x+1,y),(x+2,y+1),(x+1,y+2),(x,y+1)]
        lines.append(','.join(map(str, [j*radial_elements+i+1]+[nodes[p] for p in order])))
    lines += ['*NSET,NSET=MIDPLANE']
    ids = [node for (i,j),node in nodes.items() if j == 0]
    lines += [','.join(map(str, ids[k:k+12])) for k in range(0,len(ids),12)]
    lines += ['*MATERIAL,NAME=SCREEN', '*ELASTIC', f"{card['young_modulus_GPa']*1000},0.33",
              '*DENSITY', f"{card['density_g_cm3']*1e-9:.12g}", '*SOLID SECTION,ELSET=ROTOR,MATERIAL=SCREEN',
              '*BOUNDARY', 'MIDPLANE,2,2', '*STEP', '*STATIC', '*DLOAD',
              f'ROTOR,CENTRIF,{(rpm*math.pi/30)**2:.12g},0,0,0,0,1,0',
              '*NODE PRINT,NSET=NALL', 'U', '*EL PRINT,ELSET=ROTOR', 'S', '*END STEP', '']
    return '\n'.join(lines)


def run(output, solve_ccx=False):
    output = output.resolve()
    if output.exists() or (output.is_relative_to(twin.ROOT) and not output.is_relative_to(twin.ROOT/'work')):
        raise ValueError('Use a new private output directory')
    cards = CCX.load_inputs(CARDS.parent)[0]['materials']
    output.mkdir(parents=True, mode=0o700)
    write_json(output/'assumptions.json', ASSUMPTIONS)
    write_json(output/'material-cards.json', cards)
    rows = []
    for card, rpm, stop, resistance in itertools.product(cards, ASSUMPTIONS['rotor_rpm'],
            ASSUMPTIONS['stop_time_s'], ASSUMPTIONS['network_resistance_multiplier']):
        case, mass = make_case(card, rpm, stop, resistance)
        result = twin.calculate(case)
        if any(m['status'] != 'hypothesis_calculation' for m in result['models'].values()):
            raise ValueError('Expected all six conditional model groups')
        models = {name: item['values'] for name,item in result['models'].items()}
        disk = annulus(card, rpm)
        torque_sum = abs(models['inertia_and_unbalance']['rotor_acceleration_torque_nm']) + models['steady_drive_budget']['steady_fan_torque_nm']
        row = {'id': case['id'], 'material': card['id'], 'rpm': rpm, 'stop_time_s': stop,
               'resistance_multiplier': resistance, 'assumed_mass_kg': mass,
               'torque_magnitude_sum_nm': torque_sum,
               'gear_tangential_force_envelope_n': 2*torque_sum/ASSUMPTIONS['gear_pitch_diameter_m'],
               'solid_shaft_torsion_envelope_mpa': 16*torque_sum/(math.pi*ASSUMPTIONS['shaft_diameter_m']**3)/1e6,
               'annulus_only_peak_hoop_mpa': disk['hoop_stress_pa']/1e6,
               'models': models, 'digital_twin_validated': False, 'manufacturing_release_allowed': False}
        write_json(output/(case['id']+'.json'), {'case': case, 'result': result, 'screen': row})
        rows.append(row)
    witnesses = []
    if solve_ccx:
        for card in cards:
            if card['id'] not in ('alsi10mg', 'we43', 'ti64'):
                continue
            solutions = [annulus(card, 8500, ASSUMPTIONS['annulus_inner_radius_m']+
                (ASSUMPTIONS['annulus_outer_radius_m']-ASSUMPTIONS['annulus_inner_radius_m'])*i/1000) for i in range(1001)]
            exact_stress = max(v['von_mises_pa'] for v in solutions)/1e6
            exact_u = max(v['radial_displacement_m'] for v in solutions)*1000
            for n in (16, 32, 64):
                folder = output/f"annulus-{card['id']}-n{n}"
                folder.mkdir()
                (folder/'rotor.inp').write_text(annulus_deck(card,n,8500))
                digest = CCX.sha(folder/'rotor.inp')
                CCX.run_ccx(folder,'rotor')
                actual = CCX.parse_static(folder,digest)
                witnesses.append({'material': card['id'], 'radial_elements': n,
                    'axial_half_thickness_elements': 2, 'rpm': 8500, 'deck_sha256': digest,
                    'analytic_peak_mpa': exact_stress, 'analytic_peak_u_mm': exact_u, **actual,
                    'relative_stress_error': abs(actual['von_mises_max_MPa']/exact_stress-1),
                    'relative_displacement_error': abs(actual['maximum_displacement_mm']/exact_u-1)})
        write_json(output/'annulus-ccx.json', witnesses)
    witness_checks = []
    for material in sorted({v['material'] for v in witnesses}):
        medium, fine = [v for v in witnesses if v['material'] == material][-2:]
        change_stress = abs(fine['von_mises_max_MPa']/medium['von_mises_max_MPa']-1)
        change_u = abs(fine['maximum_displacement_mm']/medium['maximum_displacement_mm']-1)
        witness_checks.append({'material': material, 'fine_mesh_stress_change': change_stress,
            'fine_mesh_displacement_change': change_u,
            'passed': fine['relative_stress_error'] < 0.02 and fine['relative_displacement_error'] < 0.01
                      and max(change_stress,change_u) < 0.05})
    if witnesses and not all(v['passed'] for v in witness_checks):
        raise ValueError('Rotating-annulus witness has not converged within declared limits')
    checks = {'relative_mass_balance': 0, 'relative_pressure_balance': 0, 'relative_drive_energy_balance': 0,
              'relative_braking_work_balance': 0}
    for row in rows:
        flow, drive, dynamics = (row['models'][key] for key in ('airflow', 'steady_drive_budget', 'inertia_and_unbalance'))
        checks['relative_mass_balance'] = max(checks['relative_mass_balance'],abs(flow['mass_balance_residual_m3_s'])/flow['volume_flow_m3_s'])
        checks['relative_pressure_balance'] = max(checks['relative_pressure_balance'],abs(flow['pressure_balance_residual_pa'])/flow['total_pressure_rise_pa'])
        checks['relative_drive_energy_balance'] = max(checks['relative_drive_energy_balance'],
            abs(drive['steady_drive_loss_w']+flow['fan_shaft_power_w']-drive['steady_drive_input_power_w'])/drive['steady_drive_input_power_w'])
        work = abs(dynamics['rotor_acceleration_torque_nm'])*(row['rpm']*math.pi/30)/2*row['stop_time_s']
        checks['relative_braking_work_balance'] = max(checks['relative_braking_work_balance'],abs(work/dynamics['rotor_kinetic_energy_j']-1))
    if max(checks.values()) > 1e-9:
        raise ValueError('Conditional system conservation check failed')
    report = {'status': 'completed_hypothesis_tests', 'cases': len(rows), 'system_screen': rows,
        'annulus_ccx': witnesses, 'assumptions': ASSUMPTIONS,
        'witness_checks': witness_checks, 'system_conservation_checks': checks,
        'solver': None if not solve_ccx else {'name': 'CalculiX', 'binary_sha256': CCX.sha(Path(shutil.which('ccx'))),
            'static_cases': len(witnesses), 'element_type': 'CAX8', 'axis': 'global_y', 'units': 'mm,N,s,tonne'},
        'source_scan_geometry_loaded': False, 'specimen_airflow_m3_s': None, 'safe_rotor_speed_rpm': None,
        'fatigue_life_cycles': None, 'digital_twin_validated': False, 'manufacturing_release_allowed': False,
        'limits': 'Assumed lumped rotor and air network; annulus FEA excludes blades, shaft fit, contacts, thermal gradients and material qualification. Torque sum is a magnitude envelope, not a signed transient solution.'}
    write_json(output/'results.json', report)
    source_paths = [Path(__file__), STUDY/'source/build_system_twin.py', CARDS, STUDY/'vast-omniverse-screen/source/run_campaign.py', STUDY/'operating-case.template.json']
    write_json(output/'manifest.json', {'source_sha256': {str(p.relative_to(twin.ROOT)): CCX.sha(p) for p in source_paths},
        'files_sha256': {str(p.relative_to(output)): CCX.sha(p) for p in sorted(output.rglob('*')) if p.is_file()}})
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--ccx', action='store_true')
    args = parser.parse_args()
    result = run(args.output, args.ccx)
    print(json.dumps({'cases': result['cases'], 'ccx_runs': len(result['annulus_ccx']), 'validation': False}))
