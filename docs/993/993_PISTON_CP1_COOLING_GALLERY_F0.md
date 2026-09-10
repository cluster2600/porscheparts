# Piston M64/60 à galerie de refroidissement — concept CP1 F0

Le M64/60 est documenté avec un alésage de `100 mm`, une course de `76,4 mm`
et un limiteur de `6 720 ± 20 tr/min`. Ces valeurs définissent le moteur, pas la
géométrie du piston. PorscheFanatics recoupe les ensembles pistons/cylindres de
la famille 993 et le précédent additif Porsche, sans fournir de plan de piston
993.

Porsche, MAHLE et TRUMPF ont produit pour une 911 GT2 RS moderne un piston par
fusion laser, annoncé `10 %` plus léger que la pièce forgée, optimisé suivant
les charges et doté d'une galerie fermée sous calotte impossible à obtenir par
les méthodes conventionnelles retenues. Porsche annonce aussi `200 h` d'essai
moteur. C'est un précédent de méthode, pas une validation transférable au 993.

Le registre
[`TWIN-993-M64-60-PISTON-GALLERY-F0`](../../catalog/twins/twin-993-m64-60-piston-gallery-f0.json)
relie maintenant la CAO aux cinq interfaces indispensables : cylindre, segments,
axe–bielle, chambre–soupapes et jet d'huile–galerie. Elles restent toutes
`missing_data` : ce statut est volontaire et empêche de confondre enveloppe F0
et piston M64/60 ajusté.

## Pourquoi l'additif a du sens ici

La galerie sous calotte est la fonction que l'usinage conventionnel ne peut pas
réaliser directement. Le F0 emploie un anneau torique de rayon moyen `34 mm` et
diamètre hydraulique `7 mm`. Deux ports radiaux temporaires assurent le
dépoudrage ; un processus ultérieur devrait les fermer, puis vérifier la
galerie par CT et épreuve. Le choix doit rester comparé à un piston forgé et à
une solution avec galerie moulée ou percée.

La matière candidate est Aheadd CP1 sur route Velo3D Sapphire `50 µm`, suivie
de `400 °C pendant 4 h`. La fiche publie `2,67 g/cm³`, un minimum vertical usiné
de `297 MPa` en limite d'élasticité et `331 MPa` en traction. Constellium publie
`187 W/(m·K)` à l'ambiante et une stabilité qualitative vers `250–300 °C`.
Ces valeurs ne forment pas une carte piston à chaud ou en fatigue.

Le STEP relu contient un solide BREP valide dans une enveloppe synthétique de
`99 × 99 × 70 mm`. Son volume vaut `255 175,45 mm³` et sa masse théorique
`681,32 g`. Diamètre, hauteur, jupe, cavité, bol, axe, bossages, gorges et galerie
sont entièrement propres au F0 ; aucune surface Porsche ou MAHLE n'est copiée.

## Criblages exécutés

Le cas de régression utilise une pression cylindre synthétique de `12 MPa`, une
bielle de `127 mm`, `140 g` d'axe et segments, `2 l/min` d'huile, `5 kW` retirés
par la galerie, `+200 K` et `100 h` à `6 720 tr/min`.

Avec la masse CAO, les équations donnent `94,25 kN` de force gaz, `20,21 kN`
d'inertie et une borne d'effort d'axe de `114,46 kN`. Le modèle de plaque
circulaire encastrée donne `277,57 MPa` et `0,486 mm` au centre pour un ligament
analytique de `5,5 mm`. Le rapport entre le minimum CP1 ambiant et cette
contrainte n'est que `1,07` : le F0 n'a pas de marge démontrée à chaud.

À `6 720 tr/min`, la course publiée donne une vitesse moyenne de piston de
`17,1136 m/s`, une accélération synthétique au PMH de `2 509,25 g` et un rapport
bielle/manivelle hypothétique de `3,3246`. L'alésage et la course documentaires
restituent `600,044 cm³` par cylindre et `3 600,265 cm³` pour six cylindres ;
ce contrôle de cohérence ne fournit aucune cote de piston.

La pression projetée d'axe vaut `124,41 MPa`. Le modèle laminaire de galerie
donne Reynolds `515`, `0,866 m/s` et `1,21 kPa` de perte linéaire. À `5 kW`, le
débit hypothétique prendrait `88,24 K`. La conduction 1D fournit une borne haute
de `35,91 kW`, la dilatation libre du diamètre `0,455 mm` et le cycle de `100 h`
`40,32 millions` de tours, soit `20,16 millions` de combustions par cylindre pour
un quatre-temps. `200 h` au régime maximal correspondraient mathématiquement à
`80,64 millions` de tours ; ce n'est pas le profil du banc Porsche, non publié.

Ces nombres sont des contrôles mathématiques reproductibles, pas une FEA, une
CHT, une CFD multiphasique ni une prédiction de durée de vie.

## Criblage CalculiX thermomécanique exécuté

