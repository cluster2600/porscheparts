# Éprouvette renforcée — pression et coût en passage d'air

Suite de la [comparaison ShapeKernel/LatticeLibrary](../hot-weather/README.md),
fusionnée par la PR #207. Les fichiers antérieurs restent inchangés.
Le passage chaud lisse de 0,8 mm échouait au contrôle exploratoire de pression.
Cette étape ajoute de vraies nervures longitudinales et **douze calculs CalculiX
exécutés localement**, puis contrôle la géométrie PicoGK et ses champs VDB.

## Résultat de la comparaison

Pression exploratoire : **3,75 bar relatifs**, E supposé à chaud **50 GPa**,
ν supposé **0,33**, seuil exploratoire **40 MPa**, sans loi plastique ni admissible
certifié AlSi10Mg à 233 °C. Les résultats suivants correspondent aux éléments
cibles de 0,1 mm, **pas à une solution de contrainte convergée** :

| Nervures chaudes | Pic nodal von Mises | Déplacement maximal | Section de passage |
|---|---:|---:|---:|
| Aucune | 210,2 MPa | 0,1771 mm | 67,2 mm² |
| Deux | 44,2 MPa | 0,01143 mm | 62,4 mm² |
| Quatre | 12,0 MPa | 0,000753 mm | 57,6 mm² |

