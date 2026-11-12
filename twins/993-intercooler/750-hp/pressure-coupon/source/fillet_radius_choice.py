"""Apply the rib-root fillet criterion fixed in advance; no solver, no qualification.

Reads only the retained reports, the criterion and the sourced process figures.
It runs in well under a second on the standard library and proposes a radius for
the next geometry. It measures nothing and authorises nothing.

  python3 fillet_radius_choice.py --output <new dir>   # write the report
  python3 fillet_radius_choice.py --check              # compare with the committed report
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[3]
CRITERION = ROOT / 'fillet-radius/criterion.json'
CAPABILITY = ROOT / 'fillet-radius/process-capability.json'
CONVERGENCE = ROOT / 'derived/fillet-convergence/fillet-convergence.json'
HYDRAULICS = ROOT / 'derived/fillet-hydraulics/fillet-hydraulics.json'
CFD = ROOT / 'derived/channel-cfd/channel-cfd.json'
REPORT = ROOT / 'derived/fillet-radius-choice/fillet-radius-choice.json'
INPUTS = [CRITERION, CAPABILITY, CONVERGENCE, HYDRAULICS, CFD]
# Fixed by the criterion file; repeated here so that a changed criterion fails the cross-check below.
HYDRAULIC_LIMIT = .05
SCALING_TOLERANCE = .05
SOLID_ANGLE_DEG = 270.
NOISE_SCALES = ['layer_thickness_mm', 'powder_upper_size_mm', 'as_built_roughness_rz_mm']
CLASSES = ['sourced', 'unsettled', 'not_distinguishable', 'rejected']
RIB_MM, WALL_MM, HALF_HEIGHT_MM, LAYER_FOR_CONTEXT = .8, .8, 1.5, 'layer_thickness_mm'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def williams_lambda(solid_angle_deg=SOLID_ANGLE_DEG):
    """First symmetric Williams eigenvalue: lambda sin(2a) + sin(2 lambda a) = 0, a = half the solid angle."""
    a = math.radians(solid_angle_deg) / 2
    f = lambda x: x * math.sin(2 * a) + math.sin(2 * x * a)
    lo, hi = .5, .6
    if f(lo) * f(hi) > 0:
        raise ValueError('eigenvalue not bracketed')
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(lo) * f(mid) > 0 else (lo, mid)
    return (lo + hi) / 2


def sagitta(radius):
    """Greatest distance between the fillet arc and the sharp corner it replaces."""
    return (math.sqrt(2) - 1) * radius


def upper_peak(summary):
    """S of the criterion: the larger Richardson extrapolation, each raised by its fine-grid GCI."""
    return max(summary[k]['extrapolated'] * (1 + summary[k]['gci_fine']) for k in ['root_nodal_richardson', 'integration_point_richardson'])


def low_radius_peak(peak, radius, delta, exponent):
    """S_low of the criterion; None when the reduced radius is not positive (the root may be sharp)."""
    low = radius - delta
    return None if low <= 0 else peak * (radius / low) ** exponent


def classify(tests):
    if tests['M1']['result'] == 'fail' or tests['H1']['result'] == 'fail':
        return 'rejected'
    if any(tests[k]['result'] == 'fail' for k in ['M2', 'P1', 'P2']):
        return 'not_distinguishable'
    if all(tests[k]['result'] == 'pass' for k in ['M1', 'H1', 'M2', 'P1', 'P2', 'P3']) and tests['P2']['every_scale_sourced']:
        return 'sourced'
    return 'unsettled'


def decide(classes):
    """Rules R2 to R6 of the criterion on {radius: class}."""
    radii = sorted(classes)
    if all(classes[r] in ('rejected', 'not_distinguishable') for r in radii):
        return {'proposed_radius_mm': None, 'rule': 'R2', 'design_assumption_only': None, 'other_radius_mm': None, 'other_radius_stays_in_3d_study': None}
    best = min(CLASSES.index(classes[r]) for r in radii)
    tied = [r for r in radii if CLASSES.index(classes[r]) == best]
    chosen = max(tied)
    other = next(r for r in radii if r != chosen)
    return {'proposed_radius_mm': chosen, 'rule': 'R4' if len(tied) > 1 else 'R3', 'design_assumption_only': classes[chosen] != 'sourced',
            'other_radius_mm': other, 'other_radius_stays_in_3d_study': classes[other] in ('sourced', 'unsettled')}


def evaluate():
    criterion, capability = json.loads(CRITERION.read_text()), json.loads(CAPABILITY.read_text())
    convergence, hydraulics, cfd = (json.loads(p.read_text()) for p in [CONVERGENCE, HYDRAULICS, CFD])
    if '5 %' not in criterion['definitions']['hydraulic_limit'] or 'within 5 %' not in criterion['definitions']['scaling_validity_check']:
        raise ValueError('criterion thresholds no longer match this script')
    radii = criterion['candidates_mm']
    screen = convergence['assumed_threshold_mpa']
    lam = williams_lambda()
    exponent = 1 - lam
    summary = {r: convergence['summary'][str(r)] for r in radii}
    nodal = {r: summary[r]['root_nodal_richardson']['extrapolated'] for r in radii}
    lo, hi = min(radii), max(radii)
    predicted, retained = (hi / lo) ** exponent, nodal[lo] / nodal[hi]
    scaling = {'williams_lambda': lam, 'exponent': exponent, 'predicted_peak_ratio': predicted, 'retained_nodal_peak_ratio': retained,
               'relative_difference': retained / predicted - 1, 'tolerance': SCALING_TOLERANCE, 'valid': abs(retained / predicted - 1) <= SCALING_TOLERANCE,
               'note': 'Two radii only: the check cannot show that the scaling holds below 0.2 mm.'}
    sharp_drop = hydraulics['variants']['0.0']['split']['pressure_drop_pa']
    scales = capability['scales']
    out = {}
    for r in radii:
        s, peak = sagitta(r), upper_peak(summary[r])
        converged = all(summary[r][k]['converged_within_gci'] for k in ['root_nodal_richardson', 'integration_point_richardson'])
        penalty = hydraulics['variants'][str(r)]['split']['pressure_drop_pa'] / sharp_drop - 1
        tests = {'M1': {'result': 'pass' if converged and peak < screen else 'fail', 'upper_peak_mpa': peak, 'assumed_screen_mpa': screen, 'both_sequences_converged_within_gci': converged},
                 'H1': {'result': 'pass' if penalty <= HYDRAULIC_LIMIT else 'fail', 'hydraulic_penalty': penalty, 'limit': HYDRAULIC_LIMIT}}
        # M2: only an on-route accuracy decides; indicative figures are reported.
        def m2(row):
            low_peak = low_radius_peak(peak, r, row['value'], exponent)
            return {'delta_offset_mm': row['value'], 'source_id': row['source_id'], 'condition': row.get('condition', row.get('machine')), 'low_radius_mm': r - row['value'],
                    'low_radius_peak_mpa': low_peak, 'below_assumed_screen': low_peak is not None and low_peak < screen}
        on_route = [m2(row) for row in scales['delta_offset_mm']['on_route']] if scaling['valid'] else []
        tests['M2'] = {'result': 'not_evaluable' if not on_route else 'pass' if all(x['below_assumed_screen'] for x in on_route) else 'fail', 'on_route': on_route,
                       'indicative_not_deciding': [m2(row) for row in scales['delta_offset_mm']['indicative']] if scaling['valid'] else []}
        p1 = lambda row: {'stated_minimum_mm': row['value'], 'kind': row['kind'], 'source_id': row['source_id'], 'radius_at_or_above_minimum': r >= row['value']}
        on_route = [p1(row) for row in scales['minimum_internal_radius_or_detail_mm']['on_route']]
        tests['P1'] = {'result': 'not_evaluable' if not on_route else 'pass' if all(x['radius_at_or_above_minimum'] for x in on_route) else 'fail', 'on_route': on_route,
                       'indicative_not_deciding': [p1(row) for row in scales['minimum_internal_radius_or_detail_mm']['indicative']]}
        p2 = lambda name, row: {'scale': name, 'value_mm': row['value'], 'kind': row.get('kind'), 'source_id': row['source_id'], 'form_over_scale': s / row['value'], 'form_above_scale': s > row['value']}
        on_route = [p2(name, row) for name in NOISE_SCALES for row in scales[name]['on_route']]
        unsourced = [name for name in NOISE_SCALES if not scales[name]['on_route']]
        tests['P2'] = {'result': 'pass' if all(x['form_above_scale'] for x in on_route) else 'fail', 'form_mm': s, 'on_route': on_route, 'scales_not_sourced_on_route': unsourced,
                       'every_scale_sourced': not unsourced, 'indicative_not_deciding': [p2(name, row) for name in NOISE_SCALES for row in scales[name]['indicative']]}
        measured = [m for m in capability['as_built_concave_radius_measurements'] if m.get('design_radius_mm', math.inf) <= r]
        tests['P3'] = {'result': 'pass' if measured else 'not_met', 'measurements': measured}
        layer = scales[LAYER_FOR_CONTEXT]['on_route'][0]['value']
        context = {'layers_across_the_radius': r / layer, 'form_over_laser_focus_diameter': s / capability['context_not_deciding']['laser_focus_diameter_mm']['value'],
                   'radius_over_rib_thickness': r / RIB_MM, 'radius_over_passage_half_height': r / HALF_HEIGHT_MM,
                   'added_solid_area_fraction_of_quarter_section': summary[r]['solid_area_mm2'] / convergence['summary']['0.0']['solid_area_mm2'] - 1,
                   'open_area_lost_fraction': 1 - summary[r]['full_section_open_area_mm2'] / convergence['summary']['0.0']['full_section_open_area_mm2'],
                   'retained_cfd_over_proxy': cfd['variants'][str(r)]['finest_over_proxy'], 'nodal_richardson_peak_mpa': nodal[r]}
        out[r] = {'tests': tests, 'class': classify(tests), 'context_not_deciding': context}
    classes = {r: out[r]['class'] for r in radii}
    decision = decide(classes)
    # The criterion says "D90 or the sieve cut" without saying which governs when both are sourced. Both readings are kept.
    powder = sorted(row['value'] for row in scales['powder_upper_size_mm']['on_route'])
    lenient = {}
    for r in radii:
        fails_only_on_larger_powder_figure = [x for x in out[r]['tests']['P2']['on_route'] if not x['form_above_scale']] == [x for x in out[r]['tests']['P2']['on_route'] if x['scale'] == 'powder_upper_size_mm' and x['value_mm'] == powder[-1] and not x['form_above_scale']]
        lenient[r] = 'unsettled' if classes[r] == 'not_distinguishable' and fails_only_on_larger_powder_figure and all(out[r]['tests'][k]['result'] != 'fail' for k in ['M2', 'P1']) else classes[r]
    ambiguity = {'found_at_evaluation': len(powder) > 1,
                 'text': 'The criterion defines the powder scale as the upper particle size, "D90 or the sieve cut", and does not say which governs when both are sourced. Two on-route figures exist. The evaluation requires the fillet form to exceed both, because the scale is defined as the upper size. The criterion file is not amended after the fact.',
                 'on_route_powder_figures_mm': powder,
                 'classes_if_only_the_smaller_figure_counted': {str(r): lenient[r] for r in radii},
                 'decision_if_only_the_smaller_figure_counted': decide(lenient)}
    return {'status': 'criterion_applied_no_new_solver_run', 'criterion_id': criterion['criterion_id'], 'candidates_mm': radii, 'assumed_pressure_mpa': convergence['pressure_mpa'],
            'assumed_screen_mpa': screen, 'assumed_elastic_modulus_mpa': convergence['elastic_modulus_mpa'], 'assumed_poisson_ratio': convergence['poisson_ratio'],
            'scaling_validity_check': scaling, 'radii': {str(r): out[r] for r in radii}, 'classes': {str(r): classes[r] for r in radii}, 'decision': decision,
            'criterion_ambiguity': ambiguity,
            'reading': ['The proposed radius is a design assumption for the 3D study, not a radius shown to be held by any machine.',
                        'Indicative figures come from other machines, layer thicknesses or unnamed service routes. They are reported and never decide a test.',
                        'The low-radius peak is an asymptotic extrapolation checked on two radii; it is not a retained stress result.',
                        'The 40 MPa screen, the 0.375 MPa pressure and the elastic card are assumptions of the coupon study, not qualified values.'],
            'pressure_qualified': False, 'manufacturing_authorized': False, 'lpbf_process_qualified': False, 'new_finite_element_or_cfd_run': False,
            'source_sha256': sha(Path(__file__)), 'input_hashes': {str(p.relative_to(REPO)): sha(p) for p in INPUTS}}


def criterion_commit():
    """Commit that introduced the criterion and commit that last touched it; equal when it was never amended."""
    log = subprocess.run(['git', '-C', str(REPO), 'log', '--format=%H', '--', str(CRITERION.relative_to(REPO))], capture_output=True, text=True, check=True).stdout.split()
    return {'introduced': log[-1], 'last_changed': log[0], 'never_amended': len(log) == 1}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path)
    p.add_argument('--check', action='store_true')
    args = p.parse_args()
    result = evaluate()
    text = json.dumps(result, indent=2) + '\n'
    if args.check:
        if REPORT.read_text() != text:
            sys.exit('fillet-radius-choice.json is stale: rerun with --output and copy the report')
        print('fillet radius choice: report matches its inputs;', result['decision'])
    else:
        if not args.output:
            p.error('--output or --check is required')
        args.output.mkdir(parents=True)
        (args.output / 'fillet-radius-choice.json').write_text(text)
        print(json.dumps({'classes': result['classes'], 'decision': result['decision'], 'criterion_commit': criterion_commit()}, indent=2))
