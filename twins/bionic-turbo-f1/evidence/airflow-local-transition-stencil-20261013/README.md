# Ensembles locaux exacts des transitions 086/091

Extraction en lecture seule, sans nouveau cas natif ni solveur. Les rejets de 091 restent applicables. Aucune correction de transition n'est mise en œuvre ici.

Les graines proviennent du rapport publié de l'audit précédent : cellule 825 pour la pire paire de plans 4022/4023 ; cellules 20005 et 43099 de part et d'autre de la face 93362 pour la pire non-orthogonalité. Pour chaque graine, on prend ses voisins par face, puis tous les descendants de chacun de leurs parents 086. Cette fermeture conserve des familles de raffinement complètes et évite de choisir seulement quelques enfants favorables.

| Ensemble | Parents 086 | Cellules 091 | Points 091 | Faces internes | Faces de bord | Coupes synthétiques |
|---|---:|---:|---:|---:|---:|---:|
| face_planes | 6 | 27 | 91 | 50 | 77 | 63 |
| nonorthogonality | 9 | 23 | 88 | 46 | 70 | 60 |

Le premier contient 24 cellules fines et 3 grossières, le second 16 fines et 7 grossières. Les 14 et 10 autres faces de bord sont des faces de la frontière source. Les deux ensembles peuvent se recouvrir ; ils ne constituent pas une partition du domaine.

Chaque JSON conserve les labels source, coordonnées décodées, cycles des sommets, owner/neighbour et signes sortants de chaque cellule. Les faces exposées par la sélection sont explicitement des coupes synthétiques. Les arêtes orientées s'annulent par cellule et sur la frontière de l'ensemble ; la connexion par faces est vérifiée. Ces contrôles ne constituent pas une admission native, une preuve générale de variété topologique ou une conservation entre toutes les facettisations des faces gauchies.

La version 2 du lecteur indépendant ajoute la vérification exacte de la règle de sélection (graines, voisinage par face et fermeture par parent), sans modifier la version 1. Le lecteur indépendant relit les tableaux complets de 086/091 et vérifie chaque élément enregistré. Il vérifie la parenté par les huit sommets originaux : un descendant grossier, ou huit enfants fins avec huit ancres distinctes et un centre commun. Les gros maillages restent dans leurs archives sources, sans duplication.

## Outils natifs examinés

Les membres officiels `splitCells.C` et `subsetMesh.C` de v2406 sont hachés dans readback.json. `splitCells` distingue les coupes topologiques des hexaèdres et les coupes géométriques. Son calcul géométrique incline la normale par `0.01*halfNorm` (ligne 333), et l'accrochage aux arêtes a une tolérance par défaut de 0,2 (ligne 565). Le calcul de quadrant à partir des centres de faces porte une réserve explicite pour les faces gauchies (ligne 139). Les cellules signalées à 9–18 faces ne sont pas les hexaèdres simples auxquels se rapporte la coupe topologique par défaut. Cette lecture ne qualifie donc pas une coupe corrective de ces cellules. Aucun angle ni tolérance n'a été choisi, aucun splitCells exécuté.

`subsetMesh` peut exposer des faces internes dans un patch `oldInternalFaces` ou nommé. Il utilise des cartes internes pour transférer les ensembles et écrit un nouveau sous-maillage ; ce changement de frontière devrait être admis séparément. Aucun subsetMesh exécuté : les complexes JSON servent uniquement à conserver les données locales et leur parenté.

## Reproduction et limites

Depuis la racine du dépôt, avec les archives parentes restaurées aux chemins du rapport :

```sh
work/bionic-tools/bin/python work/bionic-local-transition-stencil-20261013/extract_stencils_v2.py
work/bionic-tools/bin/python work/bionic-local-transition-stencil-20261013/verify_complexes_v2.py
```

Reproduire dans une nouvelle copie de travail ; les preuves publiées restent immuables. Le premier extracteur échoue à sérialiser un entier NumPy. Sa source et son traceback sont conservés ; v2 convertit uniquement les labels parents en entiers Python. Aucun calcul natif rejoué.

Aucun nouveau maillage, repos, débit, puissance ou calibration physique. Les ensembles sont issus d'un domaine fixe synthétique. Les parois physiques du turbo, les couches et le repos global restent à qualifier.