La variante à deux nervures dépasse le seuil supposé sur le maillage fin.
Quatre nervures constituent le candidat à poursuivre, **sans qualification en
pression**. Les pics augmentent à chaque raffinement aux angles vifs : pour
quatre nervures, 6,87 → 9,11 → 11,96 MPa aux pas 0,4 → 0,2 → 0,1 mm.
Le déplacement varie de 0,82 % entre les deux derniers maillages, mais cela
ne démontre pas une convergence des contraintes aux pieds de nervure.
Le cas sans nervure dépasse notre contrôle de petit déplacement (10 % de
l'épaisseur) ; ses contraintes linéaires ne prédisent pas une réponse plastique.

![Sensibilité des champs natifs au maillage](derived/mesh-sensitivity.png)

## Modèle mécanique, contrôles et chemin de charge

Le modèle est un **quart de section transverse en déformation plane**, avec
éléments quadratiques CPE8. X du solveur correspond à Y du coupon, Y du solveur
à Z moins 2,3 mm ; l'axe longitudinal du passage est hors plan. Deux plans de
symétrie imposent seulement les déplacements normaux nuls. La pression agit
sur toutes les faces internes, y compris les deux côtés des nervures. Le chemin
de charge étudié relie les parois supérieure/inférieure aux nervures et parois
latérales continues ; il ne fournit aucune fixation au moteur ou au banc.

Le maillage est indépendant du STL, construit sur la section analytique :
parois 0,8 mm, passage chaud haut de 3 mm, nervures épaisses de 0,8 mm,
centres Y = ±3 et ±9 mm pour la variante à quatre nervures. Les sections et
résultantes de pression sont contrôlées indépendamment par les tests.
La tranche omet le treillis froid, les raccords, les joints, le dispositif
fermant les extrémités, les contraintes thermiques, la fatigue et les effets
de longueur finie. Le coupon mesure seulement 24 mm : la déformation plane
est une approximation comparative, pas une solution complète de la pièce.

CalculiX **2.21**, image locale conservée par son SHA-256 dans le
[rapport](derived/study.json), a exécuté :

- neuf cas de pression : 0/2/4 nervures, trois maillages ;
- un élément à déformation uniforme prescrite, confronté à la solution élastique ;
- un élément sous pression de bord, contrôlant également signe et direction ;
- le cas à quatre nervures et 0,2 mm sous demi-pression, vérifiant la proportionnalité.

Les comparaisons analytiques portent sur les contraintes aux 27 points
 d'intégration de l'élément CPE8 développé et les déplacements. L'extrapolation
nodale produit une petite différence conservée dans le reçu ; elle n'est pas
utilisée pour modifier les valeurs natives. Le cas entièrement prescrit émet
l'avertissement attendu « no degrees of freedom » ; le second contrôle charge
réellement des degrés de liberté libres. Les entrées, champs FRD, contraintes DAT
et journaux des douze cas sont conservés dans [fea](derived/fea/).
Les `.frd.gz` et `.dat.gz` doivent être décompressés avant ouverture.

Référence de formulation : [manuel officiel CalculiX 2.23](https://www.dhondt.de/ccx_2.23.pdf),
sections CPE8, `*DLOAD` et `OUTPUT=2D`. Le solveur exécuté reste la version 2.21 ;
les deux contrôles analytiques vérifient concrètement les fonctions utilisées.
Le téléchargement du manuel 2.21 a expiré ; sa lecture n'est pas revendiquée.

## Coût hydraulique exploratoire

À **débit massique total identique**, correspondant à 1 m/s dans le passage
lisse, air à 506,47 K et 303 975 Pa absolus :

| Nervures | Perte de charge du modèle court de comparaison |
|---|---:|
| Aucune | 3,03 Pa |
| Deux | 3,72 Pa |
| Quatre | 4,87 Pa |

Quatre nervures retirent **14,3 % de section** et augmentent la perte calculée
d'environ **60,4 %** dans ce modèle. Le débit est réparti entre cinq canaux par
égalité de pression, sans imposer artificiellement le même débit par canal.
Les largeurs libres sont 1,8 / 5,2 / 5,2 / 5,2 / 1,8 mm.

Le calcul réutilise la résistance laminaire rectangulaire du dimensionnement
existant et ajoute K = 2 supposé. Les canaux de 24 mm sont courts : effets
d'entrée, rugosité LPBF, pertes des collecteurs et distribution réelle ne sont
pas résolus. Les longueurs d'entrée estimées sont conservées par canal.
Ces chiffres ne sont ni une CFD ni une mesure et ne se transposent pas aux
4,88 kg/s du grand échangeur. **Aucun gain thermique n'est encore démontré.**

## Géométrie native et VDB

![Deux coupes du coupon généré](derived/coupon.png)

ShapeKernel construit enveloppes et canaux ; LatticeLibrary conserve les
seize cellules BCC côté froid. La variante à quatre nervures a été générée à
voxels de **0,2 et 0,1 mm**. Les sept champs nommés VDB conservent les trois
domaines et quatre champs d'initialisation ; leur aller-retour est contrôlé
comme dans l'étude antérieure. Les cinq canaux chauds sont distincts dans le
coupon ; les collecteurs qui les réuniront ne sont pas modélisés.

Le contrôle indépendant a rejeté un premier export : deux canaux mesuraient
1,8375 mm au lieu de 1,8 mm. La cause était une interpolation aux faces
coïncidentes des outils de découpe et des extrémités du fluide. Les outils
sont maintenant prolongés au-delà du domaine fluide ; le contrôle à ±0,02 mm
passe sans changer cette tolérance. Le premier export reste conservé localement.

Le [reçu géométrique](derived/review.json) conserve les défauts bruts et le
nettoyage des faces dégénérées/dupliquées sans changement significatif de volume.
Les surfaces nettoyées sont fermées : une composante solide, cinq chaudes et
une froide. Cette topologie ne prouve ni l'étanchéité réelle ni la qualité
 d'un futur maillage CFD. La somme des volumes diffère de l'enveloppe analytique
 d'environ 0,021 % à voxels de 0,1 mm.

- [STL complet, mm, compressé](derived/ribbed-solid.stl.gz)
- [VDB 0,1 mm](derived/ribbed-0.1-fields.vdb.gz), [VDB 0,2 mm](derived/ribbed-0.2-fields.vdb.gz)
- [Source PicoGK](source/picogk/Program.cs), [calcul et génération FEA](source/study.py)
- [Versions, compilation et contrôles d'entrée](runtime.json)

Les coordonnées PicoGK sont en mm ; températures en K et vitesses initiales
en m/s. Les champs de vitesse uniformes à 1 m/s ne sont pas une solution
fluide. Les droits et empreintes des bibliothèques installées sont revérifiés
contre le reçu de l'étape précédente ; aucune dépendance binaire n'est publiée.

## Reproduction et suite

```sh
python3 twins/993-installed-cooling-f1/intercooler-750/pressure-coupon/source/study.py --output work/new-pressure
python3 -m unittest discover -s tests -p test_993_intercooler_pressure_coupon.py -v
```

Le premier appel utilise exclusivement l'image Docker locale épinglée, réseau
coupé, deux CPU et 2 Go maximum ; il ne lance aucun calcul distant payant.
La génération PicoGK utilise le SDK `~/Developer/PicoGK/sdk/dotnet` et doit
prendre le verrou partagé de `parts/picogk-catalog/tools/run_part.py`.

La prochaine étape mécanique est le dessin des congés aux pieds de nervure,
leur maillage conforme et une étude 3D avec raccords et conditions de maintien.
Il faudra aussi comparer les passages par CFD/CHT ou banc, puis qualifier
orientation, plafonds, dépoudrage, matière à chaud et étanchéité.
**Aucune autorisation d'impression ou d'épreuve sous pression n'est donnée.**
