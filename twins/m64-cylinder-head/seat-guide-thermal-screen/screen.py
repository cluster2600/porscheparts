#!/usr/bin/env python3
"""Free-expansion fit screen and dimensionless, local plane-stress ring model.

No material is selected. No CAD is modified. The ring is not the 4V head.
All lengths are millimetres; thermal strains are engineering strains relative
to the same reference temperature, not instantaneous expansion coefficients.
"""
import argparse
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
import sys


DIRECTORY = Path(__file__).resolve().parent
HEAD = DIRECTORY.parent
ROOT = HEAD.parents[1]
LAME_SOURCE = 'https://ocw.mit.edu/courses/22-312-engineering-of-nuclear-reactors-fall-2015/eb49bc4f3e701be60ca651c5a109312f_MIT22_312F15_note_L4.pdf'


def finite(*values):
    if not all(math.isfinite(x) for x in values):
        raise ValueError('all inputs must be finite')


def endpoint_strain(mean_alpha_per_K, reference_C, endpoint_C):
    """Secant coefficient over exactly [reference, endpoint], not alpha(T)."""
    finite(mean_alpha_per_K, reference_C, endpoint_C)
    strain = mean_alpha_per_K * (endpoint_C-reference_C)
    if strain <= -1:
        raise ValueError('thermal expansion would produce nonpositive length')
    return strain


def free_interference(insert_OD_mm, cold_diametral_interference_mm,
                      insert_engineering_strain, head_engineering_strain):
    """Di(Ti)-Dh(Th), with Dh0=Di0-I0; negative result is a free gap."""
    finite(insert_OD_mm, cold_diametral_interference_mm,
           insert_engineering_strain, head_engineering_strain)
    if insert_OD_mm <= 0 or insert_OD_mm-cold_diametral_interference_mm <= 0:
        raise ValueError('insert and housing diameters must be positive')
    if min(insert_engineering_strain, head_engineering_strain) <= -1:
        raise ValueError('thermal expansion would produce nonpositive length')
    # Algebraically equivalent to subtracting two expanded diameters, but
    # avoids subtracting nearly equal numbers for identical thermal strains.
    return (cold_diametral_interference_mm*(1+head_engineering_strain)
            + insert_OD_mm*(insert_engineering_strain-head_engineering_strain))


def critical_cold_interference(insert_OD_mm, insert_strain, head_strain):
    """I0 yielding exactly zero free interference; NOT a recommended fit."""
    free_interference(insert_OD_mm, 0., insert_strain, head_strain)
    return insert_OD_mm*(head_strain-insert_strain)/(1+head_strain)


def free_interference_bounds(insert_OD_mm, cold_range_mm,
                             insert_strain_range, head_strain_range):
    """Extrema over independent rectangular input intervals, not probability.

    The function is multi-affine in I0, eps_i and eps_h: its extrema over the
    full rectangular box occur at corners, not just at an arbitrary grid.
    Floating-point evaluation is not outward-rounded interval arithmetic.
    """
    ranges = (cold_range_mm, insert_strain_range, head_strain_range)
    for values in ranges:
        if len(values) != 2 or values[0] > values[1]:
            raise ValueError('ordered two-element intervals required')
    values = [free_interference(insert_OD_mm, *corner)
              for corner in itertools.product(*ranges)]
    return min(values), max(values)


def lame_normalized(a_over_b, c_over_b, E_insert_over_E_head,
                    nu_insert, nu_head, interference_over_diameter):
    """Two concentric elastic rings, sigma_z=0, contact only, frictionless.

    a=insert inner radius, b=common nominal interface radius, c=housing
    exterior FREE radius. I/D is DIAMETRAL interference / diameter.
    Returns p/E_head and housing bore hoop stress/E_head, not actual MPa.
    None of c/b, E ratio or Poisson ratios is inferred from a 2 mm bridge.
    """
    finite(a_over_b, c_over_b, E_insert_over_E_head, nu_insert, nu_head,
           interference_over_diameter)
    if not 0 <= a_over_b < 1 or c_over_b <= 1:
        raise ValueError('require 0 <= a/b < 1 < c/b')
    if E_insert_over_E_head <= 0 or not (-1 < nu_insert < .5 and -1 < nu_head < .5):
        raise ValueError('require positive E ratio and isotropic elastic -1 < nu < 0.5')
    ki = (1+a_over_b**2)/(1-a_over_b**2)-nu_insert
    kh_stress = (c_over_b**2+1)/(c_over_b**2-1)
    kh = kh_stress+nu_head
    compliance_times_E_head = ki/E_insert_over_E_head+kh
    gain = 1/compliance_times_E_head
    pressure = max(0., interference_over_diameter)*gain
    return {'pressure_over_E_head': pressure,
            'pressure_over_E_head_per_interference_over_D': gain,
            'housing_bore_hoop_stress_over_E_head': pressure*kh_stress,
            'housing_bore_von_mises_over_E_head': pressure*math.sqrt(kh_stress**2+kh_stress+1),
            'contact_active_in_ideal_ring': interference_over_diameter > 0}


