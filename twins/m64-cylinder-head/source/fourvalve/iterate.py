"""Boucle d'itération déterministe : grille pseudo-aléatoire (graine fixée) puis recherche par coordonnées.

Étape 1 : variables non sourcées seulement. Étapes 2 et 3 : ouvertes seulement si l'étape précédente
n'a trouvé aucune configuration acceptée. Chaque essai est journalisé.
"""
import math

import numpy as np

import checks as chk
from layout import derive
from provenance import validate_design

PENALTY = {'bore_diameter': lambda v: 0.5 * abs(v - 100.0),
           'intake_valve_head_diameter': lambda v: 1.0 * (40.0 - v),
           'exhaust_valve_head_diameter': lambda v: 1.0 * (33.0 - v)}


def compression_record(p):
    """Terme de combustion d'un essai, ou ``None`` hors G2.

    Le proxy calibré n'est pas le juge : il oriente la recherche vers la plage, la mesure BRep
    tranche ensuite sur le front accepté (``tune_compression.py``). ``score_penalty`` est tenu à
    part du score géométrique, que G1 journalise déjà : le journal G1 reste reproductible à
    l'octet près et, en G2, la part géométrique et la part combustion restent lisibles séparément.
    """
    if 'compression_ratio_min' not in p:
        return None
    proxy = chk.compression_proxy(p)  # une seule intégration par essai : la boucle est chaude
    gap = proxy['band_gap']
    return {'proxy_ratio_calibrated': round(proxy['ratio'], 3),
            'proxy_clearance_cc': round(proxy['clearance_mm3'] / 1000, 2),
            'band_gap': round(gap, 3), 'in_band': bool(gap <= 0.0),
            'score_penalty': round(p['compression_score_weight'] * gap, 3)}


def bore_band(bore, space):
    var = [v for v in space['variables'] if v['name'] == 'bore_diameter'][0]
    return 'documented_swindon' if bore <= var['documented_upper'] + 1e-9 else 'exploratory_beyond_sources'


def mirror(design, space):
    d = dict(design)
    if space.get('plug_mode') == 'mirror_y' and 'plug_1_px' in d:
        d['plug_2_px'] = d['plug_1_px']
        d['plug_2_py'] = -d['plug_1_py']
        d['plug_2_tilt'] = d['plug_1_tilt']
        d['plug_2_azimuth'] = -d['plug_1_azimuth']
    return d


