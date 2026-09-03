# F37 — audit `iceEngineFoam` et essai moteur mobile de référence

## Verdict

Le nom `iceEngineFoam` ne correspond à aucun exécutable disponible dans
l'image OpenFOAM Foundation 13 louée. Les exécutables historiques
`engineFoam`, `XiEngineFoam` et `coldEngineFoam` y sont également absents. La
distribution installée emploie l'architecture modulaire suivante :

```text
foamRun -> XiFluid -> multiValveEngine -> meshToMesh
```

Cette chaîne a été réellement exécutée sur le tutoriel officiel
`XiFluid/engine2Valve2D`. Il ne s'agit pas d'un renommage d'`iceEngineFoam` et
aucune substitution équivalente n'est revendiquée.

## Résultat exécuté sur Vast x86_64

| Contrôle | Résultat |
| --- | --- |
| Version | OpenFOAM Foundation 13, build `13-18870c24d21c` |
| Géométrie | tutoriel générique 2D, deux soupapes |
| Régime du tutoriel | 500 tr/min |
| Intervalle calculé | 0 à 110 CAD |
| Maillage initial | 5 040 points, 2 178 hexas, `Mesh OK` |
| Changement à 100 CAD | 2 178 vers 3 966 cellules, 10 868 couplages |
| État à 110 CAD | échappement ouvert à 30 mm, admission fermée |
| Solveur | deux segments terminés avec code 0 |

La première tentative lancée sous `root` a été correctement refusée par la
protection `dynamicCode` d'OpenFOAM. Le cas a été recréé depuis le tutoriel
installé et exécuté sous l'utilisateur non privilégié `nobody`. Le solveur
charge `XiFluid`, le mouvement `multiValveEngine`, le changement de topologie
`meshToMesh`, les interfaces non conformes et le modèle
`multiCycleConstantbXiIgnition`. Le passage à 100 CAD remappe effectivement
2 178 cellules sources vers 3 966 cellules cibles.

Les preuves compactes sont dans
`twins/reference-917-engine/evidence/f37-ice-engine-foam/`. Les empreintes des
logs complets distants et des binaires sont conservées dans `report.json`.

## Rôle de Cantera

Cantera 3.2.0 reste un calcul 0D séparé. Ses enveloppes actuelles sont
11,8847 MPa absolus pour le candidat atmosphérique et 24,6861 MPa absolus pour
le candidat turbo. La seconde valeur est conservée comme charge structurelle
aval conservatrice. Le désaccord de pression avec Wiebe reste rouge; ces
valeurs ne sont donc ni une combustion corrélée ni une puissance démontrée.
Elles n'ont pas été injectées dans le tutoriel `XiFluid`.

## Pourquoi le vrai calcul F37 reste bloqué

Le scan extérieur ne fournit pas les volumes fluides 3D nécessaires au
solveur moteur : cylindre et piston, bols et jeux, surfaces mobiles des quatre
soupapes, profils de came, intersections soupape-piston, volumes admission et
échappement étanches. Les conditions de pression/température transitoires et
la corrélation banc manquent aussi.

En conséquence, le calcul réalisé valide uniquement l'installation et le
passage d'un maillage moteur mobile générique. Il ne valide ni la culasse F37,
ni sa combustion, ni son refroidissement, ni son impression. Les portes
`metal_print_authorized` et `engine_start_authorized` restent à `false`.
