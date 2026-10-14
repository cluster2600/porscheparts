# 911–917 — packaging and driveline studies F0–F15

## F15 integrated vehicle

See the [whole-vehicle PicoGK packaging study](FULL_VEHICLE.md) for the 47-part
assembly, native views, component exports, collision checks and unresolved
functional interfaces. The public model does not require or publish the scan.
F0–F14 below remains the historical baseline, not superseded physical evidence.

## Integration status

See the [integration result and next engineering gate](INTEGRATION.md), including
the scan-free native PicoGK comparison preview.

This directory preserves the earlier French design history and adds the F13
scan-row alignment correction and F14 rear-driveline clearance study. It is
research software, not a released vehicle or a set of functional parts.
The scan does not establish an exact 917/30 or turbo-engine variant.

The current vehicle reference lives at
`twins/993-reference-envelope/reference-envelope.json`. The unused dependency
on the unrelated local carbon-cell study has been removed. Source scans,
derived scan geometry, local renderings and build/runtime binaries are not
published. The scan-free F14 comparison preview may be published separately.
NumPy and Pillow are needed for the Python geometry/image checks;
the native model requires .NET 9 and PicoGK 2.3.0.

F14 rejects the previous shaft/frame intersections. Its trial uses a 1,840 mm
rear track, 260 mm hypothetical tire width and vertical-only hub motion of
±80 mm. Required joint angle is 6.81 degrees and joint-distance change is
4.76 mm. The 2 mm PicoGK test adds 20 mm requested clearance, 2 mm sampling
allowance and a two-voxel guard. That trial is not selected: it requires
2,100 mm tire outer width and leaves only 10 mm below the engine reservation.
It does not include suspension geometry, proven chassis attachments,
structural calculations or supplier-approved driveline capacity.

F14 can be reproduced without any private scan or report. Its preparation
reads the tracked F1 hypotheses and the documentary vehicle reference directly;
F0–F13 scan-dependent runs still require the explicitly listed private inputs.

The next engineering decision must jointly address body width, engine/floor
clearance and suspension/shaft envelopes. Engine output datums, transaxle
interfaces, masses/centers of gravity and loads remain missing; no plausible
coordinate may substitute for those measurements.

## Earlier design history (French)

Cette étude commence le dessin d’une 911 type 993 recevant un flat-12 de
917/30 biturbo. Elle compare l’architecture naturelle de la 911 — boîte devant
le moteur — à l’implantation centrale de la 917.

## Décision F1 — comportement prioritaire

La F1 remplace l’implantation retenue en F0 : le moteur n’est plus suspendu
derrière les roues arrière. Le flat-12 occupe l’ancienne zone de banquette,
devant le nouvel essieu arrière, et le transaxle est réservé derrière lui. Le
plus court essai passant parmi les trois dessinés porte l’empattement de
2 272 à **2 722 mm**, soit **+450 mm**.

Dans ce screening, la réserve moteur commence à X=1 472 mm, donc 107 mm après
la limite arrière hypothétique des occupants et 52 mm après la cloison
provisoire. Le centre géométrique du scan partiel se trouve environ 654 mm
devant l’essieu arrière. Ce point n’est pas le centre de masse du moteur et la
répartition 55–60 % arrière affichée est une cible, pas un résultat calculé.

Les sorties F1 restent dans `work/911-917-packaging-f1/`, hors Git :

- `911-917-mid-engine-layout-f1.png` et `.svg` : élévation cotée, vue de dessus
  et comparaison des empattements +300/+450/+600 mm ;
- `911-917-mid-engine-packaging-f1.step` : volumes de garde Build123d ;
- `911-917-mid-engine-designer-f1.png` : vue de designer générée à partir de la
  planche technique, non cotée et non dimensionnelle ;
- `packaging-report-f1.json` : calculs reproductibles et limites de preuve.

Le mode, le prompt exact et les empreintes de la vue de designer sont conservés
dans `designer-render-f1.json`.

### Variantes F2/F3 — aileron 930 et caisse étirée

