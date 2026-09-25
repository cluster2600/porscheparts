"""Bounded G6 thermal and mechanical screens, NOT full-head CFD/FEA or allowables."""
import itertools
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np

import features
import kinematics as kin
import rocker_geometry as rg

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'valvetrain'))
import spring_selection as springs


def inputs():
    c = json.loads((HERE / 'g6-inputs.json').read_text())
    p = json.loads((HERE.parents[1] / 'evidence/g5-rocker-train-20260925/candidate.json').read_text())['values']
    p.update(c['geometry_assumptions_mm'])
    return p, c


def positive(*values):
    if not all(math.isfinite(x) and x > 0 for x in values):
        raise ValueError('finite positive physical inputs required')


def fin_conductance(width, thickness, length, k, h, cells=None):
    """SI units; fixed base excess 1 K, insulated tip. Exact or cell-centred FV."""
    positive(width, thickness, length, k, h)
    A, P = width * thickness, 2 * (width + thickness)
    if cells is None:
        return math.sqrt(h * P * k * A) * math.tanh(length * math.sqrt(h * P / (k * A)))
    if not isinstance(cells, int) or cells < 2:
        raise ValueError('at least two finite volumes required')
    dx = length / cells
    G, S = k * A / dx, h * P * dx
    matrix = np.diag(np.full(cells, 2 * G + S))
    matrix += np.diag(np.full(cells - 1, -G), 1) + np.diag(np.full(cells - 1, -G), -1)
    matrix[0, 0], matrix[-1, -1] = 3 * G + S, G + S
    rhs = np.zeros(cells); rhs[0] = 2 * G
    theta = np.linalg.solve(matrix, rhs)
    flux = 2 * G * (1 - theta[0])
    if not math.isclose(flux, float(S * sum(theta)), rel_tol=1e-8, abs_tol=1e-10):
        raise ValueError('finite-volume heat balance failed')
    return float(flux)


def shaft_beam(force_N, span_mm, load_offset_mm, diameter_mm, E_GPa=200):
    """Two equal transverse forces at +/-offset, simply supported ends; no fatigue model."""
    positive(force_N, span_mm, load_offset_mm, diameter_mm, E_GPa)
    L, y, d = np.array([span_mm, load_offset_mm, diameter_mm]) * 1e-3
    if not y < L / 2:
        raise ValueError('loads must lie between supports')
    E, I, a = E_GPa * 1e9, math.pi * d ** 4 / 64, L / 2 - y
    delta = force_N * a * (3 * L * L - 4 * a * a) / (24 * E * I)
    # Independent Euler-Bernoulli stiffness assembly; loads exactly at mesh nodes.
    nodes = np.array([0, a, L / 2, L - a, L])
    K, f = np.zeros((10, 10)), np.zeros(10)
    for i, ell in enumerate(np.diff(nodes)):
        ke = E * I / ell ** 3 * np.array([[12, 6*ell, -12, 6*ell],
            [6*ell, 4*ell**2, -6*ell, 2*ell**2], [-12, -6*ell, 12, -6*ell],
            [6*ell, 2*ell**2, -6*ell, 4*ell**2]])
        ix = np.arange(2*i, 2*i+4); K[np.ix_(ix, ix)] += ke
    f[2] = f[6] = force_N
    free = [i for i in range(10) if i not in (0, 8)]
    u = np.zeros(10); u[free] = np.linalg.solve(K[np.ix_(free, free)], f[free])
    return {'centre_deflection_mm': delta * 1000, 'beam_FE_deflection_mm': float(u[4] * 1000),
            'bending_stress_MPa': 32 * force_N * a / (math.pi * d ** 3) / 1e6,
            'E_GPa_hypothesis': E_GPa, 'stress_allowable_MPa': None}


def hot_fits(p):
    path = HERE.parents[1]/'seat-guide-thermal-screen/screen.py'
    spec = importlib.util.spec_from_file_location('g6_free_expansion',path)
    fit = importlib.util.module_from_spec(spec);spec.loader.exec_module(fit)
    source = HERE.parents[1]/'cp1-hot-points-supplement-20260907.json'
    points = json.loads(source.read_text())['thermal_expansion_interval_coefficients']
    rows=[]
    for point in points:
        if not point['source_id'].startswith('eos_'):continue  # never merge different source/process states
        T0, Th = point['temperature_interval_C']
        eh = fit.endpoint_strain(point['coefficient_per_K'],T0,Th)
        for Ti, alpha in itertools.product((Th,max(T0,Th-100)),(10e-6,15e-6,20e-6)):
            ei = fit.endpoint_strain(alpha,T0,Ti)
            row={'head_C':Th,'insert_hypothesis_C':Ti,'reference_C':T0,'source_id':point['source_id'],
                 'head_mean_CTE_per_K':point['coefficient_per_K'],'insert_mean_CTE_hypothesis_per_K':alpha,
                 'guide_free_interference_mm':fit.free_interference(p['guide_outer_diameter'],p['guide_outer_diameter']-p['guide_head_bore_diameter'],ei,eh)}
            for s in ('intake','exhaust'):
                D=p[s+'_valve_head_diameter']+2*p['seat_insert_radial_wall']
                row[s+'_seat_zero_contact_cold_interference_mm']=fit.critical_cold_interference(D,ei,eh)
            rows.append(row)
    return {'classification':'free_expansion_sensitivity_not_press_fit_selection_or_stress',
            'source_path':str(source),'helper_path':str(path),'seat_cold_interference_selected_mm':None,
            'guide_cold_interference_candidate_mm':p['guide_outer_diameter']-p['guide_head_bore_diameter'],
            'cases':rows,'retention_qualified':False}