def load(path):
    return json.loads(path.read_text())


def provenance(path):
    return {'path': str(path.relative_to(ROOT)),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def generate_report():
    module_path = HEAD/'source/build_four_valve_distribution.py'
    spec = importlib.util.spec_from_file_location('m64_distribution_thermal_source', module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    build_path = HEAD/'evidence/four-valve-design-v2-20260907/build-report.json'
    audit_path = build_path.with_name('audit-report.json')
    build, audit = load(build_path), load(audit_path)
    p = module.Parameters(**build['parameters']).validate()
    mahle_path = HEAD/'valve-module-documentary-references-20260907.json'
    cte_path = HEAD/'cp1-hot-points-supplement-20260907.json'
    mahle, cte = load(mahle_path), load(cte_path)
    components = []
    for valve in module.valve_specs(p)[::2]:
        profiles, _ = module.profiles(p, valve)
        for role in ('seat', 'guide'):
            profile = profiles[role]
            OD = 2*max(r for r, z in profile)
            item = {'id': valve['name'].rsplit('_', 1)[0]+'_'+role,
                    'role': role, 'count_per_4v_module': 2,
                    'outer_diameter_mm': OD,
                    'minimum_inner_diameter_mm': 2*min(r for r, z in profile),
                    'geometry_scope': 'own_mm_design_module_not_Porsche_fitment',
                    'cold_diametral_interference_selected_mm': None}
            if role == 'seat':
                rows = [row for row in mahle['seat_insert_retention_reference']['rows']
                        if row['seat_insert_outer_diameter_range_mm'][0] < OD < row['seat_insert_outer_diameter_range_mm'][1]]
                if len(rows) != 1:
                    raise ValueError('unambiguous MAHLE diameter reference row required')
                item['cold_reference_range_mm'] = rows[0]['interference_range_mm']
                item['reference_scope'] = 'generic_MAHLE_aluminum_head_not_selected_LPBF_turbo_fit'
            else:
                item['cold_reference_range_mm'] = None
                item['reference_scope'] = 'guide_to_head_press_fit_unknown_running_clearance_not_reused'
            components.append(item)

    # Deliberately synthetic, NOT a stated material property range for steel,
    # bronze or a supplier insert. Uniform-temperature endpoint cases only.
    insert_mean_coefficients = [10e-6, 15e-6, 20e-6]
    endpoints = []
    for point in cte['thermal_expansion_interval_coefficients']:
        T0, T = point['temperature_interval_C']
        eh = endpoint_strain(point['coefficient_per_K'], T0, T)
        rows = []
        for component in components:
            D = component['outer_diameter_mm']
            for alpha in insert_mean_coefficients:
                ei = endpoint_strain(alpha, T0, T)
                row = {'component': component['id'], 'insert_mean_alpha_hypothesis_per_K': alpha,
                       'insert_engineering_strain': ei,
                       'zero_contact_cold_interference_mm': critical_cold_interference(D, ei, eh),
                       'required_design_margin_mm': None,
                       'hot_free_interference_for_cold_reference_range_mm': None}
                cold = component['cold_reference_range_mm']
                if cold:
                    row['hot_free_interference_for_cold_reference_range_mm'] = list(free_interference_bounds(D, cold, [ei, ei], [eh, eh]))
                    row['hot_free_interference_at_cold_reference_midpoint_mm'] = free_interference(D, sum(cold)/2, ei, eh)
                rows.append(row)
        endpoints.append({'head_CTE_source_id': point['source_id'], 'reference_temperature_C': T0,
                          'head_temperature_C': T, 'insert_temperature_C': T,
                          'head_mean_CTE_per_K': point['coefficient_per_K'],
                          'head_engineering_strain': eh, 'rows': rows})

    # Separate Ti and Th: head endpoint remains exactly within its source
    # interval; insert coefficient and temperatures remain artificial inputs.
    source = cte['thermal_expansion_interval_coefficients'][0]
    T0, Th = source['temperature_interval_C']
    eh = endpoint_strain(source['coefficient_per_K'], T0, Th)
    unequal = []
    for Ti in (150., 200., 250.):
        ei = endpoint_strain(15e-6, T0, Ti)
        unequal.append({'insert_temperature_hypothesis_C': Ti, 'head_temperature_hypothesis_C': Th,
                        'reference_temperature_C': T0,
                        'head_CTE_source_id': source['source_id'],
                        'insert_mean_alpha_hypothesis_per_K': 15e-6,
                        'zero_contact_cold_interference_mm': {
                            part['id']: critical_cold_interference(part['outer_diameter_mm'], ei, eh)
                            for part in components}})

    normalized = []
    for component in components:
        for c_over_b in (1.1, 1.5, 2.):
            ratio = component['minimum_inner_diameter_mm']/component['outer_diameter_mm']
            result = lame_normalized(ratio, c_over_b, 3., .3, .3, .001)
            normalized.append({'component': component['id'], 'a_over_b': ratio,
                               'c_over_b_hypothesis': c_over_b,
                               'E_insert_over_E_head_hypothesis': 3.,
                               'nu_insert_hypothesis': .3, 'nu_head_hypothesis': .3,
                               'interference_over_D_hypothesis': .001, **result})

    return {'schema': 'm64-seat-guide-free-expansion-screen/v1',
            'status': 'parametric_analytical_screen_not_material_selection_or_head_FEA',
            'manufacturing_authorized': False, 'material_selected': False,
            'head_contact_pressure_MPa': None, 'head_stress_MPa': None,
            'source_bindings': [provenance(path) for path in (Path(__file__).resolve(), module_path, build_path, audit_path, mahle_path, cte_path, build_path.with_name('closed.step'))],
            'equation_reference': {'url': LAME_SOURCE,
                                   'scope': 'radial_equilibrium_and_Hooke_law; plane_stress_compliance_derived_locally_not_copied_from_plane_strain_case'},
            'components': components,
            'synthetic_insert_mean_CTE_values_per_K': insert_mean_coefficients,
            'synthetic_CTE_range_is_material_property_bound': False,
            'cold_reference_temperature_handling': 'MAHLE_room_temperature_no_exact_C; each_case_assumes_dimensions_at_its_CTE_reference_T0_no_cross_source_temperature_rebasing',
            'CTE_endpoint_cases': endpoints,
            'unequal_temperature_hypothesis_cases': unequal,
            'normalized_ring_sensitivity': normalized,
            'four_vs_two_valve_scope': {
                'four_valve_seat_count': 4, 'four_valve_guide_count': 4,
                'four_valve_cold_seat_envelope_gap_mm': audit['seat_envelope_minimum_gap_mm'],
                'gap_is_existing_body_ligament': False,
                'two_valve_seat_outer_diameters_mm': None,
                'two_valve_housing_geometry_known': False,
                'comparison_of_thermal_or_structural_superiority_performed': False,
                'bridge_is_axisymmetric_ring': False},
            'excluded_physics': ['3D_interacting_inclined_seats_and_guides', 'housing_not_yet_defined',
                                 'seat_cone_and_finite_length_end_effects', 'thermal_gradients_and_transients',
                                 'plasticity_creep_relaxation_fatigue', 'friction_roughness_insertion_damage',
                                 'combustion_pressure_valve_impact_and_bolt_loads',
                                 'coupled_contact_heat_conductance', 'press_fit_guide_ID_contraction'],
            'required_data': ['chosen_insert_and_guide_supplier_alloy_and_heat_treatment',
                              'matched_body_insert_guide_expansion_curves_and_uncertainties',
                              'E_T_nu_T_plasticity_creep_strength_for_same_LPBF_build_and_treatment',
                              'actual_seat_and_guide_housing_geometry_and_tolerances_at_named_T0',
                              'guide_to_head_cold_interference_and_engagement',
                              'CHT_temperatures_at_each_side_of_each_contact_through_duty_cycle',
                              'retention_load_requirement_contact_friction_and_heat_transfer_data',
                              'coupled_3D_contact_FEA_and_hot_coupon_retention_tests']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DIRECTORY/'report.json')
    args = parser.parse_args()
    report = generate_report()
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps({'status': report['status'], 'output': str(args.output),
                      'components': len(report['components']), 'CTE_endpoint_cases': len(report['CTE_endpoint_cases']),
                      'manufacturing_authorized': False}))


if __name__ == '__main__':
    main()
