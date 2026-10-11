# Pilote d'écoulement sans snapping

Le maillage `medium-gap-002` conservait les trois coquilles et leurs invariants,
mais le contrôle étendu rejetait 1 167 cellules concaves, dont 1 156 au contact
d'une transition de raffinement. Le solveur n'a pas été exécuté sur ce maillage.

`prepare_castellated.py` réutilise la préparation F1 et change uniquement
`snap true` en `snap false`. Les sommets restent sur la grille cartésienne
raffinée : les parois deviennent des marches d'escalier. Cette expérience
isole l'effet du déplacement des sommets, avec les mêmes surfaces sources,
raffinements, conditions et contrôles d'admission. Elle ne corrige pas encore
le maillage conforme aux parois et ne permet aucune comparaison de performance.
Les erreurs de forme, de rugosité et de section des jeux restent non quantifiées.

Conditions hypothétiques communes : 100 000 tr/min autour de +Z, pression totale
d'entrée 101 325 Pa, température totale 298,15 K, pression statique de sortie
121 590 Pa. Le débit est une sortie du solveur. Les 800 itérations demandées
ne représentent pas une durée physique. La puissance calculée au rotor serait
une puissance à l'arbre du compresseur, pas une puissance moteur.

```sh
python twins/bionic-turbo-f1/cfd/prepare_castellated.py SURFACE_ASCII_METRES NEW_CASE
python twins/bionic-turbo-f1/cfd/run_case.py NEW_CASE --stage config --timeout 180
python twins/bionic-turbo-f1/cfd/run_case.py NEW_CASE --stage mesh --timeout 1200 --cpus 4 --memory-gb 12
python twins/bionic-turbo-f1/cfd/run_case.py NEW_CASE --stage solve --timeout 7200 --cpus 2 --memory-gb 6
python twins/bionic-turbo-f1/cfd/audit_case.py NEW_CASE NEW_AUDIT.json
```

Chaque commande doit réussir avant la suivante. L'exécuteur refuse un solveur
sans admission du maillage. Les cas existants, leurs sorties et leurs journaux
ne sont jamais écrasés. L'image locale OpenCFD 2406 et tous les fichiers préparés
sont liés par SHA-256 ; aucun calcul distant payant n'est utilisé.

## Admission séparée du diagnostic cartésien

Sur la référence sans snapping, le contrôle étendu signale 18 307 cellules.
La reconstruction indépendante de son critère retrouve exactement cet ensemble,
sans pénétration positive hors de la bande quasi coplanaire. Le critère natif
signale aussi les centres de faces coplanaires subdivisant le côté d'une cellule
aux transitions de raffinement. Cela ne supprime pas le rejet de la chaîne F1.

`check_cartesian_cells.py` vérifie une propriété plus restrictive pour ce seul
cas diagnostique : toutes les faces doivent être des rectangles plans alignés
sur les axes, orientés sur les plans extérieurs des cellules, et les sommes
d'aires doivent couvrir les six côtés de chaque boîte. Ces vérifications
s'ajoutent aux contrôles natifs de fermeture/topologie et à la conservation des
coquilles, des invariants d'Euler et de la zone MRF. La tolérance de coordonnées
est de 10⁻¹² m ; l'erreur relative d'aire maximale admise est de 10⁻⁷.
Toute déformation, face inversée, couverture manquante ou modification des
entrées empêche le calcul. Le maillage conforme avec de vraies concavités
n'est pas éligible à cette procédure.

```sh
python twins/bionic-turbo-f1/cfd/check_cartesian_cells.py NEW_CASE
python twins/bionic-turbo-f1/cfd/prepare_runtime_004.py NEW_CASE NEW_RUNTIME_CASE
python twins/bionic-turbo-f1/cfd/run_cartesian_pilot.py NEW_RUNTIME_CASE
```

Ce second exécuteur exige une preuve liée aux empreintes du maillage et des
entrées. Il conserve `FAILED-mesh.json` et écrit un rapport distinct
`run-cartesian-solve.json`, avec `canonical_mesh_gate_passed=false`.
Le solveur est limité à deux CPU, 6 Gio et deux heures, sans réseau.
Sa fin normale ne signifie ni convergence ni validation : les historiques de
masse, couple, énergie et résidus doivent encore être audités. Le rapport
d'admission canonique ne devient jamais positif par cette procédure.

La préparation `runtime_003` copie uniquement les entrées et le maillage
vérifiés dans un nouveau dossier. Elle corrige deux références requises par
le runtime natif : `Hf` dans `hConst`, et `thermo:psi` pour les conditions de
pression/température totales. Les valeurs physiques ne changent pas. La preuve
géométrique est héritée avec les empreintes exactes de chaque fichier de maillage,
les reçus parents sont copiés dans `provenance/`, et les entrées corrigées reçoivent
de nouvelles empreintes. Les tentatives précédentes restent intactes.

`runtime_004` conserve ces corrections et remplace uniquement le solveur linéaire
de pression GAMG/DIC par PCG/DIC, avec les mêmes tolérances, après l'exception
flottante native dans `GAMGSolver::scale` au premier calcul de pression.
Cette modification numérique ne démontre pas la convergence de la solution.

La réussite d'un calcul pilote ne valide ni les performances physiques,
ni le débit maximal, ni la puissance maximale. Il reste à obtenir un maillage
conforme accepté, qualifier les couches limites et la sensibilité au maillage,
puis explorer une carte régime/contre-pression avec des conditions justifiées.
