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


def _rss_mb():
    with open('/proc/self/status') as fh:
        for line in fh:
            if line.startswith('VmRSS:'):
                return int(line.split()[1]) / 1024
    return 0.0


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


def continuation(spec, space, base, seed, args):
    """Descente d'angle par paliers, chaque palier réoptimisé à chaud depuis le précédent.

    La descente par coordonnées seule plafonne : depuis G1 elle remonte le taux de 4,5 à 6,2 puis
    ne trouve plus de voisin meilleur, parce qu'aller vers la plage coûte d'abord de la marge
    géométrique avant d'en rendre. On fige donc les deux angles à chaque palier — les quinze autres
    variables se replacent librement — et on enchaîne les paliers à chaud, comme ``bore_sweep.py``
    le fait pour l'alésage. Le rapport admission/échappement de G1 est conservé.
    """
    import iterate as it
    budget = {'grid_samples': args.continuation_grid, 'local_evaluations': args.continuation_local,
              'search_sweep_step_deg': space['budget']['search_sweep_step_deg'],
              'final_sweep_step_deg': space['budget']['final_sweep_step_deg']}
    angles = {k: seed[k] for k in ('intake_axis_angle', 'exhaust_axis_angle')}
    lower = {v['name']: v['lower'] for v in space['variables']}
    history, warm, rows = [], {k: v for k, v in seed.items() if k not in angles}, []
    factor = 1.0
    while factor > 0.05:
        fixed = {k: max(round(v * factor, 4), lower[k]) for k, v in angles.items()}
        search = it.Search(spec, space, base, fixed=fixed, budget=budget)
        best = search.run(max_stage=1, seed_designs=[warm])
        history += search.history
        comp = best.get('compression') or {}
        rows.append({'factor': round(factor, 3), 'angles': fixed, 'accepted': best['accepted'],
                     'min_slack': best['min_slack'], 'limiting_check': best['limiting_check'],
                     'trials': len(search.history), 'compression': comp})
        print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
        if best['accepted']:
            warm = dict(best['design'])
        over = comp.get('proxy_ratio_calibrated', 0.0) > base['compression_ratio_max'] + \
            base['compression_proxy_band_tolerance']
        if over and best['accepted']:  # la plage est traversée : descendre plus bas n'apporte rien
            break
        if all(fixed[k] <= lower[k] + 1e-9 for k in fixed):
            break
        factor -= args.continuation_step
    return history, rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('out', nargs='?')
    ap.add_argument('--seed-design', default=str(G1), help='configuration de départ chaud (G1 acceptée)')
    ap.add_argument('--top', type=int, default=12, help='candidats acceptés mesurés en BRep')
    ap.add_argument('--select-best-accepted', action='store_true',
                    help='faute de configuration dans la plage, retenir la meilleure acceptée : les preuves CAO '
                         'sont produites, run.py refuse quand même l\'acceptation sur le taux BRep')
    ap.add_argument('--progress', type=int, default=50, help='journaliser un essai sur N (0 : muet)')
    ap.add_argument('--method', choices=('continuation', 'search'), default='continuation',
                    help='continuation : descente d\'angle par paliers (défaut) ; search : recherche unique')
    ap.add_argument('--continuation-step', type=float, default=0.05, help='pas de la descente, en fraction des angles G1')
    ap.add_argument('--continuation-grid', type=int, default=20, help='tirages par palier')
    ap.add_argument('--continuation-local', type=int, default=150, help='évaluations locales par palier')
    ap.add_argument('--local-evaluations', type=int, default=1200,
                    help='budget de recherche locale : G2 doit parcourir 33° -> 16° sans jamais sortir du domaine admissible')
    ap.add_argument('--reselect', help='reprendre le journal d\'un réglage déjà calculé : refaire le choix des '
                                       'candidats et les mesures BRep sans relancer la recherche')
    ap.add_argument('--extra', default=str(EXTRA))
    ap.add_argument('--measure-one', help='interne : mesurer un seul candidat (sous-processus)')
    ap.add_argument('--measure-out')
    args = ap.parse_args()

    if args.measure_one:
        measure_one(args.measure_one, args.measure_out, args.extra)
        return 0

    spec, base = resolved(args.extra)
    space = pv.load_design_space()
    seed = seed_design(args.seed_design)
    if args.reselect:  # refaire le choix et les mesures BRep sur un journal déjà calculé
        history = json.loads(Path(args.reselect).read_text())['search_history']
        previous = json.loads(Path(args.reselect).read_text()).get('angle_ladder')
        return report(args, base, history, ladder=previous)
    if args.method == 'continuation':
        history, ladder = continuation(spec, space, base, seed, args)
        return report(args, base, history, ladder=ladder)

    budget = dict(space['budget'], local_evaluations=args.local_evaluations)
    search = it.Search(spec, space, base, budget=budget)
    if args.progress:  # la recherche est longue et muette : sans trace, un arrêt brutal est illisible
        trial = search.trial

        def traced(design, stage, phase):
            rec = trial(design, stage, phase)
            if rec['trial'] % args.progress == 0:
                print(json.dumps({'trial': rec['trial'], 'stage': stage, 'phase': phase,
                                  'accepted': rec['accepted'], 'min_slack': rec['min_slack'],
                                  'rss_mb': round(_rss_mb(), 1),
                                  'compression': rec.get('compression')}, ensure_ascii=False), flush=True)
            return rec

        search.trial = traced
    best = search.run(seed_designs=[seed])
    print(json.dumps({'trials': len(search.history), 'best_trial': best['trial'],
                      'accepted': best['accepted'], 'compression': best.get('compression')}, ensure_ascii=False),
          flush=True)
    return report(args, base, search.history)


