# Deux programmes de ventilation améliorée : 993 et architecture 935

Périmètre confirmé le 3 octobre 2026 : deux projets distincts, avec réduction
de masse et augmentation de l'air utile envoyé sur le moteur dans les deux cas.
PicoGK sert à construire les géométries éditables ; les calculs et les mesures
établissent les caractéristiques et alimentent les jumeaux numériques.

| Programme | Architecture conservée | Objectif et dossier |
|---|---|---|
| `FAN-993-VERTICAL` | Rotor dans un plan vertical ; axe horizontal dans le repère moteur | Améliorer le ventilateur 993 et son fonctionnement dans le circuit moteur : masse, pales, débit utile et distribution. [Programme existant](../twins/993-engine-cooling-fan-system-f0/README.md) |
| `FAN-935-HORIZONTAL` | Rotor à plat au-dessus du moteur ; axe vertical dans le repère moteur | Recréer l'ensemble rotor, support, entraînement, carter et guides de l'architecture 935, puis l'améliorer avec matériaux, procédés et géométries actuels. [Recherche système](research/935-horizontal-cooling/README.md) |

Le programme 993 existant étudie une référence hypothétique Turbo M64.60 ;
la variante exacte et ses interfaces restent à qualifier avant une pièce
fonctionnelle. Pour le programme horizontal, le spécimen 935 de référence et
le moteur recevant la version améliorée doivent être explicités dans le
contrat d'installation. La cible finale ne découle pas du seul nom « 935 ».

## Référence et versions améliorées

Chaque programme possède une référence caractérisée, puis des variantes
`improved-*` avec géométrie, matériaux, interfaces et résultats propres.
La référence sert à mesurer les gains. Une région interne redessinée dispose
d'un statut de reconception ; elle n'est pas déclarée copiée du scan extérieur.

Les deux programmes peuvent partager outils, méthodes de calcul et essais.
Leurs paramètres, assemblages et champs de simulation restent associés à leur
identité. Les scans annoncés par le propriétaire comme pièces 935 alimentent
le programme horizontal ; leur ancien classement M64 ne démontre pas une
compatibilité 993.

## Mesurer les gains

Comparer séparément masse du rotor, inertie tournante et masse de l'ensemble,
avec bilan matière et composants normalisés inclus. Un rotor allégé peut
modifier les transitoires sans réduire autant la masse du système complet.

Comparer référence et variante à régime de rotor, densité d'air, circuit et
contre-pression cohérents. Publier débit, pression, couple, puissance et
répartition entre zones moteur. Une seconde comparaison à budget de puissance
commun permet d'évaluer le coût du gain de débit. Le rapport d'entraînement
établit le lien entre régime moteur et régime du rotor.

L'objectif porte sur l'air qui atteint les passages de refroidissement et sur
les températures correspondantes lorsque les charges thermiques sont connues.
Les mesures et les calculs doivent résoudre les gains au-delà de leurs
incertitudes. Aucun pourcentage de gain n'est fixé avant la référence mesurée.

Le propriétaire a retenu trois familles pour la fabrication additive des
versions améliorées : aluminium, magnésium et titane. Le
[dossier matière et procédé](research/935-horizontal-cooling/ADDITIVE_MATERIALS.md)
documente AlSi10Mg, WE43 et Ti64 comme candidats de départ. Le choix est
propre à chaque pièce et ne découle pas de la matière historique.

Le [rapport comparatif des alliages](../twins/fan-alloy-comparison-f0/README.md)
présente les calculs masse, inertie et centrifuge sur le rotor paramétrique
993, ainsi que les essais PicoGK de reconstruction volumique du scan 935.

| Levier d'amélioration | Effet à étudier | Contraintes à vérifier |
|---|---|---|
| Sections, corde, cambrure, vrillage et extrémités de pales | Débit, pression, rendement, recirculation et bruit | Racines, épaisseurs, centrifuge, jeu et fabrication |
| Structure des pales, moyeu et support | Masse, inertie et raideur | Déformation, modes, fatigue, températures et équilibrage |
| Matériau et procédé actuels | Masse et propriétés réalisables | État matière, défauts, traitements, inspection et interfaces |
| Carter, entrée et guides | Pertes et distribution sur le moteur | Encombrement, étanchéité et accès maintenance |
| Transmission et appuis du système horizontal | Pertes, masse et couple transmis | Denture, arbres, durée de vie, lubrification et chaleur |

Les variantes cherchent un compromis mesurable entre masse, air utile et
puissance consommée, sous les contraintes mécaniques et thermiques. Retirer
de la matière ou augmenter le régime ne démontre pas à lui seul l'amélioration
du refroidissement.

## Ordre du travail

1. Établir identités, unités, repères et contrats d'interfaces des deux projets.
2. Construire leurs références éditables, dont l'assemblage horizontal complet.
3. Caractériser ces références : géométrie, masse/inertie, entraînement,
   aérodynamique installée, structure, vibrations et thermique disponible.
4. Générer des variantes contrôlées et comparer les gains à conditions définies.
5. Confronter les variantes retenues aux essais et construire deux jumeaux
   associés aux bonnes géométries, conditions et mesures.

Le [plan horizontal](research/935-horizontal-cooling/RECONSTRUCTION_PLAN.md)
détaille la reconstruction et l'optimisation système. Le
[plan de validation 993](../twins/993-engine-cooling-fan-system-f0/program/VALIDATION_PLAN.md)
reste applicable aux preuves manquantes de ce programme. À cette date, les
audits et études exploratoires ne démontrent aucun gain de performance validé.
