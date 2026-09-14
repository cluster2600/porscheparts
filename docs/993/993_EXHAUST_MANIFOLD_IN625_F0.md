# Collecteur d'échappement 993 Turbo — concept IN625 F0

Kline publie un collecteur 993 Turbo en **Inconel 625** à **2,9 kg par côté,
échangeur de chaleur inclus**. PorscheFanatics recoupe cette offre et documente
séparément un collecteur inox 3-en-1 pour la même famille de véhicule. Le PET
202-10 identifie les échangeurs gauche `993 211 039 55` et droit
`993 211 040 55`. Aucune de ces sources ne publie diamètre, épaisseur,
trajectoire, bride ou tolérance.

Le F0 est donc un noyau d'écoulement propre au projet : trois conduits ouverts
de `34 mm` convergent vers un collecteur ouvert de `56 mm`, avec paroi nominale
de `1,2 mm` et longueur axiale de `215 mm`. Toutes ces cotes sont synthétiques.
Le STEP omet les brides, la turbine, les supports et l'échangeur de chauffage.

## Pourquoi l'additif a du sens ici

Le LPBF peut produire en une pièce la jonction interne trois-en-un, sans cordon
de soudure dans le chemin de gaz, tout en laissant trois entrées et une sortie
pour évacuer la poudre. Ce bénéfice doit encore être comparé à des tubes IN625
ou inox cintrés et soudés sur coût, rugosité, masse, réparabilité, distorsion,
inspection et durée de vie.

Le BREP OCCT et sa relecture STEP sont valides : un solide matière, un volume
interne connecté, trois entrées et une sortie. L'enveloppe F0 est
`146,4 × 66,4 × 215,0 mm` et la masse théorique du noyau est `509,97 g` avec
`rho = 8,44 g/cm³`. Cette masse ne se compare pas directement aux `2,9 kg`
publiés, qui incluent l'échangeur complet.

## Criblages exécutés

Le cas synthétique prend un moteur `3,6 L`, `5 750 tr/min`, rendement
volumétrique `0,95`, gaz à `900 K`, pression relative `50 kPa` et coefficient
de jonction `K=0,2`. Il recalcule :

- débit quatre-temps et correction idéale de volume chaud ;
- continuité, Reynolds, Mach et perte singulière de jonction ;
- pression de membrane et effort axial ;
- dilatation libre, borne élastique totalement contrainte, conduction et
  rayonnement ;
- fréquence des impulsions d'un banc et quart d'onde du chemin F0 ;
- masse par volume CAO et propriétés IN625 de criblage ;
- validité BREP, continuité du volume gazeux et relecture STEP.

Le résultat donne `90,25 m/s` dans chaque primaire, `99,80 m/s` dans le
collecteur, Reynolds `28 736` et `52 340`, Mach `0,170`, et une perte de
criblage de `391,78 Pa`, soit `96,30 W` par banc. Ce n'est pas une CFD : les
ondes, la vidange des cylindres, la rugosité, les courbures réelles, la turbine
et les échanges thermiques sont absents.

La dilatation libre atteint `1,79 mm`. La borne totalement bloquée donne
`1 696 MPa`, au-dessus de la comparaison ambiante de `640 MPa` : elle démontre
qu'une hypothèse de blocage élastique est inadmissible et qu'il faut modéliser
les interfaces, la plasticité, le fluage et les cycles, pas que la pièce casse à
cette valeur.

## Gates suivants

1. Scanner un ensemble gauche/droit et mesurer ports, brides, trajectoires,
   épaisseurs, supports, turbine, échangeur, jeux et tolérances.
2. Mesurer pressions et températures pulsées, lambda, allumage, débit, spectre
   vibratoire, cartographie turbine et cycles d'usage du M64/60 retenu.
3. Refaire la CAO avec surfaces mesurées, surépaisseurs, brides, supports et
   échangeur étanche au monoxyde de carbone.
4. Comparer LPBF et tubes cintrés/soudés par CFD compressible transitoire, CHT,
   FEA coque/contact/modal, fluage et fatigue thermomécanique convergés.
5. Qualifier orientation, poudre, paramètres, témoins, traitement thermique,
   rugosité, distorsion, CT, ressuage, fuite et pression.
6. Corréler banc pulsé, cycles thermiques, shaker et dyno avant véhicule.

PhysicsNeMo attendra un dataset CFD/CHT/structure convergé, puis des jeux train,
holdout et hors-distribution. SimReady attendra les interfaces et l'environnement
installé mesurés. Le STEP F0 n'est autorisé ni pour fabrication, ni pour moteur,
ni pour chauffage habitacle.
