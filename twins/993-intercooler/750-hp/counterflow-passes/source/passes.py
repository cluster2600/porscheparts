#!/usr/bin/env python3
"""Multi-pass cross-counterflow screen of the offset-strip core; no physical acceptance."""
import argparse
import csv
import hashlib
import itertools
import json
import math
import runpy
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
STUDY = HERE.parent
BASE = runpy.run_path(str(STUDY/'source/size_core.py'))
duct, effectiveness, geometry, properties = BASE['duct'], BASE['effectiveness'], BASE['geometry'], BASE['properties']


def validate(card, spec):
    if any(spec['acceptance'].values()) or any(card['acceptance'].values()): raise ValueError('Uncalibrated screen cannot grant acceptance')
    arr = spec['arrangement']
    if sorted(arr['passes']) != arr['passes'] or arr['passes'][0] != 1 or max(arr['passes']) > 8: raise ValueError('Pass list must start at the single-pass reference')
    if min([arr['return_tank_loss_k'], *arr['return_tank_loss_k_sensitivity']]) <= 0: raise ValueError('Return tanks cannot recover pressure')
    if spec['thermal_models']['grid_cells'] < 10: raise ValueError('Grid too coarse')


def series_effectiveness(eps_pass, ratio, passes):
    """Overall counterflow arrangement of identical passes, both streams mixed between passes."""
    if passes == 1: return eps_pass
    if abs(1-ratio) < 1e-12: return passes*eps_pass/(1+(passes-1)*eps_pass)
    x = (1-eps_pass*ratio)/(1-eps_pass)
    return (x**passes-1)/(x**passes-ratio)


def pass_channels(g, passes):
    n = (g['hot_channels_per_tube']-(passes-1))//passes
    if n < 2: raise ValueError('Too few channels per pass')
    return n


def pass_geometry(g, passes):
    out = {**g, 'charge_passes': passes, 'hot_channels_per_pass': pass_channels(g, passes)}
    out['divider_metal_volume_m3'] = (passes-1)*g['tubes']*g['width_mm']*g['hot_gap_mm']*g['wall_mm']*1e-9
    out['metal_volume_m3'] = g['metal_volume_m3']+out['divider_metal_volume_m3']
    return out


