"""Contrat d'interface du monocoque 964/993 : le jeu de parametres de la conception.

Un monocoque remplace la caisse. Il doit donc porter toutes les interfaces du
vehicule dans un repere unique. Ce script ne dessine rien : il etablit **ce qui
est connu, ce qui ne l'est pas, et ce qui commande quoi**, pour que la conception
puisse etre parametrique au lieu d'attendre le relevé de marbre.

Les noms et ecartements viennent du registre documentaire ; les X de travail
restent ceux de `floor_assembly.py`, avec leur provenance :
  MANUAL   = manuel d'atelier 964 volume V, planches 50-02 / 50-03 / 50-05a
  DERIVED  = resolu depuis une diagonale projetee, hypothese verifiee pour M seul
  SCAN     = mesure sur le scan de dessous recale
  ASSUMED  = ni publie ni mesurable ici

Sortie : `monocoque-interface.json` + rapport console. Aucun drapeau de
liberation. La classe reste `prohibited_pending_engineering` (SAFETY.md).

    python3 monocoque_interface.py
"""
import json
from pathlib import Path

# --- reseau de datums, volume V ---------------------------------------------
LEDGER = "catalog/measurements/MEAS-MANUAL-964-BODY-CONTROL.json"
values = json.loads((Path(__file__).resolve().parents[3] / LEDGER).read_text())["declared_values"]
DATUMS = {v["details"]["point"]: v for v in values
          if v["details"]["kind"] == "datum_point"}
TRANSVERSE = {v["details"]["between"][0]: v for v in values
              if v["details"].get("measurement_kind") == "transverse"}
X_LOCAL = {17: 0.0, 18: -1245.0, 19: -1328.0, 20: 1211.1,
           3: 654.2, 5: 527.3, 21: -2606.1, 12: -1197.0}
X_SOURCE = {17: "MANUAL", 18: "MANUAL(R)", 19: "MANUAL(S)",
            20: "DERIVED(K)", 3: "DERIVED(L)", 5: "DERIVED(P)",
            21: "DERIVED(O)", 12: "DERIVED(N)"}

# Regroupement fonctionnel ; les designations restent celles du registre.
ROLE = {
    20: "carrosserie", 3: "suspension", 5: "suspension", 6: "suspension",
    17: "levage", 18: "levage", 19: "levage",
    12: "groupe motopropulseur", 21: "groupe motopropulseur",
}

REGISTRATION_X = -506.0     # P17 dans le repere vehicule. UNE inconnue globale.
WHEELBASE_FACTORY = 2272.0  # mm, catalogue 964
WHEELBASE_SCANNED = 2278.1  # mm, mesure sur scan, +0,27 %

# P21 est invalide : place selon la diagonale O il tombe a X = -3112 mm dans le
# pare-chocs, alors que le scan montre la structure moteur entre -2300 et -2800.
INVALID = {21: "hors structure sur le scan, les deux appariements echouent"}


def classify(p):
    """Statut du X relatif uniquement, jamais validation d'un point XYZ complet."""
    if p in INVALID:
        return "INVALIDE"
    if p not in X_LOCAL:
        return "MANQUANT"
    return "DETERMINE" if X_SOURCE[p].startswith("MANUAL") else "PARAMETRIQUE"


points = {}
for p in sorted(TRANSVERSE, key=lambda k: -X_LOCAL.get(k, 0)):
    span, tol = TRANSVERSE[p]["numeric_values"]
    x = X_LOCAL.get(p)
    points[f"P{p}"] = {
        "designation": DATUMS[p]["value_text"],
        "designation_source_value_id": DATUMS[p]["value_id"],
        "fonction_monocoque": ROLE[p],
        "transverse_span_mm": span,
        "transverse_tolerance_mm": tol,
        "transverse_source_value_id": TRANSVERSE[p]["value_id"],
        "y_half_mm": span / 2.0,
        "y_tolerance_mm": None,
        "y_source": "DERIVED(MANUAL, symetrie supposee)",
        "x_local_mm": x,      # chaine locale, P17 = 0
        "x_source": X_SOURCE.get(p, "UNKNOWN"),
        "x_statut": classify(p),
        "x_vehicle_mm_provisoire": round(x + REGISTRATION_X, 1) if x is not None else None,
    }
    if p in INVALID:
        points[f"P{p}"]["invalide_raison"] = INVALID[p]

