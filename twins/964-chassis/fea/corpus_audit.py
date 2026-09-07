"""Ce que le corpus contient reellement, avant qu'un GPU ne soit loue pour l'apprendre.

Un substitut ne peut pas apprendre ce qui n'est pas dans le corpus. Cette
verification-la se fait sur CPU, en quelques secondes, et elle peut disqualifier
le corpus avant la premiere heure de GPU. Elle repond a trois questions.

**Le corpus est-il homogene ?** Les echecs de solveur ne sont pas du bruit s'ils
frappent une architecture plutot qu'une autre : ils creusent un trou oriente,
que le substitut apprendra comme une frontiere.

**Est-il physiquement coherent ?** L'elasticite lineaire impose une identite
exacte : K est homogene de degre 1 en (E, G) pris ensemble, donc les exposants
d ln K / d ln E et d ln K / d ln G doivent sommer a 1. Ce n'est pas un ajustement
mais un controle : le corpus le verifie ou il est faux.

**Porte-t-il la decouverte de la session ?** `dominance_study.py` montre que le
mecanisme change avec l'architecture — flexion quasi pure sur le plancher nu,
cisaillement dominant une fois la cellule fermee. Si l'exposant de G ne monte pas
avec la fermeture, le corpus ne contient pas cette information et aucun substitut
ne l'apprendra, quelle que soit l'architecture de reseau choisie.

    pycad corpus_audit.py [--corpus corpus] [--split]

`--split` gele le lot de validation. Il est tire AVANT qu'un substitut existe,
et c'est le seul moment ou cela veut dire quelque chose : choisi apres coup, un
lot de test est une note qu'on se donne a soi-meme.
"""
import argparse, hashlib, json, pathlib, sys
import numpy as np

HERE = pathlib.Path(__file__).parent
LOGV = ["t", "E", "G"] + ["BODY_SILL_W", "BODY_SILL_H", "BODY_XW", "BODY_XH",
                          "BODY_H_BULK", "BODY_TUN_W", "BODY_TUN_H", "BODY_ROOF_H"]
# Exposants de reference, mesures en coques S6 sur la geometrie par defaut par
# `dominance_study.py` et re-verifies par `run_fea.py` : doubler G rend +2,3 % sur
# le plancher nu et +56,7 % sur la cellule fermee, soit ln(1,023)/ln 2 = 0,03 et
# ln(1,567)/ln 2 = 0,65. Un corpus en S3 s'en ecarte fortement sur les
# architectures ouvertes, et c'est un biais d'element, pas un defaut de tirage.
EXPO_G_S6 = {"f": 0.03, "fbtaprw": 0.65}
TEST_FRACTION = 0.15
SPLIT_SEED = 20260907


def load(corpus):
    rows = [json.loads(l) for l in open(corpus / 'index.jsonl')]
    # index.jsonl est ouvert en append : une reprise, ou une reparation, peut y
    # republier une ligne. La DERNIERE fait foi, sinon un cas repare serait relu
    # avec la valeur fausse qui a motive sa reparation.
    par_cas = {r['case']: r for r in rows}
    return [par_cas[k] for k in sorted(par_cas)]


