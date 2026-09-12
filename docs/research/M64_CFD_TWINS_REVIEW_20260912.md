# CFD, thermique et modèles appris pour la culasse M64

Le chemin défendable est une chaîne de calculs vérifiés, puis corrélés à des
mesures, sur laquelle un modèle appris peut accélérer la sélection de variantes.
Les dix publications retenues entre 2023 et le 12 septembre 2026 ne démontrent
ni une culasse M64 quatre soupapes de 700 hp, ni un solveur universel combinant
combustion, distribution mobile et refroidissement air/huile. Les accélérations
publiées restent propres à leurs problèmes et matériels.

La [référence locale](../M64_700CH_ENGINE_RESEARCH.md) conserve **700 PS au
vilebrequin = 514,849 kW**. Une sensibilité à **700 hp mécaniques = 521,990 kW**
ajoute 1,387 %. Cette ambiguïté d'unité ne modifie pas le contrat existant.
Régime, carburant, cylindrée réelle, durée à pleine charge et conditions de banc
restent à figer. Une puissance cible ne fournit ni pression cylindre, ni flux
thermique, ni pression de suralimentation.

## Ce qui se transpose des publications

Pati et al. simulent 33 cycles entraînés, sans combustion, du moteur optique
Darmstadt : 800 tr/min, admission moyenne 0,95 bar, paroi du piston résolue à
25 µm et `y+ < 1`. Les vitesses proches de la paroi sont confrontées à des
mesures. L'absence de région logarithmique et les fluctuations cycliques
signalent les limites des lois de paroi d'équilibre ; ces résultats ne valident
pas un flux thermique de combustion turbo.[^1]

Caramia et al. montrent l'intérêt de schémas WENO pour des jets compressibles,
mais leur cas est **axisymétrique, non réactif, hydrogène/air**, avec rapports
de pression 8,5–30. La largeur de jet peut être surestimée de 30 %. Une bonne
capture des chocs ne garantit donc pas le mélange, encore moins une combustion
essence dans une chambre à quatre soupapes.[^2] Gärtner et al. traitent un autre
verrou : l'équilibrage MPI du coût de chimie, avec accélérations annoncées jusqu'à
6 pour la chimie standard et 5 pour TDAC. C'est un résultat CPU parallèle,
pas une preuve d'accélération GPU ni de justesse d'un mécanisme carburant.[^3]

Pour le refroidissement, Lei Jilin et al. articulent mesures moteur, modèle 1D
et calcul thermique/mécanique sur un moteur aéronautique à air. L'effet conjoint
de la longueur et de l'épaisseur des ailettes est pertinent, mais leurs gains
ne sont pas des facteurs applicables au M64.[^4] Tandis et al. comparent les
couplages CHT sur des enceintes de convection naturelle et des propriétés
construites pour faire varier le couplage. Leur solveur monolithique est
intéressant numériquement ; ses performances ne prouvent pas la compatibilité
avec la combustion compressible, l'huile ou les contacts siège/guide.[^5]

CFDverify facilite l'estimation des erreurs de discrétisation et révèle même
des erreurs de recopie/arrondi dans des exemples publiés. Son périmètre est la
**vérification de solution**, sans comparaison au système physique. Il faut
conserver la précision des données exportées et examiner les hypothèses de
Richardson/GCI ; trois maillages arbitraires ne rendent pas toute extrapolation
valide.[^6]

GINO et DoMINO apprennent surtout des résultats CFD aérodynamiques sur des
familles automobiles.[^7][^8] Leur intérêt est d'amortir une campagne répétitive
sur un domaine connu. La convergence vis-à-vis de la discrétisation d'un
opérateur appris n'est pas une preuve de convergence vers la physique réelle.
Un modèle entraîné sur OpenFOAM reproduit aussi ses biais. Il ne constitue
pas un second solveur indépendant ni une validation expérimentale.

## Métriques publiées : comparaisons à garder distinctes

Les lignes ci-dessous concernent des tâches différentes ; elles ne forment
pas un classement transversal de précision.

