# Feuille de route — de l'avant-projet à la monocoque finale 964/993

État de référence : **8 septembre 2026**, après la campagne F1 et le compte rendu
Vast versionné dans le commit `03473bbc93d825e45fc4e90da6be70ee5b233772`.

Objectif : développer une monocoque autoporteuse à structure primaire CFRP,
ses modules compatibles avec les configurations 964/993 retenues, ses moules,
son procédé de fabrication et les preuves nécessaires aux usages route et
circuit définis. Les étapes physiques ci-dessous sont planifiées ; leur
exécution et leur acceptation ne sont pas acquises.

Le [contrat de validation](engineering-validation-contract.json) conserve les
critères techniques et les autorisations. Cette feuille de route explique
l'ordre du travail, les dépendances, les livrables et les intervenants requis.
Elle ne change aucune autorisation de fabrication ou d'utilisation.

## Point de départ vérifié

| Domaine | Preuve disponible | Limite actuelle |
| --- | --- | --- |
| Architecture | Huit topologies comparées ; `all_carbon_multicell_x10` présélectionnée | Treillis F1 à propriétés isotropes équivalentes |
| Structure | 21 011,7 Nm/° dans le treillis ; contre-calcul CalculiX ; trois cas inertiels | Aucune rigidité réelle de coque multicouche démontrée |
| CAO | Cellule conceptuelle de 49 solides, deux jeux de modules de plateforme, enveloppes C2/C4 | Interfaces XYZ et tolérances de montage non fermées |
| Outillage | Dix éléments conceptuels, dont un mandrin de tunnel | Plans de joint, extraction, pression et thermique à valider |
| Fabrication | Deux cycles génériques sur témoins de 4, 8 et 12 mm | Les six cas échouent au critère thermique provisoire ; cinétique résine hypothétique |
| Vast / NVIDIA | Location et runtime vérifiés ; résultats récupérés et instances détruites lors de la campagne | Préflight bloqué par PyYAML avant inspection de l'USD ; aucune validation SimReady ni rendu OVRTX |
| Produit | Exigences et lacunes répertoriées | Aucun prototype de cette conception corrélé, aucune réception obtenue |

Sources : [structure](derived/structural-screening.json),
[contre-calcul](derived/calculix-verification.json),
[cas inertiels](derived/final-product-f1-screening.json),
[CAO](derived/cad-generation-report.json),
[fabrication](derived/manufacturing-process-screening.json),
[campagne Vast](evidence/vast-simready-execution-f1.json).
L'état Vast décrit cette campagne datée, pas un inventaire permanent du compte.

Le [visuel produit](derived/964-993-carbon-monocoque-clean-sheet-product-concept-v2.png)
est une illustration générative de direction de forme. Les surfaces mesurées,
la CAO paramétrique et leurs rapports d'écart feront autorité pour la pièce.

## Neuf étapes jusqu'à la version finale

Les responsables indiqués sont des rôles nécessaires ; aucune nomination,
commande fournisseur ou disponibilité de laboratoire n'est présumée.

### 1. Cahier des charges et voie de réception

- Figer pays d'immatriculation, carrosserie, millésimes, largeur, C2/C4,
  moteur/boîte, puissance/couple, pneus, aérodynamique et durée de vie cible.
- Définir précisément les **1 200 kg** : le contrat actuel retient un véhicule
  prêt à rouler sans occupant. Figer les conventions de carburant et fluides,
  puis les masses en charge, par essieu, le centre de gravité et les inerties.
- Faire examiner le remplacement de structure par l'expert de réception :
  classification du véhicule, identité, base réglementaire, configurations
  acceptées, preuves virtuelles recevables et essais physiques requis.
- Distinguer usage circuit loisir et compétition, puis identifier les
  exigences de l'organisateur ou du règlement choisi.

**Livrable et sortie :** cahier des charges versionné et programme d'essais
avec critères d'acceptation convenus. Pilotage projet, ingénieur véhicule,
expert de réception et interlocuteur circuit sont requis.

