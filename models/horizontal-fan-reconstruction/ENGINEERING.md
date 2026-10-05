# Études du ventilateur horizontal : état et reproduction

[Accueil](../../README.md) · [CAD et rendus](README.md) ·
[Paramètres R0](parameters/R0.json) · [Paramètres V5](parameters/V5.json) ·
[Comparaison mécanique](results/mechanics/mechanical-two-grid-comparison.csv) ·
[Screening LPBF](results/lpbf/lpbf-screen.json) · [Scène OpenUSD](omniverse/studies.usda)

Ces études reprennent les travaux existants : [PR103](https://github.com/cluster2600/porscheparts/pull/103),
[PR105](https://github.com/cluster2600/porscheparts/pull/105),
[programme 993](../../twins/993-engine-cooling-fan-system-f0/README.md),
[PR121](https://github.com/cluster2600/porscheparts/pull/121),
[diagnostic CFD PR123](https://github.com/cluster2600/porscheparts/pull/123) et
[références du système horizontal PR126](https://github.com/cluster2600/porscheparts/pull/126).
Les géométries et résultats des anciennes études restent distincts de R0/V5.
La culasse de PR106 constitue un autre projet.

## Identité, provenance et hypothèses

Le scan a été retrouvé dans les téléchargements iCloud du propriétaire et conservé
localement. Son identité historique, son unité et une éventuelle équivalence
935/993 ne sont pas démontrées. Le brut présente des ouvertures et intersections ;
il n'est ni le domaine CFD ni une pièce prête à fabriquer. Sa disponibilité privée
ne constitue pas une licence publique. Les autorisations expresses du propriétaire
du 4 octobre 2026 couvrent les reconstructions, rendus, scripts, paramètres et
rapports de calcul nettoyés ; le scan brut reste exclu. Aucun droit de réutilisation
supplémentaire n'est accordé par ces autorisations.

R0 est une reconstruction analytique originale, guidée par des proportions relatives
du scan. Les 275 mm, neuf pales, profils, calages, épaisseurs, jeu froid de 1,1 mm,
axes, alésage et interfaces sont des hypothèses. Le repère +Z est l'axe de rotation,
+X celui de l'entrée du renvoi d'angle. Les huit composants ont des BRep valides
avec contrôle de volume après relecture STEP ; le rotor est un solide connecté.
L'assemblage contient neuf solides, car les deux enveloppes de pignons restent
séparées. Aucune denture, portée de roulement, étanchéité ou tolérance n'est définie.

V5 modifie seulement le voile porteur : épaisseur +30 %, volume du rotor +12,76 %.
Les identifiants historiques des calculs commencent par `private_scan_informed` ;
ils sont conservés pour tracer les preuves. Aucun fichier du scan n'est embarqué.

## Rotation et modes propres

CalculiX 2.23, Gmsh 4.15.2, tétraèdres quadratiques C3D10, permutation Gmsh/CalculiX
vérifiée sur les coordonnées de référence. Matériau hypothétique : E = 70 GPa,
ν = 0,33, ρ = 2700 kg/m³ ; unités mm–N–s–tonne. Toutes les translations des nœuds
du seul alésage hypothétique sont fixées ; rotation de 6000 tr/min. Les douze modes
sont calculés sans précontrainte de rotation. Les huit jobs se terminent normalement.

| Cas | C3D10 | Déplacement max (mm) | Extension radiale max (mm) | Premier mode (Hz) | Pic nodal von Mises (MPa) |
|---|---:|---:|---:|---:|---:|
| R0, taille 4,5 mm | 30825 | 0,5043 | 0,2276 | 377,79 | 189,25 |
| R0, taille 3,6 mm | 51796 | 0,5100 | 0,2307 | 376,00 | 225,93 |
| V5, taille 4,5 mm | 31443 | 0,2982 | 0,1568 | 511,38 | 182,39 |
| V5, taille 3,6 mm | 60821 | 0,3033 | 0,1599 | 507,97 | 192,17 |

Les déplacements et le premier mode varient de moins de 2 % entre ces deux
maillages, sans constituer une convergence complète ni une corrélation physique.
Le gain global V5 se retrouve sur les deux maillages : déplacement max environ
−40,5 % et premier mode environ +35,1 % sur le maillage fin. Les contraintes ne sont
pas indépendantes du maillage : pic R0 +19,38 % et pic V5 +5,36 % entre les deux tailles.
Les pics sont au départ des pales, r ≈ 83,897 mm, et non à l'alésage fixé r = 13,75 mm.
La jonction analytique sans congé mesuré rend ces pics sensibles au maillage.
Aucun classement en fatigue, régime sûr ou jeu chaud minimum n'en découle.

Les rapports conservent les maxima bruts et les empreintes des fichiers solveur.
Les journaux rotation/modal sont publiés avec des fins de lignes LF et sans
espaces finaux ; les empreintes avant/après de cette seule normalisation sont
[enregistrées](results/runtime/text-normalization.json). Les empreintes des
rapports solveur restent celles des originaux archivés. les champs complets et entrées
volumineuses restent dans une archive privée vérifiée, sans scan incorporé.
Le budget d’incertitude mécanique est un instantané initial ; son champ CFD
historique à 22 cellules est remplacé, pour l’état courant, par les rapports CFD
et le présent état de validation.
Le percentile est pondéré par les nœuds, pas par le volume. Les images représentent
les champs nodaux réellement calculés, aux positions non déformées, sans écrêtage.
Précontrainte tournante, gyroscopie, roulements/contact, température et charges
aérodynamiques ne sont pas inclus.

![Champs CalculiX R0](results/mechanics/R0-fields.png)

![Champs CalculiX V5](results/mechanics/V5-fields.png)

## Aérodynamique et admission CFD

Le modèle scalaire à éléments de pale est un screening : ses polaires sont supposées
et écrêtées sur 100 % des sections R0/V1/V2. Il ne permet pas de classer le calage
42° contre 36°. La sensibilité du débit scalaire à ±11 % d'échelle atteint environ
−14,9 % / +15,5 %. Une amélioration de débit n'est pas démontrée.

Le domaine fluide reconstruit directement avec OCC conserve le même rotor et
la même enveloppe intérieure de carter. Le meilleur maillage initial passait le
contrôle standard mais échouait au contrôle étendu : 22 déterminants de cellules
inférieurs à 0,001. La formule indépendante reproduit exactement les 22 identifiants.
Les essais d'unions convexes échouent en présence de petites concavités locales ;
aucune union partielle n'a été appliquée. Le raffinement des voisinages diagnostiqués,
répété par la symétrie exacte des neuf pales, résout le défaut sans modifier le CAD
ni les seuils : 148373 cellules, minimum 0,00232225, non-orthogonalité maximale
72,903°, skewness maximale 0,9801. Les deux contrôles indépendants passent.
Le volume discret conserve un écart de l'ordre de 0,025 % au volume CAD ; cette
mesure n'établit pas la fidélité métrologique à une pièce réelle.

Le [protocole figé](parameters/reference-flow-protocol.json) définit avant solveur
la référence 6000 tr/min : air ρ = 1,2 kg/m³, ν = 1,5×10⁻⁵ m²/s, entrée supérieure
à pression totale nulle, sortie inférieure à pression statique nulle, MRF +Z,
écoulement attendu −Z. SST stationnaire incompressible et convection premier ordre.
Résidus, bilan de masse, stabilité du débit et du couple doivent tous passer.
Les couches de paroi, l'indépendance aérodynamique au maillage et le moteur installé
restent absents. Le premier pilot à 200 itérations termine normalement mais échoue
aux résidus figés ; ses mesures ne sont pas une performance admise. La continuation
séparée à 600 itérations conserve exactement les conditions et seuils et passe
tous les critères figés : débit sortant moyen 1,23587 m³/s, couple sur le rotor
−5,25296 N·m, puissance mécanique correspondante 3300,53 W. Ces valeurs sont des
sorties conditionnelles du modèle isolé ; aucune amélioration n’est prouvée. Le
Mach local maximal calculé atteint environ 0,383 : la sensibilité à la compressibilité
doit être vérifiée, en plus de la résolution de paroi et de l’indépendance au maillage.
Les [rapports 200](results/cfd/reference-flow-200-summary-complete-fields.json) et
[600 itérations](results/cfd/reference-flow-600-summary-complete-fields.json)
conservent les critères, les champs contrôlés et les empreintes des mesures.

La variante [V2 à 36°](V2-assembly.step) conserve les autres paramètres R0
([paramètres exacts](parameters/V2.json)). Son BRep est valide, mais deux essais
CFD échouent au contrôle étendu : 36 cellules / 22 faces à faible interpolation,
puis 51 cellules / 15 faces après raffinement ciblé. Aucun flow V2 n'est lancé.
Le [diagnostic de petites arêtes](results/cfd/V2-final-records.json) mesure neuf
arêtes de 0,176 mm, contre 1,278 mm minimum pour R0 ; elles accompagnent la
modification de jonction voile/pales. Cette corrélation cible la révision CAD,
sans prouver à elle seule la cause de chaque cellule. Une jonction définie et
contrôlée, avec déviation géométrique tracée pour toute réparation, est requise
avant comparaison. Le calage 36° n'est pas classé comme meilleur ou moins bon.

## Fabrication additive

Le [screening géométrique](results/lpbf/lpbf-screen.json) utilise le vrai STL du rotor
R0. Scénario explicite : poudre AlSi10Mg hypothétique, machine LPBF non sélectionnée,
enveloppe supposée 250 × 250 × 300 mm, marges de 10 mm par côté, couches de 50 µm,
critère de surplomb 45°. Parmi dix poses, seule la pose verticale avec azimut 45°
rentre dans cette enveloppe avec marges. Les sections de 1105 couches de la pose
horizontale sont calculées ; l'intégration diffère du volume STL de 0,111 %.
Le proxy de supports additionne des colonnes verticales avec recouvrements possibles.
Ce n'est ni un support généré, ni un chemin laser, ni une simulation thermo-mécanique.

Une simulation process qualifiée demande une machine et une stratégie laser choisies,
une carte matériau dépendante de la température, des supports/contacts et échanges
thermiques définis et calibrés, un traitement thermique, des reprises d'usinage,
une inspection et un plan de validation en fatigue. Le matériau élastique FEM ne
qualifie pas l'AlSi10Mg LPBF. Aucune fabrication ou commande n'est autorisée.

## OpenUSD et Omniverse

[Scène comparative](omniverse/studies.usda), [R0](omniverse/R0.usda),
[V5](omniverse/V5.usda). Les coordonnées proviennent des vraies tessellations CAD,
sans coupe visuelle : huit meshes par modèle, axes +Z/+X, `metersPerUnit = 0.001`,
matériau visuel aluminium `UsdPreviewSurface`, empreintes et liens aux paramètres
et résultats. La scène écarte les deux configurations uniquement pour la comparaison.

Parsing, composition, topologie fermée, unités et binding des matériaux sont
vérifiés dans OpenUSD 25.11 ; 24 validateurs génériques exécutés sans finding.
La règle Sdr shader est bloquée par l'absence de `shaderDefs.usda` dans le runtime
USD déjà disponible et reste explicitement non validée. Aucun runtime GPU NVIDIA,
rendu RTX, qualification SimReady ou corrélation de jumeau physique n'est établi.
L'asset ne résout aucune équation ; les calculs externes restent liés séparément.

## Commandes reproductibles

Utiliser les outils déjà disponibles : build123d 0.13 / OCP 8, Gmsh 4.15.2,
CalculiX 2.23, NumPy et Matplotlib, Foundation OpenFOAM 13, OpenUSD 25.11.
Les sorties doivent être neuves. Les timestamps STEP et dépendances peuvent changer
les empreintes à la régénération ; contrôler volumes, topology et paramètres en plus
des hashes. Les versions originales des mailleurs sont conservées pour reproduire
les empreintes des rapports : `build_analytical_mesh_original.py` (65df79b8) et
`build_analytical_mesh_netgen_original.py` (09acff31).

Depuis ce dossier :

```sh
python source/verify_study.py
python source/build_analytical_system.py parameters/R0.json work/R0
python source/build_analytical_system.py parameters/V5.json work/V5
python source/render_analytical_system.py work/R0 work/R0.png --display-label 'R0 horizontal fan reconstruction study'
python source/build_analytical_mesh_original.py work/R0 work/R0-h3p6 --mode structural --size-mm 3.6 --rpm 6000
(cd work/R0-h3p6 && ccx rotation && ccx modal)
python source/summarize_analytical_fem.py work/R0-h3p6 work/R0-h3p6/summary.json
python source/render_analytical_fem.py work/R0-h3p6/summary.json work/R0-h3p6/fields.png
python source/screen_analytical_variants.py parameters/R0.json work/scalar-screen.json
python source/screen_lpbf_geometry.py work/R0 work/lpbf
python source/build_openusd_asset.py work/R0 work/R0.usda --label R0
python source/validate_openusd_asset.py omniverse/studies.usda work/USD-validation.json
python source/build_analytical_mesh.py work/R0 work/fluid --mode fluid --size-mm 7 --netgen --local-refinement parameters/targeted-refinement-symmetric.json
python source/prepare_analytical_cfd.py work/fluid work/CFD parameters/R0.json
```

Le gate et le runner OpenFOAM attendent le cas monté dans `/case`, sous l'image
existante `ghcr.io/cluster2600/3dprinting993-mesh-cfd@sha256:a1db60cbf61bbcca52c171e50cab01ed0b6ec860b227e7c5fc50f7b809659b4f`.
Exécuter d'abord `source/run_analytical_cfd_gate.sh`, copier le protocole figé dans
le cas sous `reference-protocol.json`, puis `source/run_reference_pilot.sh`.
Le gate échoue fermé dès qu'un contrôle échoue. Un résultat de mesh seul ne vaut
pas résultat de flow. Le runner borné limite chaque job isolé : affinité, nice,
mémoire et délai ; aucun service ou processus tiers n'est modifié.

## Données manquantes pour une pièce et un jumeau validés

Identité et échelle indépendantes du spécimen ; datums, interfaces et tolérances
mesurés ; congés réels, matériau/état et roulements ; régimes et transitoires,
températures et courbes ventilateur/système ; plan d'essais professionnel.
Pour LPBF : scénario qualifié et calibration process. Pour Omniverse : runtime
adapté et validation du profil, puis données de corrélation physique.
Les statuts du catalogue restent inchangés : aucune pièce n'est libérée.

## Vérifications du dépôt

La CI GitHub a exécuté `make check` avec succès sur le premier commit CAD
2a9dba8cb3d06a3b2208c60a848dbe5f2a63899d. Les contrôles locaux sur Linux ont
rencontré les incompatibilités documentées dans le
[rapport runtime](results/runtime/repository-checks.json). Ils ne sont pas annoncés
verts. La CI du commit final fait autorité pour le logiciel du dépôt, sans valider
la physique. Les contrôles spécialisés ci-dessus concernent uniquement leurs
artefacts et hypothèses. Aucun merge n'est autorisé pour cette mission.