Le master STEP sain, et non les STL PicoGK non-manifold, a été maillé en
tétraèdres quadratiques C3D10 à `5`, `3,5` et `2,5 mm`. CalculiX 2.21 a exécuté
pour chaque maille une statique froide et une analyse stationnaire séquentielle
température–déplacement, soit six résolutions réelles sur le X1.

Le cas chaud applique l'enveloppe axiale synthétique pression plus inertie, un
total de `5 kW` réparti sur les nœuds extérieurs de calotte, une galerie idéale
à `120 °C` et la jupe à `160 °C`. L'alésage d'axe est totalement fixé : cette
borne surcontraint volontairement la dilatation. Elle ne remplace ni le contact
axe–bossages, ni la CHT combustion, ni le jet d'huile.

| Maille | Nœuds | C3D10 | Froid p95 | Chaud p95 | Tmax chaud |
|---:|---:|---:|---:|---:|---:|
| 5,0 mm | 28 208 | 14 469 | 116,88 MPa | 333,87 MPa | 193,77 °C |
| 3,5 mm | 61 975 | 33 836 | 110,73 MPa | 326,31 MPa | 192,41 °C |
| 2,5 mm | 139 924 | 81 861 | 112,17 MPa | 323,46 MPa | 187,04 °C |

Entre les deux maillages les plus fins, le p95 froid varie de `1,28 %`, le p95
chaud de `0,88 %` et la température maximale de `2,87 %`. Le déplacement chaud
maximal fin vaut `0,262 mm`. Les maxima bruts de contrainte atteignent
`379,11 MPa` à froid et `685,97 MPa` à chaud ; ils restent dominés par la
fixation idéale et sont conservés, pas masqués.

Même le p95 chaud donne seulement `297 / 323,46 = 0,918` face à la limite CP1
publiée à l'ambiante. Comme cette limite n'est pas un admissible chaud, elle ne
peut pas valider le dessin ; le dépassement suffit en revanche à rejeter ce F0
dans ce cas conservateur. Les `20,16 millions` de combustions par cylindre sur
`100 h` sont comptées, mais aucune durée de vie n'est calculée sans courbe S-N
CP1 chaude qualifiée.

Le rapport, les hashes des sorties brutes et son vérificateur indépendant sont
dans [`evidence/calculix-f0`](../../twins/993-m64-60-piston-gallery-f0/evidence/calculix-f0/).

## Criblage d'optimisation PicoGK exécuté

L'objectif demandé est désormais formalisé ainsi : minimiser la masse et la
température de calotte, sous contraintes de résistance statique à chaud,
fatigue, rigidité, dilatation, débit d'huile, dépoudrage et usinage. « Très
solide » est une contrainte éliminatoire ; une variante plus légère ne gagne
pas si elle l'affaiblit.

Les photographies Porsche montrent une matière dense conservée autour des
gorges, du bord de calotte et de l'axe, avec une structure interne ouverte
orientée par les chemins d'effort. Les coupes IAV fournies séparément montrent
un treillis triangulé jupe–calotte et des circuits distincts près du bol et de
la première gorge. Elles concernent un piston diesel lourd d'environ `130 mm`,
avec d'autres matériaux et des canaux partiellement remplis de sodium : seule
l'architecture du treillis inspire les variables PicoGK, jamais ses cotes ou
ses limites thermiques.

Un premier balayage réel a été exécuté hors réseau sur le X1 avec PicoGK 2.3.0
et le runtime natif `picogk.26.2`, à voxels de `0,5 mm`. Six variantes
géométriques F0 combinent poches de jupe ouvertes, galerie de `7 à 9 mm` et
treillis triangulé jupe–calotte et renforts d'axe. PicoGK a servi de noyau
voxel/booleen et de générateur de
maillages ; il n'a exécuté ni calcul de structure ni calcul thermique.

| Variante | Masse voxel CP1 | Écart à la masse BREP | Surface mouillée relative | Perte laminaire relative | Marge plaque ambiante |
|---|---:|---:|---:|---:|---:|
| P0 référence voxelisée | 687,37 g | +0,89 % | 1,000 | 1,000 | 1,070 |
| P1 six poches | 683,37 g | +0,30 % | 1,000 | 1,000 | 1,070 |
| P2 huit poches | 680,96 g | -0,05 % | 1,000 | 1,000 | 1,070 |
| P3 galerie 8 mm + treillis | 683,39 g | +0,30 % | 1,143 | 0,586 | 0,884 |
| P4 galerie 8,5 mm + treillis | 681,21 g | -0,02 % | 1,214 | 0,460 | 0,798 |
| P5 allègement maximal du balayage | 670,44 g | -1,60 % | 1,286 | 0,366 | 0,716 |