F2 remplace le grand aileron de course par une « whale tail » fixe inspirée de
la 930 Turbo. Un échangeur horizontal d’air de suralimentation est montré sous
sa grille, avec une sortie d’air canalisée. F3 corrige ensuite la perspective de
la vue trois-quarts : les 450 mm sont visiblement ajoutés entre la cabine et
l’essieu arrière, pas dans le porte-à-faux.

- `911-917-mid-engine-930-tail-f2.png` : première intégration de l’aileron et de
  l’échangeur ;
- `911-917-mid-engine-930-tail-stretched-f3.png` : vue trois-quarts corrigée ;
- `designer-render-930-tail-f2.json` et
  `designer-render-930-tail-stretched-f3.json` : prompts, empreintes et limites.

F4 reprend la référence visuelle fournie par l’utilisateur : la lèvre supérieure
est plus large, plus reculée et remonte davantage. L’échangeur reste sous la
grille. Le rendu final est `911-917-mid-engine-930-tail-wide-f4.png` et son
contrat de provenance `designer-render-930-tail-wide-f4.json`. La photographie
de référence n’est pas copiée dans le dépôt et reste interdite de publication
tant que ses droits ne sont pas établis.

Ces images ne dimensionnent ni la puissance thermique, ni la perte de charge,
ni l’équilibre aérodynamique. Le dessin coté et le STEP F1 restent l’autorité
géométrique du screening.

### Variante F5 — prises d’air de custode et cloison moteur

F5 supprime les deux vitres latérales arrière. Leurs ouvertures deviennent des
prises d’air symétriques à ailettes, reliées visuellement à des plénums et aux
conduits du refroidissement moteur et des admissions biturbo. Une cloison pleine
hauteur à double peau ferme l’habitacle immédiatement derrière les sièges.

Le rendu est `911-917-mid-engine-intakes-firewall-f5.png` et sa provenance est
conservée dans `designer-render-intakes-firewall-f5.json`. Les sections de
passage, pertes de charge, entrées d’eau, matériaux, joints, traversées et tenue
au feu restent inconnus ; aucune fonction de sécurité n’est validée.

### Variante F6 — habitacle visuellement fermé

F6 corrige la vue trois-quarts : aucun siège, dossier ou volume habitable ne
subsiste derrière le montant B. La lunette arrière montre la face opaque de la
cloison, tandis que la coupe conserve exactement deux sièges devant celle-ci.
Le rendu final est `911-917-mid-engine-cabin-closed-f6.png` et les deux retouches
sont consignées dans `designer-render-cabin-closed-f6.json`.

### Variante F7 — cloison droite dans la coupe

F7 corrige uniquement la géométrie apparente de la cloison moteur dans la coupe
latérale. Ses deux peaux sont représentées par des lignes verticales parallèles,
sans cassure ni inclinaison, et la cloison reste continue du plancher à la
structure supérieure derrière les deux sièges. Le rendu est
`911-917-mid-engine-straight-firewall-f7.png` et sa provenance est conservée
dans `designer-render-straight-firewall-f7.json`.

Cette rectitude est une intention graphique : la position longitudinale,
l'épaisseur, les interfaces de coque et les performances feu/fumées ne sont pas
encore cotées ni validées.

### Variante F8 — profil de toit corrigé et gel artistique

F8 remplace, dans la coupe uniquement, le toit en pente montante par un arc de
coupé peu prononcé : raccord tangent au pare-brise, sommet au-dessus des
occupants avant, puis descente continue vers la cloison verticale. Le rendu est
`911-917-mid-engine-roof-profile-f8.png` et sa provenance est conservée dans
`designer-render-roof-profile-f8.json`.

F8 clôt les rendus artistiques. Son profil sert de brief visuel, pas de surface
CAO : la suite du projet doit partir des datums de coque mesurés, d'enveloppes
3D traçables et de calculs mécaniques reproductibles.

## F9 — démarrage de l'ingénierie mécanique

`mechanical-engineering-basis-f9.json` remplace le raisonnement par image par
un registre calculable et fermé par défaut. Le script
`source/build_mechanical_engineering_basis_f9.py` calcule le couple équivalent
à 1 600 mechanical hp entre 7 000 et 9 000 tr/min, applique un facteur de
screening provisoire de 1,30 et compare ce besoin aux seules valeurs publiées
par D.M.A., Hewland et Xtrac.

