"""Balayage d'alésage : pour chaque alésage, itération (étape 1) avec le motif de goujons 935, puis,
seulement en cas d'échec, avec l'entraxe des goujons libre (conséquence : carter/cylindres non M64).

Usage : python bore_sweep.py <out_json>
"""
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import checks as chk  # noqa: E402
import iterate as it  # noqa: E402
import provenance as pv  # noqa: E402
from layout import derive  # noqa: E402

STUD_CONSEQUENCE = 'motif de goujons changé : carter et cylindres non compatibles M64'


def _space(space, with_studs):
    s = copy.deepcopy(space)
    keep = []
    for v in s['variables']:
        if v['stage'] == 1:
            keep.append(v)
        elif with_studs and v['name'].startswith('stud_span'):
            keep.append(dict(v, stage=1))
    s['variables'] = keep + [v for v in space['variables'] if v['name'] == 'bore_diameter']
    return s


def _order(bores, reference):
    """Du plus proche de l'alésage de référence vers l'extérieur, pour chaîner les démarrages à chaud."""
    up = sorted(b for b in bores if b >= reference)
    down = sorted((b for b in bores if b < reference), reverse=True)
    return up + down


def sweep(spec=None, space=None, bores=None, budget_override=None, seed_design=None):
    spec = spec or pv.load_spec()
    space = space or pv.load_design_space()
    base, _ = pv.resolve_base(spec)
    cfg = dict(space['bore_sweep'], **(budget_override or {}))
    bore_var = [v for v in space['variables'] if v['name'] == 'bore_diameter'][0]
    budget = {k: cfg[k] for k in ('grid_samples', 'local_evaluations', 'search_sweep_step_deg', 'final_sweep_step_deg')}
    bores = list(bores or cfg['bores'])
    for bore in bores:
        if not bore_var['lower'] <= bore <= bore_var['upper']:
            raise ValueError(f'bore {bore} outside [{bore_var["lower"]}, {bore_var["upper"]}]')
    rows, trials = [], 0
    initial = [seed_design] if seed_design else []
    last_ok = {}
    for bore in _order(bores, base['bore_diameter']):
        side_key = bore >= base['bore_diameter']
        seeds = [last_ok[side_key]] if side_key in last_ok else initial
        row = {'bore_diameter': bore, 'bore_band': it.bore_band(bore, space),
               'displacement_cc': round(chk.displacement_cc(bore, base['crank_stroke'], cfg['cylinders']), 1),
               'provenance': 'derived_by_iteration' if abs(bore - base['bore_diameter']) > 1e-9 else 'sourced_m64'}
        for label, with_studs in (('stud_pattern_935', False), ('stud_pattern_free', True)):
            sp = _space(space, with_studs)
            search = it.Search(spec, sp, base, fixed={'bore_diameter': bore}, budget=budget)
            best = search.run(max_stage=1, seed_designs=seeds)
            trials += len(search.history)
            p = derive(base, it.mirror(dict({'bore_diameter': bore}, **best['design']), sp))
            checks, summary = chk.evaluate(p, cfg['final_sweep_step_deg'], force_cycle=True)
            liner = {c['check']: c for c in checks if c['check'] in ('register_vs_required_liner_od', 'liner_od_vs_stud_holes',
                                                                    'stud_wall_to_chamber', 'inter_cylinder_bridge')}
            row[label] = {'accepted': summary['accepted'], 'min_slack': summary['min_slack'],
                          'limiting_check': summary['limiting_check'], 'blocking_failed': summary['blocking_failed'],
                          'trials': len(search.history), 'best_trial': best['trial'], 'design': best['design'],
                          'liner_and_stud_checks': liner,
                          'consequence': STUD_CONSEQUENCE if with_studs else None}
            if summary['accepted']:
                last_ok[side_key] = {k: v for k, v in best['design'].items() if not k.startswith('stud_span')}
                break
        rows.append(row)
    rows.sort(key=lambda r: r['bore_diameter'])
    return dict({
        'schema_version': 1, 'master_geometry': False, 'manufacturing_authorized': False,
        'rule': 'plus petit alésage qui passe préféré ; bande > documented_upper = exploratory_beyond_sources ; '
                'goujons libres seulement si le motif 935 échoue',
        'cylinders': cfg['cylinders'], 'stroke_mm': base['crank_stroke'], 'documented_upper': bore_var['documented_upper'],
        'budget_per_search': budget, 'seed': space['seed'], 'total_trials': trials,
        'inter_cylinder_bridge': 'not_computable',
        'rows': rows,
        'sha256': {'generator': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   'design_space': hashlib.sha256(pv.DESIGN_SPACE.read_bytes()).hexdigest()},
    }, **edges(rows))


def _result(row, pattern):
    """Résultat d'un alésage pour un motif : 'stud_pattern_935' ou 'any' (935, sinon goujons libres)."""
    if pattern == 'stud_pattern_935' or row['stud_pattern_935']['accepted']:
        return row['stud_pattern_935']
    return row.get('stud_pattern_free', row['stud_pattern_935'])


def edges(rows):
    """Alésages min/max qui passent, et contrainte limitante du premier alésage refusé de chaque côté.

    Chaque côté lit le résultat de SON motif de goujons (jamais celui de l'autre)."""
    out = {}
    for pattern, key in (('stud_pattern_935', 'stud_935'), ('any', 'any')):
        ok = [r['bore_diameter'] for r in rows if _result(r, pattern)['accepted']]
        for pick, label in ((min, 'minimal'), (max, 'maximal')):
            if not ok:
                out[f'{label}_passing_bore_{key}'] = None
                continue
            edge = pick(ok)
            outside = [r for r in rows if (r['bore_diameter'] < edge if pick is min else r['bore_diameter'] > edge)]
            if not outside:
                out[f'{label}_passing_bore_{key}'] = {'bore_diameter': edge, 'limit': 'borne du balayage atteinte'}
                continue
            near = max(outside, key=lambda r: r['bore_diameter']) if pick is min else \
                min(outside, key=lambda r: r['bore_diameter'])
            res = _result(near, pattern)
            out[f'{label}_passing_bore_{key}'] = {'bore_diameter': edge, 'first_failing_bore': near['bore_diameter'],
                                                  'limiting_check': res['limiting_check'], 'min_slack': res['min_slack']}
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('out_json')
    ap.add_argument('--seed-manifest', help='manifeste run.py dont la configuration retenue sert de démarrage à chaud')
    args = ap.parse_args()
    seed = None
    if args.seed_manifest:
        seed = json.loads(Path(args.seed_manifest).read_text())['iteration']['design_variables']
    result = sweep(seed_design=seed)
    result['warm_start_from'] = args.seed_manifest
    Path(args.out_json).write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n')
    for r in result['rows']:
        a = r['stud_pattern_935']
        b = r.get('stud_pattern_free')
        print(r['bore_diameter'], r['bore_band'], r['displacement_cc'], a['accepted'], a['min_slack'], a['limiting_check'],
              '|', None if b is None else (b['accepted'], b['min_slack'], b['limiting_check']))
    print(json.dumps({k: result[k] for k in result if k.startswith(('minimal', 'maximal'))}, ensure_ascii=False))
