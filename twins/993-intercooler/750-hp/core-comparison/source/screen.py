#!/usr/bin/env python3
"""Three-family core screen (offset strip witness, helical tube bank, gyroid); no physical acceptance."""
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
properties, effectiveness = BASE['properties'], BASE['effectiveness']

# Incropera table 7.6, staggered banks, Re_max > 1000.
ROW_CORRECTION = [(1, .64), (2, .76), (3, .84), (4, .89), (5, .92), (7, .95), (10, .97), (13, .98), (16, .99), (20, 1.)]


def validate(card, spec):
    if any(spec['acceptance'].values()) or any(card['acceptance'].values()): raise ValueError('Uncalibrated screen cannot grant acceptance')
    h, g = spec['helical'], spec['gyroid']
    if min(h['web_mm']) < 4*spec['coupon_voxel_mm'] or h['tube_wall_mm'] <= 0: raise ValueError('Unresolved helical walls')
    if min(h['twist_ratio_y']) < 2.5 or min(h['transverse_pitch_over_outer_diameter']) <= 1: raise ValueError('Helical layout outside screen')
    if any(2*t >= c for c in g['cell_mm'] for t in g['wall_mm']) or g['tortuosity'] < 1: raise ValueError('Gyroid sheet blocks the cell')


def row_correction(rows):
    if rows >= 20: return 1.
    for (n0, c0), (n1, c1) in zip(ROW_CORRECTION, ROW_CORRECTION[1:]):
        if n0 <= rows <= n1: return c0+(c1-c0)*(rows-n0)/(n1-n0)
    raise ValueError('No tube rows')


def twisted_tape(mass, d, web, y, length, temp, pressure, a, hfactor, ffactor):
    """Manglik-Bergles 1993 turbulent form; worst case of two flow-area conventions."""
    rho, mu, k = properties(temp, pressure, a['hot_cp_j_kg_k'], a['gas_constant_j_kg_k'])
    r = web/d; blockage = math.pi/(math.pi-4*r); wetted = (math.pi+2-2*r)/(math.pi-4*r)
    out = []
    for area in (math.pi*d*d/4, math.pi*d*d/4-web*d):
        u = mass/(rho*area); re = rho*u*d/mu
        nu = .023*re**.8*.71**.4*(1+.769/y)*blockage**.8*wetted**.2
        f = .0791*re**-.25*(1+2.752/y**1.29)*blockage**1.75*wetted**1.25
        out.append({'re': re, 'h': hfactor*nu*k/d, 'dp': (ffactor*4*f*length/d+a['header_loss_k'])*rho*u*u/2, 'u': u})
    return {'re': min(o['re'] for o in out), 'h_w_m2_k': min(o['h'] for o in out),
            'pressure_drop_pa': max(o['dp'] for o in out), 'velocity_m_s': max(o['u'] for o in out),
            'mach': max(o['u'] for o in out)/math.sqrt(a['gamma']*a['gas_constant_j_kg_k']*temp),
            'admissible': min(o['re'] for o in out) >= 1e4 and y >= 2.5}


def tube_bank(mass, face, do, st, sl, rows, temp, a, hfactor, ffactor):
    rho, mu, k = properties(temp, a['ambient_pressure_pa'], a['cold_cp_j_kg_k'], a['gas_constant_j_kg_k'])
    v = mass/(rho*face); sd = math.hypot(sl, st/2)
    vmax = v*st/(2*(sd-do)) if 2*(sd-do) < st-do else v*st/(st-do)
    re = rho*vmax*do/mu
    c, m = (.35*(st/sl)**.2, .6) if st/sl < 2 else (.40, .6)
    nu = row_correction(rows)*c*re**m*.71**.36
    fj = (.25+.118/((st-do)/do)**1.08)*re**-.16
    dp = ffactor*2*fj*(rho*vmax)**2*rows/rho+a['ambient_entry_exit_k']*rho*vmax**2/2
    return {'re': re, 'h_w_m2_k': hfactor*nu*k/do, 'pressure_drop_pa': dp, 'velocity_m_s': vmax,
            'mach': vmax/math.sqrt(a['gamma']*a['gas_constant_j_kg_k']*temp), 'admissible': 2000 <= re <= 40000}


