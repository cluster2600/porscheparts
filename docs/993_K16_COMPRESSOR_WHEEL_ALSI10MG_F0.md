# Roue de compresseur K16 993 — concept AlSi10Mg LPBF F0

Une fiche fournisseur du K16 droit `53169886735` déclare pour la roue
`53241232006` un inducer de `40,6 mm`, un exducer de `60,5 mm` et `6 + 6`
pales. Elle ne donne ni profil, ni hauteur, ni moyeu, ni alésage, ni tolérance,
ni matière. PorscheFanatics situe les deux turbocompresseurs dans la chaîne
d'admission du 993 et recense des roues d'upgrade, mais aucune roue K16
fabriquée additivement.

Le F0 conserve donc uniquement les deux diamètres et le compte de pales. Son
disque de `3 mm`, sa hauteur de `18 mm`, son alésage de `6 mm`, son moyeu et ses
pales droites de `1,2 mm` sont des hypothèses indépendantes.

## Pourquoi étudier l'additif

Douze pales, leurs congés et le moyeu peuvent être produits et itérés sans
outillage de fonderie. Le LPBF n'est cependant pertinent que si une géométrie
optimisée ou des fonctions internes apportent un gain que l'usinage cinq axes
ne donne pas. La rugosité, les défauts, la distorsion et la tenue HCF peuvent au
contraire rendre le LPBF inférieur.

La comparaison obligatoire reste :

1. roue aluminium moulée et qualifiée ;
2. roue taillée cinq axes dans un lopin ;
3. roue AlSi10Mg LPBF, usinée, équilibrée et qualifiée en sur-vitesse/éclatement.

## Géométrie obtenue

Le STEP relu contient un solide BREP valide de `60,5 × 60,5 × 18 mm`, six pales
principales, six séparatrices et un alésage traversant. Son volume vaut
`12 248,31 mm³` et sa masse théorique `32,70 g`. Un cylindre enveloppe plein
pèserait `138,16 g`, soit un rapport de brut théorique de `4,22`. Ce cylindre
n'est pas un brut industriel ni une preuve économique.

## Point aérodynamique synthétique

À `330 K`, Mach périphérique `0,9` donne `327,75 m/s` et une vitesse dérivée de
`103 464 tr/min`. Pour un banc d'un moteur `3,6 l` à `5 750 tr/min`, remplissage
`0,95`, le débit géométrique vaut `0,08194 m³/s`. Avec un moyeu inducer supposé
de `12 mm`, la vitesse axiale vaut `69,35 m/s`, Mach `0,190`, Reynolds `281 588`
et le coefficient de débit `0,212`.

À rapport de pression `1,8` et rendement synthétique `0,72`, la température de
sortie calculée vaut `413,8 K`, le travail `84,23 kJ/kg`, la puissance par banc
`13,11 kW` et le couple `1,21 N·m`. Ce point n'est pas une carte K16 et ne traite
ni surge, ni choke, ni incidence, ni rendement réel.

## Criblage mécanique — F0 rejeté

Le disque tournant idéalisé atteint `119,4 MPa`, puis `171,9 MPa` à une
sur-vitesse de `1,2×`. La pale principale droite atteint `271,5 MPa` au point
nominal et `390,9 MPa` à la sur-vitesse. Face à la comparaison ambiante EOS de
`245 MPa`, le rapport n'est que `0,627` : **la topologie F0 échoue** et ne doit
pas passer en CFD/FEA détaillée sans redimensionnement.

La croissance élastique et thermique additionnée vaut `0,147 mm`, alors que le
jeu réel est inconnu. La borne thermique totalement contrainte vaut
`220,5 MPa`. Dix mg·mm de balourd produisent déjà `1,17 N`. L'énergie de rotation
approximative vaut `878 J` et le décompte atteint `620,8 millions` de tours en
`100 h`. Aucun de ces résultats ne prouve la tenue, l'équilibrage ou le
confinement.

## Reproduction logicielle

```bash
docker run --rm --platform linux/amd64 -v "$PWD:/work" -w /work \
  ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57 \
  python parts/993-eng-k16-compressor-wheel-alsi10mg-f0-0001/source/compressor_wheel.py \
  --out parts/993-eng-k16-compressor-wheel-alsi10mg-f0-0001/derived/compressor_wheel_alsi10mg_f0.step \
  --report parts/993-eng-k16-compressor-wheel-alsi10mg-f0-0001/evidence/engineering-screen.json
```

## Gates suivants

1. Scanner/CT la roue droite et gauche, puis mesurer profils, moyeu, alésage,
   écrou, arbre, backplate, diffuseur, carter, jeux et datums d'équilibrage.
2. Obtenir cartes compresseur, vitesses, pression/température, accélérations,
   surge/choke, balourd et cycle de service.
3. Reconstruire les pales avec surfaces aérodynamiques, congés, surépaisseurs,
   tolérances et interfaces réelles.
4. Faire CFD tournante avec convergence, puis FSI/FEA centrifuge-thermique,
   contact, rotor dynamique, Campbell, HCF et éclatement probabiliste.
5. Qualifier AlSi10Mg, orientation, supports, distorsion, traitement, HIP,
   finition de pales, CT, métrologie, équilibrage et spin proof.
6. Tester sur spin rig confiné, turbo au banc puis moteur, sous revue d'un
   spécialiste turbomachines.

PhysicsNeMo attend des cas CFD-structure-rotordynamique corrélés avec train,
holdout et hors-distribution. SimReady attend l'assemblage mesuré. Ce STEP F0
n'est autorisé ni pour fabrication, ni pour rotation, ni pour turbo ou moteur.
