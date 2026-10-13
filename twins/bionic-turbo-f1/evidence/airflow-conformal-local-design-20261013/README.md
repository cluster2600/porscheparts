# Refus géométrique de deux propositions locales à pyramides

Un seul stencil, appliqué séparément aux cellules grossières 825 et 20005 de 091 : une pyramide par face existante, avec le centre volumique natif reconstruit comme sommet commun. Aucune optimisation du sommet, aucun balayage. Ce sont deux propositions indépendantes stockées en JSON, pas un maillage global. L'identifiant de sommet ajouté 76049 est local à chaque fichier : ne pas assembler les fichiers en fusionnant cet identifiant.

Les faces de base gardent exactement leurs cycles et coordonnées. Chaque arête produit un triangle latéral partagé deux fois en sens opposés ; les chaînes d'arêtes s'annulent pour chaque enfant. Les faces vers les voisins sont conservées et les angles utilisent les centres des véritables voisins du maillage complet 091, sans transformer les coupes locales en murs.

Les formules déjà publiées de centres, volumes, critère de plans, déterminants et angles sont réutilisées. Le calcul du déterminant inclut les faces internes seulement ; les bases situées sur une paroi native ne contribuent pas. Les triangles latéraux contribuent, étant internes à la famille. Ce n'est pas un appel à checkMesh.

| Cellule source | Enfants | Triangles internes | Déterminant minimal | Enfants < 0,001 | Critère de plans dépassé | Angle maximal | Faces > 70° |
|---|---:|---:|---:|---:|---:|---:|---:|
| 825 | 15 | 34 | 0,000763994164 | 1 | 3 | 84,069061° | 14 |
| 20005 | 9 | 20 | 0,0000140173854 | 5 | 4 | 82,494356° | 16 |

Les deux propositions sont **refusées au précontrôle calculé**, sans nouveau cas natif. Le critère de plans reste le produit normalisé > −1e−6 ; il inclut des configurations planaires, et les nombres ci-dessus ne certifient pas une concavité stricte. Les maxima d'angle concernent de nouveaux triangles internes. La base héritée 93362 passe de 81,887377° dans le source à 74,663766° dans la proposition 20005 : elle reste au-dessus de 70°. Une amélioration sur cette face ne compense pas les autres défauts.

Tous les volumes calculés sont positifs. Leur somme algébrique par parent concorde avec la formule du volume source : différence relative jusqu'à 1,64e−14 dans l'évaluateur, zéro à son arrondi dans le lecteur scalaire indépendant. Cela ne prouve pas à soi seul l'absence d'intersections ou de recouvrements géométriques. Aucune admission globale ou partition géométrique complète n'est revendiquée.

Le lecteur indépendant utilise une implémentation scalaire séparée des centres/aires de faces, moments volumiques, déterminants et angles. Il vérifie un cube unitaire et une pyramide analytique, les sommets source, chaque base, chaque triangle et sa paire, le sommet commun contre le centre du parent, puis reproduit tous les indicateurs. Les volumes, centres et voisins source sont relus dans le maillage complet.

Les refus des subdivisions 040/041/056 restent conservés. Cette étude locale n'applique aucune reconstruction au turbo réel et n'autorise aucune variante globale. Sources physiques, patches, jeux, connexions et tous les maillages archivés restent intacts. Aucun nouveau numéro de cas, conteneur, solveur, repos, débit ou puissance.

## Reproduction

Restaurer les dépendances hachées puis travailler dans une nouvelle copie, sans réécrire les preuves publiées :

```sh
work/bionic-tools/bin/python work/bionic-conformal-local-design-20261013/evaluate_pyramids.py
work/bionic-tools/bin/python work/bionic-conformal-local-design-20261013/verify_pyramids.py
```
