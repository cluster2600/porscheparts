#!/usr/bin/env python3
"""G2 : recherche complète avec le critère de combustion, puis mesure BRep du front accepté.

La recherche G1 ne connaissait aucun critère de combustion et a retenu 33,4°/24,6°, soit une
chambre de 172 cm³ et un taux de 4,5. Un balayage des deux seuls angles ne corrige pas cela : les
quinze autres variables de G1 (bougies, poches, calage, longueur de soupape) ont été optimisées
*pour* ces angles, et les déplacer casse les ponts. Le critère descend donc dans l'itération
(``iterate.compression_record``), qui replace toutes les variables ensemble.

Le proxy numpy calibré filtre pendant la recherche ; le taux BRep tranche sur le front accepté.
Chaque mesure BRep tourne dans un sous-processus : OCCT ne rend pas sa mémoire entre deux
constructions de culasse, et une mesure en série finissait tuée (code 137).

Usage : tune_compression.py OUT.json [--top 12] [--seed-design EVIDENCE/parameters-resolved.json]
Jamais géométrie maître, jamais autorisation de fabrication.
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / 'cad')]

import provenance as pv  # noqa: E402

EXTRA = HERE / 'params-g2' / 'head_features.json'
G1 = HERE.parents[1] / 'evidence/g1-four-valve-20260914/parameters-resolved.json'


def seed_design(path):
    """Configuration G1 complète : elle passe déjà les contrôles G2, conduits et galerie compris.

    C'est le seul point admissible connu ; la recherche part de lui et descend vers la plage en
    restant acceptée. Retirer les x de tête reviendrait à jeter cet optimum.
    """
    rows = json.loads(Path(path).read_text())
    return {name: row['value'] for name, row in rows.items() if row['provenance'] == 'derived_by_iteration'}


def resolved(extra):
    import run as fv_run
    spec = fv_run.load_extra(pv.load_spec(), [str(extra)])
    base, _ = pv.resolve_base(spec, pv.load_sources())
    return spec, base


def measure_one(design_path, out_path, extra):
    """Sous-processus : une construction BRep, un taux mesuré, puis le processus rend sa mémoire."""
    import assembly
    from layout import derive
    _, base = resolved(extra)
    p = derive(base, json.loads(Path(design_path).read_text()))
    Path(out_path).write_text(json.dumps(assembly.compression_ratio(p), ensure_ascii=False) + '\n')


def brep_ratio(design, extra):
    with tempfile.TemporaryDirectory() as tmp:
        din, dout = Path(tmp) / 'design.json', Path(tmp) / 'brep.json'
        din.write_text(json.dumps(design))
        cmd = [sys.executable, str(Path(__file__).resolve()), '--measure-one', str(din),
               '--measure-out', str(dout), '--extra', str(extra)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0 or not dout.exists():
            return {'error': f'rc={proc.returncode}', 'stderr': proc.stderr[-800:]}
        return json.loads(dout.read_text())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('out', nargs='?')
    ap.add_argument('--seed-design', default=str(G1), help='configuration de départ chaud (G1 acceptée)')
    ap.add_argument('--top', type=int, default=12, help='candidats acceptés mesurés en BRep')
    ap.add_argument('--local-evaluations', type=int, default=1200,
                    help='budget de recherche locale : G2 doit parcourir 33° -> 16° sans jamais sortir du domaine admissible')
    ap.add_argument('--extra', default=str(EXTRA))
    ap.add_argument('--measure-one', help='interne : mesurer un seul candidat (sous-processus)')
    ap.add_argument('--measure-out')
    args = ap.parse_args()

    if args.measure_one:
        measure_one(args.measure_one, args.measure_out, args.extra)
        return 0

    import iterate as it
    spec, base = resolved(args.extra)
    space = pv.load_design_space()
    budget = dict(space['budget'], local_evaluations=args.local_evaluations)
    search = it.Search(spec, space, base, budget=budget)
    best = search.run(seed_designs=[seed_design(args.seed_design)])
    print(json.dumps({'trials': len(search.history), 'best_trial': best['trial'],
                      'accepted': best['accepted'], 'compression': best.get('compression')}, ensure_ascii=False),
          flush=True)

    # Front accepté, doublons écartés : un même optimum local revient souvent dans la recherche locale.
    ranked = sorted((r for r in search.history if r['accepted']), key=it.Search.rank, reverse=True)
    seen, candidates = set(), []
    for rec in ranked:
        key = tuple(sorted((k, round(v, 2)) for k, v in rec['design'].items()))
        if key in seen:
            continue
        seen.add(key)
        candidates.append(rec)
        if len(candidates) >= args.top:
            break

    measured = []
    for rec in candidates:
        design = it.mirror(dict(rec['design']), space)
        brep = brep_ratio(design, args.extra)
        row = {'design': rec['design'], 'trial': rec['trial'], 'min_slack': rec['min_slack'],
               'limiting_check': rec['limiting_check'], 'proxy': rec.get('compression'), **brep}
        measured.append(row)
        print(json.dumps({'trial': rec['trial'], 'min_slack': rec['min_slack'],
                          'proxy_ratio': (rec.get('compression') or {}).get('proxy_ratio_calibrated'),
                          'brep_ratio': brep.get('compression_ratio'), 'error': brep.get('error')},
                         ensure_ascii=False), flush=True)

    band = (base['compression_ratio_min'], base['compression_ratio_max'])
    in_band = [r for r in measured if r.get('compression_ratio') is not None
               and band[0] <= r['compression_ratio'] <= band[1]]
    selected = max(in_band, key=lambda r: r['min_slack']) if in_band else None
    if selected:  # le facteur observé rend visible la dérive de chamber_proxy_calibration
        selected = dict(selected, observed_calibration=round(
            selected['clearance_volume_cc'] / (selected['proxy']['proxy_clearance_cc']
                                               / base['chamber_proxy_calibration']), 4))
    result = {'schema_version': 1, 'artifact': 'm64_g2_compression_tuning', 'master_geometry': False,
              'manufacturing_authorized': False, 'band': list(band),
              'method': 'recherche complète avec critère de combustion (proxy calibré), puis mesure BRep du front accepté',
              'seed_design': args.seed_design, 'budget': budget, 'trials': len(search.history),
              'accepted_trials': sum(bool(r['accepted']) for r in search.history),
              'candidates_measured': len(measured), 'in_band': len(in_band),
              'selected': selected, 'measured': measured,
              'search_history': search.history, 'front': it.pareto_front(search.history)}
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps({'trials': result['trials'], 'accepted_trials': result['accepted_trials'],
                      'measured': len(measured), 'in_band': len(in_band),
                      'selected': selected and {'trial': selected['trial'], 'brep_ratio': selected['compression_ratio'],
                                                'min_slack': selected['min_slack'],
                                                'observed_calibration': selected['observed_calibration']}},
                     ensure_ascii=False))
    return 0 if selected else 2


if __name__ == '__main__':
    raise SystemExit(main())