Le résultat F9 ne sélectionne aucune boîte. Le facteur 1,30 n'est pas un critère
de réception : il devra être remplacé par la courbe moteur mesurée, les pics
torsionnels et un spectre de charge accepté par le fabricant. Le registre F9
énumère aussi les mesures manquantes pour les datums de coque, l'enveloppe
moteur complète, les masses/centres de gravité, les interfaces de boîte, les
charges dynamiques et les rejets thermiques.

```bash
python3 twins/vehicle-911-917/source/build_mechanical_engineering_basis_f9.py --mode build
python3 twins/vehicle-911-917/source/build_mechanical_engineering_basis_f9.py --mode check
```

Le contrôle F9 compare le rapport enregistré au résultat recalculé. Un rapport
absent ou périmé échoue ; il faut alors relancer `--mode build`.

## F10 — contrôle volumique PicoGK

F10 remplace la simple boîte englobante du scan par sa surface complète
réorientée, voxelisée par PicoGK 2.3.0. Le calcul teste les intersections avec
la zone interdite devant la cloison, le plancher et la zone située derrière
l'essieu arrière. L'enveloppe du moteur complet reste une hypothèse distincte.

Le maillage source étant ouvert, PicoGK construit une coque voxel de contrôle,
pas un volume moteur. La boîte n'est pas modélisée : aucun produit n'est
sélectionné et aucun plan général constructeur n'est disponible.

```bash
python3 twins/vehicle-911-917/source/prepare_picogk_scan_f10.py --mode build
python3 twins/vehicle-911-917/source/prepare_picogk_scan_f10.py --mode check
```

Le reçu F10 lie le STL au scan source et aux rapports de packaging et de
métrologie utilisés pour le repère. Toute modification de ces entrées impose
de reconstruire le STL ; les anciens reçus sans ces empreintes sont rejetés.

## F11 — vues d'ingénierie PicoGK

F11 ajoute au scan voxelisé une coque 911 transparente fondée sur les dimensions
documentaires et le profil hypothétique F1, l'enveloppe réservée au moteur
complet, les plans du pare-feu, du plancher, de la limite occupants et de
l'essieu arrière. PicoGK produit quatre captures natives : latérale, coupe
agrandie du compartiment moteur, dessus et isométrique. Le post-traitement ne
modifie pas la géométrie : il convertit et annote seulement les captures.

La marge de 2 mm au-delà du dégagement de pare-feu reste inférieure au voxel de
5 mm et n'est donc pas résolue. La boîte n'est pas dessinée tant qu'aucune boîte
et aucun plan général constructeur ne sont sélectionnés. La planche principale
est `work/911-917-picogk-f11/picogk-packaging-engineering-board-f11.png`.

Le générateur courant a évolué en F12. Les sorties F11 restent conservées comme
témoin historique.

## F12 — maquette d'encombrement complète PicoGK

**F12 est conservée comme historique et remplacée par F13 pour le contrôle
d'implantation.** Son axe issu d'une analyse globale des deux bancs introduisait
une rotation parasite de 7,51°. Ses boîtes et sphères ne représentaient pas une
transmission ni des turbos détaillés.

F12 représente avec PicoGK le scan moteur, l'enveloppe du moteur complet, la
coque, la cloison droite et les corridors de structure arrière, les roues et
essieux, les volumes chauds des deux turbos et des échappements, les admissions
par les custodes, les conduits de refroidissement, ainsi que l'aileron fixe de
type 930 avec son plénum et son échangeur. Chaque sous-système est exporté en
VDB, avec un VDB d'assemblage et quatre captures natives annotées.

Ces volumes ne sont pas tous des pièces mesurées. La boîte violette est
explicitement la réserve historique F1, non une transmission sélectionnée ou
qualifiée pour 1 600 ch. Le scan moteur reste non étalonné; la caisse, les
turbos, les conduits, la structure, les roues et l'aileron sont des hypothèses
d'encombrement. La planche principale est
`work/911-917-picogk-f12/picogk-full-vehicle-engineering-board-f12.png`.

