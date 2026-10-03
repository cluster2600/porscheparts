# Reconstruction et amélioration du système horizontal 935

[Deux programmes distincts](../../FAN_DEVELOPMENT_PROGRAMMES.md) ·
[Dossier et nomenclature](README.md) · [Sources](sources.json)

Le résultat attendu est une géométrie source éditable de toutes les pièces
spécifiques, une nomenclature des composants normalisés, un assemblage avec
interfaces documentées, des calculs caractérisant le système et un jumeau
confronté aux mesures, pour une version modernisée, plus légère et envoyant
davantage d'air utile sur le moteur. Le spécimen fourni sert de référence de
départ ; une reproduction exacte et une reconception d'une zone non observable
ont des statuts distincts. Les lots ci-dessous caractérisent la référence et
les variantes améliorées avec les mêmes exigences de preuve.

## Lot 1 — Repères, segmentation et interfaces

Reprendre les deux OBJ présents en copies privées réversibles. Segmenter les
pièces mécaniques et les acquisitions sans éliminer les fragments inconnus.
Classer trous, surfaces absentes et intersections avant réparation. Identifier
les régions dos du rotor et l'empilage moyeu/arbre du Fan Drive.

Établir un repère moteur et des repères de pièces : axe de sortie vertical,
axe d'entrée, faces de fixation et référence angulaire. Les poses PCA privées
servent uniquement à l'inspection. Mesurer orthogonalité, entraxes et
transformations avant d'affirmer un assemblage commun.

Pour chaque interface de la nomenclature : côté source et côté récepteur,
axe/face/trous, cote nominale, tolérance, mode de fixation, charge transmise et
preuve indépendante. En priorité : rotor/moyeu/arbre vertical ; arbre/appuis ;
support/moteur ; poulie/arbre d'entrée ; carter/rotor ; guide/moteur.
Les surfaces non acquises restent absentes du contrat fonctionnel.

Obtenir unité d'export et au moins deux cotes de calibration par scan, avec
outil/incertitude. Le rotor et l'entraînement ne sont pas mis à l'échelle par
un ajustement visuel. Les scans de carter/guide et une vue de l'assemblage
monté complètent le lot lorsqu'ils sont accessibles. Le catalogue ou une
inspection démontée doit résoudre les interfaces cachées et pièces internes.

**Livrables :** registre des composants, matrice d'assemblage, contrat
d'interfaces, carte de couverture et liste d'acquisitions. **Passage :**
assemblage traçable sans contradiction d'échelle ni coordonnées inventées.

## Lot 2 — Reconstruction C# PicoGK et CAO exploitable

Réutiliser la chaîne C# PicoGK existante après témoin du runtime exact.
Reconstruire séparément rotor, moyeu, support/carter, arbres, poulies et
guidages avec paramètres issus des régions observées. Conserver distributions
de sections et surfaces fonctionnelles. La résolution voxel est soumise à
une étude sur trois pas ; les choix doivent résoudre les parois et jeux.

Les engrenages ne sont pas obtenus par copie de l'enveloppe extérieure.
Qualifier type, nombre de dents, rapport, module/géométrie, largeur, angle,
position des axes, jeux et processus avant leur définition. Avec ces données,
produire la source géométrique et les plans adaptés au procédé. Les roulements,
joints et courroies normalisés sont spécifiés par référence et interface ;
leur fabrication intégrale n'est pas supposée nécessaire.

Mesurer les écarts bidirectionnels entre reconstruction et scan sur les régions
observées, puis sections, épaisseurs, jeux et continuité. Les zones interpolées
ou redessinées disposent de leur propre statut et d'une justification.
Le budget d'erreur dépend de la métrologie ; aucune précision universelle
n'est promise d'après le nom du fichier.

**Livrables :** C#, paramètres, géométrie PicoGK, meshes et plans d'interfaces.
Compléter avec une reconstruction surfacique/BRep dans un outil CAD pour un
STEP exploitable ; l'enveloppe voxel ne remplace pas les tolérances d'usinage
ou la qualification d'une denture. **Passage :** fidélité, intégrité et
complétude des interfaces compatibles avec le calcul concerné.

