# Système de ventilation horizontal Porsche 935

Recherche du 3 octobre 2026. Objectif confirmé par le propriétaire : faire le
reverse engineering de **tout le système horizontal de ventilation 935**,
puis en créer une version améliorée, plus légère, avec des pales mieux
structurées et davantage d'air utile sur le moteur. PicoGK sert à la géométrie,
les calculs physiques à sa caractérisation et les mesures à valider le jumeau.
Le [programme 993 vertical amélioré](../../FAN_DEVELOPMENT_PROGRAMMES.md)
constitue un projet distinct.

[Plan de reconstruction](RECONSTRUCTION_PLAN.md) ·
[Sources et limites](sources.json) · [Résumé des audits OBJ](scan-summary.json) ·
[Programme ventilateur existant](../../../twins/993-engine-cooling-fan-system-f0/README.md)

## Architecture documentée

Le plan du rotor est horizontal au-dessus du moteur ; son axe est vertical dans
le repère moteur. Gunnar Racing, qui montre l'installation sur deux moteurs
935, décrit une courroie entraînant un arbre horizontal, puis un renvoi à 90°
vers l'arbre vertical du ventilateur. Cette observation donne une architecture
de départ ; elle ne donne ni rapport, ni dimensions, ni denture du spécimen
scanné. [Source de l'atelier](https://www.gunnarracing.com/team/lola/stage4.htm).

```mermaid
flowchart LR
    E[Entraînement moteur] --> B[Courroie et poulies]
    B --> H[Arbre horizontal]
    H --> G[Renvoi à 90°]
    G --> V[Arbre vertical et moyeu]
    V --> R[Rotor dans un plan horizontal]
    S[Support et carter fixes] -. appuis .-> H
    S -. appuis .-> V
```

Ce schéma est fonctionnel, sans cotes et sans disposition interne présumée.
Le support reprend les efforts des arbres et des appuis ; il fait partie du
système mécanique à reconstruire. Le réseau aéraulique devra relier entrée,
carter/entonnoir, rotor, éléments fixes éventuels, guides, passages moteur et
sorties, avec sens de débit établi par observation.

Design911 décrit directement son produit de reproduction comme un entonnoir et
une roue pour ventilateur horizontal 935. Les matériaux annoncés concernent
ce produit commercial, pas le scan du propriétaire ni toutes les pièces
d'époque. [Fiche du produit](https://www.design911.co.uk/p/fan-housing-with-fan-blades-porsche-935/).

## Une variante et un spécimen à identifier

Porsche distingue plusieurs évolutions historiques. La 935/78 « Moby Dick »
possède des culasses quatre soupapes refroidies par eau et des cylindres
refroidis par air. Le périmètre thermique du ventilateur dépend donc de la
variante. [Porsche Heritage Moments](https://newsroom.porsche.com/en/2026/history/porsche-heritage-moments-935-norbert-singer-timo-bernhard-42018.html).

L'orientation horizontale est le besoin confirmé. Année, moteur, version
usine/Kremer/équipe, référence de chaque pièce et identité du donneur restent
à établir. La 935 de 2019 et les kits modernes ne servent pas à définir cette
géométrie. Les interfaces, nombres de pales et rapports 993 ne sont pas
transférés à la 935. Le moteur recevant la version horizontale améliorée reste
à fixer dans son contrat d'installation ; le projet vertical 993 garde son
propre assemblage et ses variantes.

## OBJ retrouvés sur le Mac

La recherche couvre récursivement Downloads local et iCloud Downloads, puis
les noms OBJ pertinents indexés par Spotlight sous le dossier utilisateur.
Ce périmètre ne prouve pas l'absence d'un fichier non indexé ou nommé autrement.
Les chemins complets, coordonnées et projections restent dans le dossier
privé `work/fan-935-plan-20261003/` du checkout principal.

| Fichier | Présence et intérêt | État vérifié |
|---|---|---|
| `Fan+0.5mm+back+not+lined+up+with+center.obj` | iCloud Downloads ; rotor candidat | 624 492 sommets ; 1 240 465 triangles ; ouvert |
| `Fan+Drive+0.21mm.obj` | Downloads local ; ensemble support/entraînement candidat | 1 256 836 sommets ; 2 484 656 triangles ; ouvert |
| `935+Xtreme+Cyl+head.obj` | Downloads local ; contexte géométrique éventuel | Présence constatée ; pas de qualification de compatibilité avec le système |
| `917+engine+case+w+cyl+0.5mm.obj` | iCloud Downloads ; contexte 917 | Présence constatée ; ne définit pas le montage moteur 935 |

Les deux scans principaux ont été relus sans soudure, réparation ni changement
d'échelle. Le rotor conserve 8 611 arêtes de bord et 26 faces d'aire nulle.
Le Fan Drive conserve 29 476 arêtes de bord, 200 cycles simples, une composante
de surface, aucune face dupliquée/nulle ni arête incidente à plus de deux faces.
Une composante topologique ne signifie pas une seule pièce mécanique.
Les auto-intersections du Fan Drive n'ont pas été contrôlées dans cette reprise.

Le hash du Fan Drive correspond au
[catalogue existant](../../../catalog/scans/scan-fan-drive-0p21mm.json), dont
le titre l'affecte au M64. Ce rattachement antérieur ne prouve pas son identité. Les anciens
comptes de bord/non-manifold diffèrent du nouvel audit des indices originaux ;
la cause n'est pas établie. Les anciens rapports restent intacts. Les unités
ne sont pas déclarées dans les OBJ et les suffixes des noms ne qualifient pas
leur précision. Voir le [résumé reproductible](scan-summary.json).

## Ce que les sources de scan établissent

Wolfe vend séparément [rotor](https://www.wolfeclassics.com/shop/p/porsche-935-fan-3d-scan),
[entraînement](https://www.wolfeclassics.com/shop/p/porsche-935-fan-drive-3d-scan),
[carter](https://www.wolfeclassics.com/shop/p/porsche-935-fan-housing-3d-scan)
et [guide](https://www.wolfeclassics.com/shop/p/porsche-935-air-guide-3d-scan).
Le vendeur présente le rotor comme assorti à l'entraînement ; leur appairage
physique reste à vérifier. Il décrit l'entraînement déposé pour entretien et
scanné extérieurement. Cela ne révèle pas automatiquement les dentures,
portées internes, précharges ou passages de lubrification.

Le carter est décrit comme un scan sommaire. La fiche titrée « 935 Air Guide »
décrit un guide **934** et propose des acquisitions dessus/dessous séparées.
Cette contradiction est enregistrée ; aucune équivalence 934/935 n'est admise.
Ces deux derniers fichiers n'ont pas été retrouvés dans les périmètres inspectés.
Aucun achat ni contact fournisseur n'a été effectué.

## Nomenclature de travail

Les identifiants ci-dessous désignent des fonctions à documenter. Ils ne sont
ni des références Porsche ni la preuve d'une architecture interne particulière.

| ID | Fonction/composant | Couverture actuelle et acquisition nécessaire |
|---|---|---|
| `935-COOL-ROTOR` | Rotor et pales | Scan présent ; dos, axe, matière et interfaces à qualifier |
| `935-COOL-HUB` | Moyeu et liaison rotor/arbre | Régions visibles à segmenter ; portée, fixation et tolérances à mesurer |
| `935-COOL-DRIVE-CASE` | Support/carter de transmission | Extérieur du Fan Drive ; fixations moteur et alésages internes à établir |
| `935-COOL-INPUT` | Arbre d'entrée et poulie | Observations extérieures ; diamètre primitif, clavette/cannelure et appuis à identifier |
| `935-COOL-BELT` | Courroie, poulies et tension | Profil, rapport réel, course/tension et pièces exactes inconnus |
| `935-COOL-GEARSET` | Transmission à angle droit | Type, géométrie, matériaux et jeux internes inconnus |
| `935-COOL-OUTPUT` | Arbre vertical et appuis | Interfaces extérieures candidates ; intérieur et reprise axiale à mesurer |
| `935-COOL-BEARINGS` | Roulements, retenues et joints | Références, fits, précharge, vitesse et lubrification inconnus |
| `935-COOL-LUBE` | Lubrification et étanchéité | Architecture, débit/huile éventuels et dissipation à établir |
| `935-COOL-INLET` | Carter/entonnoir et jeu rotor | Source publique repérée ; scan local non retrouvé |
| `935-COOL-GUIDES` | Éléments fixes, guides et distribution | Présence/type à constater ; guide commercial 934/935 ambigu |
| `935-COOL-MOUNTS` | Fixations, empilages et raccords moteur | Datums, axes, trous, faces, chemin des efforts et joints à relever |
| `935-COOL-COUPLING` | Accouplement souple | Reproduction EB identifiée ; emplacement, cotes et raideur du spécimen inconnus |
| `935-COOL-ALTERNATOR` | Alternateur séparé et intégration moteur | Application documentée chez les fabricants ; support, courroie et encombrement à établir |

Le [relevé des dimensions et détails](DIMENSIONS_AND_DETAILS.md) ajoute la
lecture de la fiche FIA 645 et de l'Annexe J 1976, les cotes PET 993 et les
informations des fabricants de reproductions. Le [registre](dimensions.json)
conserve chaque valeur avec sa portée et ses limites.

Le [relevé des matières](MATERIALS.md) distingue carters d'entraînement 935
usine en magnésium rapportés par l'atelier, reproductions aluminium et 7075,
conduits composites, ainsi que les applications Carrera/Turbo et les rechanges
993. Ces sources ne constituent pas une identification matière des deux OBJ.

Le [dossier de fabrication additive](ADDITIVE_MATERIALS.md) enregistre les
trois familles choisies par le propriétaire : aluminium, magnésium et titane.
Les premiers candidats sont AlSi10Mg, WE43 et Ti64, à comparer séparément
pour chaque pièce et procédé des versions améliorées 993 et 935.

## Préparation exécutée

Les deux scans ont été préparés en privé et importés dans le noyau natif
PicoGK 26.2.0, puis réexportés en OBJ. La connectivité a été vérifiée dans le
noyau et par un nouvel audit des exports. Les trous restent ouverts. Un
contrôle d'ajustement des seuls contours de bord ne trouve aucun cercle
répondant aux seuils diagnostiques ; cela ne signifie pas que les pièces
sont dépourvues d'alésages ou d'interfaces.

Le [résumé de préparation](preparation-summary.json) publie seulement les
empreintes, comptes et états. La [fiche technique de cette étape](../../../twins/935-horizontal-cooling-system-f0/README.md)
décrit les sources exécutables et les preuves restant à établir. Les
géométries préparées, transformations et rapports détaillés restent privés.

## Suite concrète

Le contrat d'interfaces est désormais défini ; ses cotes restent inconnues.
Le prochain lot doit établir échelle, segmentation mécanique et repères
physiques pour construire l'assemblage de référence. La reconstruction PicoGK, les maillages de
calcul et le jumeau utiliseront ce même assemblage et des identifiants de
géométrie communs. Les anciens calculs 993 paramétriques restent des outils
de méthode ; ils n'apportent aucune performance validée à ce système 935.
La référence reconstruite permettra ensuite de comparer les nouvelles pales,
l'allègement et les améliorations de transmission/distribution à conditions
de fonctionnement définies, avant leur intégration au jumeau.
