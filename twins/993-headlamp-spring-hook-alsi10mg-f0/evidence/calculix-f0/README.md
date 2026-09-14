# Criblage thermo-mécanique CalculiX du crochet de phare F0

CalculiX 2.21 a exécuté six cas sur le STEP exact : statique froide et
température–déplacement stationnaire sur trois maillages C3D10 de `1,5`, `1,0`
et `0,7 mm`. Le maillage fin compte `22 415` nœuds et `12 837` tétraèdres.

Sous la force synthétique de `30 N`, le p95 fin vaut `10,786 MPa` à froid. Avec
un champ imposé de `80 à 180 °C`, il atteint `141,898 MPa`; le maximum local
vaut `303,467 MPa`. La variation p95 entre les deux maillages les plus fins est
de `0,47 %` à froid et `2,84 %` à chaud.

La charge, l'encastrement de la cavité et les températures sont des entrées de
régression. La résistance chaude AlSi10Mg, la colle, le vrai contact du ressort
et le spectre vibratoire sont absents. Le rapport démontre la chaîne numérique,
pas la tenue d'une pièce installée.