| Publication et cas | Mesure effectivement publiée | Limite de lecture |
| --- | --- | --- |
| GINO, Ahmed/ShapeNet [7] | Accélération annoncée jusqu'à 26 000× pour la traînée ; erreur de pression Ahmed 8,31 % dans le résumé | Inférence après entraînement ; ni coût total d'acquisition ni combustion |
| DoMINO v1, DrivAerML [8], tableaux 1–2 | `R²` traînée 0,96 ; erreur relative L2 pression surfacique 15,05 %, pondérée par aire 11,81 % ; pression volumique 21,93 % | Bon classement global compatible avec erreurs locales ; jeux et métriques différents de GINO |
| CFDLLMBench v1 [9], tableau 2, Foam-Agent/Sonnet 3.5 | Basic : exécution 83,6 %, succès global 33,6 % ; Advanced : 62,5 % et 25 % | Les critères de champs et de configuration abaissent le succès ; aucune culasse industrielle |
| Xiao et al. [10], §4.1 | 9/9 cas proches de tutoriels exécutés avec consigne adaptée ; 7/9 avec `NMSE < 0,1` | Petit échantillon, protocole à une exécution ; pas une garantie générale |

Les résultats des agents justifient la récupération de cas vérifiés, les
changements minimaux et la réparation guidée par journaux.[^9][^10] Ils ne
démontrent pas qu'un LLM « comprend la physique ». Le contrôleur doit interdire
qu'une réparation change discrètement carburant, frontières, durée, géométrie
ou critères d'acceptation pour obtenir un code de sortie nul.

## Plan d'exécution proposé

1. **Contrat et géométrie.** Reprendre les interfaces et le
   [checkpoint multiphysique](../M64_MULTIPHYSICS_EXECUTION.md), puis construire
   des domaines séparés gaz, solide, air et éventuellement huile. Fixer les
   normales, unités, contacts et surfaces d'échange. Le rejet de maillage
   documenté reste un blocage avant étiquetage CFD ; la recherche ne le lève pas.
2. **Admission quasi stationnaire.** À levées imposées et frontières de banc
   définies, comparer 2V/4V par débit, coefficient de décharge, perte de pression
   totale et structures de rotation. Utiliser la compressibilité si les rapports
   de pression/Mach l'exigent. Chaque point représente un banc de flux ; il
   ne prédit pas remplissage transitoire, combustion ou puissance.
