# Crochet de ressort de phare 993 AlSi10Mg — jumeau F0

## Décision

Le crochet est un bon premier candidat métal additif : petite série de
réparation, géométrie creuse, masse très faible et précédent commercial imprimé
en aluminium ou inox. Contrairement à une vis standard, la fabrication additive
peut avoir du sens pour restaurer une fonction devenue difficile à approvisionner.

Le F0 n'est toutefois pas une copie de la pièce commerciale ou Porsche. Aucune
cote publique du crochet ni de son interface avec le phare n'a été trouvée. La
CAO `16 × 8 × 15 mm` est donc une hypothèse indépendante destinée à éprouver la
chaîne logicielle. Elle ne doit être ni imprimée pour montage, ni collée, ni
installée.

Références :
[crochet commercial Roadster-Fashion](https://shop.roadster-fashion.de/de/reparaturteil-federhaken-am-scheinwerfer.html) et
[route officielle EOS M 290 / AlSi10Mg / 30 µm](https://www.eos.info/metal-solutions/data-sheets/aluminium/pds-eos-aluminium-alsi10mg-eos-m-290-30um).

## Matière et procédé retenus pour le criblage

La route candidate est `EOS Aluminium AlSi10Mg`, jeu matière
`AlSi10Mg_FlexM291 2.01`, EOS M 290, couches de `30 µm`, état brut de
fabrication. La fiche EOS publie notamment une densité minimale de
`2,67 g/cm³`, une limite d'élasticité verticale de coupon de `233 MPa`, une
résistance ultime minimale de `461 MPa`, une conductivité verticale de
`100 W/(m·K)` et une paroi minimale indicative de `0,4 mm`.

Ces valeurs sont des propriétés de coupons, pas des admissibles de pièce. La
résistance dépendante de la température, la surface brute, les entailles, le
lot de poudre et l'orientation réelle doivent être qualifiés.

## Résultats exécutés

| Domaine | Exécution | Résultat utile | Autorité |
|---|---|---|---|
| Équations analytiques | flexion, cisaillement, Von Mises, flèche, collage moyen, dilatation | masse `2,352 g`; Von Mises `15,348 MPa`; croissance libre `0,0352 mm` | régression synthétique |
| Géométrie LPBF | 4 000 sondes et section de chaque couche | `425` couches; orientation `roll_y_45`; supports proxy `3,06 mm³`; pas de poudre piégée à `0,25 mm` | criblage, pas EOSPRINT |
| CalculiX | six calculs C3D10, froid et chaud, trois maillages | p95 fin `10,786 MPa` froid et `141,898 MPa` chaud; variation p95 fin/précédent `0,47 %` et `2,84 %` | cas de charge synthétique |
| OpenUSD | conversion STEP avec `usd-convert-cad 0.2.0` | asset binaire Z-up en millimètres | conformité d'échange |
| Validation NVIDIA | `nvidia_usd_validate 1.21.0` | asset et scène rigide sans règle en échec | schéma/qualité USD |
| Corps rigides | `ovstage 0.1.1.355824` + `ovphysx 0.5.11` CPU | témoin stabilisé de `22` à `17 mm` en `240` pas | intégration logicielle seulement |
| PhysicsNeMo | non exécuté | six cas non corrélés sont insuffisants pour entraîner un surrogate | bloqué |
| OVRTX | non exécuté pour ce F0 | GPU RTX non nécessaire avant géométrie réelle | bloqué |

Le maximum local chaud CalculiX vaut `303,467 MPa`, supérieur à la limite
d'élasticité ambiante de coupon. Il se situe près de l'encastrement thermique
rigide et ne converge pas comme le p95 : c'est un signal de singularité ou de
conception défavorable à investiguer, jamais une preuve de rupture ni de tenue.

## Ce qui bloque l'impression

- scan ou métrologie du crochet cassé, du logement et du ressort ;
- force, direction, course, contact et nombre de cycles du ressort ;
- température, rayonnement et spectre vibratoire mesurés dans le phare ;
- colle, préparation, jeu, cisaillement et pelage à chaud ;
- carte matière chaude et traitement de la route EOS retenue ;
- supports, orientation et fichier machine fournisseur ;
- première pièce, CT/CND, métrologie, essai de rétention, réglage du faisceau et
  revue d'ingénierie signée.

Les preuves et leurs SHA-256 sont regroupées dans
[`twins/993-headlamp-spring-hook-alsi10mg-f0/evidence/`](../twins/993-headlamp-spring-hook-alsi10mg-f0/evidence/).