det = [k for k, v in points.items() if v["x_statut"] == "DETERMINE"]
par = [k for k, v in points.items() if v["x_statut"] == "PARAMETRIQUE"]
inv = [k for k, v in points.items() if v["x_statut"] == "INVALIDE"]
missing = [k for k, v in points.items() if v["x_statut"] == "MANQUANT"]

# Ecart entre supports de traverse avant (P5) et de boite (P12).
# Ce n'est pas l'empattement ni une cote entre fixations de deux essieux.
SPAN_P5_P12 = X_LOCAL[5] - X_LOCAL[12]

report = {
    "contrat": "MONOCOQUE-964-993-INTERFACE",
    "statut": "concept",
    "classe_securite": "prohibited_pending_engineering",
    "repere": "ADR-0003 vehicule ; X avant, Y gauche, Z haut ; origine essieu avant / sol",
    "unites": "mm",
    "source_ledger": LEDGER,
    "transverse_note": ("La tolerance publiee porte sur l'ecartement de la paire, "
                        "pas sur chaque coordonnee Y. y_half_mm suppose la symetrie ; "
                        "la position du plan median reste a qualifier."),
    "inconnue_globale": {
        "nom": "REGISTRATION_X",
        "definition": "position de P17 dans le repere vehicule",
        "valeur_de_travail_mm": REGISTRATION_X,
        "source": "SCAN, faiblement contraint",
        "effet": "translation rigide de tout le reseau ; ne change aucune cote relative",
    },
    "cote_gouvernante": {
        "nom": "SPAN_P5_P12",
        "definition": "ecart longitudinal support traverse essieu avant -> support traverse de boite",
        "defines_wheelbase": False,
        "valeur_mm": round(SPAN_P5_P12, 1),
        "x_sources": [X_SOURCE[5], X_SOURCE[12]],
        "statut": "NON VERIFIE — les deux extremites sont DERIVED",
        "consequence": ("Une erreur affecte le positionnement des interfaces avant/boite. "
                        "Cette cote ne definit ni l'empattement ni les points d'ancrage "
                        "de suspension arriere, qui restent a relever separement."),
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
print(f"{'point':<6}{'designation':<48}{'fonction':<22}{'y/2':>8}{'x local':>10}  statut")
for k, v in points.items():
    x_text = f"{v['x_local_mm']:.1f}" if v['x_local_mm'] is not None else "manquant"
    print(f"{k:<6}{v['designation']:<48}{v['fonction_monocoque']:<22}"
          f"{v['y_half_mm']:8.1f}{x_text:>10}  {v['x_statut']}")

print(f"\nTransverse : {len(points)} ecartements de paires publies, tolerance 1 a 2 mm.")
print(f"Longitudinal : {len(det)} determines {det}, {len(par)} parametriques {par}, "
      f"{len(inv)} invalides {inv}, {len(missing)} manquants {missing}.")

print(f"""
Ce que dit ce tableau, et c'est le resultat utile :

  DETERMINE decrit uniquement un X relatif documentaire. Aucun point XYZ
  complet n'est valide : recalage longitudinal et hauteurs restent a qualifier.
  P6 reste visible avec X manquant ; P21 reste invalide.

SPAN_P5_P12 = {SPAN_P5_P12:.1f} mm relie des supports de traverse avant et de
boite, PAS deux essieux. Ses deux extremites restent DERIVED sous une hypothese
de diagonale croisee non verifiee pour ces points.

Les interfaces arriere et les volumes de transmission C2/C4 doivent etre releves
separement. Le present contrat n'est pas un releve complet de la caisse et ne
prouve pas la compatibilite 993. Aucun lancement d'outillage sur ces hypotheses.
""")
print("ecrit ../derived/monocoque-interface.json")
