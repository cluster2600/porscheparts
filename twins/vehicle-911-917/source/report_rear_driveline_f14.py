#!/usr/bin/env python3
"""Planche des résultats calculés et captures natives, sans retouche géométrique."""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps
from annotate_picogk_visualization_f11 import cropped_capture, font, sha256
from study_rear_driveline_f14 import OUTPUT, ROOT


def main():
    inputs = OUTPUT / "study-inputs-f14.json"
    c = json.loads(inputs.read_text())
    r = json.loads((OUTPUT / "picogk-driveline-report-f14.json").read_text())
    if r["input_sha256"].lower() != sha256(inputs) or any(r["release_gates"].values()):
        raise ValueError("stale or physically released report rejected")
    if any(sha256(ROOT / entry["path"]) != entry["sha256"] for entry in c["inputs"]):
        raise ValueError("source or configuration changed after calculation")
    board = Image.new("RGB", (2400, 2000), "#f3f4f6")
    d = ImageDraw.Draw(board)
    d.rectangle((0, 0, 2400, 165), fill="#142234")
    d.text((55, 28), "911 / 917     ÉTUDE MÉCANIQUE DU TRAIN ARRIÈRE", font=font(39, bold=True), fill="white")
    d.text((55, 94), "F14   •   Géométrie PicoGK, voxel 2 mm   •   Comparaison de deux implantations, pas un plan de fabrication", font=font(24), fill="#cbd5e1")
    panels = [("baseline-isometric", "01  ÉTAT F13 : INTERFÉRENCES", 55, 195, 1100, 690),
              ("candidate-isometric", "02  VARIANTE : PASSAGE DES CARDANS DÉGAGÉ", 1235, 195, 1100, 690),
              ("candidate-rear", "03  VUE ARRIÈRE : VOIE ET HAUTEURS DE LA VARIANTE", 55, 990, 1320, 660)]
    for key, title, x, y, w, h in panels:
        d.text((x, y), title, font=font(25, bold=True), fill="#142234")
        capture = cropped_capture(OUTPUT / f"{key}-f14.tga")
        fitted = ImageOps.contain(capture, (w, h - 55), Image.Resampling.LANCZOS)
        board.paste(fitted, (x + (w - fitted.width) // 2, y + 50 + (h - 55 - fitted.height) // 2))
    labels = [("#64748b", "GRIS : corridors berceau / plancher"), ("#22a89c", "VERT : volume parcouru par les cardans"),
              ("#d52e36", "ROUGE : intersection calculée"), ("#c99a4f", "OCRE : boîte-pont hypothétique")]
    for i, (color, label) in enumerate(labels):
        x = 55 + (i % 2) * 1180; y = 895 + (i // 2) * 40
        d.rectangle((x, y, x + 23, y + 23), fill=color)
        d.text((x + 36, y - 1), label, font=font(23), fill="#334155")
    y = 1055
    lines = ["DONNÉES DE LA VARIANTE D'ÉTUDE", f"Voie AR : {c['candidate_rear_track_mm']:.0f} mm",
             f"Largeur extérieure des pneus : {c['tyre_outer_width_mm']['candidate']:.0f} mm",
             "Largeur d'un pneu hypothétique : 260 mm", "Longerons : Y = ±690 ; Z = 590 mm",
             "Course étudiée : ±80 mm, verticale seule", "Réserve demandée : 20 mm",
             f"Réserve testée avec garde : {r['continuous_keepout_allowance_mm']:.0f} mm", "(échantillonnage + résolution inclus)"]
    for i, text in enumerate(lines):
        d.text((1430, y), text, font=font(25, bold=(i == 0)), fill="#142234" if i == 0 else "#334155")
        y += 55 if i == 0 else 45
    d.rectangle((55, 1690, 2345, 1810), fill="#e2e8f0")
    b = c["kinematics"]["baseline"][-1]; a = c["kinematics"]["candidate"][-1]
    d.text((80, 1705), "À ±80 mm : comparaison analytique des besoins aux joints", font=font(25, bold=True), fill="#142234")
    d.text((80, 1755), f"F13 : {b['required_joint_angle_deg']:.2f}° / {b['required_length_change_mm']:.2f} mm       Variante : {a['required_joint_angle_deg']:.2f}° / {a['required_length_change_mm']:.2f} mm de variation de longueur", font=font(26), fill="#334155")
    d.text((55, 1850), "Contrôle local : berceau / cardans / enveloppes de pneus. Ne valide ni la suspension ni la tenue à 1 600 ch.", font=font(26, bold=True), fill="#9a3412")
    d.text((55, 1900), "Empattement conservé à 2 722 mm. Coque, fixations, masses, efforts, freinage et joints réels restent à définir.", font=font(25), fill="#475569")
    image_path = OUTPUT / "rear-driveline-engineering-board-f14.png"
    board.save(image_path)
    rows = []
    for name, label in (("baseline", "F13"), ("candidate", "Variante F14")):
        for case in c["kinematics"][name]:
            rows.append(f"| {label} | ±{case['travel_each_direction_mm']:.0f} | {case['nominal_joint_distance_mm']:.0f} | {case['required_joint_angle_deg']:.3f} | {case['required_length_change_mm']:.3f} |")
    checks = []
    for name in ("baseline", "candidate"):
        for key, result in r["cases"][name].items():
            if isinstance(result, dict):
                checks.append(f"| {name} | {key} | {'INTERFÉRENCE' if result['collision'] else 'Aucune intersection sur ce modèle'} |")
    report = f"""# 911 / 917 — étude mécanique F14

![Contrôles natifs PicoGK](rear-driveline-engineering-board-f14.png)

## Résultat et décision

L'implantation F13 est rejetée dans la baie arrière : les cardans recoupent le berceau à l'arrêt et en mouvement.
Une **variante d'encombrement**, non une architecture approuvée, écarte ces intersections : voie de 1 840 mm,
longerons déplacés à Y = ±690 / Z = 590 mm, suppression des traverses dans le passage des cardans,
traverse arrière conservée à X = 3 440 mm, plancher rétréci à 1 100 mm et abaissé de 20 mm.
Les raccordements de ce berceau à la coque ne sont pas conçus ; sa continuité résistante n'est pas démontrée.

Cette variante exige **2 100 mm entre faces extérieures des pneus**, contre 1 704 mm auparavant, pour les mêmes
pneus hypothétiques de 260 mm. La coque documentaire de 1 735 mm ne couvre donc pas cette variante.
Ce résultat ne prouve pas la motricité : aucun calcul pneu/charge/aérodynamique n'a été effectué.

## Cinématique vérifiable

Repère véhicule : X vers l'arrière, Y transversal, Z vers le haut. Centres de joints intérieurs :
(2 722, ±250, 330) mm. Moyeux nominaux F13 : (2 722, ±722, 330) ; variante : (2 722, ±920, 330).
Translation du moyeu uniquement selon Z ; axes de sortie supposés parallèles à Y.
Avec L = voie/2 − 250 : angle = atan(|déplacement|/L), longueur = sqrt(L² + déplacement²).
La variation est relative à la position neutre, pas le double entre détente et compression.
Elle n'inclut ni tolérances, ni mouvements du groupe, ni migration X/Y du moyeu.

| Cas | Déplacement Z (mm) | Distance neutre (mm) | Angle requis (°) | Variation requise (mm) |
|---|---:|---:|---:|---:|
{chr(10).join(rows)}

Les capacités de joint et de coulissement restent **inconnues**, donc aucun joint n'est accepté.

## Contrôle volumique indépendant — PicoGK {r['kernel']}

Voxel : {r['voxel_size_mm']} mm. Domaine : X 2 500–3 600, Y ±1 200, Z 80–1 050 mm.
Le volume parcouru est échantillonné tous les 4 mm au maximum. Pour tester 20 mm de réserve continue,
on dilate chaque échantillon de 20 + 2 (demi-pas) + 4 (deux voxels) = {r['continuous_keepout_allowance_mm']} mm.
La garantie entre échantillons ne vaut que pour la translation linéaire supposée.
Le contrôle des pneus utilise des boîtes englobantes pleines et conservatrices sur toute la course.

| Cas | Vérification | Résultat |
|---|---|---|
{chr(10).join(checks)}

Bornes analytiques conservatrices cardans/structure de la variante :
{json.dumps(c['candidate_analytic_clearance_lower_bounds_mm'], indent=2)}

Écarts latéraux nominaux : enveloppe moteur/longeron 35 mm ; longeron/face intérieure du pneu 45 mm.
Attention : la réserve moteur démarre à Z = 180 et le plancher proposé finit à Z = 170 : **10 mm seulement**.
La réserve moteur de 20 mm ne serait donc pas satisfaite au plancher ; le véhicule complet reste non accepté.

## Boîte et charge

La boîte visible reste le schéma F13, sans fournisseur sélectionné. Ne pas usiner de cloche sur cette base.
La direction ajustée des rangées de cylindres n'est pas une mesure de l'axe de sortie moteur.
À 7 000 tr/min, 1 600 ch métriques correspondent à {c['torque_sensitivity'][0]['equivalent_input_torque_nm']:.0f} N·m ;
1 600 hp mécaniques à {c['torque_sensitivity'][3]['equivalent_input_torque_nm']:.0f} N·m. Ce ne sont pas des courbes moteur.
Ces valeurs seules ne dimensionnent ni engrenages, ni embrayage, ni cardans : rapports, transitoires et cycle manquent.
La [gamme Albins ST6](https://www.albins.com.au/items-1/st6) reste une piste de consultation,
pas une sélection. Aucun accord de capacité ni plan d'interfaces n'a été reçu.

## Prochaines entrées nécessaires

1. Calibrer le scan et relever la face et l'axe de sortie moteur, séparément des cylindres.
2. Obtenir un plan d'ensemble de boîte et l'accord fournisseur sur le spectre couple/régime/rapport/durée.
3. Mesurer les ancrages de suspension : recalculer carrossage, pincement, migration et enveloppes complètes.
4. Définir les attaches du berceau, masses/centres de gravité et cas de charge avant tout calcul de résistance.
5. Résoudre plancher/moteur, enveloppe de roue/coque, circuits chauds et refroidissement avant figer la largeur.

Le moteur moderne 4 soupapes/biturbo disponible localement n'a pas été substitué au 917 : c'est une autre hypothèse.
Les turbos F13 ne sont pas améliorés par cette étude et leurs raccordements restent ouverts.

## Fichiers et portée

Sources : `twins/vehicle-911-917/rear-driveline-study-f14.json`, `source/study_rear_driveline_f14.py`,
`picogk/RearDrivelineStudy.cs`. Entrées et empreintes : `study-inputs-f14.json` ; calcul natif :
`picogk-driveline-report-f14.json`. Maillages STL et volumes VDB séparés, **inspection uniquement**.
Les sources C#/JSON sont éditables ; les STL ne sont pas une CAO paramétrique de fabrication.

Aucun calcul de résistance/fatigue, aucune CFD, aucune validation physique et aucune autorisation de fabrication.
"""
    (OUTPUT / "engineering-report-f14.md").write_text(report)
    (OUTPUT / "delivery-manifest-f14.json").write_text(json.dumps({"phase": "F14", "files": {
        p.name: sha256(p) for p in sorted(OUTPUT.iterdir()) if p.suffix in (".json", ".png", ".md", ".stl", ".vdb")
        and p.name != "delivery-manifest-f14.json"}}, indent=2) + "\n")
    print(image_path)


if __name__ == "__main__":
    main()
