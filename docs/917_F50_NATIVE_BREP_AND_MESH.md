# F50 — maîtres B-Rep natifs 2V/4V et maillages indépendants

## Résultat utile

F50 ferme le défaut de p-curves **dans le format B-Rep natif OCCT** pour les
deux variantes. Après écriture et relecture :

| variante | BOPAlgo | BRepCheck exact | solides/coques | arêtes libres | non-manifold | delta bbox |
|---|---:|---:|---:|---:|---:|---:|
| 2V | 0 | valide | 1 / 1 | 0 | 0 | 0 |
| 4V | 0 | valide | 1 / 1 | 0 | 0 | 0 |

La réparation ne remplace ni ne déplace aucune courbe ou surface 3D. Elle
recalcule seulement les courbes 2D portées par les faces (`p-curves`) sur une
copie topologique qui partage la géométrie 3D d'origine. La peau F43 reste donc
la seule autorité extérieure.

F50 n'ajoute **aucune ellipse, aucun ovale, aucune boîte globale et aucune mise
à l'échelle anisotrope**. Les alésages fonctionnels restent ceux du candidat
F47. Les maîtres `.brep` et les rapports contenant des coordonnées restent
privés sur Kali; seuls leurs empreintes et résultats sanitaires sont publiés.

## Pourquoi le STEP reste rouge

Le candidat réparé vaut zéro défaut avant export. Le même candidat, sérialisé
en STEP et relu, recrée les défauts historiques :

- AP214 avec précision noyau : 8 `InvalidCurveOnSurface`, 5 faces/8 arêtes;
- AP214 avec précision utilisateur 0,02 unité : même résultat;
- AP242DIS avec précision utilisateur 0,02 unité : même résultat.

La stratégie de ports facettés 96 côtés a également été rejetée : 22 défauts
après STEP au lieu de 8. Les quatre stratégies F49 (soustraction groupée,
soustraction séquentielle, reprojection puis STEP, conversion NURBS) n'avaient
pas franchi le round-trip STEP. Le défaut restant est donc une limite
d'interopérabilité STEP des trims internes, pas une autorisation de modifier la
forme extérieure.

Le `.brep` natif peut servir de **maître CAO/CAE privé dans le même noyau OCCT**.
Il ne devient pas pour autant un fichier de fabrication libéré. L'interop STEP
reste un gate indépendant obligatoire.

## Gmsh : trois niveaux 2V et niveau comparable 4V

Le B-Rep maître n'est jamais modifié. Chaque profil redémarre un processus Gmsh
propre et ne change que les options de discrétisation.

| variante/profil | tétras | inversés | minSICN | p01 | `< 0,1` | verdict |
|---|---:|---:|---:|---:|---:|---|
| 2V, grossier, brut | 556 459 | 1 numérique | -9,54e-16 | 0,2994 | 1 271 | rejeté |
| 2V, grossier + Relocate3D | 556 459 | 0 | 1,85e-14 | 0,2995 | 1 236 | rejeté |
| 2V, moyen | 1 557 441 | 0 | 7,88e-6 | 0,3458 | 1 095 | rejeté |
| 2V, fin | 3 433 600 | 0 | 3,33e-6 | 0,3599 | 676 | rejeté |
| 4V, moyen | 1 906 555 | 0 | 3,80e-6 | 0,3504 | 1 086 | rejeté |

`UntangleMeshGeometry` a dégradé la queue de distribution et a été rejeté.
HXT a échoué lors de la récupération des facettes; l'algorithme frontal n'est
pas disponible dans le build sans Netgen. Le raffinement améliore le p01 mais
ne fait pas converger le minimum. La porte de qualité stricte reste donc rouge.

## Vérification indépendante TetGen

Une tessellation de surface est générée directement depuis chaque maître natif,
sans healing, sewing ni booléen. L'audit d'incidence donne exactement deux
triangles par arête :

| variante | nœuds | triangles | arêtes | volume tessellé / B-Rep | TetGen `-d` |
|---|---:|---:|---:|---:|---|
| 2V | 110 266 | 220 560 | 330 840 | +0,0346 % | aucune intersection |
| 4V | 126 517 | 253 078 | 379 617 | -0,0010 % | aucune intersection |

TetGen 1.5.0 est exécuté en PLC avec contrainte de qualité, angle dièdre et
optimisation. Le contrôle utilise ensuite `minSICN` dans Gmsh sur le maillage
converti afin de rendre la comparaison explicite. La contrainte TetGen
rayon-arête/dièdre et `minSICN` ne sont toutefois pas mathématiquement
interchangeables; les deux sont conservées dans la preuve.

Le premier écran 2V (`q1.4/10`, volume maximal 20 unités³) donne 3 037 292
tétras, zéro inversion, `minSICN=0,00404` et 416 éléments sous 0,1. La dernière
tentative bornée (`q1.2/15`, `O2`) améliore les quantiles mais conserve des
slivers : 14 320 517 tétras, zéro inversion, `minSICN=0,00329`, p01=0,3570 et
497 éléments sous 0,1. La tentative 4V comparable produit 16 590 701 tétras,
zéro inversion, `minSICN=0,00616`, p01=0,3571 et 402 éléments sous 0,1. Les
deux variantes échouent donc le même seuil strict; aucune itération
supplémentaire n'est lancée pour masquer cette queue de slivers.

## Portes de décision

- maître privé OCCT 2V : **accepté pour CAO/CAE dans le même noyau**;
- maître privé OCCT 4V : **accepté pour CAO/CAE dans le même noyau**;
- interopérabilité STEP : **rejetée**;
- qualité volumique stricte Gmsh/TetGen : **rejetée tant qu'un élément reste
  sous `minSICN=0,1`**;
- échelle et interfaces Porsche 917 : **non certifiées**;
- épaisseur exhaustive, matière à chaud, LPBF, CHT/FEA/fatigue et corrélation
  physique : **non validées**;
- impression métal, démarrage moteur et revendication 1 600 ch : **interdits**.

Les chiffres publics expurgés sont dans
[`native-brep-mesh-f50.json`](../twins/reference-917-engine/evidence/f50-native-brep/native-brep-mesh-f50.json).
Les scripts reproductibles ne contiennent ni géométrie privée ni coordonnées
du scan.