La marge provisoire exigée était `1,50`; aucune variante ne la passe. Les
renforts PicoGK ne sont volontairement pas crédités par l'équation de plaque :
seule une FEA 3D thermomécanique peut quantifier leur apport. Le contrôle aval
révèle en outre des arêtes non-manifold dans les six STL PicoGK, malgré zéro
arête ouverte. Ces sorties brutes restent donc en quarantaine : aucune n'est
reconstruite en BREP, envoyée au tranchage LPBF ou promue dans Omniverse.

Le résultat est un **criblage PicoGK exécuté sans dessin sélectionné**, pas une
optimisation validée. Le meilleur allègement brut observé, `1,60 %`, est un candidat de
recherche qui échoue le critère mécanique et le gate d'intégrité maillage.
Voir [`evidence/picogk-f0`](../../twins/993-m64-60-piston-gallery-f0/evidence/picogk-f0/).

## Simulation d'impression et Omniverse exécutées

Le STEP a été maillé en `273 988` triangles étanches puis réellement sectionné
sur les `2 390` couches de `50 µm` de l'orientation candidate `roll_y_45`.
L'écran trouve quatre nouveaux îlots, `759` couches avec une région non
soutenue, un maximum de `4,898 mm²` et une enveloppe conservative de supports
de `8,365 cm³`. Aucun vide piégé n'est détecté au pas voxel de `1 mm`, ce qui ne
remplace pas un CT. L'épaisseur locale p01 vaut `0,420 mm` sur 2 000 sondes et
`6,25 %` des sondes sont sous `1,5 mm` : le dessin doit donc encore être revu.

Le même master passe OpenUSD minimum, NVIDIA Asset Validator, Geometry,
Physics et le profil SimReady `Prop-Robotics-Neutral 1.0.0`. Le rendu OVRTX est
visible dans le dossier de preuves. Il s'agit d'un prop d'inspection isolé ; les
interfaces du moteur sont absentes.

Une scène de préparation LPBF séparée place le piston dans l'orientation
`roll_y_45` sur un plateau nominal Sapphire `Ø315 mm`, contrôle l'enveloppe et
passe OpenUSD minimum, NVIDIA Asset Validator, Geometry et Physics. Le piston
est présent dans le rendu aplati inspecté. Le recoater animé n'est qu'un guide :
la distorsion, les supports fournisseur et la collision recoater restent faux
dans les portes de validation.

Voir [le pipeline et le verdict détaillé](../AM_VALIDATION_PIPELINE.md),
[les résultats LPBF](../../twins/993-m64-60-piston-gallery-f0/evidence/lpbf-f0/)
et [le résumé Omniverse](../../twins/993-m64-60-piston-gallery-f0/evidence/simready-f0/).

## Reproduction logicielle

Le master build123d est exécuté dans l'image CAO `linux/amd64` fixée par digest :

```bash
docker run --rm --platform linux/amd64 -v "$PWD:/work" -w /work \
  ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57 \
  python parts/993-eng-piston-cp1-gallery-f0-0001/source/piston.py \
  --out parts/993-eng-piston-cp1-gallery-f0-0001/derived/piston_cp1_gallery_f0.step \
  --report parts/993-eng-piston-cp1-gallery-f0-0001/evidence/engineering-screen.json
```

## Gates suivants

1. Remplacer les charges F0 par un domaine virtuel approuvé avec enveloppes
   conservatrices, puis fixer des admissibles CP1 à chaud et un objectif de
   température de calotte ; aucune donnée supplémentaire n'est inventée.
2. Mesurer piston, axe, segments, cylindre, bielle et jeux du M64/60 exact ;
   relever profil de jupe, ovalisation, conicité, compression height et masses.
3. Mesurer pression cylindre transitoire, températures, flux, jet d'huile,
   capture, drainage, blow-by, cliquetis, survitesse et cycle d'usage.
4. Reconstruire les surfaces et tolérances, puis dimensionner calotte, bossages,
   gorges, jupe, galerie et ports avec keep-outs d'usinage.
5. Relancer PicoGK dans le seul domaine de conception autorisé, reconstruire
   chaque candidat retenu en BREP et exiger un maillage manifold convergé.
6. Remplacer le criblage linéaire séquentiel acquis par une FEA 3D non linéaire
   avec contacts et champs transitoires, puis corréler multibody,
   fatigue/fluage et CFD/VOF de l'huile sous accélération du piston.
7. Qualifier CP1 à chaud, orientation, supports, distorsion, traitement, HIP,
   fermeture des ports, CT, usinage, revêtement et coupons.
8. Effectuer preuve, cycles thermiques, fatigue grandeur réelle puis `200 h`
   moteur instrumentées avant toute décision véhicule.

PhysicsNeMo attend un dataset corrélé avec train, holdout et cas
hors-distribution. Le niveau asset SimReady est acquis, mais le test fonctionnel
Omniverse attend toujours les interfaces piston–segments–axe–bielle–cylindre–
soupapes mesurées. Ce STEP F0 n'est autorisé ni pour fabrication, ni pour
montage, ni pour mise en route moteur.
