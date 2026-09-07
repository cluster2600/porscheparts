# Culasses 917/30 turbo F45 — autorité bi-architecture

F45 verrouille deux produits distincts pour le moteur 5,374 L biturbo : une
culasse à deux soupapes servant de témoin morphologique et une culasse à quatre
soupapes optimisée. La cible de 1 600 hp reste une exigence non prouvée.

## Suppression de l'ovale

L'enveloppe elliptique créée par `ellipse_volume` dans le prototype F39 est
rejetée. Elle ne venait pas du scan et ne peut plus être utilisée pour le corps
ou les ailettes. Toute reconstruction suivante doit suivre les contours du
scan, conserver les interfaces visibles et justifier numériquement chaque
modification locale.

## Refroidissement rendu possible par le LPBF

La culasse reste refroidie par air et huile. La fabrication additive doit être
exploitée pour créer des passages d'air traversants et dépoudrables, des
sections autoportantes en goutte ou losange, des ailettes à pas et épaisseur
variables, ainsi que des réseaux ouverts de picots autour du pont
d'échappement et de la bougie. Les nervures conductrices doivent relier ces
zones chaudes aux bancs d'ailettes parcourus par le débit le plus élevé.

Une cavité fermée, une chemise d'eau, un canal impossible à contrôler par CT ou
une réduction de paroi non qualifiée ferme la porte de fabrication.

Un circuit d'huile secondaire dessert la distribution, les guides et les zones
chaudes côté échappement. Il comporte une galerie pressurisée, des jets calibrés
et des retours gravitaires/scavenge vers le carter sec. Les passages imprimés
doivent rester traversants, nettoyables et contrôlables par CT, avec des accès
d'usinage et de bouchonnage. Il ne remplace pas le refroidissement principal par
air et ne forme jamais une chemise fermée autour de la chambre.

## Validation exigée

Les architectures 2V et 4V utilisent les mêmes conditions turbo. Chaque
résultat critique demande trois niveaux de maillage et une seconde méthode
indépendante. Les seuils initiaux sont 1 % pour les bilans masse/énergie et 5 %
pour la convergence de maillage et l'écart entre méthodes. Ces seuils sont des
portes numériques, pas une homologation physique.

```bash
python3 twins/reference-917-engine/source/validate_head_architecture_authority_f45.py \
  --project-root .
```

Tant que les cartes matière à chaud, la simulation LPBF, le contrôle CT/CND,
les bancs de flux et moteur et la revue professionnelle ne sont pas exécutés,
les deux autorisations d'impression métal restent fermées.