def report(args, base, history, ladder=None):
    import iterate as it
    space = pv.load_design_space()
    # Un seul candidat par palier d'angles : sinon la recherche locale, qui produit des dizaines de
    # variantes voisines du même optimum, monopolise les mesures BRep (constaté : 12 mesures pour
    # une seule configuration). Le meilleur de chaque palier, puis les meilleurs paliers.
    ranked = sorted((r for r in history if r['accepted']), key=it.Search.rank, reverse=True)
    best_per_step = {}
    for rec in ranked:
        key = tuple(sorted((k, round(v, 3)) for k, v in (rec.get('fixed') or {}).items()))
        best_per_step.setdefault(key, rec)
    candidates = sorted(best_per_step.values(), key=it.Search.rank, reverse=True)[:args.top]

    measured = []
    for rec in candidates:
        design = it.mirror(dict(rec.get('fixed') or {}, **rec['design']), space)
        brep = brep_ratio(design, args.extra)
        row = {'design': dict(rec.get('fixed') or {}, **rec['design']), 'trial': rec['trial'], 'min_slack': rec['min_slack'],
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
    out_of_band = False
    if selected is None and args.select_best_accepted:
        # Aucune configuration dans la plage : on retient quand même la meilleure acceptée, pour que
        # les preuves CAO existent. run.py refusera l'acceptation sur le taux BRep, et c'est voulu.
        usable = [r for r in measured if r.get('compression_ratio') is not None]
        selected = max(usable, key=lambda r: r['compression_ratio']) if usable else None
        out_of_band = selected is not None
    if selected:  # le facteur observé rend visible la dérive de chamber_proxy_calibration
        selected = dict(selected, selected_out_of_band=out_of_band, observed_calibration=round(
            selected['clearance_volume_cc'] / (selected['proxy']['proxy_clearance_cc']
                                               / base['chamber_proxy_calibration']), 4))
    result = {'schema_version': 1, 'artifact': 'm64_g2_compression_tuning', 'master_geometry': False,
              'manufacturing_authorized': False, 'band': list(band),
              'method': 'recherche complète avec critère de combustion (proxy calibré), puis mesure BRep du front accepté',
              'seed_design': args.seed_design, 'method_used': args.method, 'trials': len(history),
              'accepted_trials': sum(bool(r['accepted']) for r in history),
              'candidates_measured': len(measured), 'in_band': len(in_band), 'selected_out_of_band': out_of_band,
              'selected': selected, 'measured': measured, 'angle_ladder': ladder,
              'search_history': history, 'front': it.pareto_front(history)}
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps({'trials': result['trials'], 'accepted_trials': result['accepted_trials'],
                      'measured': len(measured), 'in_band': len(in_band),
                      'selected': selected and {'trial': selected['trial'], 'brep_ratio': selected['compression_ratio'],
                                                'min_slack': selected['min_slack'],
                                                'observed_calibration': selected['observed_calibration']}},
                     ensure_ascii=False))
    return 0 if (selected and not out_of_band) else 2


if __name__ == '__main__':
    raise SystemExit(main())