class Search:
    """``fixed`` : valeurs imposées pour toute la recherche (ex. alésage du balayage), journalisées à chaque essai."""

    def __init__(self, spec, space, base_values, step_deg=None, fixed=None, budget=None):
        self.spec, self.space, self.base = spec, space, base_values
        self.budget = budget or space['budget']
        self.step = step_deg or self.budget['search_sweep_step_deg']
        self.fixed = dict(fixed or {})
        self.history = []

    def start_point(self, stage):
        p0 = derive(self.base, self.fixed)
        vars_ = [v for v in self.space['variables'] if v['stage'] <= stage and v['name'] not in self.fixed]
        return {v['name']: float(min(max(p0[v['name']], v['lower']), v['upper'])) for v in vars_}

    def trial(self, design, stage, phase):
        design = {k: round(float(v), 4) for k, v in design.items()}
        validate_design(self.spec, self.space, design, stage)
        full = mirror(dict(self.fixed, **design), self.space)
        p = derive(self.base, full)
        checks, summ = chk.evaluate(p, self.step)
        penalty = sum(PENALTY[k](v) for k, v in design.items() if k in PENALTY)
        score = summ['min_slack'] - penalty
        comp = compression_record(p)  # G2 seulement : absent du journal G1, qui reste reproductible
        rec = {'trial': len(self.history), 'stage': stage, 'phase': phase, 'design': design,
               'fixed': self.fixed, 'bore_diameter': round(p['bore_diameter'], 3),
               'bore_band': bore_band(p['bore_diameter'], self.space),
               'stud_pattern_changed': any(k.startswith('stud_span') for k in full),
               'accepted': summ['accepted'], 'cycle_evaluated': summ['cycle_evaluated'], 'min_slack': summ['min_slack'],
               'penalty': round(penalty, 3), 'score': round(score, 3), 'limiting_check': summ['limiting_check'],
               'blocking_failed': summ['blocking_failed'],
               'slacks': {c['check']: c['slack'] for c in checks if c['blocking']}}
        if comp:
            rec['compression'] = comp
        self.history.append(rec)
        return rec

    @staticmethod
    def rank(rec):
        """Géométrie d'abord, combustion ensuite : le critère G2 ne classe que des essais acceptés.

        Tant que les contrôles bloquants échouent, la compression est ignorée — sinon la recherche
        locale poursuit la plage en abandonnant la géométrie (essai constaté : dans la plage, six
        contrôles en échec, marge −4,1 mm). Sans paramètres G2, les deux termes sont neutres et le
        classement G1 est inchangé.
        """
        comp = rec.get('compression') or {}
        if not rec['accepted']:  # ``score`` reste le score géométrique : valeur G1 inchangée
            return (False, rec['cycle_evaluated'], True, rec['score'])
        return (True, rec['cycle_evaluated'], comp.get('in_band', True), rec['score'] - comp.get('score_penalty', 0.0))

    def run(self, max_stage=3, seed_designs=()):
        rng = np.random.default_rng(self.space['seed'])
        budget = self.budget
        best = self.trial({}, 1, 'base_935_start')
        for stage in range(1, max_stage + 1):
            vars_ = [v for v in self.space['variables'] if v['stage'] <= stage and v['name'] not in self.fixed]
            names = {v['name'] for v in vars_}
            start = self.start_point(stage)
            best = max(best, self.trial(start, stage, 'start_projected_in_bounds'), key=self.rank)
            bounds = {v['name']: (v['lower'], v['upper']) for v in vars_}
            for seed in seed_designs:
                d = dict(start)
                d.update({k: min(max(v, bounds[k][0]), bounds[k][1]) for k, v in seed.items() if k in names})
                best = max(best, self.trial(d, stage, 'warm_start'), key=self.rank)
            for _ in range(budget['grid_samples']):
                design = {v['name']: rng.uniform(v['lower'], v['upper']) for v in vars_}
                for v in vars_:
                    if v['stage'] > 1 and rng.random() < 0.5:
                        design[v['name']] = start[v['name']]
                best = max(best, self.trial(design, stage, 'grid'), key=self.rank)
            best = max(best, self._local(best, vars_, stage, budget['local_evaluations']), key=self.rank)
            if best['accepted']:
                break
        return best

    def _local(self, seed_rec, vars_, stage, evaluations):
        current = dict(self.start_point(stage))
        current.update({k: v for k, v in seed_rec['design'].items() if k in current})
        cur = self.trial(current, stage, 'local_seed')
        steps = {v['name']: 0.25 * (v['upper'] - v['lower']) for v in vars_}
        bounds = {v['name']: (v['lower'], v['upper']) for v in vars_}
        used = 1
        while used < evaluations and max(s / (bounds[n][1] - bounds[n][0]) for n, s in steps.items()) > 0.005:
            improved = False
            for name in sorted(steps):
                for sign in (1, -1):
                    if used >= evaluations:
                        break
                    cand = dict(cur['design'])
                    cand[name] = min(max(cand[name] + sign * steps[name], bounds[name][0]), bounds[name][1])
                    if math.isclose(cand[name], cur['design'][name]):
                        continue
                    rec = self.trial(cand, stage, 'local')
                    used += 1
                    if self.rank(rec) > self.rank(cur):
                        cur, improved = rec, True
                        break
            if not improved:
                steps = {n: s / 2 for n, s in steps.items()}
        return cur


def pareto_front(history, top=8):
    """Meilleurs essais, classés par (accepté, marge), avec la contrainte limitante."""
    rows = sorted(history, key=Search.rank, reverse=True)
    keys = ('trial', 'stage', 'phase', 'accepted', 'min_slack', 'score', 'limiting_check',
            'blocking_failed', 'bore_band', 'design')
    return [{**{k: r[k] for k in keys}, **({'compression': r['compression']} if 'compression' in r else {})}
            for r in rows[:top]]
