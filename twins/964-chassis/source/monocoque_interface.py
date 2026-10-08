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
    13: (1200, 1),    # 50-05a "transversal 1200", attributed to P13 by its position on the plan
    14: (616.6, 2),   # 50-05a, between the rear strut mounts P14
    15: (None, None), # 50-05a draws P15 without a transverse dimension
}
# Longitudinal chain: published dimensions (plates 50-02, 50-03, 50-05a), see
# datum_chain_50_05a.py; P13, P14, P15 scaled off plate 50-05a, see
# plate_50_05a_scale.py; the tie to the scan, see scan_tie_50_05a.py.
CHAIN = json.load(open("../derived/datum-chain-50-05a.json"))
TIE = json.load(open("../evidence/scan-tie-50-05a.json"))
DRAWING = json.load(open("../derived/plate-50-05a-scaled.json"))
D17 = CHAIN["points"]["P17"]["d_behind_0_line_mm"]
X_LOCAL = {int(name[1:]): row["x_from_P17_mm"] for name, row in CHAIN["points"].items()
           if name not in ("P1", "P16")}
for name in ("P13", "P14", "P15"):
    X_LOCAL[int(name[1:])] = round(D17 - DRAWING["points"][name]["d_behind_0_line_mm"], 1)
X_SOURCE = {17: "MANUAL(50-05a via K and L)", 18: "MANUAL(R)", 19: "MANUAL(S)",
            20: "MANUAL(50-05a 143, P)", 3: "MANUAL(50-05a 215)", 5: "MANUAL(50-05a 143)",
            21: "MANUAL(O, unbracketed)", 12: "MANUAL(O and N, unbracketed)",
            13: "DRAWING(50-05a scaled)", 14: "DRAWING(50-05a scaled)", 15: "DRAWING(50-05a scaled)"}

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
    13: ("Mount - outer cross tube RA",        "suspension"),
    14: ("Mount - RA spring strut",            "suspension"),
    15: ("Mount - engine bearing",             "groupe motopropulseur"),
}

# P17 in the vehicle frame: the published chain tied to the scan by the offset
# of the plate 0 line, measured on P5, P17 and P19 (scan_tie_50_05a.py).
REGISTRATION_X = round(TIE["delta"]["value_mm"] - CHAIN["points"]["P17"]["d_behind_0_line_mm"], 1)
REGISTRATION_U = TIE["delta"]["u_mm"]
WHEELBASE_FACTORY = 2272.0  # mm, catalogue 964
WHEELBASE_SCANNED = 2278.1  # mm, mesure sur scan, +0,27 %

# No point is invalid since the rear diagonals were read (datum_chain_50_05a.py).
INVALID = {}


def classify(p):
    """DETERMINE si la cote longitudinale est publiee, PARAMETRIQUE sinon."""
    if p in INVALID:
        return "INVALIDE"
    if X_SOURCE[p].startswith("MANUAL"):
        return "DETERMINE"
    if X_SOURCE[p].startswith("DRAWING"):
        return "MESURE_DESSIN"
    return "MESURE_SCAN" if X_SOURCE[p].startswith("SCAN") else "PARAMETRIQUE"


points = {}
for p in sorted(TRANSVERSE, key=lambda k: -X_LOCAL.get(k, 0)):
    if p not in X_LOCAL:
        continue                       # P6 : pas de cote longitudinale publiee
    span, tol = TRANSVERSE[p]
    points[f"P{p}"] = {
        "designation": ROLE[p][0],
        "fonction_monocoque": ROLE[p][1],
        "y_half_mm": span / 2.0 if span else None,
        "y_tolerance_mm": tol,
        "y_source": "MANUAL" if span else "NOT PUBLISHED",
        "x_local_mm": X_LOCAL[p],      # chaine locale, P17 = 0
        "x_source": X_SOURCE[p],
        "x_statut": classify(p),
        "x_vehicle_mm_provisoire": round(X_LOCAL[p] + REGISTRATION_X, 1),
    }
    if p in INVALID:
        points[f"P{p}"]["invalide_raison"] = INVALID[p]

det = [k for k, v in points.items() if v["x_statut"] == "DETERMINE"]
drawn = [k for k, v in points.items() if v["x_statut"] == "MESURE_DESSIN"]
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
        "statut": "both ends published: P5 (50-05a, 143) and P12 (diagonals O and N, unbracketed); P12 cross-checked by plates 50-05a and 50-02",
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
          f"{v['y_half_mm'] if v['y_half_mm'] is not None else float('nan'):8.1f}{v['x_local_mm']:10.1f}  {v['x_statut']}")

print(f"\nLongitudinal: {len(det)} determined from published dimensions {det}, "
      f"{len(drawn)} scaled off plate 50-05a {drawn}, {len(scan)} measured on the scan {scan}, "
      f"{len(par)} parametric {par}, {len(inv)} invalid {inv}.")
print(f"""
Governing dimension SPAN_P5_P12 = {SPAN_P5_P12:.1f} mm, both ends published.
Its history: 1724.3 mm with P read as a diagonal and the bracketed N; 1567.3 mm
with P12 taken from the transmission carrier's bolts on the scan; {SPAN_P5_P12:.1f} mm
with the rear diagonals read unbracketed, which plates 50-05a and 50-02 confirm
within 3 to 6 mm.

The rear suspension mounts P13 and P14 and the engine mount P15 are scaled off
plate 50-05a (+/- {DRAWING["points"]["P14"]["u_mm"]} mm): good enough to lay out
a structure, not to cut a tool. The tie to the scan's wheel frame carries
+/- {REGISTRATION_U} mm.
""")
print("ecrit ../derived/monocoque-interface.json")
