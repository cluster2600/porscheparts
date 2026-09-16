#!/usr/bin/env python3
"""G2 : choisir les angles de soupape sur le taux de compression BRep, pas sur le proxy numpy.

La recherche G1 ne connaissait aucun critère de combustion et a retenu 33,4°/24,6°, soit une
chambre de 172 cm³ et un taux de 4,5. Ici chaque candidat passe d'abord tous les contrôles
bloquants (numpy), puis son taux est mesuré en BRep ; on garde le meilleur dans la plage.

Usage : tune_compression.py OUT.json [--start EVIDENCE/parameters-resolved.json] [--step 2]
Jamais géométrie maître, jamais autorisation de fabrication.
"""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / 'cad')]

import numpy as np  # noqa: E402

import checks as chk  # noqa: E402
import provenance as pv  # noqa: E402
import run as fv_run  # noqa: E402
from layout import derive  # noqa: E402

EXTRA = HERE / 'params-g2' / 'head_features.json'
G1 = HERE.parents[1] / 'evidence/g1-four-valve-20260914/parameters-resolved.json'


def start_design(path):
    rows = json.loads(Path(path).read_text())
    return {name: row['value'] for name, row in rows.items() if row['provenance'] == 'derived_by_iteration'}


def candidates(base, design, space, step):
    """Angles admissibles, bornes du design_space ; x de tête suit l'angle (tangent à l'arête)."""
    bounds = {v['name']: (v['lower'], v['upper']) for v in space['variables']}
    lo_i, hi_i = bounds['intake_axis_angle']
    lo_e, hi_e = bounds['exhaust_axis_angle']
    for ai in np.arange(lo_i, hi_i + 1e-9, step):
        for ae in np.arange(lo_e, hi_e + 1e-9, step):
            trial = dict(design, intake_axis_angle=float(ai), exhaust_axis_angle=float(ae))
            # Les x de tête de G1 sont figés par l'itération : on les laisse se redériver.
            trial.pop('intake_valve_x', None)
            trial.pop('exhaust_valve_x', None)
            yield trial, derive(base, trial)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('out')
    ap.add_argument('--start', default=str(G1))
    ap.add_argument('--step', type=float, default=2.0)
    ap.add_argument('--max-brep', type=int, default=40, help='nombre maximal de candidats mesurés en BRep')
    args = ap.parse_args()

    spec = fv_run.load_extra(pv.load_spec(), [str(EXTRA)])
    base, _ = pv.resolve_base(spec, pv.load_sources())
    space = pv.load_design_space()
    design = start_design(args.start)

    passing = []
    for trial, p in candidates(base, design, space, args.step):
        checks, summary = chk.evaluate(p, space['budget']['final_sweep_step_deg'], force_cycle=True)
        if not summary['accepted']:
            continue
        passing.append({'design': trial, 'min_slack': summary['min_slack'],
                        'proxy_ratio': round(chk.compression_ratio(p), 3),
                        'proxy_clearance_cc': round(chk.chamber_volume_mm3(p) / 1000, 2)})
    # Mesure BRep par ordre de proxy décroissant : les chambres les plus petites d'abord.
    import assembly
    passing.sort(key=lambda row: -row['proxy_ratio'])
    measured = []
    for row in passing[:args.max_brep]:
        p = derive(base, row['design'])
        brep = assembly.compression_ratio(p)
        row = {**row, 'brep_ratio': brep['compression_ratio'], 'brep_clearance_cc': brep['clearance_volume_cc']}
        measured.append(row)
        print(json.dumps({k: row[k] for k in ('proxy_ratio', 'brep_ratio', 'brep_clearance_cc', 'min_slack')}
                         | {'angles': [row['design']['intake_axis_angle'], row['design']['exhaust_axis_angle']]}),
              flush=True)
    band = (base['compression_ratio_min'], base['compression_ratio_max'])
    in_band = [row for row in measured if band[0] <= row['brep_ratio'] <= band[1]]
    best = max(in_band, key=lambda row: row['min_slack']) if in_band else None
    result = {'schema_version': 1, 'artifact': 'm64_g2_compression_tuning', 'master_geometry': False,
              'manufacturing_authorized': False, 'band': list(band), 'step_deg': args.step,
              'start_design': args.start, 'candidates_passing_checks': len(passing),
              'measured_brep': len(measured), 'in_band': len(in_band),
              'selected': best, 'measured': measured,
              'note': 'angles retenus sur le taux BRep ; le proxy numpy sous-estime le volume mort'}
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps({'passing': len(passing), 'measured': len(measured), 'in_band': len(in_band),
                      'selected': best and {'angles': [best['design']['intake_axis_angle'], best['design']['exhaust_axis_angle']],
                                            'brep_ratio': best['brep_ratio'], 'min_slack': best['min_slack']}},
                     ensure_ascii=False))
    return 0 if best else 2


if __name__ == '__main__':
    raise SystemExit(main())
