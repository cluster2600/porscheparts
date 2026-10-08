"""Contrat d'interface du monocoque 964/993 : le jeu de parametres de la conception.

Un monocoque remplace la caisse. Il doit donc porter toutes les interfaces du
vehicule dans un repere unique. Ce script ne dessine rien : il etablit **ce qui
est connu, ce qui ne l'est pas, et ce qui commande quoi**, pour que la conception
puisse etre parametrique au lieu d'attendre le relevé de marbre.

Les designations et les ecartements viennent du registre documentaire
(`MEAS-MANUAL-964-BODY-CONTROL.json`) ; chaque cote longitudinale porte sa provenance :
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
# Names and pair spans from the documentary ledger (plates 50-02 / 50-03).
LEDGER = "catalog/measurements/MEAS-MANUAL-964-BODY-CONTROL.json"
_values = json.loads((Path(__file__).resolve().parents[3] / LEDGER).read_text(encoding="utf-8"))["declared_values"]
DATUMS = {v["details"]["point"]: v for v in _values if v["details"]["kind"] == "datum_point"}
LEDGER_SPANS = {v["details"]["between"][0]: v for v in _values
                if v["details"].get("measurement_kind") == "transverse"}
TRANSVERSE = {p: (*v["numeric_values"], v["value_id"]) for p, v in LEDGER_SPANS.items()}
# Plate 50-05a adds spans that the ledger does not carry yet (local copy).
TRANSVERSE.update({
    13: (1200, 1, "PLATE-50-05a"),    # "transversal 1200", attributed to P13 by its position on the plan
    14: (616.6, 2, "PLATE-50-05a"),   # between the rear strut mounts P14
    15: (None, None, None),           # 50-05a draws P15 without a transverse dimension
})
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

# Functional grouping for the monocoque; the designation itself is the ledger's.
# P12 is the GEARBOX crossmember support (MNL-964BC-0009), not the rear axle.
ROLE = {
    20: "carrosserie", 3: "suspension", 5: "suspension", 6: "suspension",
    17: "levage", 18: "levage", 19: "levage",
    12: "groupe motopropulseur", 21: "groupe motopropulseur",
    13: "suspension", 14: "suspension", 15: "groupe motopropulseur",
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
    """Status of the relative X only, never the validation of a full XYZ point."""
    if p in INVALID:
        return "INVALIDE"
    if p not in X_LOCAL:
        return "MANQUANT"
    if X_SOURCE[p].startswith("MANUAL"):
        return "DETERMINE"
    if X_SOURCE[p].startswith("DRAWING"):
        return "MESURE_DESSIN"
    return "MESURE_SCAN" if X_SOURCE[p].startswith("SCAN") else "PARAMETRIQUE"


points = {}
for p in sorted(TRANSVERSE, key=lambda k: -X_LOCAL.get(k, 0)):
    span, tol, span_source = TRANSVERSE[p]
    x = X_LOCAL.get(p)                 # P6: no published longitudinal dimension
    points[f"P{p}"] = {
        "designation": DATUMS[p]["value_text"],
        "designation_source_value_id": DATUMS[p]["value_id"],
        "fonction_monocoque": ROLE[p],
        "transverse_span_mm": span,
        "transverse_tolerance_mm": tol,
        "transverse_source_value_id": span_source,
        # The published tolerance is on the pair span, not on each Y; y_half
        # assumes left/right symmetry about a median plane still to qualify.
        "y_half_mm": span / 2.0 if span else None,
        "y_tolerance_mm": None,
        "y_source": "DERIVED(MANUAL, symetrie supposee)" if span else "NOT PUBLISHED",
        "x_local_mm": x,               # chaine locale, P17 = 0
        "x_source": X_SOURCE.get(p, "UNKNOWN"),
        "x_statut": classify(p),
        "x_vehicle_mm_provisoire": round(x + REGISTRATION_X, 1) if x is not None else None,
    }
    if p in INVALID:
        points[f"P{p}"]["invalide_raison"] = INVALID[p]

det = [k for k, v in points.items() if v["x_statut"] == "DETERMINE"]
drawn = [k for k, v in points.items() if v["x_statut"] == "MESURE_DESSIN"]
scan = [k for k, v in points.items() if v["x_statut"] == "MESURE_SCAN"]
par = [k for k, v in points.items() if v["x_statut"] == "PARAMETRIQUE"]
inv = [k for k, v in points.items() if v["x_statut"] == "INVALIDE"]
missing = [k for k, v in points.items() if v["x_statut"] == "MANQUANT"]

# --- la cote gouvernante ------------------------------------------------------
# Front axle outer crossmember support (P5) to GEARBOX crossmember support (P12).
# It is neither the wheelbase nor a span between the two axles' mounts.
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
        "incertitude_mm": REGISTRATION_U,
        "source": "published chain tied to the scan on P5, P17 and P19 (scan_tie_50_05a.py)",
        "effet": "translation rigide de tout le reseau ; ne change aucune cote relative",
    },
    "cote_gouvernante": {
        "nom": "SPAN_P5_P12",
        "definition": "ecart longitudinal support traverse essieu avant -> support traverse de boite",
        "defines_wheelbase": False,
        "valeur_mm": round(SPAN_P5_P12, 1),
        "x_sources": [X_SOURCE[5], X_SOURCE[12]],
        "statut": "both ends published: P5 (50-05a, 143) and P12 (diagonals O and N, unbracketed); P12 cross-checked by plates 50-05a and 50-02",
        "consequence": ("Le monocoque impose cet ecart par construction. Une erreur "
                        "deplace les interfaces avant et boite l'une par rapport a l'autre ; "
                        "cette cote ne definit ni l'empattement ni les ancrages de "
                        "suspension arriere (P13, P14), qui se relevent separement."),
    },
    "empattement_reference": {"usine_mm": WHEELBASE_FACTORY, "scan_mm": WHEELBASE_SCANNED},
    "points": points,
    "release_flags": {"geometry_released": False, "manufacturing_released": False},
}

with open("../derived/monocoque-interface.json", "w", encoding="utf-8", newline="\n") as f:
    json.dump(report, f, indent=1, ensure_ascii=False)
    f.write("\n")

# ----------------------------------------------------------------- rapport
print("Contrat d'interface du monocoque 964/993\n")
print(f"{'point':<6}{'designation':<52}{'fonction':<22}{'y/2':>8}{'x local':>10}  statut")
for k, v in points.items():
    y_text = f"{v['y_half_mm']:.1f}" if v["y_half_mm"] is not None else "-"
    x_text = f"{v['x_local_mm']:.1f}" if v["x_local_mm"] is not None else "manquant"
    print(f"{k:<6}{v['designation']:<52}{v['fonction_monocoque']:<22}{y_text:>8}{x_text:>10}  {v['x_statut']}")

print(f"\nLongitudinal: {len(det)} determined from published dimensions {det}, "
      f"{len(drawn)} scaled off plate 50-05a {drawn}, {len(scan)} measured on the scan {scan}, "
      f"{len(par)} parametric {par}, {len(inv)} invalid {inv}, {len(missing)} missing {missing}.")
print(f"""
Governing dimension SPAN_P5_P12 = {SPAN_P5_P12:.1f} mm, both ends published:
front axle outer crossmember (P5) to GEARBOX crossmember (P12), not the wheelbase.
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
