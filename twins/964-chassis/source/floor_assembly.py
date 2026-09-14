"""
Jumeau numerique du chassis (plancher) de la Porsche 911 (964) — modele parametrique acier.

Repere : ADR 0003. Origine sur le plan de symetrie, a la verticale du centre
d'essieu avant, sur le plan de sol nominal. X vers l'avant, Y vers la gauche,
Z vers le haut. Unites mm.

Chaque cote porte sa provenance :
  MANUAL  = manuel d'atelier 964 volume V, planches 50-02/50-03/50-05a (avec tolerance)
  SCAN    = mesure sur le scan de dessous recale (MESH-964-UNDERSIDE-2P13)
  ASSUMED = non publie et non mesurable ici ; valeur de travail, a confirmer

Sortie : STEP + resume JSON.  Executer avec le venv .venv-cad (build123d).
"""
from build123d import *
import json, sys

# ----------------------------------------------------------------- parametres
# Ecartements transversaux gauche/droite, table 50-03 (MANUAL, tolerance en mm)
TRANSVERSE = {                      # point : (ecartement, tolerance)
    20: (440, 2), 3: (610, 1), 5: (770, 2), 6: (204, 2), 17: (1330, 1),
    18: (1236, 1), 12: (278, 1), 19: (1018, 1), 21: (640, 1),
}
# Chaine longitudinale, P17 = 0, +X vers l'avant (MANUAL : R et S directement
# publies en vue de cote ; les autres resolus depuis les diagonales projetees)
X_LOCAL = {17: 0.0, 18: -1245.0, 19: -1328.0, 20: 1211.1,
           3: 654.2, 5: 527.3, 21: -2606.1, 12: -1197.0}
X_LOCAL_SOURCE = {17: "MANUAL", 18: "MANUAL(R)", 19: "MANUAL(S)",
                  20: "DERIVED(K)", 3: "DERIVED(L)", 5: "DERIVED(P)",
                  21: "DERIVED(O)", 12: "DERIVED(N)"}
REGISTRATION_X = -506.0             # P17 dans le repere vehicule (SCAN, faiblement contraint)

FLOOR_Z        = 271.7              # SCAN : dessous du plancher au-dessus du sol
FLOOR_X_FRONT  =  400.0             # SCAN : limite avant du plancher plat
FLOOR_X_REAR   = -1500.0            # SCAN : limite arriere du plancher plat
SILL_INNER_Y   =  600.0             # SCAN/MANUAL : bord interieur du longeron
SHEET_T        =    1.0             # ASSUMED : tole de plancher, epaisseur non publiee
SILL_W, SILL_H =   90.0, 120.0      # ASSUMED : section du longeron, non publiee
XMEMBER_W, XMEMBER_H = 80.0, 70.0   # ASSUMED : section de traverse, non publiee

MATERIAL = {
    "floor_pan":  "acier (nuance non publiee au volume V)",
    "sill":       "acier haute resistance HS (planche 50-013, 'inner side member')",
    "front_floor_member": "acier haute resistance HS (planche 50-013)",
    "seat_base":  "acier haute resistance HS (planche 50-013)",
    "rear_axle_crossmember": "acier haute resistance HS (planche 50-013)",
    "engine_mount_crossmember": "acier haute resistance HS (planche 50-013)",
}

def half(p): return TRANSVERSE[p][0] / 2.0
def xv(p):   return X_LOCAL[p] + REGISTRATION_X          # -> repere vehicule

# ----------------------------------------------------------------- geometrie
parts = {}

# 1. Plancher : tole plate entre les longerons (SCAN pour l'etendue)
with BuildPart() as floor:
    with BuildSketch(Plane.XY.offset(FLOOR_Z)):
        Rectangle(FLOOR_X_FRONT - FLOOR_X_REAR, 2 * SILL_INNER_Y,
                  align=(Align.CENTER, Align.CENTER))
    extrude(amount=SHEET_T)
floor.part.move(Location((( FLOOR_X_FRONT + FLOOR_X_REAR)/2, 0, 0)))
parts["floor_pan"] = floor.part

