"""Plan d'experiences CalculiX : le corpus dont PhysicsNeMo a besoin avant d'exister.

`docs/MONOCOQUE_964_993_CHAINE_CALCUL.md` pose la regle : un substitut n'a de sens
qu'apres un corpus coherent, et `ROADMAP.md` en fait une condition ecrite. Ce
script produit ce corpus. Il ne demande **ni GPU ni SSH** : un plan d'experiences
CalculiX est du calcul CPU, et c'est precisement ce qui peut etre prepare
maintenant pour n'avoir qu'a etre lance plus tard.

Ce qui est stocke, et pourquoi. La cible n'est pas le scalaire K : une raideur en
fonction de huit parametres se regresse avec n'importe quel modele, et n'aurait
aucun besoin de PhysicsNeMo. Chaque cas conserve donc le **champ nodal de
deplacement sur le maillage**, qui est la grandeur pour laquelle les
architectures de PhysicsNeMo — MeshGraphNet, Transolver — sont faites.

Reproductibilite. Le tirage est deterministe pour une graine donnee, chaque cas
porte ses parametres, et le manifeste enregistre l'empreinte des scripts qui l'ont
produit. Relancer le script complete un corpus existant au lieu de le refaire :
les cas deja calcules sont sautes.

    python3 doe_corpus.py --n 200 [--seed 0] [--out corpus] [--order 1]
    python3 doe_corpus.py --smoke          # 4 cas, pour verifier la chaine
"""
import argparse, hashlib, json, os, pathlib, subprocess, sys, time
import numpy as np

PY = sys.executable
HERE = pathlib.Path(__file__).parent
CCX_TAG = "doe_run"

# --- espace de conception --------------------------------------------------
# Les architectures sont celles de body_study.py. Les bornes continues encadrent
# les valeurs ASSUMED du modele, qu'aucune source ne publie : le plan explore
# donc l'incertitude autant que la conception.
FEATURES = ["f", "fb", "fbt", "fbta", "fbtap", "fbtapr", "fbtaprw"]
RANGES = {
    "BODY_SILL_W": (60.0, 130.0),      # largeur de longeron
    "BODY_SILL_H": (80.0, 180.0),      # hauteur de longeron
    "BODY_XW":     (50.0, 120.0),      # largeur de traverse
    "BODY_XH":     (40.0, 110.0),      # hauteur de traverse
    "BODY_H_BULK": (350.0, 650.0),     # hauteur de cloison
    "BODY_TUN_W":  (120.0, 260.0),     # largeur de tunnel
    "BODY_TUN_H":  (80.0, 200.0),      # hauteur de tunnel
    "BODY_ROOF_H": (950.0, 1300.0),    # hauteur de pavillon
}
T_RANGE = (0.6, 2.0)                   # epaisseur de peau, mm
E_RANGE = (40000.0, 210000.0)          # module, MPa : de l'ordre composite a l'acier
# Rapport du module de cisaillement a sa valeur isotrope. A 1,0 le materiau est
# isotrope ; ailleurs E et G sont decouples. Sans cette dimension, G resterait
# proportionnel a E et le substitut ne pourrait pas apprendre la difference entre
# flexion et cisaillement — celle-la meme qui commande l'architecture.
GK_RANGE = (0.4, 2.0)
NU = 0.30
RHO = 7.85e-6


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()[:16]


def sample(rng, n):
    """Hypercube latin : chaque marge est balayee uniformement, sans grille."""
    keys = list(RANGES)
    cuts = {k: (rng.permutation(n) + rng.random(n)) / n for k in keys + ["_t", "_e", "_g"]}
    out = []
    feats = np.array(FEATURES)[rng.integers(0, len(FEATURES), n)]
    for i in range(n):
        p = {k: RANGES[k][0] + cuts[k][i] * (RANGES[k][1] - RANGES[k][0]) for k in keys}
        p["features"] = str(feats[i])
        p["t"] = T_RANGE[0] + cuts["_t"][i] * (T_RANGE[1] - T_RANGE[0])
        p["E"] = E_RANGE[0] + cuts["_e"][i] * (E_RANGE[1] - E_RANGE[0])
        gk = GK_RANGE[0] + cuts["_g"][i] * (GK_RANGE[1] - GK_RANGE[0])
        p["G"] = p["E"] / (2.0 * (1.0 + NU)) * gk
        p["G_ratio_iso"] = gk
        out.append(p)
    return out


def read_field(tag, nid):
    """Champ nodal de deplacement, repris du .frd par numero de noeud."""
    u, mode = {}, None
    for line in open(f'{tag}.frd'):
        if ' -4  DISP' in line: mode = 'U'; continue
        if line.startswith(' -3'): mode = None; continue
        if mode == 'U' and line.startswith(' -1'):
            u[int(line[3:13])] = (float(line[13:25]), float(line[25:37]), float(line[37:49]))
    if len(u) < len(nid):
        return None
    return np.array([u[int(n)] for n in nid], dtype=np.float32)