3. **Cycle mobile avant combustion.** Reproduire d'abord un tutoriel
   [ICengines/AATE](https://github.com/OpenFOAM/ICengines), avec couple
   solveur/cas épinglé. Les commandes fournies sont `./Allmesh` puis `./Allrun` ;
   ajouter le contrôle `checkMesh` adapté aux régions et aux positions mobiles.
   Vérifier volumes, fermeture des soupapes, conservation géométrique et erreurs
   de transfert entre maillages, puis périodicité et statistiques de plusieurs
   cycles. La [méthode officielle](https://cfd.direct/openfoam/free-software/ic-engines/)
   combine mouvement, changement de maillage et couplage non conforme ; elle
   n'établit pas que notre assemblage CHT complet est déjà disponible.
4. **Chimie et charges.** Conserver le
   [calcul Cantera existant](../M64_700PS_VARIABLE_THERMO_20260908.md) comme témoin
   thermodynamique à combustion prescrite. Choisir ensuite un substitut et un
   mécanisme documentés pour le carburant, tester délais d'auto-inflammation et
   vitesses de flamme, puis intégrer la fermeture turbulence/chimie compatible.
   L'[exemple moteur Cantera](https://cantera.org/stable/examples/python/reactors/ic_engine.html)
   est illustratif, au n-dodécane gazeux : il n'est pas un modèle M64 à copier.
   Comparer `p(θ)`, dégagement de chaleur, CA10/50/90, travail `∮p dV`, pompage,
   flux paroi et variabilité aux mesures disponibles. Le cliquetis exige une
   validation spécifique ; un cycle moyen ne suffit pas.
5. **CHT et mécanique.** Commencer par ailettes/carénage avec charges thermiques
   explicitement supposées, puis itérer gaz–solide avec charges cycle-moyennées
   si la séparation des temps est justifiée. Résoudre séparément les transitoires
   utiles à la fatigue. Comparer air seul et air/huile à débit, température,
   pression et puissance auxiliaire traçables, en incluant viscosité et contacts.
   Transférer conservativement les champs vers
   [CalculiX](https://www.calculix.de/) ou
   [Elmer](https://www.nic.funet.fi/pub/sci/physics/elmer/doc/ElmerModelsManual.pdf)
   pour dilatation, précharge et contacts, après vérification des fonctions
   nécessaires. Aucun assemblage automatique de ces codes n'est démontré ici.
6. **Modèle réduit et jumeau.** Commencer par une régression de KPI, puis tester
   DoMINO/GINO si les champs et le nombre de variantes le justifient. Séparer
   entraînement, calibration et test par familles géométriques et régimes.
   L'apprentissage actif choisit des cas nouveaux, notamment incertains ; les
   finalistes repassent par CFD/FEA. Un jumeau corrélé exige des mesures physiques
   réservées au contrôle, distinctes de celles utilisées pour le calage.

## Vérification commune et décision de calcul

| Niveau | Critères à fixer avant la campagne |
| --- | --- |
| Conservation | Masse et espèces ; énergie gaz/solide/air/huile ; continuité de flux aux interfaces ; bilan des efforts et moments FEA |
| Discrétisation | Trois niveaux cohérents d'espace et de temps, ordre observé/intervalle d'erreur si applicable ; statistiques convergées pour LES |
| Réalité physique | Débit/pression de banc, pression cylindre phasée, thermocouples aux ponts/sièges et entrées/sorties, débit d'huile et d'air ; incertitude des capteurs |
| Modèle appris | Erreur absolue locale et maximale, L2 pondérée, erreur KPI, erreurs de classement, couverture d'intervalles calibrés, détection hors domaine |
| Coût | Temps et mémoire mesurés, CPU/GPU-heures, données + entraînement + recalculs, tokens et réparations par cas accepté |

Pour la conduction seule, comparer également à une solution analytique de
plaque/ailette ou à un calcul FEM utilisant mêmes propriétés et frontières.
Ce contre-calcul peut détecter une erreur d'implémentation ; partager les mêmes
charges supposées ne valide pas leur réalité. Aucun seuil universel de 1 %
ne remplace un budget d'incertitude adapté à la décision.

Le chemin initial recommandé est CPU/MPI pour CFD/CHT et GPU pour le modèle
appris lorsque son jeu de données existe. Les
[recettes PhysicsNeMo](https://docs.nvidia.com/physicsnemo/latest/physicsnemo/examples/cfd/external_aerodynamics/domino/README.html)
documentent ce dernier chemin. Un backend CFD GPU n'est retenu qu'après
équivalence et gain mesurés sur le même cas, avec son modèle physique complet.
Les forks OpenFOAM sont incompatibles par défaut : la bibliothèque chimique
citée vise v2212/v2306/v2312, tandis que le README ICengines consulté indique
OpenFOAM-14. Leur réunion demande une adaptation vérifiée, pas un simple
changement de nom d'image.

Le LLM intervient sur préparation, diagnostic et rapports compacts ; scripts
déterministes et contrôles physiques pilotent les calculs. Le
[coupon plafonné à 3 300 K](../M64_QUADRATURE_EXECUTION_20260912.md) est exclu
des vérités d'entraînement. Aucun calcul, entraînement ou achat de ressources
n'est réalisé par cette revue.

## Sources et niveau d'accès

« Texte consulté » signifie lecture des sections méthodes/résultats/limites
pertinentes, pas reproduction numérique. Les prépublications sont identifiées
par version ; les URL `main`, `master`, `latest` sont des pointeurs de
documentation à épingler avant usage. Aucun résultat postérieur au
12 septembre 2026 n'est utilisé.

[^1]: Andrea Pati, Max Hasenzahl, Suad Jakirlic, Christian Hasse.
    [Large Eddy Simulation of the Piston Boundary Layer Evolution During the Compression Stroke in a Motored Internal Combustion Engine](https://doi.org/10.1007/s10494-025-00649-4).
    *Flow, Turbulence and Combustion* 114, 1269–1295 ; 14 avril 2025.
    Article évalué, texte HTML consulté, §2–4. OpenFOAM 2.4.x + TFMotion
    interne ; données sur demande, aucun paquet complet de reproduction identifié.

[^2]: Giovanni Caramia, Riccardo Amirante, Pietro De Palma.
    [Unsteady RANS simulations of under-expanded hydrogen jets for internal combustion engines](https://doi.org/10.1016/j.ijhydene.2024.11.242).
    *International Journal of Hydrogen Energy* 96, 849–859 ; en ligne
    28 novembre 2024. Article évalué, PDF institutionnel consulté, §2–5 ;
    OpenFOAM avec extension WENO, dépôt exact du cas non identifié.

[^3]: Jan Wilhelm Gärtner, Ali Shamooni, Thorsten Zirwes, Andreas Kronenburg.
    [A chemistry load balancing model for OpenFOAM](https://doi.org/10.1016/j.cpc.2024.109322).
    *Computer Physics Communications* 305, 109322 ; décembre 2024.
    Article évalué ; résumé éditeur et
    [code GPL-3.0](https://github.com/ITV-Stuttgart/loadBalancedChemistryModel)
    consultés, texte intégral non obtenu. Tests jusqu'à 8 000 cœurs annoncés ;
    tutoriel public `counterFlowFlame2D`, pas une validation moteur essence.

[^4]: Lei Jilin et al.
    [Multi-objective optimisation of heat transfer and structural strength of aero-piston air-cooled engine cylinder based on orthogonal test](https://doi.org/10.1016/j.tsep.2024.102500).
    *Thermal Science and Engineering Progress* 50, 102500 ; mai 2024.
    Article évalué ; résumé et présentation éditeur consultés uniquement.
    Quatre paramètres à cinq niveaux ; températures/pressions expérimentales
    annoncées. Aucun code public identifié ; résultats détaillés non réaudités.

[^5]: Emad Tandis, Philip Cardiff, Ali Ashrafizadeh.
    [Analysis of Coupling Strategies for Conjugate Heat Transfer Problems](https://doi.org/10.51560/ofj.v5.92).
    *OpenFOAM Journal* 5, 38–58 ; 7 mars 2025.
    Article évalué, PDF consulté, §2–4 et conclusions.
    [Code et cas](https://github.com/tandise/ConjugateHeatTransfer-OpenFOAM)
    sur foam-extend-4.0 ; licence de réutilisation du dépôt non établie ici.
    Benchmarks d'enceintes, pas d'ailettes moteur forcées ni d'huile.

[^6]: Justin Weinmeister, Devina P. Sanjaya.
    [An Open-Source Python Package for CFD Solution Verification](https://doi.org/10.1115/VVUQ2025-151463).
    Conférence ASME VVUQ, 9–10 avril 2025 ; contribution aux actes,
    [manuscrit intégral](https://www.osti.gov/servlets/purl/3002740) consulté,
    §1–6. [CFDverify, MIT](https://github.com/ORNL/cfd-verify).
    Exemple de réattachement/vitesse issu de données publiées ; outil de
    vérification, sans certification ni validation physique automatique.

[^7]: Zongyi Li et al.
    [Geometry-Informed Neural Operator for Large-Scale 3D PDEs](https://arxiv.org/abs/2309.00583).
    *NeurIPS 2023*, prépublication du 1er septembre 2023 ; papier de conférence
    évalué, PDF des actes consulté, §1–4.
    [Implémentation maintenue](https://github.com/neuraloperator/neuraloperator/blob/main/neuralop/models/gino.py).
    Ahmed/ShapeNet, pression surfacique ; versions, poids et licences de chaque
    jeu à verrouiller séparément avant reproduction.

[^8]: Rishikesh Ranade et al.
    [DoMINO: A Decomposable Multi-scale Iterative Neural Operator for Modeling Large Scale Engineering Simulations](https://arxiv.org/html/2501.13350v1).
    Prépublication arXiv v1, 23 janvier 2025 ; texte consulté, §2–4.
    [Code PhysicsNeMo](https://github.com/NVIDIA/physicsnemo/tree/main/examples/cfd/external_aerodynamics/domino).
    DrivAerML : 500 variantes, 10 % au test, environ 150 millions de cellules
    volumiques par cas source ; champs moyennés en temps, pas cycle mobile.

[^9]: Nithin Somasekharan et al.
    [CFDLLMBench: A Benchmark Suite for Evaluating Large Language Models in Computational Fluid Dynamics](https://arxiv.org/html/2509.20374v1).
    Prépublication arXiv v1, 19 septembre 2025 ; texte consulté, §3–6,
    tableaux 1–4. [Code/données](https://github.com/NLR-Theseus/cfdllmbench).
    108 questions, 24 problèmes Python, 126 cas OpenFOAM ; benchmarks
    synthétiques/tutoriels, sans géométrie de culasse industrielle.

[^10]: Ke Xiao et al.
    [A Preliminary Assessment of Coding Agents for CFD Workflows](https://arxiv.org/html/2602.11689v1).
    Prépublication arXiv v1, 12 février 2026 ; texte consulté, §3–5.
    OpenCode/OpenFOAM, prompt en annexe ; dépôt de reproduction propre non
    identifié. Cas proches de tutoriels et obstacles plans 2D ; variations entre
    exécutions et validation industrielle non établies.
