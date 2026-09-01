# Plan de validation et d'amélioration

## Objectif

Construire un jumeau numérique capable de comparer des variantes sans confondre
une simulation avec une preuve de fonctionnement. Chaque résultat doit être
recalé par une mesure physique avant de servir à une décision de fabrication.

## Niveaux du jumeau

| Niveau | Modèle | Critère de passage |
|---|---|---|
| F0 | scan de référence | provenance et empreinte vérifiées |
| F1 | enveloppe et interfaces | échelle, datums et cotes physiques contrôlés |
| F2 | conduits et volumes internes | CT ou mesure destructive, domaines étanches |
| F3 | thermique et structure | matière, contacts et cas de charge justifiés |
| F4 | corrélation physique | banc de flux, pression et température corrélés |
| F5 | prototype métal | procédé qualifié, usinage et contrôles NDT réussis |
| F6 | essai moteur | protocole instrumenté et revue professionnelle |

## Batterie d'essais numériques

1. **Géométrie et métrologie** — carte d'écart scan/CAO, planéité, coaxialité,
   entraxes, épaisseurs minimales, collisions et tolérances d'assemblage.
2. **CFD froide** — perte de charge, coefficient de débit, uniformité de vitesse,
   séparation, swirl/tumble et sensibilité aux levées de soupapes.
3. **CFD compressible** — pression et température transitoires côté turbo ; ce
   cas exige les vraies lois de soupapes et conditions moteur, absentes à ce jour.
4. **Thermique conjuguée** — gaz, métal, sièges, guides, cylindre et refroidissement
   par air ; recherche des points chauds et gradients.
5. **Structure non linéaire** — serrage des goujons, contacts, pression cylindre,
   dilatation, déformation des sièges et plans de joint.
6. **Fatigue et fluage** — cycles thermomécaniques, fatigue haute et basse
   fréquence, maintien à chaud et marges sur défauts de fabrication.
7. **Modal et vibrations** — modes propres, excitation moteur et tenue des
   ailettes ou éléments minces.
8. **Fabrication additive** — orientation, supports, surépaisseurs d'usinage,
   retrait, distorsion, contraintes résiduelles, porosité et accessibilité des
   poudres prisonnières.
9. **Dynamique de soupape** — loi de levée mesurée, vitesse et accélération,
   contact came/linguet, marge avant flottement, rebond au siège, contraintes de
   gorge et de tête, sensibilité aux masses Ti-6Al-4V, acier et alliage nickel.
10. **Tribologie et gaz chauds** — jeu guide/queue, lubrification, frottement,
    usure de siège, oxydation et fatigue thermomécanique. Le Ti-6Al-4V ne passe
    côté échappement qu'après mesure des températures et essais dédiés.

## Boucle d'amélioration

Les variables de conception admises seront limitées aux zones dont la géométrie
est prouvée : évolution de section, rayon de court-circuit du conduit, transition
vers le siège, bossage de guide, ailettes et masses locales. Les objectifs seront
multi-critères : réduire la perte de charge et les points chauds sans dégrader la
vitesse utile, la combustion, la rigidité, la fatigue, l'usinabilité ou la masse.

Une variante n'est retenue que si elle améliore un front de Pareto et respecte
les contraintes. Une simple hausse du débit maximal n'est pas une optimisation
de culasse.

## Matières à comparer

L'aluminium doit rester la référence thermique tant que la matière d'origine
n'est pas identifiée. Le Ti-6Al-4V et l'Inconel 718 peuvent être modélisés comme
comparatifs, mais leur conductivité thermique beaucoup plus faible rend une
culasse complète susceptible de conserver davantage de chaleur. L'Inconel est
plus naturellement candidat près des gaz d'échappement très chauds ; le titane
peut être pertinent pour certains inserts ou éléments allégés. Aucun des deux ne
doit être choisi par défaut sans simulation conjuguée, architecture de siège et
stratégie de refroidissement.

## Validation physique avant essai moteur

1. scan CT de la pièce ou d'une culasse de référence pour les vides internes ;
2. maquette polymère pour assemblage et accessibilité, jamais pour fonctionnement ;
3. coupon matière imprimé avec la même machine, orientation et traitement ;
4. mesure dimensionnelle, densité, métallographie et éprouvettes mécaniques ;
5. inspection CT, ressuage et contrôle des filetages après usinage ;
6. épreuve de pression, étanchéité, cycles thermiques et banc de flux ;
7. essai sur banc moteur instrumenté, avec arrêt automatique et revue ingénieur.

## Données bloquantes

- variante exacte de moteur 993 cible et géométrie de référence ;
- unité du scan et au moins trois dimensions physiques de contrôle ;
- géométrie interne CT, sièges, guides, filetages et galeries ;
- matière originale, masse, état métallurgique et températures mesurées ;
- profils de cames, levées, régimes, débits, pressions et températures ;
- géométrie complète des soupapes, masses des coupelles/clavettes/ressorts,
  courbes force-course, jeux de guides et températures tête/queue ;
- pression cylindre résolue en angle vilebrequin et précharge des goujons ;
- capabilité réelle de la machine métal, traitements et usinages disponibles.
