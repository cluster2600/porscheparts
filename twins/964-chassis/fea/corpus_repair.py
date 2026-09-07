"""Rejoue le corpus case par case et remplace les cas que le solveur a rates.

Pourquoi c'est necessaire. Un audit du corpus a trouve un cas dont la raideur
stockee valait **neuf fois** la valeur rejouee, puis un second a 2,4 % sur
quarante cas tires au hasard. Ces cas-la ne se signalent pas : le champ de
deplacement stocke est parfaitement coherent avec le K stocke, parce que les
deux viennent du meme solve rate. Aucun controle interne ne peut donc les voir,
et un substitut entraine dessus apprendrait ces valeurs comme les autres.

Le seul juge est la repetition. Le calcul est deterministe — trois executions
d'un meme cas rendent le meme chiffre — donc un desaccord entre le corpus et un
rejeu signale un solve transitoirement faux, d'un cote ou de l'autre. Le
departage se fait a la majorite : en cas de desaccord, un troisieme calcul
tranche, et le cas n'est remplace que si deux calculs independants s'accordent
contre la valeur stockee.

Ce script ne corrige rien qu'il n'ait verifie deux fois, et il enregistre dans le
manifeste combien de cas ont ete repares. Un corpus dont on ignore le taux
d'erreur n'est pas un corpus.

    pycad corpus_repair.py [--corpus corpus] [--work work_repair] [--limit N]
"""
import argparse, json, os, pathlib, subprocess, sys, time
import numpy as np

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import doe_corpus as D

TOL = 0.005          # 0,5 % : sous le plancher de resolution documente, du bruit


def solve(p, env, work, tag):
    """Un calcul complet depuis les parametres. Rend (K, mesh, res) ou None."""
    for k in D.RANGES:
        env[k] = f"{p[k]:.4f}"
    r = subprocess.run([D.PY, 'build_body.py', f"{p['t']:.4f}", p['features'], '1.0',
                        str(env['_ORDER'])], capture_output=True, text=True, env=env, cwd=HERE)
    if r.returncode:
        return None
    r = subprocess.run([D.PY, 'run_fea.py', f"{p['t']:.4f}", tag, f"{p['E']:.1f}",
                        f"{D.NU}", f"{p['G']:.1f}"],
                       capture_output=True, text=True, env=env, cwd=HERE)
    if r.returncode:
        return None
    mesh = np.load(HERE / work / 'mesh.npz')
    res = np.load(HERE / work / f'{tag}_res.npz')
    u = D.read_field(str(HERE / work / tag), mesh['nid'])
    if u is None:
        return None
    area = float(mesh['area'])
    return dict(xyz=mesh['xyz'].astype(np.float32), tri=mesh['tri'].astype(np.int32),
                u=u, K=float(res['K']), theta=float(res['theta']),
                area=area, mass=area * p['t'] * D.RHO)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus', default='corpus')
    ap.add_argument('--work', default=None)
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    corpus = HERE / a.corpus
    man = json.loads((corpus / 'manifest.json').read_text())
    work = a.work or f'work_repair_{a.corpus}'
    (HERE / work).mkdir(exist_ok=True)

    env = dict(os.environ)
    S = '/home/maxime/work/964twin/syslibs/usr/lib/x86_64-linux-gnu'
    env['LD_LIBRARY_PATH'] = f"{S}:{S}/lapack:{S}/blas:{S}/openmpi/lib"
    env.setdefault('OMP_NUM_THREADS', '2')
    env['FEA_WORK'] = work
    env['_ORDER'] = str(man['ordre_element'])

    plan = D.sample(np.random.default_rng(man['seed']), man['n_demande'])
    cases = sorted(int(f.stem.split('_')[1]) for f in corpus.glob('case_*.npz'))
    if a.limit:
        cases = cases[:a.limit]
    journal = corpus / 'repair.jsonl'
    deja = set()
    if journal.exists():
        deja = {json.loads(l)['case'] for l in open(journal)}

    t0, n_ok, n_rep, n_amb, n_ko = time.time(), 0, 0, 0, 0
    with open(journal, 'a') as jl:
        for i in cases:
            if i in deja:
                continue
            p = plan[i]
            stock = float(np.load(corpus / f'case_{i:05d}.npz')['K'])
            r1 = solve(p, env, work, 'rep1')
            if r1 is None:
                n_ko += 1
                jl.write(json.dumps({"case": i, "verdict": "echec"}) + "\n"); jl.flush()
                continue
            if abs(r1['K'] / stock - 1.0) <= TOL:
                n_ok += 1
                jl.write(json.dumps({"case": i, "verdict": "ok", "K": stock}) + "\n")
            else:
                # Desaccord : un troisieme calcul tranche, et lui seul.
                r2 = solve(p, env, work, 'rep2')
                if r2 is not None and abs(r2['K'] / r1['K'] - 1.0) <= TOL:
                    np.savez_compressed(corpus / f'case_{i:05d}.npz', **r1,
                                        **{k: v for k, v in p.items() if k != 'features'},
                                        features=p['features'])
                    # index.jsonl fait foi pour l'audit : la ligne corrigee y est
                    # republiee, la derniere valant pour un meme numero de cas.
                    with open(corpus / 'index.jsonl', 'a') as ix:
                        ix.write(json.dumps({"case": i, "file": f'case_{i:05d}.npz', **p,
                                             "K": r1['K'], "mass": r1['mass'],
                                             "nodes": int(len(r1['xyz']))}) + "\n")
                    n_rep += 1
                    v = {"case": i, "verdict": "repare", "K_stocke": stock,
                         "K_rejeu_1": r1['K'], "K_rejeu_2": r2['K']}
                else:
                    n_amb += 1
                    v = {"case": i, "verdict": "ambigu", "K_stocke": stock,
                         "K_rejeu_1": r1['K'],
                         "K_rejeu_2": (r2 or {}).get('K')}
                jl.write(json.dumps(v) + "\n")
                print(f"  cas {i:05d} {v['verdict']}  stocke {stock:.1f} "
                      f"rejeu {r1['K']:.1f}", flush=True)
            jl.flush()
            n = n_ok + n_rep + n_amb + n_ko
            if n % 100 == 0:
                print(f"  {n}/{len(cases)}  {n_rep} repares  {n_amb} ambigus  "
                      f"{n_ko} echecs  {time.time()-t0:.0f}s", flush=True)

    print(f"\n{n_ok} confirmes, {n_rep} repares, {n_amb} ambigus, {n_ko} echecs")
    if not a.limit:
        # Le taux d'erreur mesure appartient au manifeste : c'est une propriete du
        # corpus, pas une note de passage.
        man['reparation'] = {"confirmes": n_ok, "repares": n_rep, "ambigus": n_amb,
                             "echecs": n_ko, "tolerance": TOL,
                             "regle": "remplace seulement si deux rejeux independants "
                                      "s'accordent contre la valeur stockee"}
        (corpus / 'manifest.json').write_text(json.dumps(man, indent=1,
                                                         ensure_ascii=False) + "\n")


if __name__ == '__main__':
    main()
