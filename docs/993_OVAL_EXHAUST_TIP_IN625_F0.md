# Embout d'échappement ovale 993 — concept IN625 F0

FVD publie pour son jeu d'embouts inox `FVD11199300` une sortie de
**120 × 85 mm** destinée aux 993 étroites C2, C4 et RS. La fiche ne donne ni
diamètre d'entrée, ni longueur, ni angle, ni épaisseur, ni datum, ni tolérance.
PorscheFanatics recense séparément plusieurs échappements de 993 Turbo dont le
fabricant déclare l'IN625. Ce second fait justifie seulement l'étude matière ;
il ne transfère ni géométrie ni compatibilité à cet embout.

Le F0 est une transition indépendante ronde-vers-ovale de `120 mm`, avec un
conduit interne, une enveloppe externe de `0,8 mm` et huit attaches radiales.
L'entrefer reste ouvert aux deux extrémités, donc sans volume de poudre captif.
La sortie publiée est la seule dimension commerciale conservée ; l'entrée et
toute la construction interne sont des hypothèses révisables.

## Pourquoi l'AM est testée

Le LPBF permettrait de réunir le chemin de gaz, l'écran extérieur, les attaches
et une lame d'air ouverte dans un seul BREP. Cet intérêt de consolidation doit
encore battre un embout inox hydroformé ou soudé sur coût, masse, rugosité,
distorsion et endurance.

Le STEP pèse théoriquement `406,38 g` en IN625. Sans masse publiée du produit
FVD, cette valeur ne valide rien ; elle montre déjà que la double paroi IN625
n'est pas automatiquement une solution légère.

## Criblages exécutés

Le rapport recalcule :

- le volume de deux coques par intégration de `pi a(z)b(z)` et la masse `rho V` ;
- le débit quatre-temps à `3,8 L`, `6 500 tr/min`, rendement volumétrique `0,95`
  et deux sorties, puis la dilatation idéale du gaz de `300 K` à `850 K` ;
- continuité `u=Q/A`, densité idéale, Reynolds et borne de perte Borda-Carnot ;
- membrane mince `sigma=p r/t` et effort axial `p A` sous `30 kPa` synthétiques ;
- dilatation libre `alpha L delta_T` et borne bloquée `E alpha delta_T` ;
- rayonnement `epsilon sigma A(T⁴-Tamb⁴)`, résistance `t/k` et capacité `m cp` ;
- premier mode d'une bande encastrée équivalente ;
- BREP OCCT unique, enveloppe et relecture du STEP.

Le cas synthétique donne `107,05 m/s` à l'entrée, une borne d'expansion brusque
de `845,43 Pa` et `234,20 W`. Le vrai loft est progressif : ces deux dernières
valeurs ne sont pas sa perte CFD. La dilatation libre atteint `0,669 mm`; la
borne entièrement bloquée atteint `1 137,48 MPa`, au-dessus des `640 MPa`
ambiants de comparaison. Le mode de bande vaut `44,12 Hz`, mais ne représente
pas un mode de coque ou une excitation véhicule.

## Gates suivants

1. Scanner un embout et mesurer emmanchement, longueur, angle, collier, jeux et
   température de la jupe arrière.
2. Mesurer débit, température, pression et spectre pulsatoire sur le moteur
   réellement retenu.
3. Comparer inox formé/soudé, IN625 simple paroi et IN625 double paroi.
4. Exécuter CFD transitoire, CHT, coque/contact, modal et fatigue thermique avec
   cartes matière qualifiées.
5. Définir orientation, supports, surépaisseurs et compensation de distorsion,
   puis contrôler par métrologie, CT et ressuage.
6. Tester fuite, vibration, acoustique et cycles thermiques avant tout véhicule.

PhysicsNeMo attendra des cas CFD/CHT/structure ou des essais corrélés. SimReady
attendra l'interface mesurée et les propriétés chaudes qualifiées. Le STEP F0
n'est pas une pièce autorisée pour fabrication ou montage.