def fit(rows, cols):
    """Moindres carres de ln K sur les logarithmes des parametres continus."""
    A = np.column_stack([np.log([r[c] for r in rows]) for c in cols]
                        + [np.ones(len(rows))])
    y = np.log([r['K'] for r in rows])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - A @ beta
    r2 = 1.0 - resid.var() / y.var()
    return dict(zip(cols, beta)), r2, float(np.exp(np.abs(resid).max()) - 1.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus', default='corpus')
    ap.add_argument('--split', action='store_true')
    a = ap.parse_args()
    corpus = HERE / a.corpus
    man = json.loads((corpus / 'manifest.json').read_text())
    rows = load(corpus)
    feats = man['espace']['features']

    print(f"corpus {a.corpus} : {len(rows)} cas lus, "
          f"{man['n_demande']} demandes, {man['n_echec']} echecs au dernier passage")
    if len(rows) != len(set(r['case'] for r in rows)):
        sys.exit("numeros de cas dupliques dans index.jsonl")

    # 1. Homogeneite. Le tirage est uniforme sur les architectures : un ecart
    #    significatif au nombre attendu signale un trou oriente, pas du hasard.
    print("\n-- couverture par architecture")
    attendu = man['n_demande'] / len(feats)
    for f in feats:
        sub = [r for r in rows if r['features'] == f]
        ecart = (len(sub) - attendu) / np.sqrt(attendu)   # ecarts-types de Poisson
        flag = "  <-- trou" if ecart < -3 else ""
        print(f"   {f:8s} {len(sub):4d} cas  ({ecart:+.1f} sigma){flag}")

    K = np.array([r['K'] for r in rows])
    n = np.array([r['nodes'] for r in rows])
    print(f"\n-- K de {K.min():.0f} a {K.max():.0f} N.m/deg, mediane {np.median(K):.0f}"
          f"   |   noeuds de {n.min()} a {n.max()}")
    if not np.isfinite(K).all() or (K <= 0).any():
        sys.exit("des raideurs non finies ou negatives dans le corpus")

    # 2 et 3. Exposants, par architecture.
    print("\n-- exposants d ln K / d ln x, par architecture")
    print("   " + f"{'arch':8s} {'t':>6s} {'E':>6s} {'G':>6s} {'E+G':>7s} "
                  f"{'R2':>6s} {'ecart max':>10s}")
    somme_ok = True
    expo = {}
    for f in feats:
        sub = [r for r in rows if r['features'] == f]
        if len(sub) < 50:
            print(f"   {f:8s} trop peu de cas"); continue
        b, r2, emax = fit(sub, LOGV)
        expo[f] = b
        s = b['E'] + b['G']
        if abs(s - 1.0) > 0.02: somme_ok = False
        print(f"   {f:8s} {b['t']:6.3f} {b['E']:6.3f} {b['G']:6.3f} {s:7.3f} "
              f"{r2:6.3f} {emax*100:9.1f}%")

    print("\n   E+G doit valoir 1,000 : K est homogene de degre 1 en (E, G).",
          "Verifie." if somme_ok else "ECHEC — le corpus est incoherent.")
    if not somme_ok:
        sys.exit(1)

    # L'exposant de t doit valoir 1 : la loi d'echelle lineaire en epaisseur est
    # le resultat le plus robuste du dossier. Le corpus doit la contenir.
    et = [expo[f]['t'] for f in expo]
    print(f"   exposant de t : de {min(et):.3f} a {max(et):.3f} — "
          f"la loi lineaire en epaisseur est {'presente' if max(abs(np.array(et)-1))<0.05 else 'ABSENTE'}.")

    ouvert, ferme = expo.get('f'), expo.get(feats[-1])
    if ouvert and ferme:
        print(f"\n   plancher nu   G {ouvert['G']:.3f}  E {ouvert['E']:.3f}")
        print(f"   cellule fermee G {ferme['G']:.3f}  E {ferme['E']:.3f}")
        montee = ferme['G'] - ouvert['G']
        print(f"   montee de l'exposant de G a la fermeture : {montee:+.3f}")
        print("   " + ("Le corpus porte un changement de mecanisme."
                       if montee > 0.15 else
                       "ATTENTION : le corpus ne porte pas le changement de mecanisme. "
                       "Un substitut entraine dessus ne pourra pas l'apprendre."))

        # Le sens du changement ne suffit pas : il faut la bonne valeur. Sur le
        # plancher nu, l'exposant de G doit etre nul, la flexion y etant quasi
        # pure. S'il ne l'est pas, ce sont les elements lineaires qui attribuent
        # au cisaillement ce qui revient a la flexion.
        ecart = ouvert['G'] - EXPO_G_S6['f']
        print(f"\n   plancher nu, exposant de G : {ouvert['G']:.3f} contre "
              f"{EXPO_G_S6['f']:.2f} attendu en coques S6")
        if ecart > 0.1:
            print(f"   ATTENTION : ecart de {ecart:+.3f}. "
                  f"{'Le corpus est en S3 : ' if man.get('ordre_element') == 1 else ''}"
                  "les triangles lineaires sont trop raides en flexion et donnent a G "
                  "une part qui revient a E. Un substitut entraine la-dessus apprendra "
                  "une repartition flexion / cisaillement fausse sur les architectures "
                  "ouvertes. Regenerer en ordre 2.")

    if a.split:
        # Stratifie par architecture, pour que le lot de test ne puisse pas se
        # vider d'une architecture rare.
        rng = np.random.default_rng(SPLIT_SEED)
        test = []
        for f in feats:
            ids = sorted(r['case'] for r in rows if r['features'] == f)
            k = int(round(TEST_FRACTION * len(ids)))
            test += [int(i) for i in rng.choice(ids, k, replace=False)]
        test.sort()
        out = corpus / 'split.json'
        payload = {
            "graine": SPLIT_SEED, "fraction": TEST_FRACTION,
            "stratifie_par": "features", "n_test": len(test),
            "n_total": len(rows), "test": test,
            "regle": ("Ces cas sont exclus de tout apprentissage. Ils ont ete tires "
                      "avant qu'aucun substitut n'existe. Un substitut valide sur un "
                      "lot choisi apres coup n'est pas valide."),
        }
        out.write_text(json.dumps(payload, indent=1) + "\n")
        h = hashlib.sha256(out.read_bytes()).hexdigest()[:16]
        print(f"\n-- lot de validation gele : {len(test)} cas sur {len(rows)}")
        print(f"   {out}  sha256:{h}")


if __name__ == '__main__':
    main()