# 2. Longerons interieurs (inner side member, HS) le long des points de levage.
#    Section creuse en tole : une caisse fermee, pas un barreau plein.
for side, sgn in (("left", +1), ("right", -1)):
    with BuildPart() as sill:
        with BuildSketch(Plane.XY.offset(FLOOR_Z)):
            Rectangle(FLOOR_X_FRONT - FLOOR_X_REAR, SILL_W,
                      align=(Align.CENTER, Align.CENTER))
        extrude(amount=SILL_H)
        with BuildSketch(Plane.XY.offset(FLOOR_Z + SHEET_T)):
            Rectangle(FLOOR_X_FRONT - FLOOR_X_REAR, SILL_W - 2*SHEET_T,
                      align=(Align.CENTER, Align.CENTER))
        extrude(amount=SILL_H - 2*SHEET_T, mode=Mode.SUBTRACT)
    sill.part.move(Location(((FLOOR_X_FRONT + FLOOR_X_REAR)/2,
                             sgn * (SILL_INNER_Y + SILL_W/2), 0)))
    parts[f"sill_{side}"] = sill.part

# 3. Traverses positionnees sur les points de datum publies
def crossmember(name, point, width_span):
    """Traverse en tole pliee, section creuse ouverte vers le plancher."""
    with BuildPart() as cm:
        with BuildSketch(Plane.XY.offset(FLOOR_Z)):
            Rectangle(XMEMBER_W, width_span, align=(Align.CENTER, Align.CENTER))
        extrude(amount=-XMEMBER_H)
        with BuildSketch(Plane.XY.offset(FLOOR_Z)):
            Rectangle(XMEMBER_W - 2*SHEET_T, width_span - 2*SHEET_T,
                      align=(Align.CENTER, Align.CENTER))
        extrude(amount=-(XMEMBER_H - SHEET_T), mode=Mode.SUBTRACT)
    cm.part.move(Location((xv(point), 0, 0)))
    parts[name] = cm.part

crossmember("front_floor_member",        5,  2*half(5)  + XMEMBER_W)   # P5  traverse ext. AV
crossmember("seat_base_member",         17,  2*half(17) - SILL_W)      # P17 assise de siege
crossmember("rear_axle_crossmember",    12,  2*half(12) + 400)         # P12 traverse de boite
crossmember("engine_mount_crossmember", 21,  2*half(21) + 200)         # P21 palier moteur

# 4. Marqueurs de datum (spheres de rayon = tolerance publiee)
datums = []
for p, (span, tol) in TRANSVERSE.items():
    if p not in X_LOCAL:
        continue
    for sgn in (+1, -1):
        with BuildPart() as d:
            Sphere(radius=max(tol, 3))
        d.part.move(Location((xv(p), sgn * half(p), FLOOR_Z)))
        datums.append(d.part)
        parts[f"datum_P{p}_{'L' if sgn>0 else 'R'}"] = d.part

assembly = Compound(children=list(parts.values()))
export_step(assembly, "../derived/964-floor-assembly.step")

summary = {
    "twin": "TWIN-964-CHASSIS-FLOOR-0001",
    "frame": "ADR-0003 vehicule ; X avant, Y gauche, Z haut ; origine essieu avant / sol",
    "units": "mm",
    "registration_P17_x_vehicle": REGISTRATION_X,
    "floor_pan_height_above_ground": FLOOR_Z,
    "sheet_thickness_assumed": SHEET_T,
    "materials": MATERIAL,
    "datum_points": {
        f"P{p}": {"x_vehicle": round(xv(p), 1), "y_half": half(p),
                  "transverse_span": TRANSVERSE[p][0], "tolerance": TRANSVERSE[p][1],
                  "x_source": X_LOCAL_SOURCE[p]}
        for p in sorted(X_LOCAL)},
    "solids": sorted(parts.keys()),
}
json.dump(summary, open("../derived/964-floor-assembly.json", "w"), indent=1)
STEEL_DENSITY = 7.85e-6                      # kg/mm3, acier
struct = {k: v for k, v in parts.items() if not k.startswith("datum_")}
vol = sum(v.volume for v in struct.values())
mass = vol * STEEL_DENSITY
summary["structural_volume_mm3"] = round(vol, 1)
summary["structural_mass_kg_steel"] = round(mass, 2)
summary["mass_note"] = ("Masse des seuls solides modelises, sections creuses de tole. "
                        "Ce n'est pas la masse d'une caisse 964 : traverses avant, "
                        "passages de roue, tabliers et plancher arriere ne sont pas modelises.")
json.dump(summary, open("../derived/964-floor-assembly.json", "w"), indent=1)
print(f"structural volume {vol:.4e} mm3 -> {mass:.1f} kg en acier")
print(f"solids: {len(parts)}")
print(f"bbox mm: {assembly.bounding_box().size}")
print("wrote ../derived/964-floor-assembly.step and .json")
