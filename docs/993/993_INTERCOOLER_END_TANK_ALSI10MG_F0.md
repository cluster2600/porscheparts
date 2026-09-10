# End-tank d'intercooler 993 Turbo — concept AlSi10Mg F0

TA Technix publie pour son intercooler aftermarket 993 Turbo deux noyaux de
`260 × 260 × 100 mm`, des raccords extérieurs de `66 mm`, un raccord intérieur
de `68 mm`, une largeur maximale de `860 mm`, une hauteur de `240 mm` et un
entraxe de montage de `690 mm`. Albert Motorsport recoupe les deux noyaux et
déclare un ensemble aluminium soudé. Ces fiches ne donnent aucun plan d'end-tank,
aucune orientation des trois dimensions ni aucune nuance d'aluminium.

PorscheFanatics situe le refroidissement de suralimentation air-air du 993
Turbo et ses charge coolers, mais n'apporte aucune cote. Le F0 interprète donc
`260 × 100 mm` comme une face de noyau et `66 mm` comme le diamètre extérieur
d'un raccord. Le raccord central de `68 mm`, le second noyau, les fixations et
la géométrie gauche/droite ne sont pas modélisés.

## Pourquoi l'additif a du sens ici

Le LPBF permet une transition continue ronde-vers-rectangle, trois guides de
flux intégrés et une bride dans une seule pièce ouverte et dépoudrable. Il faut
encore démontrer que ce bénéfice bat un end-tank en tôle aluminium soudée TIG ou
une pièce moulée sur débit, uniformité, masse, coût, inspection, réparabilité et
fatigue.

Le F0 possède une transition synthétique de `120 mm`, une paroi de `2,2 mm`,
trois guides ouverts de `1,5 mm`, une bride de noyau et un collet rond. La
matière candidate est l'AlSi10Mg LPBF ; l'alliage de l'intercooler commercial
reste inconnu.

Le STEP relu contient un solide BREP valide et un volume fluide connecté entre
la face rectangulaire et le port rond. Son enveloppe vaut
`134 × 274 × 114 mm`, son volume matière `226 936,46 mm³` et sa masse théorique
`605,92 g` à `2,67 g/cm³`. Ce n'est ni une géométrie OEM ni une pièce compatible.

## Criblages exécutés

Le cas synthétique prend `3,6 l`, `5 750 tr/min`, un rendement volumétrique de
`0,95`, `1,8 bar` absolu, `330 K`, une aire ouverte de noyau de `65 %`, une
pression relative de `0,8 bar`, `+100 K` et `100 h`.

Les équations quatre-temps et gaz parfait donnent `0,08194 m³/s` et
`0,1557 kg/s` par banc. La vitesse passe de `27,49 m/s` au raccord à
`4,85 m/s` sur l'aire ouverte du noyau, pour Reynolds `169 408`. L'écran
d'expansion brusque donne `487 Pa` et `39,9 W` perdus, avec une récupération
cinétique idéale de `696 Pa`. Ce n'est pas une CFD et le noyau réel est absent.

À `0,8 bar`, l'effort sur la face vaut `2,08 kN`, la membrane du raccord
`1,2 MPa` et le panneau guidé idéalisé `3,18 MPa`. La dilatation libre de la
bride vaut `0,575 mm`. La borne totalement contrainte atteint `147 MPa`, soit un
rapport de `1,67` face à la comparaison ambiante de `245 MPa`. Les
`51,75 millions` de pulsations calculées sur `100 h` ne donnent aucune durée de
vie faute de carte fatigue qualifiée.

## Reproduction logicielle

```bash
docker run --rm --platform linux/amd64 -v "$PWD:/work" -w /work \
  ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57 \
  python parts/993-eng-intercooler-end-tank-alsi10mg-f0-0001/source/end_tank.py \
  --out parts/993-eng-intercooler-end-tank-alsi10mg-f0-0001/derived/end_tank_alsi10mg_f0.step \
  --report parts/993-eng-intercooler-end-tank-alsi10mg-f0-0001/evidence/engineering-screen.json
```

## Gates suivants

1. Scanner l'ensemble gauche/droit et mesurer noyaux, ports, brides,
   soudures/brasages, fixations, flexibles, conduit de capot et jeux installés.
2. Mesurer débit, pression, température, uniformité, perte du noyau, transitoires,
   mouvement moteur, vibrations et cycles d'usage.
3. Reconstruire les deux end-tanks avec datums, tolérances, hose beads,
   surépaisseurs et interfaces d'assemblage réelles.
4. Comparer sans guides/avec guides par CFD RANS puis transitoire, CHT et FEA
   pression-température/modal/fatigue avec convergence.
5. Qualifier AlSi10Mg, orientation, supports, distorsion, traitement, usinage,
   soudure/brasage, CT, rugosité, fuite, épreuve et éclatement.
6. Corréler sur banc débit-pression-température, cycles et shaker avant dyno et
   véhicule sous revue d'ingénierie.

PhysicsNeMo attend un dataset CFD/CHT/structure corrélé avec train, holdout et
hors-distribution. SimReady attend l'assemblage mesuré. Ce STEP F0 n'est
autorisé ni pour fabrication, ni pour montage, ni pour mise en route moteur.
