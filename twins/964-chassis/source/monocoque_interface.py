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
# Longitudinal chain: published dimensions (plates 50-02, 50-03, 50-05a), see
# datum_chain_50_05a.py; P12 measured on the scan, see scan_tie_50_05a.py.
CHAIN = json.load(open("../derived/datum-chain-50-05a.json"))
TIE = json.load(open("../evidence/scan-tie-50-05a.json"))
X_LOCAL = {int(name[1:]): row["x_from_P17_mm"] for name, row in CHAIN["points"].items()
           if name not in ("P1", "P16")}
X_LOCAL[12] = round(CHAIN["points"]["P17"]["d_behind_0_line_mm"]
                    - TIE["p12_scan_candidate"]["d_behind_0_line_mm"], 1)
X_LOCAL[21] = -2606.1          # diagonal O, crossed-plan reading, not verified
X_SOURCE = {17: "MANUAL(50-05a via K and L)", 18: "MANUAL(R)", 19: "MANUAL(S)",
            20: "MANUAL(50-05a 143, P)", 3: "MANUAL(50-05a 215)", 5: "MANUAL(50-05a 143)",
            21: "DERIVED(O)", 12: "SCAN(P12 bosses)"}

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

# P17 in the vehicle frame: the published chain tied to the scan by the offset
# of the plate 0 line, measured on P5, P17 and P19 (scan_tie_50_05a.py).
REGISTRATION_X = round(TIE["delta"]["value_mm"] - CHAIN["points"]["P17"]["d_behind_0_line_mm"], 1)
REGISTRATION_U = TIE["delta"]["u_mm"]
WHEELBASE_FACTORY = 2272.0  # mm, catalogue 964
WHEELBASE_SCANNED = 2278.1  # mm, mesure sur scan, +0,27 %

# P21 hangs on diagonal O, whose crossed-plan reading also places P12, through
# N, 73 mm away from the scan. It stays out of the determined set.
INVALID = {21: "diagonal O not decoded: the same reading misses P12 by 73 mm on the scan"}


def classify(p):
    """DETERMINE si la cote longitudinale est publiee, PARAMETRIQUE sinon."""
    if p in INVALID:
        return "INVALIDE"
    if X_SOURCE[p].startswith("MANUAL"):
        return "DETERMINE"
    return "MESURE_SCAN" if X_SOURCE[p].startswith("SCAN") else "PARAMETRIQUE"


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
scan = [k for k, v in points.items() if v["x_statut"] == "MESURE_SCAN"]
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
        "incertitude_mm": REGISTRATION_U,
        "source": "published chain tied to the scan on P5, P17 and P19 (scan_tie_50_05a.py)",
        "effet": "translation rigide de tout le reseau ; ne change aucune cote relative",
    },
    "cote_gouvernante": {
        "nom": "SPAN_P5_P12",
        "definition": "entraxe longitudinal fixation train avant -> traverse essieu arriere",
        "valeur_mm": round(SPAN_P5_P12, 1),
        "x_sources": [X_SOURCE[5], X_SOURCE[12]],
        "statut": "P5 published (50-05a); P12 measured on the scan, not published",
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

print(f"\nTransverse: {len(points)}/{len(points)} points published in the manual, tolerance 1 to 2 mm.")
print(f"Longitudinal: {len(det)} determined {det}, {len(scan)} measured on the scan {scan}, "
      f"{len(par)} parametric {par}, {len(inv)} invalid {inv}.")
print(f"""
Since plate 50-05a was read, the front suspension mounts P3 and P5 are
determined from published dimensions, like the jacking points. Governing
dimension SPAN_P5_P12 = {SPAN_P5_P12:.1f} mm: P5 published, P12 measured on the
scan (+/- {REGISTRATION_U} mm on the tie). The previous value, 1724.3 mm, was
wrong at both ends: dimension P read as a diagonal put P5 230 mm forward, and
diagonal N put P12 73 mm forward.

Still open before any tooling: P12 and P21 from a publication (diagonals N
and O are not decoded), and the rear suspension mounts P13 and P14.
""")
print("ecrit ../derived/monocoque-interface.json")
