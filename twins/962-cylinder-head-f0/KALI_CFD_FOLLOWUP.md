# Circuit d’eau 4 L : contrôles réellement exécutés sur kali1

Le contrôle OpenFOAM est maintenant exécuté. **Le maillage tétraédrique est
rejeté ; aucune résolution hydraulique n’a démarré.** Les deux dérivées
polyédriques essayées sont également rejetées. Le succès SICN décrit dans le
[dossier précédent](COOLANT_MESH_FOLLOWUP.md) reste valable pour son périmètre,
mais ne suffit pas à admettre le maillage dans le solveur.

Le [reçu d’exécution](derived/kali-cfd-20261025/execution-report.json) lie
les entrées, le runtime, les journaux natifs et l’archive des six essais.
Les maîtres PicoGK, les quatre soupapes et le double allumage sont inchangés.

## Exécution et entrée

La connexion SSH IPv6 par Thunderbolt à kali1 fonctionne, avec vérification
de la clé d’hôte déjà connue. Docker n’est pas accessible au compte de calcul.
Un paquet officiel **OpenFOAM Foundation 13, build 13-cde978a97c93**, est donc
extrait dans le dossier du travail, sans installation système. Sa somme
SHA-256 est vérifiée contre l’index APT signé de la fondation ; la signature,
l’index et le paquet sont liés dans le reçu. Le paquet est celui du 11 septembre
2025, et n’est pas présenté comme la dernière version disponible.

Bubblewrap fournit les chemins standards `/opt/openfoam13`, un système en
lecture seule, un espace réseau séparé et un dossier utilisateur masqué sauf
le travail. Des unités utilisateur temporaires limitent chaque essai à 6 Gio
de mémoire, sans swap, et un cœur CPU. Le lanceur MPI de l’hôte échoue à son
propre contrôle de version ; le chemin de calcul retenu est donc séquentiel.
Aucun droit système n’a été changé. Les unités de travail sont terminées.

L’entrée est exactement le MSH sauvegardé de 542 188 tétraèdres, en mètres,
SHA-256 `b368f5971be2dc559a613175c8e383a86d6dd33a25de8834908cc812af57e903`.
Les 18 empreintes du cas préparé sont vérifiées après transfert. Deux appels
à `createPatch` donnent effectivement le type `wall` à la paroi, sans changer
les noms des conditions limites.

Le cas exploratoire conserve **48,6236 L/min par culasse**, une masse volumique
supposée de 965 kg/m³ et une viscosité dynamique supposée de 0,000315 Pa·s.
La section terminale réelle du maillage à x = −76 mm est **339 mm²** ; la
vitesse moyenne imposée serait donc **2,39054 m/s**. La coupe à −75,5 mm utilisée
auparavant n’est pas cette section terminale. Le cas RANS k–ω SST isotherme
est préparé, avec pression cinématique et schémas amont du premier ordre.
Ce débit provient du bilan exploratoire SP95 et n’est pas une mesure.

## Résultats conservés

| Essai | Cellules | Résultat effectif |
|---|---:|---|
| 001 : import du MSH et typage des parois | 542 188 | Deux contrôles échouent : 252 cellules sous le seuil de déterminant 0,001 et cinq faces sous le poids d’interpolation 0,05 |
| 002 : `polyDualMesh 0 -concaveMultiCells` | 700 751 | Huit contrôles échouent ; dérivée rejetée |
| 003 : préparation de la fusion native | — | Mauvaise syntaxe de `-writeSets`, puis ensemble de cellules absent ; aucune fusion |
| 004 : préparation corrigée des ensembles | — | `patchToFace` requiert `patch`, et non `patches` ; aucune fusion |
| 005 : `topoSet`, puis `removeFaces mergeFaces -noFields` | — | Arrêt natif sur une face illégale à deux sommets ; aucune dérivée sauvegardée admise |
| 006 : fusion locale conservant les faces de frontière | 541 931 | Déterminant et interpolation corrigés, mais quatre autres contrôles échouent ; dérivée rejetée |

Dans 001, l’import contient une seule région et les trois patches non vides.
Le volume est 0,0001379370876514855 m³, la non-orthogonalité maximale
81,9899° et le skewness maximal 2,34484. Les deux défauts supplémentaires sont
détectés par `checkMesh -allGeometry -allTopology` : le minimum SICN supérieur
à 0,1 ne les prédit pas.

Dans 006, 257 faces intérieures sont retirées. Tous les points et toutes les
faces orientées de frontière sont conservés exactement par la construction.
Le minimum de déterminant atteint 0,00100337 et le poids d’interpolation
minimal 0,0506967. Cependant, OpenFOAM relève **106 cellules concaves**, quatre
faces à pyramide mal orientée, cinq faces trop déformées et huit faces avec
une décomposition tétraédrique déficiente. Ces corrections ne sont donc pas
une solution acceptable.

