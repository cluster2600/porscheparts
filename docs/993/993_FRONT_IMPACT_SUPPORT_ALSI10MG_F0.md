# Support d'impact avant 993 — concept AlSi10Mg F0

PorscheFanatics recoupe le `Lightweight Bumper Support 993` avant gauche ou
droit de FVD à **145 g**. La fiche FVD publie **139 × 100 × 53 mm** et indique
seulement aluminium. Aucun alliage, dessin, trou, interface, courbe
effort-course ou essai crash n'est disponible.

Le F0 conserve cette enveloppe et construit une topologie indépendante : une
plaque arrière de `3 mm`, une coque elliptique ouverte `60 × 38 mm` de `1,2 mm`
et quatre segments de cœur cruciforme décroissant de `1,4` à `0,8 mm`. Les
quatre canaux débouchent en face avant et ne piègent pas de poudre. Aucun trou
de montage n'est inventé.

## Pourquoi l'AM est testée

Le LPBF pourrait réunir plaque, coque et cœur gradué dans un seul BREP, avec une
progression d'écrasement impossible à obtenir par un simple tube. Il doit encore
battre un support aluminium extrudé ou assemblé sur la dispersion, le coût, la
réparabilité et surtout la courbe effort-course dynamique.

Le STEP pèse théoriquement `144,65 g`, soit `99,76 %` des `145 g` publiés. Cette
proximité est un objectif scalaire du concept, pas une preuve de géométrie ou de
performance crash.

## Criblages exécutés

Le rapport recalcule :

- aire de coque elliptique et aire des quatre épaisseurs de cœur cruciforme ;
- volume, masse `rho V` et comparaison aux `145 g` commerciaux ;
- contrainte axiale moyenne `F/A` et borne de plastification `A Rp0,2` ;
- flambement de plaques par
  `k pi² E/[12(1-nu²)] (t/b)²` pour coque et âme frontale ;
- inertie elliptique et borne d'Euler `pi² E I/L²` ;
- énergie synthétique `Fmean s`, vitesse équivalente `sqrt(2E/m)` et SEA ;
- premier mode d'une coque encastrée équivalente ;
- dilatation libre `alpha L delta_T` et capacité thermique ;
- BREP OCCT unique, enveloppe et relecture du STEP.

Sous `15 kN` synthétiques, la section minimale donne `59,03 MPa`; la borne de
plastification ambiante vaut `62,26 kN`. L'âme frontale donne `199,41 MPa` au
modèle de plaque, sous les `245 MPa` de comparaison, ce qui signale un possible
déclenchement progressif. Cela ne prédit pas un écrasement réel.

Le cas `15 kN × 80 mm` donne `1 200 J` par support et un équivalent énergétique
de `6,55 km/h` pour deux supports et `1 450 kg`. Ce n'est ni une procédure
réglementaire, ni une preuve de protection du véhicule ou des occupants.

## Gates obligatoires

1. Scanner le support, la caisse et la poutre ; mesurer les interfaces, trous,
   fixations, jeux et tolérances par variante.
2. Définir masse véhicule, barrière, pulse, intrusion, distribution de charge et
   critères réglementaires avec un ingénieur crash.
3. Qualifier l'AlSi10Mg LPBF en traction dynamique, anisotropie, rupture,
   porosité et sensibilité aux défauts.
4. Exécuter un modèle explicite non linéaire complet avec contacts, rupture,
   imperfections, convergence et courbe effort-course cible.
5. Contrôler poudre, orientation, supports, distorsion, CT, ressuage et
   métrologie sur lots représentatifs.
6. Tester coupons, écrasement quasi-statique, sous-système dynamique puis
   véhicule avant toute homologation.

PhysicsNeMo ne pourra servir de substitut qu'après constitution d'un ensemble de
cas explicites corrélés, avec incertitude et rejet hors domaine. SimReady attend
les interfaces, contacts et cartes matière. Fabrication, montage et roulage sont
interdits au stade F0.