def thermal(p, c):
    t, load = c['thermal_sensitivity'], c['load_sensitivity']
    power = load['target_mechanical_hp'] * 745.699871582
    duties = [{'efficiency': eta, 'fraction_to_heads': fraction,
               'heat_per_head_W': power / eta * fraction / load['cylinders']}
              for eta, fraction in itertools.product(load['brake_efficiency'], load['fuel_heat_fraction_to_heads'])]
    boxes = features.fin_boxes(p)
    # Only the two fin-bearing side walls, less fin roots. No top/port flange credit.
    base_area = (2 * (p['exhaust_flange_x'] - p['intake_flange_x']) * p['carrier_face_height']
                 - sum(dx * dz for _, _, _, dx, _, dz in boxes)) * 1e-6
    rows = []
    for k, h in itertools.product(t['constant_k_hypotheses_W_mK'], t['air_h_W_m2K']):
        g = h * base_area
        gf = [h * base_area for _ in (8, 16, 32)]
        for _, _, _, dx, dy, dz in boxes:
            # Corrected length approximates tip convection; same model in both methods.
            args = (dx * .001, dz * .001, (dy + dz / 2) * .001, k, h)
            g += fin_conductance(*args)
            for j, n in enumerate((8, 16, 32)):
                gf[j] += fin_conductance(*args, cells=n)
        qair = g * (t['head_temperature_limit_C'] - t['air_inlet_C'])
        rows.append({'constant_k_hypothesis_W_mK': k, 'air_h_hypothesis_W_m2K': h,
                     'air_capacity_at_screen_ceiling_W': qair, 'air_conductance_W_K': g,
                     'finite_volume_relative_errors_8_16_32': [abs(v/g-1) for v in gf]})
    oil = []
    area = math.pi * p['oil_gallery_diameter'] * p['head_block_width_y'] * 1e-6
    for flow in t['oil_flow_per_head_L_min']:
        Q = flow / 60000
        C = t['oil_density_hypothesis_kg_m3'] * Q * t['oil_cp_hypothesis_J_kgK']
        q = C * (-math.expm1(-t['oil_h_hypothesis_W_m2K'] * area / C)) * (t['head_temperature_limit_C'] - t['oil_inlet_C'])
        d, L, mu = p['oil_gallery_diameter'] * .001, p['head_block_width_y'] * .001, t['oil_dynamic_viscosity_hypothesis_Pa_s']
        reynolds = 4 * t['oil_density_hypothesis_kg_m3'] * Q / (math.pi * mu * d)
        if reynolds >= 2000:
            raise ValueError('laminar gallery screen outside assumed regime')
        oil.append({'assumed_flow_L_min': flow, 'Re': reynolds,
                    'straight_fully_flooded_gallery_dp_Pa': 128 * mu * L * Q / (math.pi * d**4),
                    'gallery_heat_capacity_upper_screen_W': min(q, C * t['oil_rise_limit_K']),
                    'actual_gravity_return_flow_or_cooling_validated': False})
    highest = max(r['air_capacity_at_screen_ceiling_W'] for r in rows) + max(r['gallery_heat_capacity_upper_screen_W'] for r in oil)
    smallest = min(r['heat_per_head_W'] for r in duties)
    q=dict(p,fin_count=17,fin_pitch=3.8,fin_thickness=2,fin_x_margin=0)
    dense=features.fin_boxes(q)
    h,k=max(t['air_h_W_m2K']),max(t['constant_k_hypotheses_W_mK'])
    gd=h*(2*(q['exhaust_flange_x']-q['intake_flange_x'])*q['carrier_face_height']-sum(dx*dz for _,_,_,dx,_,dz in dense))*1e-6
    gd+=sum(fin_conductance(dx*.001,dz*.001,(dy+dz/2)*.001,k,h) for _,_,_,dx,dy,dz in dense)
    return {'classification': 'constant_property_1D_fin_and_bulk_heat_budget_not_CHT',
            'fin_count': len(boxes), 'base_air_area_m2': base_area, 'duty_scenarios': duties,
            'air_scenarios': rows, 'oil_scenarios': oil, 'best_screen_capacity_W': highest,
            'minimum_hypothetical_demand_W': smallest, 'smallest_deficit_W': smallest-highest,
            'any_scenario_meets_heat_budget': highest >= smallest,
            'dense_fin_comparison_not_applied_to_CAD':{'count':len(dense),'thickness_mm':2,'pitch_mm':3.8,
                'same_head_bounding_box':True,'air_capacity_W':gd*(t['head_temperature_limit_C']-t['air_inlet_C']),
                'constant_h_comparison_not_fan_or_pressure_loss_validation':True},
            'optimistic_minimum_effective_air_area_m2': (smallest-max(r['gallery_heat_capacity_upper_screen_W'] for r in oil)) /
                (max(t['air_h_W_m2K']) * (t['head_temperature_limit_C']-t['air_inlet_C'])),
            'limitations': ['uniform fin base temperature, no head conduction resistance', 'constant cold inlet air, no duct/fan pressure loss',
                           'no local exhaust bridge or combustion heat-flux map', 'fully flooded gallery assumption is not the G6 gravity-return condition',
                           'no temperature-dependent material law or radiation model; no operating-temperature prediction']}