def helical_geometry(face, depth, banks, d, wall, web, y, ratio):
    w, s, z = face[0]/1000, face[1]/1000, depth/1000
    di, do = d/1000, (d+2*wall)/1000; st = ratio*do; sl = st*math.sqrt(3)/2
    across, rows = math.floor((s-do)/st)+1, math.floor((z-do)/sl)+1
    if min(across, rows) < 1: raise ValueError('No tubes')
    tubes = across*rows
    metal = (math.pi*(do*do-di*di)/4+web/1000*di)*w*tubes
    return {'family': 'helical', 'width_mm': face[0], 'span_mm': ((across-1)*st+do)*1000, 'depth_mm': ((rows-1)*sl+do)*1000,
            'charge_parallel_banks': banks, 'tube_inner_mm': d, 'tube_wall_mm': wall, 'web_mm': web, 'twist_ratio_y': y,
            'twist_pitch_180_mm': y*d, 'transverse_pitch_mm': st*1000, 'longitudinal_pitch_mm': sl*1000,
            'tubes_across_span': across, 'tube_rows': rows, 'tubes_per_bank': tubes, 'metal_volume_m3': metal,
            'core_volume_l': w*s*z*1000}


def gyroid_geometry(face, depth, banks, cell, wall, area_density):
    w, s, z = face[0]/1000, face[1]/1000, depth/1000
    metal_fraction = area_density*wall/cell
    porosity = (1-metal_fraction)/2
    return {'family': 'gyroid', 'width_mm': face[0], 'span_mm': face[1], 'depth_mm': depth, 'charge_parallel_banks': banks,
            'cell_mm': cell, 'wall_mm': wall, 'network_porosity': porosity, 'metal_fraction': metal_fraction,
            'hydraulic_diameter_mm': 4*porosity*cell/area_density, 'wetted_area_per_side_m2': area_density/(cell/1000)*w*s*z,
            'metal_volume_m3': metal_fraction*w*s*z, 'core_volume_l': w*s*z*1000}


def analogue(mass, area, dh, length, nu, temp, pressure, cp, a, hfactor, ffactor, entry):
    rho, mu, k = properties(temp, pressure, cp, a['gas_constant_j_kg_k'])
    u = mass/(rho*area); re = rho*u*dh/mu
    return {'re': re, 'h_w_m2_k': hfactor*nu*k/dh, 'pressure_drop_pa': (ffactor*64/re*length/dh+entry)*rho*u*u/2,
            'velocity_m_s': u, 'mach': u/math.sqrt(a['gamma']*a['gas_constant_j_kg_k']*temp), 'admissible': False}


