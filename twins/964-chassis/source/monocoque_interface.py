"""Contrat d'interface du monocoque 964/993 : le jeu de parametres de la conception.

Un monocoque remplace la caisse. Il doit donc porter toutes les interfaces du
vehicule dans un repere unique. Ce script ne dessine rien : il etablit **ce qui
est connu, ce qui ne l'est pas, et ce qui commande quoi**, pour que la conception
puisse etre parametrique au lieu d'attendre le relevé de marbre.

Chaque cote porte sa provenance, reprise de `floor_assembly.py` :
  MANUAL   = manuel d'atelier 964 volume V, planches 50-02 / 50-03 / 50-05a
  DERIVED  = resolu depuis une diagonale projetee, hypothese verifiee pour M seul
  SCAN     = mesure sur le scan de dessous recale
  ASSUMED  = ni publie ni mesurable ici

Sortie : `monocoque-interface.json` + rapport console. Aucun drapeau de
liberation. La classe reste `prohibited_pending_engineering` (SAFETY.md).

    python3 monocoque_interface.py
"""
import json

# --- reseau de datums, volume V (identique a floor_assembly.py) --------------
TRANSVERSE = {                      # point : (ecartement gauche-droite, tolerance)
    20: (440, 2), 3: (610, 1), 5: (770, 2), 6: (204, 2), 17: (1330, 1),
    18: (1236, 1), 12: (278, 1), 19: (1018, 1), 21: (640, 1),
}
X_LOCAL = {17: 0.0, 18: -1245.0, 19: -1328.0, 20: 1211.1,
           3: 654.2, 5: 527.3, 21: -2606.1, 12: -1197.0}
X_SOURCE = {17: "MANUAL", 18: "MANUAL(R)", 19: "MANUAL(S)",
            20: "DERIVED(K)", 3: "DERIVED(L)", 5: "DERIVED(P)",
            21: "DERIVED(O)", 12: "DERIVED(N)"}

# Ce que chaque point EST sur la voiture, et ce qu'il devient pour un monocoque.
ROLE = {
    20: ("Point de controle avant",            "carrosserie"),
    3:  ("Fixation traverse avant interieure", "suspension"),
    5:  ("Mount - outer cross member FA",      "suspension"),
    6:  ("Point de controle central",          "carrosserie"),
    17: ("Prise de cric avant",                "levage"),
    18: ("Prise de cric arriere",              "levage"),
    19: ("Point de controle arriere",          "carrosserie"),
    12: ("Traverse d'essieu arriere",          "suspension"),
    21: ("Palier moteur",                      "groupe motopropulseur"),
}

REGISTRATION_X = -506.0     # P17 dans le repere vehicule. UNE inconnue globale.
WHEELBASE_FACTORY = 2272.0  # mm, catalogue 964
WHEELBASE_SCANNED = 2278.1  # mm, mesure sur scan, +0,27 %

# P21 est invalide : place selon la diagonale O il tombe a X = -3112 mm dans le
# pare-chocs, alors que le scan montre la structure moteur entre -2300 et -2800.
INVALID = {21: "hors structure sur le scan, les deux appariements echouent"}


def classify(p):
    """DETERMINE si la cote longitudinale est publiee, PARAMETRIQUE sinon."""
    if p in INVALID:
        return "INVALIDE"
    return "DETERMINE" if X_SOURCE[p].startswith("MANUAL") else "PARAMETRIQUE"


points = {}
for p in sorted(TRANSVERSE, key=lambda k: -X_LOCAL.get(k, 0)):
    if p not in X_LOCAL:
        continue                       # P6 : pas de cote longitudinale publiee
    span, tol = TRANSVERSE[p]
    points[f"P{p}"] = {
        "designation": ROLE[p][0],
        "fonction_monocoque": ROLE[p][1],
        "y_half_mm": span / 2.0,
        "y_tolerance_mm": tol,
        "y_source": "MANUAL",
        "x_local_mm": X_LOCAL[p],      # chaine locale, P17 = 0
        "x_source": X_SOURCE[p],
        "x_statut": classify(p),
        "x_vehicle_mm_provisoire": round(X_LOCAL[p] + REGISTRATION_X, 1),
    }
    if p in INVALID:
        points[f"P{p}"]["invalide_raison"] = INVALID[p]

