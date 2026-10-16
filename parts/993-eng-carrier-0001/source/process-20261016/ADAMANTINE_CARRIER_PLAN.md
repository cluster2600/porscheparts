# Déformation d'impression : contrat de calcul du berceau

## Contrôle exécuté le 16 octobre 2026

Le binaire corrigé existant et son manifest ont été vérifiés sur Kali1 :
`e7637a1a3729f82c0b11a9a1864fd96b7fbdee9408ede0aad5b59e573699b959`
et `642a7f8c7928a2bf8171162f4928a02c093fc0677956c3c7023d37a12a1b128f`.
Le code `Geometry.cc` est identique à la révision
`3990489a10902912889617856f6e2e097d52a412`, SHA-256
`d58cab9a1220a61324dff91aabdc639982238cbd62642b0cb5b9e72a23101b47`.

Un petit appel natif à `Geometry::is_within_stl`, lié à l'objet déjà compilé,
a été configuré puis a échoué à la compilation en 2,75 s : cette méthode
n'existe pas dans ce runtime. Le paquet installé est **ArborX 1.5** ; le code
requiert `ARBORX_VERSION_MAJOR >= 2` pour le filtrage STL. L'objet compilé
contient les lecteurs STL mais aucun symbole `is_within_stl`.

Les sources du contrôle sont `adamantine_occupation.cc` et
`occupation-CMakeLists.txt`. Les entrées, journaux et empreintes sont conservés
dans `work/carrier-process-20261016/adamantine-occupation-001/`.
L'entrée géométrique du contrôle est le V6f remeshing Gmsh006, SHA-256
`8fe38c5069bc20831257dced425d91770ad76cfd4109276998a21cf60b7ecfb2`,
à plat, tourné de 45° dans le plan, avec 10 mm sous la pièce. Il s'agit du
témoin géométrique de référence, pas de la nouvelle révision mécanique.
**Aucune occupation ni déformation du berceau n'a été calculée par ce contrôle ;
zéro pas thermique et zéro résolution mécanique.**

## Limites concrètes de la voie STL

Le [constructeur Geometry](https://github.com/adamantine-sim/adamantine/blob/3990489a10902912889617856f6e2e097d52a412/source/Geometry.cc)
génère une boîte d'hexaèdres autour du STL. Avec ArborX 2, le prédicat refuse
chaque cellule coupant la surface puis teste les cellules entièrement
intérieures. C'est une approximation intérieure ; les parois minces
rétrécissent ou disparaissent si le maillage est grossier. Avec ArborX 1.5,
la branche de [sélection pour activation](https://github.com/adamantine-sim/adamantine/blob/3990489a10902912889617856f6e2e097d52a412/source/material_deposition.cc)
ne filtre pas la forme STL. Lire un STL sans erreur ne prouve donc pas que la
matière activée représente le berceau.

L'autre entrée est `geometry.import_mesh true`, `mesh_format gmsh`,
`mesh_file ...`, `units.mesh millimeter`. Le moteur utilise des éléments
`FE_Q` hexaédriques : le C3D10 tétraédrique de CalculiX n'est pas interchangeable.
Un import HEX conforme ou un HEX dont l'occupation a déjà été auditée évite le
filtrage STL manquant, sans résoudre à lui seul les autres limites du modèle.

Le [raffinement natif](https://github.com/adamantine-sim/adamantine/blob/3990489a10902912889617856f6e2e097d52a412/application/adamantine.hh)
raffine près de la trajectoire des sources jusqu'à `n_refinements` ;
`coarsen_after_beam` et `time_steps_between_refinement` pilotent le transfert.
Il ne garantit pas trois éléments à travers une paroi de 1,5 mm ni la
conservation de sa géométrie. L'activation sélectionne les cellules intersectant
une boîte de dépôt : une cellule haute peut être activée dès la première
couche de 60 µm qui la touche.

À titre de budget, pour le témoin seul de 268 852 mm³ et sa boîte
451,134 × 451,134 × 52 mm, les nombres ci-dessous sont des **estimations**
`volume/h³` et des comptes de boîte structurée, pas des maillages exécutés.
Ils excluent la plaque et les supports.

| Taille isotrope h | Cellules de matière estimées | Cellules de boîte |
| --- | ---: | ---: |
| 0,5 mm | 2 150 816 | 84 802 536 |
| 0,25 mm | 17 206 532 | 677 669 200 |
| 0,06 mm | 1 244 685 456 | 49 016 157 987 |

## Réponse mécanique et séquence à préparer

Le profil installé limite les propriétés à des constantes, une seule matière,
la mémoire CPU et la 3D. Le [solveur mécanique](https://github.com/adamantine-sim/adamantine/blob/3990489a10902912889617856f6e2e097d52a412/source/MechanicalPhysics.cc)
résout le déplacement élastique par gradient conjugué, puis applique un retour
radial J2 aux contraintes. Le [second membre](https://github.com/adamantine-sim/adamantine/blob/3990489a10902912889617856f6e2e097d52a412/source/MechanicalOperator.cc)
contient les dilatations thermiques et les forces ; le retour plastique ne
rééquilibre pas ce déplacement par une itération globale. Ce code ne doit donc
pas être assimilé à une résolution globale élastoplastique convergée du
retrait résiduel. Le contrat examiné ne fournit pas non plus une étape de
libération de plaque/supports prête à l'emploi.

La voie la plus courte du pilote reste **CalculiX existant**, avec le STEP et
le nouveau maillage, des groupes de dépôt explicitement distingués des couches
de 60 µm, une déformation inhérente bornée et la libération des contraintes
dans le même état de calcul. Une voie thermique puis élastoplastique réclame
en plus les champs thermiques et la loi Ti64 en température. La publication
[OpenAM-SimCCX](https://doi.org/10.3390/ma18214990) décrit une telle chaîne
CalculiX ; ses données sont dans la collection auteur
[10.6084/m9.figshare.c.8086513](https://doi.org/10.6084/m9.figshare.c.8086513).
Elle n'est pas un nouveau runtime installé ni un résultat pour ce berceau.

Avant une prédiction complète, figer puis vérifier :

1. Géométrie de matière et de supports volumiques, plaque et interfaces. Les
   surfaces ouvertes PySLM ne donnent pas directement leur masse ou leur
   conductance volumique.
2. Au moins trois éléments à travers les parois de 1,5 mm comme point de
   départ, puis raffinement indépendant ; ce nombre seul n'est pas un critère
   de convergence. Contrôler aussi volume, connexité, alésages et appuis.
3. Bornes verticales de chaque élément et couche/groupe d'activation, avec
   erreur d'activation publiée. Une comparaison de groupes sur un maillage
   identique ne vaut pas raffinement spatial.
4. Refroidissement, puis suppression des supports et libération de plaque en
   conservant l'état mécanique. Mesurer les déplacements après recalage sur
   les mêmes appuis et la même procédure que le calcul de référence.
5. Variation spatiale et variation des groupes/du pas de temps séparées,
   avec le seuil de convergence du protocole figé avant les calculs. Conserver
   la règle de rejet existante à 10 % pour la sensibilité d'activation ;
   aucune valeur issue d'un cas non convergé ne devient une déformation admise.

Cette étude n'a lancé ni nouvelle installation lourde ni calcul global
thermomécanique insuffisamment résolu. L'ajout d'ArborX 2 seul ne suffirait pas
à transformer le profil actuel en prédicteur complet de retrait résiduel.
