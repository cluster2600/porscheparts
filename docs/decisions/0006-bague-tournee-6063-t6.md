# 0006 — La bague sera tournée en 6063 T6

Date : 2026-09-11

Suite directe de [0005](0005-alsi10mg-nest-pas-un-choix.md), qui constatait que
l'AlSi10Mg de la bague n'avait jamais été choisi.

## Décision

Fabriquer `993-INT-SWITCH-TRIM-RING-F1-0001` par **tournage de barre en
EN AW-6063 T6**, finition anodisation brillante incolore. `preferred_process`
passe de `undecided` à `CNC`. Le LPBF reste au catalogue comme candidat screené —
les étapes 02, 03 et 04 gardent leur valeur documentaire — mais il n'est plus la
voie retenue.

## L'arbitrage réel

Le critère qui gouverne cette pièce est l'aspect. Sur ce critère, les deux
nuances candidates tirent en sens inverse.

| | 6063 T6 | 6061 T6 |
|---|---|---|
| anodisation brillante | **nuance de référence**, faible teneur en fer, surface uniforme | correcte, sans la qualité architecturale |
| tournage | tendre et collant, copeaux longs et filants | nettement plus agréable, copeaux courts |
| résistance | suffisante — la pièce ne porte rien | supérieure, sans utilité ici |

Le 6063 gagne parce que la seule exigence réelle est celle sur laquelle il est le
meilleur, et que son défaut — l'usinabilité — est une contrainte de paramètres,
pas une impossibilité : outil carbure non revêtu, arête vive et polie, grande
vitesse de coupe. Cette instruction est transmise au tourneur, qui peut la
contredire ; le devis demande explicitement le 6061 T6 chiffré en regard.

Le 6262 T6511, développé pour l'usinabilité par ajout de bismuth et de plomb, est
écarté : le plomb relève de la directive véhicules hors d'usage et de ses
exemptions, question que ce dépôt n'a pas instruite.

## Ce que changer de procédé n'a pas résolu

C'est le point important. La route tournage compte **cinq portes fermées** contre
sept pour le LPBF, mais les deux qui comptent sont les mêmes qu'avant :

- **la cote d'ajustement n'est pas tolérancée** — le Ø30,5 mm vient d'une page de
  vente d'une bague adaptable, pas d'une mesure du logement ;
- **les arêtes ne sont pas définies** — le maître est à arêtes vives, et une bague
  décorative se juge d'abord sur son arête avant.

S'y ajoutent la prise de pièce sur une paroi de 1,25 mm, soit 4,1 % du diamètre
extérieur, et la croissance d'anodisation de 5 à 15 µm, du même ordre que le jeu
recherché.

## La sortie proposée pour la cote d'ajustement

Sur une pièce tournée, la deuxième et la troisième coûtent une fraction de la
première. Le devis demande donc **trois bagues nues, non anodisées, à Ø30,40,
Ø30,50 et Ø30,60 mm**. On essaie, on garde, on n'anodise que la bonne en
retranchant alors la couche.

Cela ne remplace pas la mesure du logement, qui reste à faire. Cela permet
d'avancer sans métrologie du véhicule, ce qui est différent.

## Limite acceptée

La nuance d'origine de la bague reste inconnue. Le 6063 T6 est un choix du
dépôt appuyé sur le critère d'aspect, pas une identification de la pièce
commerciale. Rien de ce qui sortira de ce devis n'est conforme à l'origine, et
rien n'est autorisé au montage.
