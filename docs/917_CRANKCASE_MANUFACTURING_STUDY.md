> **Archive documentaire importée le 6 septembre 2026 depuis iCloud.**
> Cette étude décrit un autre état du dépôt (commit cité ci-dessous). Ses contrats
> F32–F46, choix de variantes et objectif en hp ne remplacent pas les paramètres
> actifs de ce checkout. Références externes non revérifiées lors de cet import.
> Voir [le bilan d’intégration](ICLOUD_PORSCHE_IMPORT_2026_09_06.md).

# Étude de faisabilité — bloc du flat-12 917 modernisé

**Projet :** `cluster2600/3dprinting993` · **Date :** 5 septembre 2026 · **Version :** 1.0

**Objet :** développer les deux demi-carters structurels d’un moteur inspiré de la Porsche 917, modernisé pour 2026, et comparer leur fabrication par impression métallique, fonderie et usinage. Cette étude prépare une décision technique ; elle ne constitue ni une CAO de définition ni une validation moteur.

## 1. Décision proposée

**Ouvrir une étude comparative des deux demi-carters en aluminium LPBF, avec finition par usinage, face à une version aluminium coulée et une version usinée dans la masse.** Le titane reste une variante à justifier par les calculs ; aucun matériau n’est sélectionné pour fabrication.

L’impression directe d’un carter ou d’un bloc automobile a des précédents industriels. La question propre au projet est désormais de démontrer la géométrie, la rigidité des paliers, la stabilité thermique, la propreté des galeries et la durée de vie du flat-12 visé. Le nombre de cylindres ou l’existence d’un fichier STL ne répond pas à ces questions.

La priorité de développement proposée est un **secteur représentatif réunissant un logement de palier, un registre de cylindre, une liaison entre demi-carters et une galerie d’huile**, puis la paire complète. Le secteur réduit l’engagement du premier essai ; il ne remplace pas le contrôle de la distorsion d’un carter complet ni ses modes vibratoires.

## 2. Référence exacte du projet GitHub

Les contrats F43, F34a, F19, F41 et F46 ont été consultés sur la branche `main`. La copie locale utilisée pour les lectures complémentaires est au commit `6e987d1cecc45a65b35e78cc346af00c7bc64523`, daté du 4 septembre 2026. Le dépôt contient aussi des travaux antérieurs sur la 993 : ils ne définissent pas ce nouveau bloc.

| Paramètre | Atmosphérique 2026 | Biturbo 2026 |
|---|---|---|
| Architecture | 12 cylindres à plat | 12 cylindres à plat |
| Cylindrée documentaire | 4 999 cm³ | 5 374 cm³ |
| Alésage × course | 86,8 × 70,4 mm | 90 × 70,4 mm |
| Puissance | Non fixée par F43 | Objectif de 1 600 **hp mécaniques** |
| Distribution envisagée | Quatre soupapes par cylindre | Quatre soupapes par cylindre |
| Cœur moteur | Air forcé et huile | Air forcé et huile |