def evaluate(g, scenario, a, spec, hfactor=1., ffactor=1., nusselt=4.):
    mh, mc = scenario['charge_mass_flow_kg_s'], a['cooling_mass_flow_kg_s']
    tc = a['ambient_c']+273.15; target = a['charge_outlet_target_c']+273.15
    th = (a['compressor_inlet_c']+273.15)*(1+(scenario['compressor_pressure_ratio']**((a['gamma']-1)/a['gamma'])-1)/scenario['compressor_efficiency'])
    pressure = a['ambient_pressure_pa']*scenario['compressor_pressure_ratio']
    ch, cc = mh*a['hot_cp_j_kg_k'], mc*a['cold_cp_j_kg_k']
    w, s, z, banks, km = g['width_mm']/1000, g['span_mm']/1000, g['depth_mm']/1000, g['charge_parallel_banks'], a['metal_k_w_m_k']
    tout, cout = target, tc
    for _ in range(80):
        if g['family'] == 'helical':
            d, do = g['tube_inner_mm']/1000, (g['tube_inner_mm']+2*g['tube_wall_mm'])/1000; n = g['tubes_per_bank']
            hot = twisted_tape(mh/(banks*n), d, g['web_mm']/1000, g['twist_ratio_y'], w/banks, (th+tout)/2, pressure, a, hfactor, ffactor)
            cold = tube_bank(mc, w*s, do, g['transverse_pitch_mm']/1000, g['longitudinal_pitch_mm']/1000, g['tube_rows'], (tc+cout)/2, a, hfactor, ffactor)
            ua = 1/(1/(hot['h_w_m2_k']*math.pi*d*w*n)+math.log(do/d)/(2*math.pi*km*w*n)+1/(cold['h_w_m2_k']*math.pi*do*w*n))
        else:
            dh, area = g['hydraulic_diameter_mm']/1000, g['wetted_area_per_side_m2']; e = g['network_porosity']; tau = spec['gyroid']['tortuosity']
            hot = analogue(mh/banks, e*s*z, dh, tau*w/banks, nusselt, (th+tout)/2, pressure, a['hot_cp_j_kg_k'], a, hfactor, ffactor, a['header_loss_k'])
            cold = analogue(mc, e*w*s, dh, tau*z, nusselt, (tc+cout)/2, a['ambient_pressure_pa'], a['cold_cp_j_kg_k'], a, hfactor, ffactor, a['ambient_entry_exit_k'])
            ua = 1/(1/(hot['h_w_m2_k']*area)+g['wall_mm']/1000/(km*area)+1/(cold['h_w_m2_k']*area))
        eps = effectiveness(ua/min(ch, cc), min(ch, cc)/max(ch, cc))
        q = eps*min(ch, cc)*(th-tc); new_t, new_c = th-q/ch, tc+q/cc
        if max(abs(new_t-tout), abs(new_c-cout)) < 1e-7: break
        tout, cout = (tout+new_t)/2, (cout+new_c)/2
    else: raise ArithmeticError('Property iteration did not converge')
    in_domain = hot['admissible'] and cold['admissible'] and max(hot['mach'], cold['mach']) < a['max_mach'] and hot['pressure_drop_pa']/pressure < a['max_pressure_fraction']
    meets = new_t <= target and hot['pressure_drop_pa'] <= a['charge_pressure_loss_budget_pa'] and cold['pressure_drop_pa'] <= a['ambient_pressure_loss_budget_pa']
    return {'scenario': scenario['id'], 'charge_inlet_c': th-273.15, 'charge_outlet_c': new_t-273.15, 'engine_inlet_c': new_c-273.15,
            'heat_rejection_w': q, 'ua_w_k': ua, 'effectiveness': eps, 'hot': hot, 'cold': cold,
            'energy_residual_w': ch*(th-new_t)-cc*(new_c-tc), 'correlation_screen_admissible': in_domain,
            'targets_met': meets, 'assumed_constraints_pass': in_domain and meets, 'physical_performance_accepted': False}


def break_even_nusselt(g, a, spec):
    """Smallest equal Nusselt number on both sides that meets all stress cases; None if pressure fails first."""
    cases = lambda nu: [evaluate(g, s, a, spec, a['heat_transfer_multiplier_stress'], a['friction_multiplier_stress'], nu) for s in a['scenarios']]
    probe = cases(4.)
    if any(c['hot']['pressure_drop_pa'] > a['charge_pressure_loss_budget_pa'] or c['cold']['pressure_drop_pa'] > a['ambient_pressure_loss_budget_pa'] for c in probe): return None
    lo, hi = .5, 200.
    if not all(c['targets_met'] for c in cases(hi)): return None
    for _ in range(50):
        mid = (lo+hi)/2
        if all(c['targets_met'] for c in cases(mid)): hi = mid
        else: lo = mid
    return hi


def sweep(card, spec):
    a, env, h, gy = card['assumed'], spec['search_envelope'], spec['helical'], spec['gyroid']
    for face, depth, banks, d, web, y, ratio in itertools.product(env['faces_mm'], env['depths_mm'], env['charge_parallel_banks'], h['tube_inner_diameter_mm'], h['web_mm'], h['twist_ratio_y'], h['transverse_pitch_over_outer_diameter']):
        yield helical_geometry(face, depth, banks, d, h['tube_wall_mm'], web, y, ratio)
    for face, depth, banks, cell, wall in itertools.product(env['faces_mm'], env['depths_mm'], env['charge_parallel_banks'], gy['cell_mm'], gy['wall_mm']):
        yield gyroid_geometry(face, depth, banks, cell, wall, gy['area_density_times_cell'])