## Lot 3 — Cinématique et transmission

Établir dimensions, nombre de pales, volume et distributions de sections.
Avec densité et matériau documentés : masse, centre de gravité et tenseur
d'inertie. Pour chaque régime du rotor, calculer vitesse périphérique, Mach,
Reynolds et fréquence de passage des pales ; laisser les entrées physiques
inconnues explicites et produire des scénarios séparés si nécessaire.

Établir sens de rotation et rapport global depuis diamètres primitifs de
poulies et rapport réel d'engrenage, avec convention explicite entrée/sortie.
Les rapports issus d'anciennes coupes M64 et les régimes de kits commerciaux
ne constituent pas les données de cette transmission.

Calculer vitesse du rotor et des arbres, inerties ramenées, couple aérodynamique,
accélérations/décélérations et efforts de courroie. Établir pertes et bilan
de puissance du moteur au ventilateur. Le couple demandé inclut la variation
d'inertie et les pertes, au-delà du seul régime stationnaire.

Après identification interne : charges radiales/axiales de denture,
flexion/torsion des arbres, contacts, tenue du carter, vis et appuis. Le
[cadre ISO 10300-1](https://www.iso.org/standard/79401.html) porte sur la capacité
de charge des engrenages coniques ; le texte complet et les parties applicables
restent à consulter pour l'engrenage retenu. Les fiches publiques ne sont pas
une preuve de conformité.

Définir fits, précharge/jeu, vitesse, durée de vie des roulements, lubrification,
étanchéité et dissipation du renvoi. Les méthodes
[ISO 281](https://www.iso.org/standard/38102.html) et
[SKF](https://evolution.skf.com/new-skf-engineering-software-for-the-evaluation-of-bearing-arrangements/)
sont des références de calcul, pas des références de pièces 935. L'édition et
les limites d'application doivent être figées au lancement du calcul.

**Livrables :** schéma cinématique, courbes de couple/régime, charges et
budget de pertes. **Passage :** entrées identifiées et résultats contrôlés
par calculs indépendants et mesures correspondantes.

## Lot 4 — Débit, distribution et refroidissement

Mailler l'assemblage rotor et pièces fixes avec sa vraie géométrie de carter,
jeux et obstacles. Un pilote isolé est utile pour vérifier la méthode ; il
n'est pas une prédiction du système installé.

Sous OpenFOAM, contrôler surfaces et maillage volumique avant solveur,
domaines tournant/fixe, interfaces, turbulence, couches limites et `y+`.
Faire d'abord un point pilote accepté, puis courbes débit/pression/couple et
puissance sur les régimes et contre-pressions utiles. Comparer trois
maillages, fenêtres de convergence, conservation et bilan énergétique ;
résoudre temporellement les interactions qui l'exigent.

Un modèle MRF peut servir aux caractéristiques moyennes ; une interface
rotative transitoire est nécessaire pour les interactions instationnaires
retenues. Qualifier compressibilité et modèle d'écoulement d'après les vitesses
et nombres sans dimension, avec famille/version OpenFOAM figée.

Inclure la résistance des guides et des passages moteur pour obtenir le point
installé et la distribution par zone/cylindre. Le calcul thermique dépend des
charges moteur, des surfaces d'échange et de la variante air/eau définie.
Conserver à part les échanges avec huile, intercooler ou refroidissement d'eau
s'ils ne font pas partie du réseau d'air documenté. Une orientation horizontale
ne démontre pas, seule, une meilleure répartition.

**Livrables :** courbes, champs natifs, répartition, pertes, températures et
incertitudes selon les données disponibles. **Passage :** fidélité du réseau,
convergence et accord aux mesures ; aucun ancien champ 993 n'est attaché à
la géométrie 935.

## Lot 5 — Résistance, vibration et fabrication

Sur l'assemblage qualifié, combiner centrifuge, pression, température,
entraînement, contacts et fixations. Vérifier racines de pales, moyeu,
arbres, carter/support et maintien des jeux. Convergence spatiale et distinction
entre singularités numériques et contraintes physiques sont nécessaires.

Effectuer modes précontraints en rotation et Campbell avec raideurs d'appuis,
effets gyroscopiques selon capacités du solveur, ordres moteur, passage des
pales et fréquence d'engrènement. Ajouter transitoires, fatigue et spectre
d'utilisation quand matériau, process, surface et données de fatigue sont
qualifiés. Prévoir équilibrage avec
[ISO 21940-11](https://www.iso.org/standard/54074.html) si le comportement rigide
est applicable ; ne pas imposer arbitrairement une classe d'équilibrage.

Définir pour chaque pièce son procédé : usinage, denture/traitement,
formage/composite ou fabrication additive lorsque justifiée. Documenter
matière, orientation, traitements, surépaisseurs, inspection et composants
normalisés. Le choix aluminium/magnésium/composite reste propre au spécimen
et à la conception qualifiée.

**Livrables :** champs mécaniques, dynamique, critères de fatigue et dossier
de fabrication/inspection. **Passage :** revue technique et plan d'essais
correspondant ; les essais en rotation restent sous responsabilité humaine.

## Optimisation après caractérisation de la référence

Définir des variantes contrôlées sur les sections, le vrillage, la cambrure,
les pieds et extrémités de pales, puis le moyeu, le support et les passages
d'air. Évaluer les matériaux et procédés actuels avec propriétés à température,
état de surface et capacité d'inspection. Les dentures, appuis et lubrification
peuvent être reconçus lorsque le bilan de pertes et les charges le justifient.

Mesurer masse du rotor et de l'ensemble, inertie, débit réellement distribué,
pression, puissance à l'entrée de transmission et températures pertinentes.
Comparer à mêmes régime rotor, air et réseau, puis à budget de puissance commun
si les variantes demandent des couples différents. Quantifier l'incertitude
des écarts. Aucune cible de gain chiffrée n'est inventée avant ces données.

Conserver les interfaces d'installation définies ou documenter explicitement
leur évolution. Recalculer structure, jeux à chaud/en rotation, modes et fatigue
pour chaque candidat retenu. Une forme allégée ou un matériau moderne ne suffit
pas à qualifier le gain global. Le résultat de ce lot est une comparaison
traçable et une variante candidate aux essais, avec ses compromis connus.

## Lot 6 — Validation et jumeau numérique

Définir des essais distinguant transmission, ventilateur sur banc et système
installé. Mesurer régime entrée/sortie, couple/puissance, température du
renvoi, débit/pressions, répartition thermique et vibration. Documenter
calibration, incertitudes et points indépendants de validation. L'éventuel
banc de survitesse/équilibrage nécessite enceinte et protocole appropriés.

Composer toutes les pièces confirmées dans OpenUSD avec unités, repères,
assemblage et liaisons cinématiques. Associer chaque résultat à son hash
géométrique, conditions, version solveur, matériaux et statut de validation.
Garder formats natifs et association cellule/point pour la revue Omniverse.

Inclure pertes de transmission et réseau thermique/aéraulique dans le modèle
système. Un modèle réduit peut interpoler les calculs acceptés dans leur
domaine de validité et être confronté aux capteurs. Une animation de roue
seule ne clôt pas ce lot.

**Livrables finaux :** sources et CAO, nomenclature, plans, dossier de calcul,
plan/rapport d'essais et package de jumeau. La validation physique demeure
ouverte si les mesures correspondantes ne sont pas disponibles.

## Première livraison géométrique

Le prochain lot exploitable sera l'assemblage rotor + support/entraînement
segmenté, ses repères et le contrat d'interfaces, suivi du premier générateur
PicoGK fondé sur le scan. Les pièces cachées et les guides auront des entrées
explicitement manquantes. Aucun solide plausible ne les remplacera dans un
assemblage déclaré complet.

Le brut, les dérivés et les paramètres issus de géométrie sous droits inconnus
restent privés. Le code générique et les rapports permis peuvent être
versionnés. Les modifications d'implémentation seront vérifiées par les
contrôles ciblés et `make check`, avec ressources existantes qualifiées et
pilotes avant toute campagne coûteuse.