Les valeurs d’alésage et course sont des paramètres de conception documentaires. Elles ne fournissent ni les entraxes, ni les ajustements, ni les épaisseurs du futur carter. La branche historique 4,5 L ne doit pas être utilisée silencieusement pour générer le produit atmosphérique 5,0 L. [Contrat F43](https://github.com/cluster2600/3dprinting993/blob/6e987d1cecc45a65b35e78cc346af00c7bc64523/twins/reference-917-engine/variant-authority-f43.json).

**Le refroidissement du cœur reste strictement air/huile.** Les circuits liquides auxiliaires éventuels concernent la charge d’admission et, sous étude séparée, les paliers des turbos ; ils ne créent pas de chemise d’eau dans le bloc. Les études antérieures de culasses refroidies par eau sont remplacées pour cette décision. [F34a](https://github.com/cluster2600/3dprinting993/blob/6e987d1cecc45a65b35e78cc346af00c7bc64523/docs/917_AIR_OIL_CORE_CONTROLS_F34A.md).

Le routage F19 classe actuellement `crankcase_half`, quantité documentaire 2, comme candidat conventionnel issu d’une disposition « cast ». La nuance, le procédé et les tolérances sont vides. F13 évoque une famille historique magnésium et ne retient AlSi10Mg que pour une maquette hors moteur. **Proposer aujourd’hui un carter aluminium fonctionnel LPBF est donc une nouvelle branche d’étude**, pas la confirmation d’une sélection déjà faite. [F19](https://github.com/cluster2600/3dprinting993/blob/6e987d1cecc45a65b35e78cc346af00c7bc64523/twins/reference-917-engine/manufacturing-routing-f19.json), [F13](https://github.com/cluster2600/3dprinting993/blob/6e987d1cecc45a65b35e78cc346af00c7bc64523/twins/reference-917-engine/manufacturing-validation-f13.json).

F41 inventorie 138 familles, mais son générateur ne couvre que six familles du train mobile ; les demi-carters n’en font pas partie. Les vues et le scan extérieur existants ne constituent pas leur CAO fonctionnelle. [F41](https://github.com/cluster2600/3dprinting993/blob/6e987d1cecc45a65b35e78cc346af00c7bc64523/docs/917_COMPONENT_FACTORY_F41.md).

## 3. Réalisations industrielles et fenêtre des six derniers mois

Fenêtre de recherche : **du 5 mars au 5 septembre 2026**. Une date d’article établit une publication récente ; elle ne date pas nécessairement la fabrication ou l’essai. La recherche ciblée ci-dessous n’est pas un inventaire exhaustif des projets confidentiels.

| Cas | Pièce et procédé documentés | Niveau de preuve public | Utilité pour le 917 |
|---|---|---|---|
| **Bosch / Nikon SLM**, publication du **22 juin 2026** | Bloc V8 monobloc en AlSi10Mg, imprimé sur NXG XII 600 à Nuremberg | Fabrication annoncée par le fabricant ; l’article ne donne pas de résultat chiffré de banc ni d’endurance. La date exacte de fabrication n’est pas précisée. | Précédent direct pour un grand bloc métallique complexe. [Source Nikon](https://nikon-slm-solutions.com/addictive-additive/printing-a-v8-how-nikon-slm-solutions-and-bosch-are-pushing-additive-manufacturing-into-automotive-production/) |
| **FEV / LeiMot**, projet antérieur ; brochure version **20 janvier 2026** | Carter, bedplate et culasse automobiles conçus pour l’additif aluminium | FEV rapporte la validation de prototypes au banc moteur et 20–30 % de réduction de masse pour carter et culasse par rapport aux références. Pas de durée d’endurance détaillée dans la brochure. | Précédent de développement et d’essais, avec géométrie et refroidissement différents. [Brochure FEV](https://www.fev.com/app/uploads/2026/08/FEV_propulsion_LightweightDesignAdditiveManufacturing.pdf) |
| **SZEngine / Audi Hungaria**, **10 octobre 2018** | Deux demi-carters, cylindre et autres pièces d’un monocylindre, fusion laser sur SLM280 | Usinage, mesures, essais au banc et installation dans une voiture d’essai rapportés | Architecture assemblée utile à comparer, échelle différente. [Source constructeur](https://nikon-slm-solutions.com/newsroom/worlds-first-3d-printed-formula-student-racing-engine-produced-on-slm280-machine/) |
| **Gray et al.**, **2023** | Carter en titane et culasse en aluminium d’un petit moteur thermique, LPBF | Contrôles tomographiques, reprises d’usinage et fonctionnement après remontage | Faisabilité sur petit moteur ; aucune preuve de transposition au flat-12. [Publication scientifique](https://doi.org/10.1016/j.jmapro.2023.04.054) |

La brochure FEV est hébergée dans un chemin comportant `2026/08`, mais porte `v20260120`. Elle ne doit pas devenir artificiellement une réalisation nouvelle d’août 2026. Elle complète en revanche notre précédente source LeiMot de 2020, qui annonçait encore les futurs essais quatre cylindres.

**IA :** ces sources ne démontrent pas conjointement « bloc fabriqué pendant ces six mois, fonctionnement validé et contribution explicite d’une IA ». L’optimisation topologique, les simulations et le traitement logiciel des données ne suffisent pas à prouver l’emploi d’apprentissage automatique. L’usage de l’IA dans notre programme est défini séparément en section 8.

Une évolution récente utile est l’annonce **EOS–Constellium du 7 juillet 2026**, avec introduction de CP1 dans le portefeuille EOS et disponibilité annoncée en août. Elle élargit les possibilités de qualification d’un procédé aluminium ; elle ne valide pas ce matériau pour notre carter. [Communiqué EOS](https://www.eos.info/press-media/press-center/press-releases/2026/strategic-partnership-with-constellium).

## 4. Comparaison des procédés

Les appréciations suivantes sont des recommandations d’ingénierie pour organiser les essais, et non des performances déjà obtenues sur le projet.

| Route candidate | Intérêt à vérifier | Difficultés à quantifier | Place dans l’étude |
|---|---|---|---|
| **LPBF aluminium + usinage** | Galeries intégrées, renforts localisés, itérations sans outillage de fonderie | Distorsion, défauts, fatigue, dépoudrage, supports, répétabilité entre zones laser | Candidat principal de recherche |
| **Fonderie aluminium + usinage** | Référence industrielle et potentiel économique en petite série | Noyaux, retrait, défauts de coulée, coût d’outillage et modifications | Comparateur obligatoire |
| **Usinage aluminium dans la masse** | Accès direct aux surfaces fonctionnelles et matière issue d’un produit métallurgique défini | Accès outils, matière retirée, galeries percées et bouchons, assemblages supplémentaires | Comparateur prototype et petite série |
| **Fonderie avec moules/noyaux imprimés en sable** | Modifier des volumes internes avec un outillage numérique | Contraintes de coulée et de nettoyage conservées | Variante du comparateur fonderie ; le métal du bloc n’est pas imprimé |
| **DED / WAAM + usinage** | Ébauche de grande taille et dépôt local de matière | Distorsions, résolution des détails, reprises lourdes et galeries complexes | Second rang, si le LPBF devient défavorable |
| **LPBF titane + usinage** | Hypothèse de matériau à comparer si une fonction précise le justifie | Couple rigidité–masse, dilatations différentielles, transfert thermique, usure et coût complet | Pas de sélection par simple préférence pour le titane |

La fonderie et l’usinage pourront nécessiter une géométrie différente. Comparer des **fonctions et interfaces équivalentes** : même spectre d’efforts, même durée de vie, même étanchéité et même rigidité admissible des logements. Copier une forme optimisée LPBF dans une route conventionnelle peut fausser la comparaison.

Conserver initialement **deux demi-carters démontables**, sans imposer aujourd’hui l’orientation du plan de joint. Leur découpage, la ligne de paliers et l’accès au train mobile doivent être définis ensemble. Une éventuelle segmentation supplémentaire pour entrer dans une machine crée des assemblages structuraux à étudier ; elle ne doit pas servir de simple raccourci d’impression.

## 5. Matières : liste courte et données à demander

| Candidat | Rôle proposé | Condition pour progresser |
|---|---|---|
| **AlSi10Mg LPBF** | Référence additive de départ, soutenue par le précédent Bosch/Nikon | Données de la machine, orientation et traitement réellement proposés ; fatigue et stabilité à la température du carter |
| **AlF357 LPBF** | Comparateur aluminium supplémentaire | Offre industrielle, propriétés et capabilité du procédé exact |
| **Aheadd CP1** | Candidat à examiner pour le compromis thermique et industriel | Vérifier notamment que la rigidité et la fatigue conviennent aux paliers ; la disponibilité d’une poudre n’est pas une qualification |
| **Aheadd HT1** | Option à examiner si la température du carter justifie un candidat à chaud | Courbes matière et traitement complet, données de fatigue/fluage et disponibilité sur grande machine |
| **Aluminium de fonderie / produit corroyé** | Références conventionnelles distinctes | Choisir la nuance après chargements, épaisseurs et stratégie de fabrication |
| **Titane** | Variante exploratoire | Démontrer un avantage de la pièce complète, avec assemblages et surfaces fonctionnelles |

Le dossier matière du dépôt compare déjà plusieurs aluminiums pour une **culasse**. Sa préférence provisoire pour HT1 et ses températures de calcul ne sont pas transférables au carter. Le carter doit recevoir son propre champ thermique, ses propres efforts de paliers et son propre état métallurgique. [Étude matière F42.2](https://github.com/cluster2600/3dprinting993/blob/6e987d1cecc45a65b35e78cc346af00c7bc64523/docs/917_F42_2_MATERIAL_PROCESS.md).

Pour chaque combinaison matière–machine–traitement, demander : élasticité et dilatation en fonction de la température, traction, fatigue HCF/LCF, fluage si pertinent, conductivité, défauts caractéristiques, état de surface, stabilité après traitement et reprise, effets de l’huile et des contacts avec inserts/vis/coussinets. La matière historique magnésium reste une référence documentaire, pas un jeu de propriétés calculables pour le nouveau moteur.

## 6. Définition du bloc et efforts à reproduire

Le développement peut combiner des interfaces mesurées sur un moteur de référence et des interfaces entièrement reconçues. Pour les secondes, produire une justification de dimensionnement et un contrôle d’assemblage ; ne pas les présenter comme des cotes historiques.

| Interface ou entrée | Livrable nécessaire | Conséquence sur la fabrication |
|---|---|---|
| Ligne des huit paliers | Positions, diamètres, largeurs, jeux, coussinets et références d’usinage | Reprise et contrôle de la ligne assemblée |
| Douze registres de cylindres | Entraxes, axes, appuis, fixations, étanchéité et dilatation | Usinage des logements et contrôle de géométrie |
| Liaison des demi-carters | Plan de joint, pions, boulons, précharges, états de surface | Accès outils, stabilité après serrage, absence d’ouverture en charge |
| Prise de puissance et distribution | Architecture retenue, engrenages, efforts et encombrements | Renforts locaux, logement et accessibilité |
| Huile et ventilation | Pressions, débits, viscosité, récupération, désaération et blow-by | Galeries accessibles au nettoyage et à l’inspection |
| Fixations moteur / banc / transmission | Charges, rigidités de liaison, interfaces et dilatations | Représentation correcte des conditions aux limites |
| Cycle de fonctionnement | Régimes, charge, démarrages, transitoires, durée de vie souhaitée | Calculs de fatigue, stabilité thermique et plan d’endurance |

Ces inconnues sont cohérentes avec le [registre F16](https://github.com/cluster2600/3dprinting993/blob/6e987d1cecc45a65b35e78cc346af00c7bc64523/twins/reference-917-engine/kinematic-interface-readiness-f16.json). Le scan extérieur et les photos servent à la forme générale, pas à déterminer un jeu de palier ou une précharge.

### Vérification d’ordre de grandeur

En reprenant **uniquement comme hypothèse** le point F32 de 1 600 hp à 9 000 tr/min et la géométrie biturbo F43 :

| Grandeur calculée | Valeur arrondie |
|---|---:|
| Puissance cible convertie | 1 193,1 kW |
| Couple correspondant | 1 265,9 N·m |
| Pression moyenne effective au frein, quatre temps | 29,60 bar |
| Vitesse moyenne du piston | 21,12 m/s |

Calculs : `P = 1 600 × 745,6998716 W`, `T = P / (2πn/60)`, `BMEP = 4πT/Vd`, `Up = 2 × course × n/60`. Valeurs recalculées pour cette étude ; ce sont des besoins arithmétiques, pas des résultats de combustion.

**La BMEP de 29,60 bar n’est pas la pression maximale dans le cylindre.** Les charges sur le carter exigent les pressions en fonction de l’angle vilebrequin, les inerties et la réaction des paliers. Un modèle statique chargé seulement avec le couple moyen manquerait une part essentielle du problème. Le régime de puissance finale et le spectre d’usage restent à fixer. [Origine du point F32](https://github.com/cluster2600/3dprinting993/blob/6e987d1cecc45a65b35e78cc346af00c7bc64523/docs/917_CLEAN_SHEET_2026_F32.md).

## 7. Chaîne logicielle pour reproduire la démarche

La stack proposée prolonge les outils présents dans le dépôt. Les versions épinglées et les conteneurs existants constituent le point de départ ; un nom de logiciel dans le tableau ne signifie pas qu’un calcul du bloc a déjà été exécuté.

| Étape | Stack de base | Entrée → résultat attendu | Travail spécifique au carter |
|---|---|---|---|
| Registre technique | GitHub, JSON, Python, contrôles de schéma | Sources et mesures → paramètres avec provenance | Créer l’autorité dimensionnelle des deux variantes |
| CAO paramétrique | **build123d / OpenCascade**, FreeCAD pour édition et revue | Paramètres → solides STEP et définition éditable | Construire les demi-carters, surfaces réservées, galeries et références |
| Maillage | **Gmsh** | Volumes CAO → maillages portant des groupes physiques | Contacts, plans de joint, paliers et zones raffinées |
| Résistance et thermique du solide | **CalculiX** ; contre-calcul industriel si nécessaire | Géométrie, matière, contacts, températures et efforts → contraintes et déformations | Serrage, déformation des logements, fatigue à traiter avec une méthode qualifiée |
| Huile et refroidissement | **OpenFOAM**, cas dédiés | Volumes fluides et conditions aux limites → pertes de charge et températures | Galeries, récupération, échanges air/huile/solide ; modèle multiphasique si nécessaire |
| Charges moteur | Stack **F46**, modèles cycle et dynamique du train mobile à compléter | Cycle, cinématique et combustion → pressions et efforts | Fournir des charges physiques au carter, distinctes du rendu moteur |
| Physique locale du procédé LPBF | **AdditiveFOAM** | Paramètres laser et matière → champs thermiques/écoulement locaux | Étudier des zones et coupons représentatifs |
| Distorsion de toute la pièce | **Ansys Additive** ou outil équivalent du prestataire, modèle calibré | Orientation, supports, traitement → distorsion prédite | Vérifier plateau, découpe, détente et marge d’usinage |
| Optimisation de forme | Boucle paramétrique Python + calculs ; **nTop** en option commerciale | Variables et contraintes → variantes classées | Renforts, évidements et galeries, en conservant les interfaces |
| Apprentissage physique | **PhysicsNeMo**, après constitution du dataset | Cas calculés et corrélés → modèle de substitution évalué | Accélérer des explorations proches des cas appris |
| Revue et résultats | **ParaView**, OpenUSD / Omniverse | Champs solveur et assemblage → inspection, animation, comparaison | Visualiser les écarts et conserver le lien vers le calcul |
| Fabrication | Logiciel de préparation et FAO du prestataire | STEP, plans et règles de fabrication → préparation machine et parcours outils | Postprocesseur et paramètres de la machine réelle |

Le dépôt décrit cette séparation dans sa [stack modulaire](https://github.com/cluster2600/3dprinting993/blob/6e987d1cecc45a65b35e78cc346af00c7bc64523/docs/917_MODULAR_COMPUTE_STACK.md). **F46 fixe AATE/OpenFOAM ICengines, un contre-calcul historique engineFoam et Cantera 3.2.0** pour des rôles différents. Il ne prouve pas encore leur exécution sur le futur bloc. Le calcul de résistance du carter ne se réduit pas à ces solveurs de combustion. [F46](https://github.com/cluster2600/3dprinting993/blob/6e987d1cecc45a65b35e78cc346af00c7bc64523/docs/917_F46_SOLVER_AUTHORITY.md).

build123d fournit une CAO paramétrique Python fondée sur OpenCascade. Il convient à une génération versionnée, avec contrôles géométriques indépendants du texte produit par l’assistant. [Documentation](https://build123d.readthedocs.io/en/latest/).

AdditiveFOAM est un outil de physique continue pour l’additif, construit sur OpenFOAM. Son emploi local ne donne pas automatiquement un modèle de distorsion complet du carter, avec supports, découpe et traitements. Il faut une méthode macroscopique et sa calibration propres. [ORNL](https://github.com/ORNL/AdditiveFOAM), [Ansys : usages des simulations additives](https://ansyshelp.ansys.com/public/views/secured/corp/v251/en/add_print/add_print_why_use_aa.html).

nTop apporte notamment optimisation topologique et modélisation implicite. C’est une option pour gagner du temps de conception, avec coût de licence à demander ; ce n’est pas une dépendance nécessaire à la première CAO. Ses résultats doivent conserver les surfaces fonctionnelles et être revérifiés. [Méthode officielle nTop](https://support.ntop.com/hc/en-us/articles/360044051214-How-to-run-a-topology-optimization).

### Organisation reproductible des calculs

Séparer les environnements : CAO/maillage sur CPU ; mécanique et CFD selon les capacités réelles de leurs solveurs ; apprentissage et rendu sur GPU quand nécessaires. Louer une grosse machine GPU ne résout pas l’absence de géométrie ou de conditions aux limites.

Chaque résultat doit identifier : variante F43, version CAO, unités, hypothèses, matériau/état, maillage, conditions aux limites, version du solveur, convergence, fichiers de sortie et critères d’acceptation. Les images conteneur sont épinglées par digest. Les champs volumineux sont stockés séparément et référencés par empreinte ; les scans bruts et documents dont la redistribution n’est pas autorisée restent hors du dépôt public.

Le pipeline concret est : **paramètres → CAO → audit géométrique → maillage → calcul de référence → contrôle → comparaison de variantes**. Une erreur de volume, d’unité ou de bilan arrête le passage au stade suivant. Les commandes supplémentaires pour le carter seront créées avec leur implémentation ; cette étude n’invente pas de cible `make` déjà disponible.

## 8. Rôle concret de l’IA

Trois usages sont proposés, avec des preuves différentes :

1. **Assistant de développement dès maintenant.** Extraire des données accompagnées de leur source, écrire les scripts CAO, préparer les cas, analyser les journaux et rédiger les rapports. Les cotes absentes restent absentes ou explicitement marquées « hypothèse de conception ». Les validations géométriques et numériques sont exécutées par des programmes déterministes.
2. **Exploration paramétrique.** Faire varier les renforts, rayons, épaisseurs, sections de galeries et orientations. Commencer par un plan d’expériences et les solveurs classiques. Une optimisation bayésienne peut ensuite orienter les prochains calculs. Un optimum obtenu sur un modèle approximatif doit repasser le modèle de référence.
3. **Modèle de substitution physique.** Employer PhysicsNeMo lorsque les données sont suffisantes. Le dépôt retient notamment GeoTransolver, DoMINO et MeshGraphNet comme pistes suivant les champs à apprendre. Choisir le modèle sur un essai comparatif, pas sur son nom. [Programme du dépôt](https://github.com/cluster2600/3dprinting993/blob/6e987d1cecc45a65b35e78cc346af00c7bc64523/docs/917_REENGINEERING_PROGRAM.md), [documentation NVIDIA](https://docs.nvidia.com/physicsnemo/latest/index.html).

Pour le premier dataset du carter, enregistrer géométrie, épaisseurs, matière, température, efforts et précharge ; apprendre éventuellement déplacements des paliers et champs de contraintes. Séparer entraînement et validation **par géométrie et cas de charge**, pour éviter qu’un quasi-doublon donne une fausse impression de précision. Mesurer les erreurs locales dans les zones critiques, pas seulement une erreur moyenne. Hors domaine appris, retourner au solveur.

L’objectif de l’IA est de réduire le nombre de calculs et d’itérations humaines. Aucun facteur d’accélération, gain de masse ni durée de vie n’est promis avant mesure. Une forme générative agréable ou une animation Omniverse ne permet pas de déclarer le carter résistant.

## 9. Machines et fabrication en Chine

**La longueur utile de chaque demi-carter, ses supports et son orientation doivent précéder le choix de machine.** Les cotes documentaires alésage/course ne donnent pas son encombrement. Un volume d’impression annoncé ne garantit ni la disponibilité d’un atelier ni un procédé aluminium qualifié pour cette pièce.

| Piste | Ce que la source confirme | Action proposée |
|---|---|---|
| **Nikon SLM / Bosch, Europe** | Précédent V8 en AlSi10Mg sur NXG XII 600 ; système multi-laser industriel | Demander une revue de faisabilité du carter et le périmètre exact des essais du précédent |
| **Eplus3D et ateliers équipés, Chine** | EP-M1550 : enveloppe publiée de **1 550 × 1 550 × 1 100 mm**, hauteur incluant le plateau ; aluminium parmi les familles compatibles ; EPControl et EPHatch indiqués | Identifier un atelier ayant une expérience démontrée du grand aluminium et des reprises de précision |

Sources : [NXG XII 600](https://nikon-slm-solutions.com/slm-systems/nxg-xii-600/), [EP-M1550](https://www.eplus3d.com/products/ep-m1550-metal-3d-printer/). Ces machines ne sont pas présentées comme des nouveautés des six derniers mois. Leur présence au catalogue n’établit pas la compatibilité de notre géométrie.

L’intérêt à évaluer en Chine est une chaîne complète : impression, traitement, contrôle interne, usinage et métrologie. Demander qui réalise chaque opération, sur quelle machine, et qui garantit la cohérence des résultats. L’alliage d’une fiche EOS n’est pas automatiquement qualifié sur une machine Eplus3D ; le changement de procédé exige ses propres données.

### Dossier de consultation prêt à constituer

Demander trois quantités : **une paire prototype, cinq paires, vingt paires**. Ce sont des scénarios commerciaux proposés, pas des commandes ni un volume de vente établi.

- STEP des deux pièces, plans fonctionnels, volumes nets, encombrements, zones critiques et quantités ; pour l’instant, joindre un périmètre d’étude et déclarer les données manquantes.
- Variante moteur, contraintes air/huile, spectre d’utilisation et température à confirmer.
- Machine/configuration laser, matériau exact, traçabilité poudre, paramètres et éprouvettes de qualification.
- Orientation proposée, zones de raccordement laser, supports, dépoudrage, accès d’inspection, séparation du plateau et traitement.
- Reprises d’usinage, surépaisseurs justifiées, bridage, alésage en ligne et contrôle après serrage.
- CT/CND avec capacité de détection adaptée aux défauts critiques, métrologie, propreté des galeries, pression/débit et étanchéité.
- Prix ventilé : préparation, fabrication, témoins, traitements, contrôle, usinage, rebut/reprise, transport et assurance ; délais de chaque étape.

Aucun prestataire n’a été contacté et aucun devis n’a été obtenu dans cette étude.

## 10. Prototypes et qualification

La gamme exacte dépendra du couple alliage–machine. Une hypothèse de gamme est : fabrication avec témoins → détente selon procédé → séparation et dépoudrage → traitements qualifiés → contrôle interne → usinage des références → contrôle → usinage fonctionnel → propreté et essais. **L’ordre des traitements, de la séparation et des contrôles doit être arrêté par le spécialiste du procédé**, en tenant compte de la stabilité dimensionnelle.

Ne pas prescrire automatiquement un HIP. Comparer, si justifié, des témoins avec et sans HIP, puis vérifier fatigue et stabilité. Prévoir dès la CAO l’accès aux galeries ; un volume fermé contenant de la poudre ne doit pas devenir une fonction d’huile. Une structure alvéolaire n’est utile que si sa fabrication, son nettoyage et son contrôle sont démontrables.

| Étape | Pièce ou essai | Décision obtenue |
|---|---|---|
| P0 | CAO, tolérances, analyses préliminaires et revue procédé | Comparaison numérique crédible des routes |
| P1 | Coupons matière et artefacts de galeries, surfaces et raccordements laser | Données utilisables pour le procédé proposé |
| P2 | Secteur palier–registre–galerie–liaison | Fabricabilité locale, usinage, propreté, tenue locale et corrélation |
| P3 | Paire de demi-carters complète | Distorsion globale, métrologie après serrage, étanchéité et montage |
| P4 | Assemblage entraîné et circuit d’huile instrumenté | Rotation, récupération d’huile, pressions et températures avant combustion |
| P5 | Banc moteur avec paliers de charge progressifs | Corrélation des calculs, comportement thermique et mécanique |
| P6 | Endurance suivant le spectre fixé, démontage et inspection | Durabilité et défauts après service |

La branche atmosphérique peut réduire la complexité des premiers essais, mais son succès ne qualifie pas la version biturbo 5,374 L. L’alésage, les efforts et les interfaces éventuellement modifiés doivent rester traçables par variante.

Les seuils finaux ne peuvent pas être remplacés par une valeur générique telle que « précision 0,1 mm » : définir notamment la déformation admissible des logements depuis les coussinets, les ajustements, le film d’huile et les températures. L’ingénieur responsable arrête les critères et la campagne physique. Les règles `AGENTS.md` du dépôt imposent cette revue avant libération de pièces moteur fortement chargées ; la présente étude est une préparation documentaire.

## 11. Coût et choix économique

Il n’existe pas encore de volume CAO validé, de temps machine ni de gamme d’usinage du carter. **Un prix présenté aujourd’hui comme un devis du bloc serait inventé.** L’étude doit néanmoins rendre les offres comparables dès la première consultation.

Coût d’une paire acceptée = préparation et études affectées + matière et fabrication + témoins + traitements + contrôle + usinage + logistique + effet des rebuts et reprises.

Pour comparer une série de `N` paires, utiliser `coût total = coûts fixes de route + N × coût variable d’une paire acceptée`. Si la fonderie a des coûts fixes supérieurs et un coût variable inférieur, son seuil économique face au LPBF est `N* = (fixe_fonderie − fixe_LPBF) / (variable_LPBF − variable_fonderie)`, uniquement lorsque ce dénominateur est positif. Ajouter ensuite délais, risque d’itération et capacité de contrôle ; un prix au kilogramme seul serait insuffisant.

Avant une commande complète, les dépenses qui réduisent le plus l’incertitude sont la définition des interfaces, la revue conjointe imprimeur–usineur et les coupons/secteurs représentatifs. Le recours à un prestataire chinois ne supprime aucune de ces tâches.

## 12. Lots à préparer pour le dépôt

Ces lots sont proposés ; ils n’ont pas été ajoutés au GitHub pendant la rédaction de cette étude.

| Lot | Travail | Livrable de revue |
|---|---|---|
| L1 — définition | Rassembler mesures et interfaces reconçues ; rattacher chaque variante à F43 | Registre de paramètres et matrice d’inconnues |
| L2 — CAO carter | Générer les deux solides paramétriques et leur assemblage | Sources éditables, STEP et rapports géométriques |
| L3 — chargements | Définir températures, précharges, pressions cylindre, efforts de paliers et supports | Cas de charge traçables et sensibilité |
| L4 — comparaison | Construire variantes LPBF, fonderie et usinage fonctionnellement équivalentes | Masse, rigidité, contraintes, nettoyage, temps/coûts et limites |
| L5 — procédé | Orientation, supports, distorsion, traitement, usinage et contrôle | Gamme candidate et dossier de consultation |
| L6 — essais | Coupons, secteur, paire complète et banc | Plan d’essais avec critères définis avant fabrication |

Cette étude est intégrée sous `docs/917_CRANKCASE_MANUFACTURING_STUDY.md` ; les lots L1 à L6 restent à réaliser. Les contrats existants restent inchangés tant que leur évolution n’est pas explicitement implémentée et revue. Conserver notamment F43, la décision air/huile F34a et les propriétés non sélectionnées dans F19. La PR documentaire doit consigner le résultat de `make check` conformément aux instructions du dépôt.

## 13. Provenance et intégration documentaire

Document d’origine : `Etude_Bloc_917_Modernise_2026.md`, version 1.0 du
5 septembre 2026. Intégration documentaire préparée le 6 septembre 2026.

Empreinte SHA-256 du fichier d’origine :

```text
65ce045b74afb2270f0376d6fa99f77d1cd56a56a7ac8d50d1e5445b770d2a96
```

Les sections techniques 1 à 11 sont reprises avec leurs sources et leurs
hypothèses. Les liens vers le dépôt sont figés au commit étudié
`6e987d1cecc45a65b35e78cc346af00c7bc64523` pour conserver le contexte de preuve.
La section 12 situe désormais le document dans le dépôt. L’ancien diagnostic
de connexion GitHub de la section 13 est remplacé par cette note de provenance.
Les références externes restent celles de l’étude du 5 septembre ; cette
intégration ne constitue pas une nouvelle recherche bibliographique.

Cette contribution est documentaire : elle ne modifie ni les contrats F43,
F34a, F19, F41 et F46, ni les autorisations de fabrication. Les sources tierces
sont citées par lien et conservent leurs droits ; aucun scan brut, manuel
propriétaire ni fichier CAO tiers n’est incorporé.

---

**Portée du livrable :** étude documentaire et programme d’ingénierie proposés.
Aucune nouvelle géométrie de carter, simulation de résistance, qualification
matière, impression ou commande fournisseur n’est réalisée par cette
contribution. Les choix propres au 917 restent des propositions à éprouver ;
la publication de l’étude ne vaut pas autorisation de fabriquer, monter ou
faire fonctionner ces pièces moteur fortement chargées.