det = [k for k, v in points.items() if v["x_statut"] == "DETERMINE"]
par = [k for k, v in points.items() if v["x_statut"] == "PARAMETRIQUE"]
inv = [k for k, v in points.items() if v["x_statut"] == "INVALIDE"]

# --- la cote qui commande la securite ---------------------------------------
# Un monocoque impose l'entraxe avant/arriere par construction : il porte a la
# fois la fixation de train avant (P5) et la traverse d'essieu arriere (P12).
SPAN_P5_P12 = X_LOCAL[5] - X_LOCAL[12]

report = {
    "contrat": "MONOCOQUE-964-993-INTERFACE",
    "statut": "concept",
    "classe_securite": "prohibited_pending_engineering",
    "repere": "ADR-0003 vehicule ; X avant, Y gauche, Z haut ; origine essieu avant / sol",
    "unites": "mm",
    "inconnue_globale": {
        "nom": "REGISTRATION_X",
        "definition": "position de P17 dans le repere vehicule",
        "valeur_de_travail_mm": REGISTRATION_X,
        "source": "SCAN, faiblement contraint",
        "effet": "translation rigide de tout le reseau ; ne change aucune cote relative",
    },
    "cote_gouvernante": {
        "nom": "SPAN_P5_P12",
        "definition": "entraxe longitudinal fixation train avant -> traverse essieu arriere",
        "valeur_mm": round(SPAN_P5_P12, 1),
        "x_sources": [X_SOURCE[5], X_SOURCE[12]],
        "statut": "NON VERIFIE — les deux extremites sont DERIVED",
        "consequence": ("Le monocoque impose cet entraxe par construction. Une erreur "
                        "ici ne se rattrape pas au montage : elle donne un empattement "
                        "et une geometrie de suspension faux."),
    },
    "empattement_reference": {"usine_mm": WHEELBASE_FACTORY, "scan_mm": WHEELBASE_SCANNED},
    "points": points,
    "release_flags": {"geometry_released": False, "manufacturing_released": False},
}

with open("../derived/monocoque-interface.json", "w") as f:
    json.dump(report, f, indent=1, ensure_ascii=False)
    f.write("\n")

# ----------------------------------------------------------------- rapport
print("Contrat d'interface du monocoque 964/993\n")
print(f"{'point':<6}{'designation':<36}{'fonction':<22}{'y/2':>8}{'x local':>10}  statut")
for k, v in points.items():
    print(f"{k:<6}{v['designation']:<36}{v['fonction_monocoque']:<22}"
          f"{v['y_half_mm']:8.1f}{v['x_local_mm']:10.1f}  {v['x_statut']}")

print(f"\nTransverse : {len(points)}/{len(points)} points publies au manuel, tolerance 1 a 2 mm.")
print(f"Longitudinal : {len(det)} determines {det}, {len(par)} parametriques {par}, "
      f"{len(inv)} invalides {inv}.")

print(f"""
Ce que dit ce tableau, et c'est le resultat utile :

  Les points DETERMINES sont des prises de cric et des points de controle de
  carrosserie. Les points PARAMETRIQUES et INVALIDES sont, eux, TOUS ceux qui
  portent la suspension et le groupe motopropulseur.

  Autrement dit, ce qui est bien connu ne sert pas a grand-chose pour un
  monocoque, et ce dont le monocoque a besoin n'est pas connu.

Cote gouvernante : SPAN_P5_P12 = {SPAN_P5_P12:.1f} mm, entraxe train avant ->
essieu arriere. Ses deux extremites sont DERIVED sous une hypothese de diagonale
croisee qui n'est verifiee que pour la diagonale M. C'est la cote la plus
critique du produit et c'est une cote non verifiee.

Consequence de conception, immediatement actionnable :

  1. La topologie, les anneaux, les chemins de cisaillement et le drapage se
     concoivent MAINTENANT : ils ne dependent d'aucune de ces inconnues.
  2. Les interfaces se declarent en parametres, pas en cotes dures. Le relevé
     de marbre remplit {len(par)} valeurs et en corrige 1.
  3. Aucune coque ne part en outillage avant que SPAN_P5_P12 soit mesure. Un
     outillage grave une cote fausse dans le produit.
""")
print("ecrit ../derived/monocoque-interface.json")
