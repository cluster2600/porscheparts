# Raccord après bisection extérieure — 087/088

Le sous-domaine fixe raffiné 086 est réuni à la région tournante intacte de 078. Le maillage final 088 passe `checkMesh -allTopology -allGeometry`. La lecture indépendante vérifie les deux sources réellement composées et retrouve exactement tous les points, cellules et faces orientées, avec leurs propriétaires et voisins. Aucun solveur d’écoulement n’est lancé.

## Entrées et opérations natives

087 identifie les 6 784 faces du raccord de 086 par correspondance exacte des 6 912 points et des cycles orientés avec le patch nommé `domain1_to_rotorZone` de 078. Aucune plage supposée après raffinement n’est utilisée. `createPatch`, avec `pointSync false`, recrée ce patch sans modifier les coordonnées ou les cellules.

088 copie la région `rotorZone` de 078, sans modification de géométrie ou de zone. Seules ses métadonnées de raccord deviennent `wall` au lieu de `mappedWall`, avec retrait de `sampleMode`, `sampleRegion` et `samplePatch`. Il ajoute 087, exécute `mergeMeshes`, conserve le maillage fusionné, exécute `stitchMesh -perfect`, conserve le maillage raccordé, puis retire les deux patches de raccord devenus vides via `createPatch`. Les patches non vides `walls` et `outerWall` restent présents.

Les entrées sont copiées **avant** chaque lancement, tous les reçus et payloads relus. Aucune carte `*RegionAddressing` héritée n’est copiée. La tolérance de `stitchMesh -perfect` ne sert pas de preuve de conformité : les correspondances sont vérifiées indépendamment après exécution. Les sources et preuves 078, 086 et antérieures restent inchangées.

## Résultats

087 termine en 0,973 s, code zéro sans OOM, Mesh OK. 088 termine en 2,168 s, code zéro sans OOM, Mesh OK :

| Quantité | 088 |
|---|---:|
| Cellules | 40 704 |
| Prismes tournants | 20 352 |
| Hexaèdres fixes | 20 352 |
| Points | 41 472 |
| Faces | 122 880 |
| Faces internes | 100 992 |
| Faces de frontière | 21 888 |
| Quadrilatères MRF | 6 784 |
| Déterminant minimal | 0,006220795333159227 |
| Non-orthogonalité maximale | 47,8173518952406° |

Une région fluide, aucune concavité ni petit déterminant signalé, seuils inchangés. Volume natif 4,610682341591126e−6 m³ ; volume reconstruit 4,610682341591068e−6 m³, égal à celui de 083. Le minimum de volume reconstruit par cellule vaut 2,836594261226707e−11 m³.

`read_coupling.py` revalide intégralement les cartes signées de 078 contre 077. Il construit ensuite le domaine attendu par réunion des deux sources **078 tournant et 086 fixe**, puis vérifie la bijection de chaque cellule et de chaque face orientée, owner/neighbour, la zone et les arêtes fermées. Les coordonnées décodées sont exactement celles des sources, après réindexation. Les 20 352 prismes tournants, leurs points et les 6 784 quads MRF restent intacts. Le retrait des seuls patches vides ne change ni géométrie ni rotorZone. Pas de trou ou de double paroi dans cette comparaison topologique.

La normale géométrique maximale de rotation à l’interface vaut 2,287947609e−12 m/s, sa planéité 1,057181821e−17 m. Le bilan géométrique maximal par cellule tournante reste 1,490777987e−19 m³/s. Le maximum calculé sur **toutes** les cellules est 4,566159484e−11 m³/s ; la rotation n’est pas appliquée aux cellules fixes concernées. Ces valeurs ne sont pas des débits d’air.

## Limites conservées

La planéité globale maximale reste 6,792080535e−7 m dans le domaine fixe. Les parois latérales sont synthétiques, le rotor et les ports physiques absents. Aucun repos nouveau, convergence linéaire, stabilité de perturbations, performance forcée ou calibration physique n’est qualifié. Le contrôle 084 reste incomplet au budget ; aucun champ final absent n’est remplacé par les historiques ou par les champs d’un autre cas.

086 conservait les 7 424 anciens `frozenPoints` mais n’ajoutait pas les 256 nouveaux points des fermetures. Le présent raccord ne constitue pas une nouvelle sélection de gel : toute projection ultérieure doit la reconstruire et la vérifier. La protection pendant castellation/snappy et le traitement des surfaces/couches physiques restent distincts.

Voir [readback.json](readback.json), [preparation-readback.json](preparation-readback.json), [validation.md](validation.md) et [next-scope.md](next-scope.md). Les maillages et logs complets sont conservés dans l’archive de cette phase.
