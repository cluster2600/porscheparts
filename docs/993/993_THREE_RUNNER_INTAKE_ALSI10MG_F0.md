# Collecteur d'admission trois conduits 993 — concept AlSi10Mg F0

PorscheFanatics et Patrick Motorsports recoupent le jeu PMO `FUE PMO 9150`,
annoncé **46 × 42 × 100 mm**, trois boulons, deux pièces et finition aluminium
brute pour des conversions Motronic avec moteur 964/993 3,6–3,8 L. Aucun dessin
ne définit la chaîne de cotes, les entraxes, les ports ou les fixations.

Le F0 interprète provisoirement `46 mm` et `42 mm` comme diamètres internes haut
et bas, et `100 mm` comme hauteur. Il réunit trois conduits coniques de `2 mm`,
légèrement évasés dans l'espace, entre deux brides communes. Les entraxes et les
brides sont synthétiques ; le motif trois boulons est volontairement absent.

## Pourquoi l'AM est testée

Le LPBF permettrait de personnaliser indépendamment les trois axes, sections et
longueurs, puis de les réunir aux brides dans un seul BREP. Cet avantage doit
encore battre le collecteur aluminium coulé, usiné ou assemblé sur coût, masse,
rugosité, planéité, propreté et endurance.

Le STEP pèse théoriquement `461,03 g` par banc et `922,07 g` la paire. Aucune
masse commerciale n'étant publiée, ce résultat ne valide pas le produit PMO.

## Criblages exécutés

Le rapport recalcule :

- volumes de troncs de cône, volume des brides et masse `rho V` ;
- débit quatre-temps à `3,6 L`, `6 800 tr/min`, rendement volumétrique `0,95` et
  six conduits ;
- continuité, Reynolds, Mach, variation de pression cinétique et perte mineure ;
- fréquence de combustion et accord quart d'onde du conduit seul ;
- contrainte de membrane `p r/t`, dilatation `alpha L delta_T`, borne bloquée
  `E alpha delta_T` et capacité thermique ;
- BREP OCCT unique, trois canaux ouverts, enveloppe et relecture STEP.

Le cas synthétique donne `19,44 m/s` en haut, `23,31 m/s` en bas, Reynolds
`59 782`, Mach `0,065` et `15,76 Pa` de perte avec `K=0,05`. La fréquence de
combustion vaut `340 Hz`, alors que le quart d'onde du conduit de `100 mm` vaut
`896,44 Hz`; un premier accord à 340 Hz demanderait `263,66 mm`. Cette
comparaison n'est pas un réglage d'admission, car le conduit complet, le plénum,
les soupapes et les réflexions ne sont pas modélisés.

## Gates suivants

1. Scanner une pièce PMO et mesurer ports de culasse, papillons, entraxes,
   brides, boulons, joints, angles, rugosité et tolérances.
2. Mesurer débit, pression pulsée, température, calage des soupapes et rendement
   volumétrique du M64 retenu.
3. Comparer coulé/CNC/assemblé et LPBF sur masse, coût, perte, égalité des
   conduits, distorsion et propreté.
4. Exécuter CFD compressible transitoire et CHT, puis modal, fatigue, cycles
   thermiques et retour de flamme avec cartes matière qualifiées.
5. Définir orientation, supports et surépaisseurs ; contrôler par métrologie,
   CT, ressuage, fuite et banc de débit.
6. Corréler sur banc moteur avant toute installation véhicule.

PhysicsNeMo attendra un ensemble de cas CFD/CHT/structure corrélés et des gates
d'incertitude. SimReady attendra les interfaces mesurées et la carte matière.
Le STEP F0 n'est pas autorisé pour fabrication ou mise en route moteur.