## F13 — correction d'axe et assemblage mécanique lisible

Le recalage ajuste une direction commune après centrage indépendant de chaque
rangée de six ouvertures. Il retire le biais dû au décalage entre bancs. Le scan
est transformé rigidement dans PicoGK : ni rotation de l'image, ni déformation du
moteur. Ce repère géométrique ne remplace pas une mesure du vilebrequin et de la
face de fixation.

La boîte-pont possède désormais une cloche, un carter, un différentiel et ses
brides. Les deux turbos sont des corps compresseur/turbine schématiques reliés
par leur palier central. Deux demi-arbres avec joints relient les sorties du
différentiel aux moyeux arrière. À l'avant, la ligne pointillée indique le plan
d'essieu; aucun arbre moteur transversal n'est inventé. Les surfaces de coque et
les conduits sont masqués dans les vues mécaniques rapprochées.

Une intersection entre cardans et corridors de structure F12 est calculée,
exportée et signalée en rouge. Elle reste à résoudre avec le berceau et les
débattements réels. Les cotes de boîte, de turbo et de suspension restent des
hypothèses; aucune tenue à 1 600 ch n'est démontrée. Les images F12 ne doivent
plus servir à juger l'alignement ou la présence de ces composants.

Le générateur courant PicoGK 2.3.0 cible .NET 9. Les entrées locales F10 et F1
doivent déjà exister :

```bash
python3 twins/vehicle-911-917/source/prepare_picogk_alignment_f13.py
REPOSITORY_ROOT="$PWD" PICOGK_INPUT_DIR="$PWD/work/911-917-picogk-f10" \
  PICOGK_OUTPUT_DIR="$PWD/work/911-917-picogk-f13" \
  dotnet run --project twins/vehicle-911-917/picogk/Vehicle911917Packaging.csproj
python3 twins/vehicle-911-917/source/annotate_picogk_mechanical_f13.py
python3 -m unittest discover -s tests -p 'test_911_917_*.py'
```

La nouvelle planche est
`work/911-917-picogk-f13/picogk-mechanical-engineering-board-f13.png`.
Le rapport `picogk-mechanical-report-f13.json` contient la transformation, les
bounds voxelisés, les contrôles d'intersection et les points de raccordement.
`image-manifest-f13.json` lie les PNG et VDB à leurs empreintes SHA-256.

Le recalage F13 lie aussi sa matrice aux rapports F1 et de métrologie, à la
configuration mécanique, au reçu F10 et aux deux scripts de préparation.
Le lecteur natif vérifie ces empreintes et une transformation rigide finie
avant de lancer PicoGK. Le lecteur Python contrôle la même provenance avant
d'annoter un résultat. Après une modification, reconstruire F10 si nécessaire,
puis le recalage et les sorties F13 ; un ancien résultat ne vaut pas une
vérification des nouvelles entrées.

```bash
python3 twins/vehicle-911-917/source/build_mid_engine_layout_f1.py --mode render
.venv/bin/python twins/vehicle-911-917/source/build_mid_engine_layout_f1.py --mode cad
python3 twins/vehicle-911-917/source/build_mid_engine_layout_f1.py --mode check
```

L’empattement +300 mm échoue sur les dégagements occupants/cloison. Le +600 mm
offre davantage d’espace, mais allonge inutilement la voiture à ce stade. Le
+450 mm est donc une décision de dessin réversible, à revalider dès réception
du plan général de boîte et des mesures de caisse.

## F14 — étude mécanique du passage des cardans

F14 compare le berceau F13 à une variante dans la seule baie arrière
X = 2 500–3 600 mm. Les cardans sont évalués à ±40/60/80 mm de translation
verticale hypothétique : angles, variation de longueur et volume parcouru.
Un contrôle PicoGK à 2 mm ajoute une réserve de 20 mm, une garde
d'échantillonnage de 2 mm et une garde numérique de deux voxels.
Les boîtes englobantes des pneus en mouvement sont aussi contrôlées.