def evaluate(g, scenario, a, k_turn, hfactor=1., ffactor=1.):
    """size_core.evaluate with the charge split into passes; identical to it for one pass."""
    passes = g['charge_passes']; np_ = g['hot_channels_per_pass']
    mh, mc = scenario['charge_mass_flow_kg_s'], a['cooling_mass_flow_kg_s']
    tc = a['ambient_c']+273.15; target = a['charge_outlet_target_c']+273.15
    th = (a['compressor_inlet_c']+273.15)*(1+(scenario['compressor_pressure_ratio']**((a['gamma']-1)/a['gamma'])-1)/scenario['compressor_efficiency'])
    pressure = a['ambient_pressure_pa']*scenario['compressor_pressure_ratio']; ch, cc = mh*a['hot_cp_j_kg_k'], mc*a['cold_cp_j_kg_k']
    w, z, h, c, t, wall = [g[k]/1000 for k in ('width_mm', 'depth_mm', 'hot_gap_mm', 'cold_gap_mm', 'fin_mm', 'wall_mm')]
    strip, banks, nt, nh, nc, km = g['strip_length_mm']/1000, g.get('charge_parallel_banks', 1), g['tubes'], g['hot_channels_per_tube'], g['cold_channels_per_gap'], a['metal_k_w_m_k']
    # Entry, exit and every return tank are charged on the pass channel velocity; spread over passes so dp*passes is the total.
    entry = (a['header_loss_k']+(passes-1)*k_turn)/passes
    tout, cout = target, tc
    for _ in range(80):
        hot = duct(h, g['hot_clear_m'], w/banks, nt*np_*banks, mh, (th+tout)/2, pressure, a['hot_cp_j_kg_k'], a, hfactor, ffactor, entry, t, strip)
        hot = {**hot, 'pressure_drop_pa': hot['pressure_drop_pa']*passes, 'flow_length_m': passes*w/banks}
        cold = duct(c, g['cold_clear_m'], z, (nt-1)*nc, mc, (tc+cout)/2, a['ambient_pressure_pa'], a['cold_cp_j_kg_k'], a, hfactor, ffactor, a['ambient_entry_exit_k'], t, strip)
        eta = lambda hh, length: math.tanh(x := math.sqrt(2*hh/(km*t))*length/2)/x
        eh, ec = eta(hot['h_w_m2_k'], h), eta(cold['h_w_m2_k'], c)
        hot_area = passes*(2*(nt-1)*np_*w*g['hot_clear_m']+eh*2*(nt-1)*(np_-1)*w*h)
        cold_area = 2*(nt-1)*nc*z*g['cold_clear_m']+ec*2*(nt-1)*(nc-1)*z*c
        separating = 2*(nt-1)*w*z*passes*np_/nh
        ua = 1/(1/(hot['h_w_m2_k']*hot_area)+wall/(km*separating)+1/(cold['h_w_m2_k']*cold_area))
        cmin, ratio = min(ch, cc), min(ch, cc)/max(ch, cc)
        eps = series_effectiveness(effectiveness(ua/passes/cmin, ratio), ratio, passes)
        q = eps*cmin*(th-tc); new_t, new_c = th-q/ch, tc+q/cc
        if max(abs(new_t-tout), abs(new_c-cout)) < 1e-7: break
        tout, cout = (tout+new_t)/2, (cout+new_c)/2
    else: raise ArithmeticError('Property iteration did not converge')
    admissible = (hot['regime'] not in ('transition_excluded', 'offset_out_of_range') and cold['regime'] not in ('transition_excluded', 'offset_out_of_range')
                  and max(hot['mach'], cold['mach']) < a['max_mach'] and hot['pressure_drop_pa']/pressure < a['max_pressure_fraction'])
    meets = new_t <= target and hot['pressure_drop_pa'] <= a['charge_pressure_loss_budget_pa'] and cold['pressure_drop_pa'] <= a['ambient_pressure_loss_budget_pa']
    return {'scenario': scenario['id'], 'charge_passes': passes, 'return_tank_loss_k': k_turn, 'charge_inlet_c': th-273.15, 'charge_outlet_c': new_t-273.15,
            'engine_inlet_c': new_c-273.15, 'heat_rejection_w': q, 'ua_w_k': ua, 'effectiveness': eps, 'hot': hot, 'cold': cold,
            'charge_capacity_w_k': ch, 'cooling_capacity_w_k': cc, 'energy_residual_w': ch*(th-new_t)-cc*(new_c-tc),
            'correlation_screen_admissible': admissible, 'targets_met': meets, 'assumed_constraints_pass': admissible and meets,
            'physical_performance_accepted': False}


def grid(ua, ch, cc, th, tc, passes, n, order='counter'):
    """Cell balance: cooling air unmixed through every pass, charge mixed only in the return tanks.

    Rows are numbered along the cooling air. In counter order the charge enters the rear row."""
    rows = list(range(passes)); charge_row = rows[::-1] if order == 'counter' else rows
    g = ua/(passes*n*n); hs, cs = ch/n, cc/n; resist = 1/g+1/(2*hs)+1/(2*cs)
    inlet = {r: th for r in rows}; outlet = {}
    for sweep in range(2000):
        air = [tc]*n; change = 0.
        for r in rows:
            slices = [inlet[r]]*n
            for i in range(n):
                for j in range(n):
                    q = (slices[i]-air[j])/resist; slices[i] -= q/hs; air[j] += q/cs
            outlet[r] = sum(slices)/n
        for k in range(1, passes):
            new = outlet[charge_row[k-1]]; change = max(change, abs(new-inlet[charge_row[k]])); inlet[charge_row[k]] = new
        if change < 1e-9: break
    else: raise ArithmeticError('Grid did not converge')
    hot_out = outlet[charge_row[-1]]; cold_out = sum(air)/n
    return {'cells': n, 'order': order, 'charge_outlet_c': hot_out-273.15, 'cooling_outlet_c': cold_out-273.15,
            'energy_residual_w': ch*(th-hot_out)-cc*(cold_out-tc), 'sweeps': sweep+1}


def grid_case(case, a, n, order='counter'):
    return grid(case['ua_w_k'], case['charge_capacity_w_k'], case['cooling_capacity_w_k'], case['charge_inlet_c']+273.15, a['ambient_c']+273.15, case['charge_passes'], n, order)