def mechanics(p, c):
    load = c['load_sensitivity']
    spring = next(r for r in json.loads(springs.CANDIDATES.read_text())['candidates'] if r['id']=='GSC5092')
    laws, vp = kin.cam_laws(p)
    rows, sdof = [], []
    for side, law in laws.items():
        profile = rg.profile(p, side)
        state, phi = profile['state'], np.radians(profile['phi_deg'])
        sp = springs.spring_from_candidate(spring, p[f'{side}_max_lift'], installed_mm=p['spring_installed_height'])
        open_mask = state['valve_lift_mm'] > .01
        lever = p['rocker_valve_arm'] * np.cos(state['beta']) / (p['rocker_cam_arm'] * np.cos(np.radians(profile['pressure_deg'])))
        for rpm, mass, factor, gas in itertools.product(load['rpm'], load['effective_valve_mass_kg'], load['spring_force_factor'], load['adverse_opening_gas_force_N']):
            motion = law.valve_kinematics(phi, rpm)
            force = factor * (sp['preload_N'] + sp['rate_N_m']*motion['lift_m']) + mass*motion['acceleration_m_s2'] - gas
            normal = force * lever
            # Triangle-inequality reaction bound, not the actual vector bearing reaction.
            reaction_bound = float(np.max(np.abs(normal[open_mask]) + np.abs(force[open_mask])))
            beam = shaft_beam(reaction_bound, 2*p['carrier_end_y'], p[f'{side}_valve_y'], 2*p['rocker_pivot_radius'])
            beam['diameter_required_by_assumed_deflection_budget_mm']=float(2*p['rocker_pivot_radius']*(beam['centre_deflection_mm']/load['shaft_axis_deflection_screen_mm'])**.25)
            rows.append({'side': side, 'rpm': rpm, 'effective_mass_hypothesis_kg': mass, 'spring_force_factor': factor,
                         'adverse_opening_gas_force_N': gas, 'minimum_required_valve_contact_N': float(min(force[open_mask])),
                         'no_forced_lift_contact_loss': bool(min(force[open_mask]) > 0),
                         'peak_required_cam_normal_N': float(max(normal[open_mask])), 'rocker_reaction_bound_N': reaction_bound,
                         'shaft_beam_bound': beam,
                         'shaft_deflection_below_assumed_budget': bool(beam['centre_deflection_mm'] < load['shaft_axis_deflection_screen_mm'])})
        # Existing V1 compliant-contact solver, no arbitrary new integrator.
        weakened = dict(sp, rate_N_m=.8*sp['rate_N_m'], preload_N=.8*sp['preload_N'])
        for n in (7200, 14400, 28800):
            r = kin.v1().simulate_sdof(law, vp[side], weakened, .18, max(load['rpm']), cycles=3, steps_per_cycle=n)
            scalar = {k: v for k, v in r.items() if not isinstance(v, np.ndarray)}
            if not all(math.isfinite(v) for v in scalar.values()):
                raise ValueError('nonfinite SDOF result')
            sdof.append({'side': side, 'steps_per_cycle': n, 'gas_force_N': 0, 'spring_factor': .8,
                         'effective_mass_kg': .18, 'law': 'G5_cold_lash_not_hot_geometry', **scalar})
    return {'classification': 'forced_lift_load_sensitivity_and_1DOF_contact_not_flexible_multibody_validation',
            'spring_curve_reference': spring['url'], 'spring_geometry_or_hot_allowables_qualified': False,
            'force_scenarios': rows, 'compliant_contact_time_step_study': sdof,
            'limitations': ['effective mass assumed, not inferred from component CAD', 'steel E=200 GPa assumed in shaft bound',
                           'two simply-supported journals, no carrier compliance or oil film', 'no material strength allowables, Hertz, fatigue or cam-drive torque qualification']}