La variante écarte les intersections testées mais exige une voie de 1 840 mm
et 2 100 mm entre faces extérieures des pneus hypothétiques. Elle déplace les
longerons et le plancher : **ce n'est pas une modification approuvée de la coque**.
Les ancrages et la résistance ne sont pas calculés. Le dégagement moteur/plancher
reste de 10 mm seulement ; aucun résultat local ne valide le véhicule complet.
Les entrées inconnues, dont l'axe de sortie moteur et les capacités des joints,
restent nulles. F13 et son recalage du scan sont conservés.

```bash
python3 twins/vehicle-911-917/source/study_rear_driveline_f14.py
PICOGK_STUDY_F14=1 REPOSITORY_ROOT="$PWD" \
  dotnet run --project twins/vehicle-911-917/picogk/Vehicle911917Packaging.csproj
python3 twins/vehicle-911-917/source/report_rear_driveline_f14.py
python3 -m unittest discover -s tests -p 'test_911_917_*.py' -v
```

Sorties privées dans `work/911-917-picogk-f14/` :

- `engineering-report-f14.md` : décisions, hypothèses, tableaux et limites ;
- `rear-driveline-engineering-board-f14.png` : captures natives comparatives ;
- `study-inputs-f14.json` : calcul analytique et empreintes des entrées/sources ;
- `picogk-driveline-report-f14.json` : intersections et portée des contrôles ;
- STL/VDB séparés : volumes d'inspection, pas des pièces à fabriquer.

## Décision F0 — historique, non retenue pour la suite

L’essai alors retenu conservait l’empattement documentaire de 2 272 mm, supprimait les
places arrière, réservait la boîte devant le moteur et allongeait provisoirement la
poupe de 450 mm. Cette configuration est la seule des trois à préserver la zone
occupants déjà utilisée par le modèle de screening tout en laissant au moins
75 mm derrière la réserve du moteur complet.

Ce n’est pas encore une validation de montage :

- le scan local du carter et des cylindres est réellement lu par le générateur,
  mais son échelle 1:1 et son orientation restent non étalonnées ;
- le scan ne contient pas les culasses complètes, les collecteurs, les turbos,
  les écrans thermiques ou les volumes de maintenance ;
- aucune boîte candidate ne publie à la fois un plan général coté, les
  interfaces nécessaires et une marge de couple acceptée pour l’objectif de
  1 600 ch ;
- la silhouette de carrosserie est un dessin de présentation autour des
  dimensions documentaires de la 993, pas une surface Porsche reconstruite.

## Sorties locales

Les sorties restent dans `work/911-917-packaging-f0/`, hors Git :

- `911-917-packaging-f0.png` et `.svg` : élévation, vue de dessus et comparaison
  des trois essais ;
- `911-917-packaging-preferred-f0.step` : volumes de garde Build123d de
  l’implantation retenue ;
- `packaging-report-f0.json` : cotes calculées, provenance, décisions et gates.

Le dessin est produit avec Matplotlib et la CAO avec Build123d 0.11.1 déjà
présent dans `.venv` :

```bash
python3 twins/vehicle-911-917/source/build_packaging_concept_f0.py --mode render
.venv/bin/python twins/vehicle-911-917/source/build_packaging_concept_f0.py --mode cad
python3 twins/vehicle-911-917/source/build_packaging_concept_f0.py --mode check
```

## Lecture des couleurs

- orange plein : projection du scan local réorienté pour le screening ;
- orange transparent : réserve hypothétique du moteur complet ;
- bleu : réserve de boîte, non issue d’un plan constructeur ;
- gris : enveloppe de carrosserie et zone des places arrière supprimées ;
- rouge pointillé : cloison pare-feu à définir après mesure de caisse.

La recherche de transmission et les données à demander aux constructeurs sont
détaillées dans [gearbox-shortlist.md](research/gearbox-shortlist.md).

## Porte suivante

Avant de figer le dessin, il faut obtenir un plan général ou un STEP de la
boîte, mesurer la coque et les sièges, étalonner le scan moteur, puis remplacer
la réserve moteur par l’assemblage complet avec admission, échappement,
refroidissement et biturbo. Tous les gates de fabrication, route et circuit
restent fermés.