def candidates(search):
    for face, depth, h, c, ph, pc, t, strip, wall, banks in itertools.product(*(search[k] for k in ('faces_mm', 'depths_mm', 'hot_gaps_mm', 'cold_gaps_mm', 'hot_pitches_mm', 'cold_pitches_mm', 'fins_mm', 'strips_mm', 'walls_mm', 'charge_parallel_banks'))):
        g = geometry((*face, depth, h, c, ph, pc, t), wall); g.update(fin_family='offset', strip_length_mm=strip, charge_parallel_banks=banks)
        yield g


def summary(g, cases, a):
    return {'geometry': {k: v for k, v in g.items() if not k.endswith('_m')}, 'mass_kg': g['metal_volume_m3']*a['metal_density_kg_m3'],
            'max_charge_outlet_c': max(c['charge_outlet_c'] for c in cases), 'max_hot_dp_pa': max(c['hot']['pressure_drop_pa'] for c in cases),
            'max_cold_dp_pa': max(c['cold']['pressure_drop_pa'] for c in cases), 'max_hot_re': max(c['hot']['re'] for c in cases)}


def run(output):
    if output.exists(): raise FileExistsError(output)
    card = json.loads((STUDY/'requirements.json').read_text()); spec = json.loads((HERE/'assumptions.json').read_text())
    validate(card, spec); a = card['assumed']; arr = spec['arrangement']; k0 = arr['return_tank_loss_k']; n = spec['thermal_models']['grid_cells']
    stress = (a['heat_transfer_multiplier_stress'], a['friction_multiplier_stress'])
    witness = json.loads((STUDY/'results/thin-sizing.json').read_text())['best_screen_candidate']
    thin = spec['search']; extended = {**thin, **{k: v for k, v in spec['hot_side_extension'].items() if k != 'purpose'}}
    in_thin = lambda g: g['hot_gap_mm'] in thin['hot_gaps_mm'] and g['hot_pitch_mm'] in thin['hot_pitches_mm']
    rows, near = [], []
    for base in candidates(extended):
        for p in arr['passes']:
            try: g = pass_geometry(base, p)
            except ValueError: continue
            cases = [evaluate(g, s, a, k0, *stress) for s in a['scenarios']]
            passed = all(c['assumed_constraints_pass'] for c in cases); s = summary(g, cases, a)
            rows.append({**s['geometry'], 'in_thin_search': in_thin(g), 'mass_kg': s['mass_kg'], 'all_scenarios_pass': passed,
                         'all_regimes_admissible': all(c['correlation_screen_admissible'] for c in cases), 'max_charge_outlet_c': s['max_charge_outlet_c'],
                         'max_hot_dp_pa': s['max_hot_dp_pa'], 'max_cold_dp_pa': s['max_cold_dp_pa'], 'max_hot_re': s['max_hot_re']})
            # Keep in-budget, in-domain candidates near the target for the conservative grid ranking.
            if all(c['correlation_screen_admissible'] for c in cases) and s['max_hot_dp_pa'] <= a['charge_pressure_loss_budget_pa'] and s['max_cold_dp_pa'] <= a['ambient_pressure_loss_budget_pa'] and s['max_charge_outlet_c'] <= a['charge_outlet_target_c']+3:
                near.append((s['mass_kg'], g, cases))
    output.mkdir(parents=True)
    with (output/'passes-sweep.csv').open('w', newline='\n') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n'); writer.writeheader(); writer.writerows(rows)

    def rank(entries):
        lightest, conservative, sensitivity = {}, {}, {}
        for p in arr['passes']:
            ranked = sorted((e for e in entries if e[1]['charge_passes'] == p), key=lambda e: (e[0], e[1]['core_volume_l']))
            formula = next((e for e in ranked if all(c['assumed_constraints_pass'] for c in e[2])), None)
            if formula:
                lightest[str(p)] = {**summary(formula[1], formula[2], a), 'stress_cases': formula[2], 'grid_check': [grid_case(c, a, n) for c in formula[2]]}
                sensitivity[str(p)] = [{'return_tank_loss_k': k, 'max_hot_dp_pa': max(evaluate(formula[1], s, a, k, *stress)['hot']['pressure_drop_pa'] for s in a['scenarios']),
                                        'all_scenarios_pass': all(evaluate(formula[1], s, a, k, *stress)['assumed_constraints_pass'] for s in a['scenarios'])} for k in arr['return_tank_loss_k_sensitivity']]
            for _, g, cases in ranked:
                if not all(c['correlation_screen_admissible'] and c['hot']['pressure_drop_pa'] <= a['charge_pressure_loss_budget_pa'] and c['cold']['pressure_drop_pa'] <= a['ambient_pressure_loss_budget_pa'] for c in cases): continue
                checks = [grid_case(c, a, n) for c in cases]
                if all(x['charge_outlet_c'] <= a['charge_outlet_target_c'] for x in checks):
                    conservative[str(p)] = {**summary(g, cases, a), 'grid_max_charge_outlet_c': max(x['charge_outlet_c'] for x in checks), 'grid_check': checks}; break
        return {'lightest_by_passes': lightest, 'lightest_by_passes_grid_conservative': conservative, 'return_tank_sensitivity': sensitivity}
    # Same witness fins, charge split into passes: what counterflow does before the core is resized.
    base = witness['geometry']; witness_passes = []
    for p in arr['passes']:
        g = pass_geometry(base, p); cases = [evaluate(g, s, a, k0, *stress) for s in a['scenarios']]
        witness_passes.append({**summary(g, cases, a), 'all_scenarios_pass': all(c['assumed_constraints_pass'] for c in cases),
                               'high_case': cases[-1], 'high_grid': grid_case(cases[-1], a, n)})
    replay = [evaluate(pass_geometry(base, 1), s, a, k0, *stress) for s in a['scenarios']]
    paths = [Path(__file__), HERE/'assumptions.json', STUDY/'requirements.json', STUDY/'source/size_core.py', STUDY/'results/thin-sizing.json']
    count = lambda sub, key=None: {str(p): sum(1 for r in rows if r['charge_passes'] == p and sub(r) and (key is None or r[key])) for p in arr['passes']}
    report = {'status': 'uncalibrated_multipass_screen', 'candidate_count': len(rows),
              'counts_by_passes': {'thin_search': count(lambda r: r['in_thin_search']), 'extended_search': count(lambda r: True)},
              'passing_by_passes': {'thin_search': count(lambda r: r['in_thin_search'], 'all_scenarios_pass'), 'extended_search': count(lambda r: True, 'all_scenarios_pass')},
              'witness_single_pass_replay_matches_retained': all(abs(r['charge_outlet_c']-c['charge_outlet_c']) < 1e-9 and abs(r['hot']['pressure_drop_pa']-c['hot']['pressure_drop_pa']) < 1e-6 for r, c in zip(replay, witness['stress_cases'])),
              'witness_mass_kg': witness['mass_kg'], 'thin_search': rank([e for e in near if in_thin(e[1])]), 'extended_search': rank(near),
              'witness_fins_split_into_passes': witness_passes, 'acceptance': spec['acceptance'],
              'source_hashes': {str(p.relative_to(STUDY)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
              'sweep_sha256': hashlib.sha256((output/'passes-sweep.csv').read_bytes()).hexdigest()}
    (output/'passes.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', newline='\n')
    print(json.dumps({'count': len(rows), 'passing': report['passing_by_passes'], 'replay': report['witness_single_pass_replay_matches_retained'],
                      **{name: {'lightest': {p: (round(v['mass_kg'], 2), round(v['max_charge_outlet_c'], 2), round(v['max_hot_dp_pa']), round(v['max_cold_dp_pa'])) for p, v in report[name]['lightest_by_passes'].items()},
                                'grid': {p: (round(v['mass_kg'], 2), round(v['grid_max_charge_outlet_c'], 2)) for p, v in report[name]['lightest_by_passes_grid_conservative'].items()}} for name in ('thin_search', 'extended_search')},
                      'witness_split': [(w['geometry']['charge_passes'], round(w['high_case']['charge_outlet_c'], 2), round(w['high_grid']['charge_outlet_c'], 2), round(w['max_hot_dp_pa'])) for w in witness_passes]}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--output', required=True, type=Path); run(p.parse_args().output)