def run_case(p, order, env_base):
    env = dict(env_base)
    work = pathlib.Path(env.get('FEA_WORK', '.'))
    for k in RANGES:
        env[k] = f"{p[k]:.4f}"
    r = subprocess.run([PY, 'build_body.py', f"{p['t']:.4f}", p['features'], '1.0', str(order)],
                       capture_output=True, text=True, env=env, cwd=HERE)
    if r.returncode:
        return None, f"build: {r.stdout.strip()[:120]}"
    mesh = np.load(HERE / work / 'mesh.npz')
    r = subprocess.run([PY, 'run_fea.py', f"{p['t']:.4f}", CCX_TAG, f"{p['E']:.1f}", f"{NU}",
                        f"{p['G']:.1f}"],
                       capture_output=True, text=True, env=env, cwd=HERE)
    if r.returncode:
        return None, f"solve: {r.stdout.strip()[-120:]}"
    res = np.load(HERE / work / f'{CCX_TAG}_res.npz')
    u = read_field(str(HERE / work / CCX_TAG), mesh['nid'])
    if u is None:
        return None, "champ de deplacement incomplet"
    area = float(mesh['area'])
    return dict(xyz=mesh['xyz'].astype(np.float32), tri=mesh['tri'].astype(np.int32),
                u=u, K=float(res['K']), theta=float(res['theta']),
                area=area, mass=area * p['t'] * RHO), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=200)
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--out', default='corpus')
    ap.add_argument('--order', type=int, default=1)
    ap.add_argument('--smoke', action='store_true')
    # Repertoire de travail propre a la campagne. Deux campagnes lancees en
    # parallele depuis le meme dossier partageaient mesh.npz et les fichiers du
    # solveur : elles se seraient contaminees en silence.
    ap.add_argument('--work', default=None)
    a = ap.parse_args()
    if a.smoke:
        a.n, a.out = 4, 'corpus_smoke'

    out = HERE / a.out; out.mkdir(exist_ok=True)
    # Reprendre suppose le MEME plan. Le tirage depend de n et de la graine :
    # relancer avec un n different reattribuerait d'autres parametres aux memes
    # numeros de cas, et l'index deviendrait faux sans que rien ne le signale.
    prev = out / 'manifest.json'
    m_prev = None
    if prev.exists():
        m = m_prev = json.loads(prev.read_text())
        if (m.get('n_demande'), m.get('seed')) != (a.n, a.seed):
            sys.exit(f"corpus existant tire avec n={m.get('n_demande')} seed={m.get('seed')} ; "
                     f"reprise demandee avec n={a.n} seed={a.seed}. Refusé : les numeros de cas "
                     f"ne designeraient plus les memes parametres. Choisir --out different.")
    env_base = dict(os.environ)
    S = '/home/maxime/work/964twin/syslibs/usr/lib/x86_64-linux-gnu'
    env_base['LD_LIBRARY_PATH'] = f"{S}:{S}/lapack:{S}/blas:{S}/openmpi/lib"
    env_base.setdefault('OMP_NUM_THREADS', '4')
    env_base['FEA_WORK'] = a.work or f'work_{a.out}'
    (HERE / env_base['FEA_WORK']).mkdir(exist_ok=True)

    plan = sample(np.random.default_rng(a.seed), a.n)
    t0, done, failed = time.time(), 0, 0
    with open(out / 'index.jsonl', 'a') as idx:
        for i, p in enumerate(plan):
            f = out / f'case_{i:05d}.npz'
            if f.exists():
                done += 1; continue
            rec, err = run_case(p, a.order, env_base)
            if rec is None:
                failed += 1
                print(f"  cas {i:05d} ECHEC  {err}")
                continue
            np.savez_compressed(f, **rec, **{k: v for k, v in p.items() if k != 'features'},
                                features=p['features'])
            idx.write(json.dumps({"case": i, "file": f.name, **p,
                                  "K": rec['K'], "mass": rec['mass'],
                                  "nodes": int(len(rec['xyz']))}) + "\n")
            idx.flush(); done += 1
            if done % 10 == 0 or a.smoke:
                print(f"  {done}/{a.n}  dernier K={rec['K']:.0f} N.m/deg  "
                      f"{len(rec['xyz'])} noeuds  {time.time()-t0:.0f}s")

    manifest = {
        "corpus": a.out, "seed": a.seed, "n_demande": a.n,
        "n_ecrit": done, "n_echec": failed, "ordre_element": a.order,
        "element": "S6" if a.order == 2 else "S3",
        "espace": {"features": FEATURES, "continus": RANGES,
                   "t_mm": T_RANGE, "E_MPa": E_RANGE, "nu": NU,
                   "G_sur_G_isotrope": GK_RANGE},
        "cible": "champ nodal de deplacement u (n,3) + scalaires K, masse",
        "scripts": {n: sha(HERE / n) for n in
                    ('build_body.py', 'run_fea.py', 'doe_corpus.py')},
        "avertissement": ("Corpus de substitution. Sections ASSUMED, modele non converge "
                          "en maillage, aucune valeur absolue exploitable. Sert a entrainer "
                          "un modele de tendance, pas a etablir une raideur."),
    }
    # Une reprise avec des scripts modifies ne doit pas effacer l'empreinte sous
    # laquelle les cas deja presents ont ete calcules : le manifeste garderait
    # alors une seule empreinte pour un corpus mixte. Les anciennes sont donc
    # empilees, et c'est au lecteur de juger si le melange est acceptable.
    if m_prev and m_prev.get('scripts') and m_prev['scripts'] != manifest['scripts']:
        manifest['scripts_precedents'] = (m_prev.get('scripts_precedents', [])
                                          + [m_prev['scripts']])
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
    print(f"\n{done} cas ecrits, {failed} echecs, {time.time()-t0:.0f}s -> {out}/")
    print(f"manifeste : {out}/manifest.json")


if __name__ == '__main__':
    main()
