# Audit des transitions de castellation rejetées

Cet audit en lecture seule reproduit les diagnostics natifs de 091, déjà rejeté. Aucun maillage, paramètre, seuil, conteneur ou solveur natif nouveau. Les surfaces physiques du turbo restent inchangées ; le domaine analysé est le témoin fixe synthétique 086 puis sa castellation 091.

## Sources et calcul indépendant

Tous les payloads des reçus 086 et 091 sont relus et hachés. Quatre membres exacts de l'archive officielle OpenCFD v2406 sont référencés avec SHA dans `source-references.json`. L'archive source conserve le SHA `8d1450fb89eec1e7cecc55c3bb7bc486ccbf63d069379d1d5d7518fa16a4686a`. Le script `reproduce_planes.py` reproduit la lecture exploratoire précédente, puis `audit_transitions.py` ajoute les centres volumiques, angles et tuples détaillés.

Les centres de face et aires suivent le lecteur géométrique déjà épinglé. Les centres de cellule sont reconstruits suivant `makeCellCentresAndVols` : estimation par moyenne des centres de face, puis somme des centres de pyramides pondérés par leurs volumes signés. Ce ne sont pas des milieux de boîtes. La non-orthogonalité suit `faceOrthogonality`, angle entre normale orientée et vecteur reliant les centres des cellules voisines. Les labels au-dessus de 70° et le maximum natif concordent ; écart maximal des trois maxima inférieur à 1e-9 degré.

`checkConcaveCells` normalise la normale sortante et le vecteur entre centres de deux faces distinctes, puis signale un produit supérieur à `-planarCosAngle_`. La valeur officielle est `1e-6` (ligne 43). Le commentaire source inclut explicitement « Concave or planar face ». Ce critère et son refus sont conservés.

## Résultats aux trois états

| État archivé | Cellules | Cellules signalées | Faces >70° | Angle maximal |
|---|---:|---:|---:|---:|
| Parent 086 | 20 352 | 0 | 0 | 23,089865268° |
| Premier instantané 091, `1e-07` | 44 992 | 6 700 | 14 080 | 81,887377114° |
| Final 091, `2.6e-06` | 44 992 | 6 700 | 14 080 | 81,887377114° |

Le journal situe le premier instantané immédiatement après le raffinement de surface, itération zéro, avant les étapes ultérieures. Ces étiquettes numériques ne sont pas des temps CFD. Les deux CSV de diagnostics sont **identiques octet pour octet entre premier et dernier instantané** ; cela ne prétend pas que les maillages complets ou leurs patches sont identiques. La phase précédente conserve leurs différences intermédiaires.

Toutes les cellules signalées sont au niveau grossier. Leurs nombres de faces sont 9, 12, 15 ou 18 pour respectivement 4 252, 1 524, 804 et 120 cellules. Les maxima de produit normalisé par cellule vont de 0 à 0,001373265214. Parmi eux, 3 441 sont inférieurs ou égaux à **+1e-6** et 3 259 sont supérieurs. Cette répartition est descriptive : l'admission reste fondée sur le seuil natif **−1e-6**. Elle ne requalifie aucune cellule et ne mesure pas une distance géométrique au bord.

La paire la plus défavorable se trouve dans la cellule 825 (15 faces), faces 4022 et 4023 : score 0,001373265214 ; distance signée du centre de la seconde face au plan de la première 3,404386894e-7 m ; produit des normales sortantes 0,999978387669. Il serait donc incorrect de présenter tous les rejets comme une simple coplanarité exacte. Cette observation ne constitue pas une certification de concavité stricte ni une preuve de cause unique.

Les 14 080 faces fortement non orthogonales séparent toutes les niveaux 0 et 1. La pire est la face 93362, propriétaire 20005, voisin 43099. Séparation normale des centres : 47,235609 µm ; séparation tangentielle : 331,371324 µm. Leur rapport explique numériquement l'angle de 81,887377° pour cette face. Les centres reconstruits, la normale et les coordonnées du centre de face sont publiés dans `readback.json` ; tous les tuples figurent dans les CSV archivés.

Les volumes reconstruits sont positifs : total 2,333381635788176e-6 m³ pour 086 et 2,333381635788175e-6 m³ pour les deux états 091. L'audit ne remplace pas les autres contrôles d'admission. La conservation des 6 784 quads du raccord démontrée dans la phase précédente n'efface pas les transitions rejetées.

## Portée

Le diagnostic est maintenant reproductible avec centres, angles, labels et paires de faces explicites. Aucun remède n'est validé. Aucun écoulement, repos, convergence, stabilité, débit ou puissance n'est qualifié. Le timeout de 084 reste incomplet, sans champs finaux, et ne sera ni rejoué ni prolongé. Les frontières restent synthétiques, sans rotor ni ports physiques.

Voir `validation.md`, `next-scope.md`, `diagnostic-pair.json` et les archives de [091](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-castellation-boundary-2026-10-13) et [086](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-wall-row-refinement-2026-10-13). Aucune preuve antérieure n'est modifiée.
