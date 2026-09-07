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

La pression projetée d'axe vaut `124,41 MPa`. Le modèle laminaire de galerie
donne Reynolds `515`, `0,866 m/s` et `1,21 kPa` de perte linéaire. À `5 kW`, le
débit hypothétique prendrait `88,24 K`. La conduction 1D fournit une borne haute
de `35,91 kW`, la dilatation libre du diamètre `0,455 mm` et le cycle de `100 h`
`40,32 millions` de tours.

Ces nombres sont des contrôles mathématiques reproductibles, pas une FEA, une
CHT, une CFD multiphasique ni une prédiction de durée de vie.

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

1. Mesurer piston, axe, segments, cylindre, bielle et jeux du M64/60 exact ;
   relever profil de jupe, ovalisation, conicité, compression height et masses.
2. Mesurer pression cylindre transitoire, températures, flux, jet d'huile,
   capture, drainage, blow-by, cliquetis, survitesse et cycle d'usage.
3. Reconstruire les surfaces et tolérances, puis dimensionner calotte, bossages,
   gorges, jupe, galerie et ports avec keep-outs d'usinage.
4. Corréler multibody, FEA 3D contact thermomécanique, fatigue/fluage et
   CFD/VOF de l'huile sous accélération du piston.
5. Qualifier CP1 à chaud, orientation, supports, distorsion, traitement, HIP,
   fermeture des ports, CT, usinage, revêtement et coupons.
6. Effectuer preuve, cycles thermiques, fatigue grandeur réelle puis `200 h`
   moteur instrumentées avant toute décision véhicule.

PhysicsNeMo attend un dataset corrélé avec train, holdout et cas
hors-distribution. SimReady attend les interfaces piston–segments–axe–bielle–
cylindre–soupapes mesurées. Ce STEP F0 n'est autorisé ni pour fabrication, ni
pour montage, ni pour mise en route moteur.