Le [pré-dossier allemand](tuv-precheck-de.md) prépare cette consultation.
TÜV SÜD recommande de discuter les transformations en amont. Le §21 StVZO
prévoit, pour sa procédure de réception individuelle, un rapport d'expert
présenté à l'autorité compétente. L'applicabilité à notre configuration doit
être confirmée ; conserver automatiquement le statut du véhicule donneur
n'est pas une hypothèse de conception admissible.
Sources officielles consultées le 8 septembre 2026 :
[TÜV SÜD](https://www.tuvsud.com/de-de/branchen/mobilitaet-und-automotive/tuning-eintragungen-und-aenderungsabnahmen/aenderungsgutachten),
[§21 StVZO](https://www.gesetze-im-internet.de/stvzo_2012/__21.html).

### 2. Métrologie et interfaces mesurées — F2

- Auditer les fichiers déjà disponibles : provenance, droits, variante,
  unités, échelle, complétude, incertitude et état du véhicule pendant le relevé.
- Exploiter le scan de dessous de 964 s'il est disponible et qualifié ; relever
  séparément les surfaces intérieures, ouvrants et points non observés.
- Mesurer les références de caisse, suspensions, direction, sous-châssis,
  supports moteur/boîte, sièges, retenues, charnières, gâches et vitrages.
- Couvrir les différences 964 C2, 964 C4, 993 C2 et 993 C4. Un relevé commun
  peut être réutilisé uniquement si l'équivalence est documentée ; les pièces
  et variantes manquantes nécessitent leur propre acquisition.

**Livrable et sortie :** rapport métrologique, repère et transformations par
variante, surfaces nominales, coordonnées et tolérances acceptées pour chaque
interface. Le métrologue et l'ingénieur d'intégration valident les écarts.
Les scans bruts, manuels et identifiants véhicule restent hors de Git.
Référence : [contrat d'interfaces](platform-interface-contract.json), porte G1.

### 3. CAO complète et intégration des quatre configurations

- Construire les masters éditables de plancher, tunnel, bas de caisse,
  cloisons, passages de roues, montants, pavillon et interfaces.
- Vérifier commande de boîte et accès au levier ; pour C4, tube/arbre
  longitudinal, joints, pont avant et demi-arbres avec leurs enveloppes en
  mouvement. Ajouter braquage, débattement et mouvement du groupe motopropulseur.
- Positionner freinage, carburant, faisceaux, frein à main, chauffage,
  refroidissement et protections thermiques ; vérifier démontage et inspection.
- Démontrer la faisabilité de la cellule commune et des modules distincts.
  Toute impossibilité mesurée entraîne une révision de cette architecture.

**Livrable et sortie :** assemblages cotés et rapports de jeux, tolérances,
interférences et maintenance pour chaque configuration. Le bilan de masse
inclut plis, âmes, adhésifs, inserts, revêtements et modules, avec incertitudes.
Référence : [contrat d'intégration](vehicle-packaging-contract.json).

### 4. Matières, stratification et assemblages

- Sélectionner fibre, résine, tissus, âmes éventuelles, adhésifs, inserts et
  isolants galvaniques avec un fabricant composite.
- Établir un zonage initial des plis : orientations, épaisseurs, recouvrements,
  arrêts de plis, renforts locaux et assemblages de la cellule autoporteuse.
- Tester coupons et détails avec le procédé envisagé : traction, compression,
  cisaillement, interlaminaire, trous, inserts, collages et dommages d'impact.
- Caractériser plusieurs lots et les environnements retenus : température,
  humidité, vieillissement, fluides et cycles thermiques.

**Livrable et sortie :** spécification matière-procédé et propriétés admissibles
documentées, puis premiers plans de stratification. Ingénieur composite,
fabricant et laboratoire portent les portes G2/G3. Les données provisoires
peuvent servir aux sensibilités, avec leur statut conservé.

### 5. Calcul du produit et optimisation — F3

- Remplacer les barres F1 par des coques multicouches et, selon les zones,
  des solides d'âme, joints, inserts, contacts et lois de dommage qualifiées.
- Appliquer les charges aux interfaces mesurées : torsion, flexion, bosse,
  freinage, virage, levage, remorquage, siège et ceinture, avec combinatoires.
- Étudier flambement, vibrations et fatigue ; traiter toit, intrusion et
  chocs selon le programme convenu, avec les composants de protection associés.
- Comparer formes et stratifications ; démontrer convergence, équilibre,
  sensibilités et marges avec des critères adaptés au composite et aux joints.

**Livrable et sortie :** dossier de calcul reproductible et revu, liste des
zones critiques et configuration candidate aux essais. Les portes G3/G4 et
la partie numérique de G5 restent distinctes des essais physiques de G7.
Référence : [plan de validation](validation-plan.md).

### 6. Simulation de fabrication et définition des moules

- Étudier drapabilité, angles de fibres après mise en forme, plis parasites,
  pontage, rayons, découpes et recouvrements sur les surfaces de l'étape 3.
- Identifier la cinétique résine par données fournisseur et essais DSC/DEA ;
  calculer cuisson, exothermie, gradients, compactage et effets du vide/pression.
  Une voie infusion/RTM nécessiterait aussi un modèle d'écoulement qualifié.
- Évaluer retrait, contraintes résiduelles et déformation après démoulage ;
  définir les compensations de moule à partir de résultats corrélés.
- Dimensionner secteurs, mandrin extractible, brides, joints, ports de vide,
  thermocouples, manutention, fermeture, extraction et accès aux contrôles.
- Préparer gabarits de collage, détourage, perçage et métrologie, puis tester
  panneaux et sous-ensembles représentatifs avant l'outillage complet.

**Livrable et sortie :** CAO/ plans d'outillage, gamme de fabrication et rapports
de simulation, avec preuves sur témoins. La sortie autorise uniquement la
fabrication d'outillage/prototypes explicitement revue. L'acceptation finale G6
requiert ensuite le premier article et la répétabilité du procédé.
Références : [moules](mold-plan.json),
[simulation de fabrication](manufacturing-simulation.json).

### 7. Fabrication et contrôle des prototypes

- Réaliser les outillages et premiers articles selon le dossier approuvé.
- Tracer lots, opérateurs, orientations de plis, collages, vide, pression,
  températures et temps de cycle ; conserver les coupons témoins.
- Mesurer masse, épaisseurs, surfaces et interfaces ; contrôler les défauts
  de stratifié et de collage par les méthodes CND retenues.
- Documenter chaque écart, sa disposition et les éventuelles reprises.

**Livrable et sortie :** dossier de premier article conforme, pièces identifiées
et rapports de contrôle. Le fabricant et la qualité clôturent les éléments G6
disponibles ; la répétabilité doit être démontrée sur plusieurs fabrications.

### 8. Corrélation physique et validation du véhicule — F4

- Mesurer torsion, flexion, modes propres, tenue des joints et fatigue ;
  réaliser les essais destructifs exigés sur détails, sous-ensembles et véhicule.
- Fixer les critères d'écart calcul/essai avant essais. Documenter le recalage
  et conserver un cas indépendant pour vérifier les prédictions finales.
- Répercuter toute correction sur la CAO, les plis, le procédé et le moule,
  puis répéter les essais concernés.
- Mener les essais du véhicule complet, dont comportement, freinage,
  endurance et exigences réglementaires retenues, sous le protocole approuvé.

**Livrable et sortie :** rapports physiques et corrélation acceptés, anomalies
closes, couverture des configurations justifiée. Ingénierie, laboratoire et
expert interviennent ; G5/G7 sont clos seulement avec les preuves requises.

### 9. Version finale, réception et maîtrise de production

- Figer les références et révisions de chaque configuration effectivement
  couverte ; toute extension 964/993 ou C2/C4 doit avoir sa justification.
- Obtenir les décisions route et circuit applicables à cette configuration.
- Établir contrôle de production, traçabilité, limites d'emploi, inspections,
  critères de dommage, réparation et fin de vie.
- Constituer le dossier final ci-dessous et organiser sa revue indépendante.

**Livrable et sortie :** configuration acceptée et dossier signé selon la porte
G8. La publication GitHub d'un dossier d'étude ne constitue pas cette réception.

## Dépendances et retour de la fabrication vers le calcul

Les étapes 1 et 2 démarrent en parallèle. Les coupons de l'étape 4 et les essais
de procédé peuvent commencer pendant la reconstruction CAO. Les étapes 3 à 6
forment une boucle de conception ; la fabrication complète attend leurs revues.

La liaison fabrication-produit est explicite : orientations obtenues après
drapage, épaisseurs compactées, géométrie après cuisson, propriétés du procédé,
défauts admissibles et contraintes résiduelles alimentent le modèle structurel.
Le premier article remplace ensuite les hypothèses par les valeurs mesurées.
Chaque transfert conserve sa provenance et son incertitude ; aucun défaut
simulé ou mesuré n'est effacé pour améliorer artificiellement les marges.

Une non-conformité de cuisson, de dimension, de fatigue ou de choc renvoie aux
étapes concernées. Le périmètre des nouveaux calculs et essais est documenté
avant de figer la révision suivante.

## Logiciels et calcul distant

La [pile du dépôt](../../docs/SOFTWARE_STACK.md) et le
[programme de simulation](simulation-program.json) décrivent les outils.

| Besoin | Voie prévue | Qualification à obtenir |
| --- | --- | --- |
| Scan et CAO | trimesh, PyMeshLab, build123d/OCCT ; revue FreeCAD ; STEP | Échelle, interfaces, écarts scan/CAO et validité des masters |
| Structure | Gmsh, CalculiX ; Code_Aster comme option de contre-calcul | Éléments et lois adaptés, cas de référence, convergence et corrélation |
| Choc | OpenRadioss proposé dans le plan de validation | Chaîne explicite, matériaux, contacts et modèles de test à qualifier |
| Fabrication | Scripts thermiques F1 existants ; outils détaillés de drapage/cuisson à sélectionner | Modèles à qualifier sur le matériau, le procédé et les témoins réels |
| Lecture des résultats | meshio, PyVista, ParaView | Unités, repères et champs rattachés au bon calcul |
| Revue du jumeau | OpenUSD, Omniverse, SimReady | Préflight, validations d'actif et rendu traçable |
| Accélération par IA | PhysicsNeMo, après constitution du corpus | Calculs de référence convergés, données corrélées, validation indépendante et hors domaine |

La machine est choisie selon les besoins CPU, RAM, GPU et stockage du logiciel
réellement lancé. Aucune accélération GPU des solveurs n'est supposée.
Les versions et licences des outils supplémentaires seront contrôlées avant
intégration ; aucun outil de fabrication détaillée n'est déjà qualifié ici.

Pour la reprise Vast, corriger d'abord le couple interpréteur/PyYAML et tester
le préflight dans l'environnement cible préqualifié. Réconcilier la dernière
tentative incertaine, puis vérifier image immuable, clé SSH, entrées, budget,
récupération et destruction avant tout nouvel essai payant. Le
[rapport d'état](simready-readiness.json) reste bloqué tant que ces preuves
manquent. La location précédente ne valide aucun calcul produit ou procédé.

## Prochain lot de travail

Ces actions sont **à faire**. Leurs critères de sortie sont distincts de la
simple création d'un document ou d'un script.

| Priorité | Action | Livrable et critère de clôture | Dépendance externe |
| --- | --- | --- | --- |
| P0 | Consolider le dossier de préconsultation TÜV | Configuration proposée, questions ouvertes, puis réponse écrite sur procédure et essais | Expert et choix du pays/configuration |
| P0 | Auditer fichiers et mesures disponibles | Matrice par interface et variante : acquis, incertain, manquant, méthode d'acquisition | Accès aux sources et métrologie |
| P0 | Qualifier et intégrer le scan de dessous de 964 | Contrôle d'échelle, repères, couverture, incertitude et rapport d'écart | Fichier et métadonnées si absents |
| P1 | Préparer les acquisitions 993 et différences C2/C4 | Liste minimale de relevés et pièces couvrant toutes les interfaces manquantes | Véhicules/pièces et métrologue |
| P1 | Préparer le programme matériaux/procédé | Matrice d'essais, options fournisseur et devis avant sélection | Fabricant composite et laboratoire |
| P1 | Corriger et préqualifier SimReady | Préflight reproductible réussi et tentative Vast réconciliée | Runtime cible ; location uniquement après préparation |

La suite immédiate attend un premier dossier F2 d'interfaces vérifiées et la
voie de réception documentée. Les tâches numériques indépendantes peuvent
progresser pendant l'acquisition des mesures et les consultations.

## Contenu exigé de la version finale

- [ ] Masters CAO éditables et STEP de la coque, modules et interfaces acceptés.
- [ ] Plans cotés, tolérances, masse/bilan véhicule et nomenclature par variante.
- [ ] Plans de plis, renforts, âmes, inserts, collages et protections.
- [ ] Moules, mandrins, gabarits et plans de contrôle révisés.
- [ ] Matières et procédé qualifiés, gamme, traçabilité et critères de défauts.
- [ ] Calculs reproductibles, convergence et correspondance avec la pièce fabriquée.
- [ ] Rapports d'essais physiques, corrélation et résolution des non-conformités.
- [ ] Réception routière et décision circuit correspondant au périmètre annoncé.
- [ ] Notices de montage, inspection, maintenance, réparation et limites d'emploi.

Le budget et le calendrier restent **à chiffrer** après clarification de la
réception, des acquisitions et des essais destructifs. Les devis devront
séparer métrologie, études, matériaux/coupons, outillage, prototypes, calcul,
laboratoire et réception, en prévoyant les itérations. Le faible coût de la
campagne Vast F1 ne représente pas le coût du développement du produit.