def run(output):
    if output.exists(): raise FileExistsError(output)
    card = json.loads((STUDY/'requirements.json').read_text()); spec = json.loads((HERE/'assumptions.json').read_text())
    validate(card, spec); a = card['assumed']; stress = (a['heat_transfer_multiplier_stress'], a['friction_multiplier_stress'])
    witness = json.loads((STUDY/'results/thin-sizing.json').read_text())['best_screen_candidate']
    replay = [BASE['evaluate'](witness['geometry'], s, a, hfactor=stress[0], ffactor=stress[1]) for s in a['scenarios']]
    rows, best = [], {}
    for g in sweep(card, spec):
        cases = [evaluate(g, s, a, spec, *stress) for s in a['scenarios']]
        mass = g['metal_volume_m3']*a['metal_density_kg_m3']
        passed = all(c['assumed_constraints_pass'] for c in cases); analogue_pass = all(c['targets_met'] for c in cases)
        rows.append({**g, 'mass_kg': mass, 'all_scenarios_pass': passed, 'analogue_targets_met': analogue_pass,
                     'all_regimes_admissible': all(c['correlation_screen_admissible'] for c in cases),
                     'max_charge_outlet_c': max(c['charge_outlet_c'] for c in cases), 'max_hot_dp_pa': max(c['hot']['pressure_drop_pa'] for c in cases),
                     'max_cold_dp_pa': max(c['cold']['pressure_drop_pa'] for c in cases), 'min_hot_re': min(c['hot']['re'] for c in cases),
                     'max_cold_re': max(c['cold']['re'] for c in cases)})
        key = g['family'] if g['family'] == 'helical' else 'gyroid_plain_duct_analogue'
        ok = passed if g['family'] == 'helical' else analogue_pass
        if ok and (key not in best or mass < best[key]['mass_kg']): best[key] = {'geometry': g, 'mass_kg': mass, 'stress_cases': cases}
    output.mkdir(parents=True)
    with (output/'screen-sweep.csv').open('w', newline='\n') as stream:
        fields = sorted({k for r in rows for k in r}, key=lambda k: (k != 'family', k))
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n'); writer.writeheader(); writer.writerows(rows)
    hel = [r for r in rows if r['family'] == 'helical']
    rejection = {'helical_count': len(hel), 'hot_reynolds_below_10000': sum(r['min_hot_re'] < 1e4 for r in hel),
                 'cold_reynolds_outside_2000_40000': sum(not 2000 <= r['max_cold_re'] <= 40000 for r in hel),
                 'charge_dp_over_budget': sum(r['max_hot_dp_pa'] > a['charge_pressure_loss_budget_pa'] for r in hel),
                 'ambient_dp_over_budget': sum(r['max_cold_dp_pa'] > a['ambient_pressure_loss_budget_pa'] for r in hel),
                 'outlet_above_target': sum(r['max_charge_outlet_c'] > a['charge_outlet_target_c'] for r in hel),
                 'admissible_and_passing': sum(r['all_scenarios_pass'] for r in hel)}
    # Closest helical candidates: in-domain, within budgets, lowest outlet temperature.
    near = sorted((r for r in hel if r['all_regimes_admissible'] and r['max_hot_dp_pa'] <= a['charge_pressure_loss_budget_pa'] and r['max_cold_dp_pa'] <= a['ambient_pressure_loss_budget_pa']), key=lambda r: r['max_charge_outlet_c'])[:5]
    gy = [r for r in rows if r['family'] == 'gyroid']
    gy_pressure_ok = sorted((r for r in gy if r['max_hot_dp_pa'] <= a['charge_pressure_loss_budget_pa'] and r['max_cold_dp_pa'] <= a['ambient_pressure_loss_budget_pa']), key=lambda r: r['mass_kg'])
    break_even = []
    for r in gy_pressure_ok:
        g = gyroid_geometry((r['width_mm'], r['span_mm']), r['depth_mm'], r['charge_parallel_banks'], r['cell_mm'], r['wall_mm'], spec['gyroid']['area_density_times_cell'])
        nu = break_even_nusselt(g, a, spec)
        if nu is not None: break_even.append({'geometry': g, 'mass_kg': r['mass_kg'], 'required_equal_nusselt': nu})
    break_even.sort(key=lambda b: (b['required_equal_nusselt'], b['mass_kg']))
    # HelixHeatX is a counterflow device: bound the witness UA in ideal counterflow, headers ignored.
    counterflow = []
    for c, s in zip(replay, a['scenarios']):
        ch, cc = s['charge_mass_flow_kg_s']*a['hot_cp_j_kg_k'], a['cooling_mass_flow_kg_s']*a['cold_cp_j_kg_k']
        cmin, cr = min(ch, cc), min(ch, cc)/max(ch, cc); ntu = c['ua_w_k']/cmin
        eps = -math.expm1(-ntu*(1-cr))/(1-cr*math.exp(-ntu*(1-cr)))
        target = (c['charge_inlet_c']-a['charge_outlet_target_c'])*ch/(cmin*(c['charge_inlet_c']-a['ambient_c']))
        counter_ntu = math.log((1-cr*target)/(1-target))/(1-cr)
        counterflow.append({'scenario': s['id'], 'crossflow_unmixed_outlet_c': c['charge_outlet_c'],
                            'required_ua_crossflow_w_k': BASE['required_ua'](ch, cc, c['charge_inlet_c']+273.15, a['ambient_c']+273.15, a['charge_outlet_target_c']+273.15),
                            'required_ua_counterflow_w_k': counter_ntu*cmin,
                            'ideal_counterflow_outlet_c': c['charge_inlet_c']-eps*cmin*(c['charge_inlet_c']-a['ambient_c'])/ch,
                            'status': 'same UA, ideal counterflow topology bound; header turning losses and mixing not modelled'})
    paths = [Path(__file__), HERE/'assumptions.json', STUDY/'requirements.json', STUDY/'source/size_core.py', STUDY/'results/thin-sizing.json']
    report = {'status': 'uncalibrated_family_screen', 'candidate_count': len(rows), 'family_counts': {f: sum(r['family'] == f for r in rows) for f in ('helical', 'gyroid')},
              'witness_offset_strip': {'geometry': witness['geometry'], 'mass_kg': witness['mass_kg'], 'replayed_stress_cases': replay,
                                       'replay_matches_retained': all(abs(r['charge_outlet_c']-c['charge_outlet_c']) < 1e-9 for r, c in zip(replay, witness['stress_cases']))},
              'best_by_family': best, 'helical_rejection_counts': rejection, 'helical_closest_in_domain': near,
              'gyroid_pressure_feasible_count': len(gy_pressure_ok), 'gyroid_break_even_count': len(break_even), 'gyroid_break_even_lowest': break_even[:10],
              'gyroid_break_even_lighter_than_witness': min((b for b in break_even if b['mass_kg'] < witness['mass_kg']), key=lambda b: b['required_equal_nusselt'], default=None),
              'witness_counterflow_bound': counterflow, 'acceptance': spec['acceptance'],
              'source_hashes': {str(p.relative_to(STUDY)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
              'sweep_sha256': hashlib.sha256((output/'screen-sweep.csv').read_bytes()).hexdigest()}
    (output/'screen.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', newline='\n')
    print(json.dumps({'count': len(rows), 'best': {k: round(v['mass_kg'], 2) for k, v in best.items()}, 'rejection': rejection,
                      'break_even': [(b['geometry']['cell_mm'], b['geometry']['wall_mm'], b['geometry']['width_mm'], b['geometry']['span_mm'], b['geometry']['depth_mm'], round(b['mass_kg'], 1), round(b['required_equal_nusselt'], 1)) for b in break_even[:5]],
                      'counterflow': [(c['scenario'], round(c['crossflow_unmixed_outlet_c'], 2), round(c['ideal_counterflow_outlet_c'], 2)) for c in counterflow]}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--output', required=True, type=Path); run(p.parse_args().output)
