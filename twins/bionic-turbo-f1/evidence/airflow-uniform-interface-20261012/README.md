# Interface raffinée : la tangence seule ne conserve pas le repos

Les témoins 034–039 étudient une petite couronne synthétique issue de 026,
entre z = 6 et 7 mm. Ils ne représentent ni le turbo complet, ni ses pales,
ni sa jonction arrière. Les pièces CFD restent inchangées.

## Ce que les témoins isolent

034 raffine uniformément le maillage natif de 026 : 20 480 hexaèdres,
5 120 faces d'interface, `Mesh OK`. Le champ `profile` des manifestes conserve la spécification parent 026 ;
ses anciens compteurs ne décrivent pas le maillage raffiné. Les nouveaux sommets restent sur les
cordes ; la composante normale géométrique de rotation atteint 3,357785 m/s.

La première projection radiale est refusée avant création de cas : le centre
natif d'une face est pondéré par l'aire et n'est pas au milieu axial exact.
Le refus, les coordonnées et la version initiale sont conservés.

035 reconstruit les demi-stations et projette seulement les points de
l'interface. Elle devient plane et tangente (3,1690e-12 m/s), et checkMesh
passe. Les parois latérales gardent exactement leurs points. Pourtant le
test tournant 036 termine ses 200 pas avec des erreurs excessives :
0,0211597 Pa, 0,000169926 K et 0,000271364 m/s. Il est rejeté. Aucun plafond
linéaire de pression n'est atteint ; cela ne répare pas le défaut de repos.

037 est le contrôle inertiel de 036 : seule la vitesse du repère devient
zéro. 038 reconstruit toute la grille logique du témoin, et pas uniquement
l'interface. Les 26 880 points forment 21 plans axiaux, 256 rayons angulaires
et cinq couches radiales. Les sommets source sont conservés, chaque point
latéral reste dans sa facette source (écart maximal 5,732e-17 m), les plans
de fermeture sont inchangés et le volume de frontière varie de moins de
7e-15 relatif. La connectivité ne change pas. Toutes les faces deviennent
planes à 3,405e-17 m, et la normale de rotation de l'interface est inférieure
à 1,473e-11 m/s. Le contrôle natif est `Mesh OK`.

039 reprend ce maillage reconstruit. La comparaison des entrées prouve que
seul `constant/polyMesh/points` change entre les cas tournants 036 et 039.
Équations, schémas, pas, conditions aux limites et tolérances sont identiques.
Les critères restent ceux de 026 : 0,001 Pa, 1e-6 K, 1e-8 m/s, sur 200 pas
de 0,1 microseconde. Les résultats finaux sont consignés dans les reçus.

## Fins natives et seuils de repos

| Cas | Variation | Erreur p maximale (Pa) | Erreur T maximale (K) | U maximale (m/s) | Repos |
|---|---|---:|---:|---:|---|
| 036 | Interface seule projetée, tournant | 0,0211597 | 0,000169926 | 0,000271364 | Rejeté |
| 037 | Même maillage, omega = 0 | 4,5111e-10 | 8,5265e-13 | 9,3599e-12 | Seuils respectés |
| 039 | Grille reconstruite, tournant | 1,5571e-9 | 1,1619e-10 | 1,1285e-11 | Seuils respectés |

Les trois calculs terminent nativement les 200 pas, code zéro. Durées :
20,737 s, 849,483 s et 844,590 s respectivement. 037 et 039 atteignent
800 fois le plafond de 1 000 itérations de pression ; **la convergence
linéaire n'est pas qualifiée**. Les champs finaux natifs p/T/U sont relus,
ainsi que tous les fichiers et historiques, sans remplacer les données par
leurs seuls résumés. La différence 036/039 soutient l'importance du bilan
géométrique de toutes les cellules ; aucun gain physique n'est déduit.

## Bilan géométrique

L'audit par cellule complète celui de l'interface. Avec la projection seule,
le défaut maximal de planéité des faces intérieures atteint 1,653e-8 m et
le flux géométrique net maximal dans une cellule tournante 1,2573e-11 m³/s.
Avec la reconstruction complète, ces valeurs descendent à 3,405e-17 m et
1,6517e-20 m³/s. Ce sont des diagnostics géométriques, pas des débits d'air.
La vitesse normale sur une face intérieure quelconque peut être grande :
la tangence est requise à l'interface, tandis que le bilan doit fermer dans
chaque cellule tournante.

Le code officiel v2406 utilise les centres et vecteurs d'aire des faces pour
le flux relatif MRF ; les références et SHA-256 sont conservés dans
`native-source-reference.json`. Aucun code du solveur n'a été modifié.
Les bilans sont corrélés au défaut de repos ; ils ne prouvent pas seuls
une cause unique. `read_balance_v2.py` ajoute la sélection des cellules
tournantes au premier audit, qui reste conservé.

## Reproduction et limites

Les scripts `run_uniform.py`, `run_projected_v2.py`, `run_equilibrium.py`,
`run_inertial.py`, `run_reconstructed.py` et
`run_reconstructed_equilibrium.py` préparent des cas neufs et bornés.
La tentative radiale refusée est dans `run_projected.py`. Aucun cas ancien
n'est écrasé. Les conteneurs terminés sont conservés. Les lecteurs vérifient
les empreintes de tous les fichiers et relisent les champs natifs p/T/U.

100 tests turbo réussissent et un est ignoré. `make check` exécute 3 810 tests,
avec 170 ignorés, les deux échecs flottants et trois erreurs rtree/networkx
hors turbo déjà connus. Les journaux sont conservés.

Cette reconstruction exige une grille tensorielle complète et refuse les
adresses manquantes ou dupliquées. Elle n'est pas applicable directement au
maillage adaptatif du turbo. Celui-ci doit encore préserver surfaces, jeux,
coquilles, interface, cellules tournantes, couches et qualité native, puis
passer un test de repos global avant une CFD forcée. Aucun débit maximal,
gain de puissance ou jumeau numérique calibré n'est validé.

## Archive native

[Archive 034–039](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-uniform-interface-2026-10-12) :
210 fichiers, 6 138 313 octets, SHA-256
`f604365991e76e73dcefee61ba5133d03a1232e40ba73e8d93bdefa64ba4e08b`.
Les payloads ont été relus localement. Les tailles et SHA-256 des cinq actifs
GitHub sont vérifiés ; aucun second téléchargement intégral distant n'est
revendiqué. Les sources des préparateurs et lecteurs sont conservées dans Git.