Les journaux natifs [001](derived/kali-cfd-20261025/case-001-log.checkMesh.txt),
[002](derived/kali-cfd-20261025/case-002-log.checkMesh.txt),
[006](derived/kali-cfd-20261025/case-006-log.checkMesh.txt) et
l’[arrêt natif de 005](derived/kali-cfd-20261025/case-005-log.removeFaces.txt)
sont versionnés avec le seul chemin local remplacé par `<job>`. Les originaux
restent dans l’archive, avec leurs empreintes propres.

**Le code de sortie de `checkMesh` ne suffit pas : il peut être nul malgré
`Failed … mesh checks`.** Le garde-fou existant `accept_mesh.py` exige
explicitement `Mesh OK.`, refuse les échecs et vérifie les types de patches.
Les recettes séquentielle et MPI placent ce garde-fou avant le solveur.
Il n’existe aucun journal `serialFoam` ou `simpleFoam` dans les essais conservés.

## Sources et conservation

- [Préparation des champs et dictionnaires](source/coolant_flow/prepare_kali_case.py),
  puis [liaison des reçus et limite de temps](source/coolant_flow/prepare_kali_bound_case.py).
- [Recette MPI initiale](source/coolant_flow/run_kali_case.sh) et
  [recette séquentielle réellement tentée](source/coolant_flow/run_kali_serial.sh).
- [Fusion locale rejetée](source/coolant_flow/merge_flagged_cells.py), utilisant
  les ensembles natifs `underdeterminedCells` et `lowWeightFaces`. Cette
  sélection par grande face ne garantit pas des unions convexes ; le contrôle
  OpenFOAM suivant est obligatoire.

Pour reproduire l’entrée, utiliser l’environnement natif de préparation déjà
documenté (`CAD_PY` avec NumPy, trimesh et Gmsh), puis un nouveau dossier de
sortie. Après transfert vérifié, exécuter la recette dans l’environnement
Foundation 13 isolé et borné décrit ci-dessus :

```sh
SRC=twins/962-cylinder-head-f0/source/coolant_flow
BASE=work/962-coolant-flow
"$CAD_PY" "$SRC/prepare_kali_bound_case.py" "$BASE/mesh-010" \
  "$BASE/surface-004" twins/962-cylinder-head-f0/derived/mezger-sp95-budget.json "$CASE"
# À l’intérieur de l’environnement Foundation 13 :
source /opt/openfoam13/etc/bashrc
bash "$SRC/run_kali_serial.sh" "$CASE"
```

Pour relire le rejet et reproduire la fusion locale, travailler sur une copie
neuve : `checkMesh -writeSets` écrit des diagnostics et ne doit donc pas être
relancé dans un cas déjà figé par un reçu. Les variables suivantes désignent
des chemins absolus, et `DIAGNOSTICS` comme `MERGED` doivent être absents :

```sh
test ! -e "$DIAGNOSTICS" && cp -a "$CASE" "$DIAGNOSTICS"
checkMesh -case "$DIAGNOSTICS" -allGeometry -allTopology -writeSets -setFormat vtk
python3 "$SRC/merge_flagged_cells.py" "$CASE" "$DIAGNOSTICS" "$MERGED"
checkMesh -case "$MERGED" -allGeometry -allTopology
python3 "$MERGED/accept_mesh.py" "$MERGED"
```

La dernière commande doit refuser le candidat observé ; cette séquence n’est
pas une recette d’admission et ne lance pas le solveur.

L’archive locale `work/962-coolant-flow/kali-execution-001/kali-cfd-attempts-001.tar.gz`
contient **189 fichiers**, pour **166 697 668 octets**, SHA-256
`49507e98c899a091ddf62887923207505045cc2019c1139f5a9254bd805171f9`.
La copie locale est relue intégralement et les 188 empreintes de charge utile
sont comparées au manifeste, lui-même vérifié séparément. Le MSH initial reste
dans la livraison précédente ; ses duplications et le runtime fournisseur ne
sont pas ajoutés à cette archive. Les grands fichiers restent hors Git.

## Vérifications et blocage restant

Les **huit nouveaux tests ciblés passent**, ainsi que la syntaxe shell.
Le passage local global `make check` atteint 4 205 tests : deux échecs de
flottants dans les modules de ventilateur non modifiés, 29 erreurs dont des
chargements SciPy/Pillow et `hashlib.file_digest` indisponible sous Python 3.10,
et 260 tests ignorés. Il n’est pas vert. Le passage culasse atteint 241 tests,
avec deux erreurs de chargement SciPy et sept tests ignorés. Ces décomptes
incluent les tests exécutés, pas uniquement les succès.

La CI du précédent commit `9f30cd90` a réussi dans
[le run 40190361113](https://github.com/cluster2600/porscheparts/actions/runs/40190361113).
Ce succès logiciel ne couvre pas les nouveaux fichiers ni l’admission CFD.

Le blocage concret est désormais la qualité du stencil OpenFOAM. La prochaine
correction doit sélectionner des unions convexes ou produire un nouveau
maillage de calcul, puis conserver la frontière et repasser **tous** les
contrôles avant toute résolution. Les seuils ne sont pas assouplis.
Perte de charge, distribution des débits, convergence, CHT, cliquetis SP95,
tenue mécanique, montage sur donneur et puissance de 1 000 ch restent ouverts.
