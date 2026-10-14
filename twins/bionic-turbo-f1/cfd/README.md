# Comparaison compressible du côté froid

Cette chaîne prépare le **compresseur conceptuel et ses hypothèses**, avec les
surfaces fournies de sa roue et de sa volute, pour OpenCFD 2406 `rhoSimpleFoam`.
La géométrie n'est pas remplacée par un conduit rectangulaire équivalent.
Aucune carte mesurée de turbo ni calibration physique n'est revendiquée.

L'unique image prise en charge est le runtime officiel OpenCFD ARM64, épinglé
dans `prepare_case.py`. La version 2406 inclut le travail de pression MRF dans
[l'équation énergétique officielle](https://gitlab.com/openfoam/core/openfoam/-/raw/OpenFOAM-v2406/applications/solvers/compressible/rhoSimpleFoam/EEqn.H).
Foundation 13 ne constitue pas un profil d'exécution pris en charge ici.

Entrée : un STL ASCII en mètres, avec exactement quatre régions `inlet`,
`outlet`, `rotor`, `stator`, dont les arêtes réunies ferment une surface orientée
de manière cohérente. Le générateur doit documenter les joints idéalisés et
les voies de fuite exclues. Ce contrôle ne vérifie ni auto-intersection, ni jeu,
ni présence du point d'amorçage dans le fluide. Vérifier indépendamment le point
`(0.015, 0, 0.040)` avant maillage. L'entrée est un plan Z au-dessus de la zone
tournante et la sortie un plan Y au-delà de celle-ci. Les bornes proviennent du STL.

La zone tournante a un rayon de 32 mm et s'étend de Z = -4 à +33 mm. Toutes les
faces de la roue doivent lui appartenir ; les deux sections de mesure doivent
rester hors de celle-ci. Les conditions initiales hypothétiques sont : pression
totale d'entrée 101325 Pa, température totale d'entrée 298,15 K, régime de
100000 tr/min autour de +Z et pression **statique** de sortie 121590 Pa.
L'option de rapport de pression désigne sortie-statique/entrée-totale, pas
le rapport total/total.

```sh
python twins/bionic-turbo-f1/cfd/prepare_case.py \
  work/domain/shell.ASCII.stl work/cfd-baseline-coarse \
  --level coarse --rotation-sign 1 --pressure-ratio 1.2
python twins/bionic-turbo-f1/cfd/run_case.py work/cfd-baseline-coarse --stage config
python twins/bionic-turbo-f1/cfd/run_case.py work/cfd-baseline-coarse --stage mesh --timeout 600 --cpus 4 --memory-gb 12
python twins/bionic-turbo-f1/cfd/run_case.py work/cfd-baseline-coarse --stage solve --timeout 1800 --cpus 4 --memory-gb 12
python twins/bionic-turbo-f1/cfd/audit_case.py \
  work/cfd-baseline-coarse work/cfd-baseline-coarse-audit.json
```

Chaque cas, étape et rapport refuse l'écrasement. Les tentatives rejetées restent
disponibles ; toute configuration modifiée reçoit un nouveau dossier. L'exécuteur
utilise uniquement l'image locale, sans réseau, avec des limites explicites de
CPU, mémoire et durée. `coarse`, `medium`, `fine` fixent les cellules de fond à
1,6, 1,2 et 0,9 mm. Une boîte de raffinement impose le niveau 1 dans tout le
volume fluide retenu : tailles nominales 0,8, 0,6 et 0,45 mm. Cette boîte ne crée
aucune frontière ; les quatre patches proviennent du seul STL.

L'essai ciblé `medium-gap` ajoute le raffinement des jeux du
[tutoriel officiel OpenCFD 2406](https://gitlab.com/openfoam/core/openfoam/-/raw/OpenFOAM-v2406/tutorials/mesh/snappyHexMesh/gap_detection/system/snappyHexMeshDict) :
`gapLevel (4 1 3)`, `gapMode mixed`, `gapSelf true`. La cible est de quatre cellules,
avec un plafond de niveau 3 ; la détection inclut les faces du même STL. Le mode
`mixed` examine les deux côtés des surfaces, sans supposer que les normales
des obstacles et celles de l'enveloppe désignent le même côté matériel.
Pour `medium`, la taille nominale minimale de 0,15 mm correspond à 3,33 cellules
dans le jeu de 0,5 mm roue/écrou et 4,27 dans le jeu arrière d'environ 0,64 mm.
Le plafond peut donc empêcher d'atteindre la cible de quatre cellules. Les profils
`coarse` et `fine` plafonnent respectivement à 0,2 et 0,1125 mm ; `coarse` ne vise
pas trois cellules dans 0,5 mm. Ces rapports sont des estimations avant snapping,
pas des comptes mesurés ni une preuve de résolution des jeux. Les transitions
de raffinement local réapparaissent et restent soumises aux mêmes contrôles
de qualité. Le snapping reste contraint à la région STL d'origine.
Le seuil natif de six millions de cellules est approximatif : une passe peut
le dépasser ou interrompre le raffinement avant son niveau demandé. La limite
mémoire du conteneur et le délai d'exécution restent indépendants. Il n'y a actuellement
**aucune couche prismatique de paroi**. Ces maillages servent de pilotes
numériques ; la résolution des couches limites reste à qualifier.

Avant tout solveur, le contrôle étendu `checkMesh -allTopology -allGeometry`
doit réussir. Le nombre de coquilles fermées, calculé par adjacence exacte des
arêtes, les régions présentes sur chaque coquille et les caractéristiques
d'Euler globale et par coquille doivent rester identiques au STL d'entrée.
Ce contrôle détecte notamment une roue isolée raccordée par
erreur au carter lors du maillage d'un jeu trop étroit. L'expression native
« closed singly connected » ne remplace pas ce comptage. L'égalité de ces
invariants ne constitue pas une démonstration de conservation de la forme et
des dimensions de tous les passages ou jeux.
La comparaison au STL ne valide pas non plus sa construction : des passages
parasites introduits en amont doivent être rejetés par un contrat géométrique
indépendant, avant toute préparation de maillage.

L'audit lie les historiques aux entrées préparées et au maillage inspecté. Il
exige des historiques complets et continus, les signes attendus aux sections,
la conservation de masse, l'imperméabilité absolue des parois, un reflux limité,
la stabilité du débit, du couple et de l'énergie, des pressions et températures
positives ainsi que des résidus faibles. Le flux d'enthalpie totale utilise
`sum(phi*h) + 0.5*sum(phi*magSqr(U))`, avec la vitesse absolue et les sections hors
MRF. Il doit correspondre à **moins** la vitesse angulaire multipliée par le
moment du fluide sur la roue ; aucune valeur absolue ne masque un mauvais signe.

Un historique accepté ne classe pas les performances. La comparaison exige
une roue, des hypothèses de joints, des extensions d'entrée/sortie et des
conditions de service communes, puis une étude de sensibilité au maillage et
au traitement de paroi. Un seul point à contre-pression imposée ne démontre
ni débit maximal ni blocage sonique. Aucun rendement n'est déduit de
l'approximation incompressible `p + rho*U²/2`. Les itérations stationnaires ne
représentent pas un temps physique de montée en régime. La validation
d'ingénierie et l'autorisation de fabrication restent fausses.
