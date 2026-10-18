# Feuilles continues sans opération booléenne sur leur contour

Cette branche construit une nouvelle matière de support à partir de chaque
intervalle libre `D`. Elle conserve tous les triangles de `D`, puis ajoute des
quadrilatères verticaux sur les seules arêtes entièrement attestées par les
interfaces source. La pénétration déclarée reste de 0,2 mm. Une interface à la
plaque Z=0 ne reçoit aucune matière sous la plaque.

Les arêtes des triangles sont subdivisées uniquement aux coordonnées IEEE déjà
présentes sur leur même droite exacte. Leurs sous-segments orientés communs
s’annulent. Les cycles restants doivent décrire un Polygon simple : les signes
et intersections sont évalués avec `Fraction`, y compris entre les trous et
entre segments adjacents. Une chaîne de triangles tous positifs égale à cette
frontière exclut les manques et recouvrements de surface positive par son nombre
d’enroulement. Une inclusion indépendante vérifie aussi `D ⊆ R`.

Chaque quadrilatère est essayé dans l’ordre stable des arêtes source. Il est
écarté explicitement si son ajout empêche la formation d’une feuille simple ;
aucun triangle de `D` n’est retiré. Une arête partiellement attestée reste sans
extension : aucune intersection approchée n’est créée. Les exclusions, les
interfaces utilisées et les contacts sont conservés dans le reçu. Cette
politique augmente des interfaces continues à détacher après construction.

Le confinement reste contrôlé contre l’union exacte des balayages verticaux des
triangles originaux de `D`, avec le même plan de plaque. L’enveloppe issue d’une
union GEOS et son aire de différence restent des diagnostics séparés. Les
demi-plans entiers compilés accélèrent uniquement la recherche d’un primitif
convexe : les choix de primitifs et les certificats rationnels restent ceux du
contrôle précédent. Les intervalles libres distincts ne peuvent partager un
segment de matière positif.

`combinatorial-evidence/fixtures.json` contient trois témoins et deux intervalles
réels des supports du concept 993, avec les empreintes de leurs résultats. Le
rejeu vérifie les frontières produites et leurs preuves exactes. Un témoin de
toit horizontal a également été coupé sur 170 plans réels de 60 µm ; les trois
dernières couches intersectent effectivement le corps après la pénétration de
0,2 mm. Ces résultats locaux ne constituent pas l’admission du support complet.
Les graphes matière, les six admissions et l’audit de toutes les expositions
restent nécessaires.

Les sources v2, leurs exécutions et leurs refus sont conservés. Les nouveaux
points d’entrée sont `generate_prism_region_v3.py` et
`generate_legacy_region_v3.py`, avec les mêmes arguments positionnels que v2.
Ils copient leurs sources avant calcul et conservent les diagnostics historiques.
Le maillage de pièce et son cache complet de 1 034 couches restent identiques.

Vérification native ciblée :

```sh
work/part-workflow/runtimes/pyslm-coverage-011/env/bin/python -B -m unittest discover -s tests -p 'test_carrier_combinatorial_*.py' -v
```
