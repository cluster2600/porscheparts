# M64 — recherche GPU au 12 septembre 2026

**CPU pour les références et petits cas ; GPU après témoin compatible et gain
bout-en-bout mesuré.** Trois revues bornées ont étudié géométrie, thermique/
résistance et LPBF. Recherche ciblée, pas revue systématique exhaustive.
Application : [jobs 2–3–4](M64_JOBS_234_20260912.md).

## Sources primaires et décisions

| Publication / code | Apport, limite et décision M64 |
|---|---|
| [PaMO, auteurs, PG2025](https://github.com/SarahWeiii/pamo) | Remeshing/projection de surfaces sur GPU, AGPL-3.0. Ne garantit ni conservation des interfaces ni polyMesh hybride. **Pas de remplacement du contour maître.** |
| [MFEM 4.10, 1 septembre 2026](https://mfem.org/news/), [TMOP officiel](https://docs.mfem.org/4.10/mesh-optimizer_8cpp_source.html) | Version logicielle, pas preuve d'une culasse réparée. TMOP offre CUDA et frontière fixée ; hr reste CPU. Le writer à 14 chiffres et l'absence de pont polyMesh exigent une conversion/contre-vérification explicite. BSD-3-Clause. **Candidat pour petite région tétra intérieure**, pas pour déplacer les ailettes. |
| [OpenFOAM Modern C++ proof-of-concept, juillet 2025](https://arxiv.org/abs/2507.18268) | Offload de `laplacianFoam` via C++ parallèle. **Faisabilité sur témoin**, pas disponibilité d'une combustion/CHT moteur sur GPU. |
| [SPUMA, décembre 2025, texte intégral](https://arxiv.org/html/2512.22215v1), [CPC 321, 2026](https://doi.org/10.1016/j.cpc.2025.110009) | Port GPU NVIDIA/AMD au-delà des matrices. La conclusion exclut encore compressible, interfaces de domaines, multiphase et transfert thermique. Les résultats DrivAer à environ 8–10 millions de cellules/GPU ne prédisent pas notre domaine de 784 675 cellules. **Exclu de la CHT/combustion dans cette version** ; code/licence à épingler pour un éventuel témoin froid. |
| [OpenCFD, infrastructure v2606, juin 2026](https://www.openfoam.com/news/main-news/openfoam-v2606/infrastructure) | Branche pilote `std::execution`, mémoire UMPIRE, opérations de champs et solveurs ; intégration principale annoncée pour v2612 après essais communautaires. Routines sérielles et nombreux patches peuvent pénaliser le calcul ; réductions non déterministes. **Qualification CHT exacte nécessaire**, pas remplacement automatique de Foundation14. |
| [Adamantine 1.0, JOSS, octobre 2024](https://joss.theoj.org/papers/10.21105/joss.07017), [code épinglé](https://github.com/adamantine-sim/adamantine/tree/3990489a10902912889617856f6e2e097d52a412) | Thermomécanique AM, Apache-2.0 avec exception LLVM. Le papier décrit l'opérateur thermique GPU, mécanique CPU. Le code actuel utilise conditionnellement Tpetra `MemorySpace::Default` avec deal.II≥9.7, puis rapatriement et contraintes Host ([source](https://github.com/adamantine-sim/adamantine/blob/3990489a10902912889617856f6e2e097d52a412/source/MechanicalPhysics.cc#L503)). **Premier candidat pour la distorsion globale**, sans promesse de mécanique entièrement GPU. |
| [GO-MELT, Additive Manufacturing 109, 2025](https://doi.org/10.1016/j.addma.2025.104897), [code MIT épinglé](https://github.com/JLnorthwestern/GO-MELT/tree/7dafdd8593711cf8ac6ccb18a1f475744610ea3d) | Thermique LPBF multi-échelles JAX, mise à jour explicite matrix-free et sous-cyclage. L'aperçu annonce 350 millions de pas en 7,3 jours sur un GPU : pas une culasse qualifiée en une nuit. Dépendances anciennes à isoler ; pas de distorsion mécanique établie dans ce code thermique. **Contre-calcul thermique potentiel.** |
| [HERMES, CMAME 452, 2026](https://doi.org/10.1016/j.cma.2025.118673), [code MIT épinglé](https://github.com/aydinalperen7/hermes-gpu-heat/tree/bfa017b5266fda2c0c576135dc8397b458cd5fe5) | Grilles thermiques imbriquées mobiles, CuPy/Numba. Constantes de type 316L dans le code, pas notre AlSi10Mg témoin. **Alternative thermique seulement**, ni contraintes ni débridage démontrés par ces noyaux. Sans rapport avec un assistant LLM homonyme. |

SPUMA et le papier court JOSS ont été lus intégralement. Pour GO-MELT/HERMES,
aperçu primaire et code accessibles, mais pas texte intégral éditeur : détails
de validation non audités. Les versions de logiciels ne sont pas présentées
comme des articles. Le contenu OpenCFD a été consulté via l'index primaire
lorsque l'ouverture directe répondait 403. Aucun téléchargement/compilation
de solveur ou installation GPU effectué dans ce lot.

## Benchmark admissible

- Même problème et précision : géométrie, unités, BC, lois matériau, second
  membre, discrétisation et tolérances. FP64 d'abord ; précision mixte séparée.
- Chronométrer lecture, conversion, transferts H2D/D2H, assemblage/setup,
  résolution et sauvegarde ; distinguer bootstrap/JIT et répétitions chaudes.
  Mesurer RAM/VRAM maximale et migrations. Énergie = intégrale de puissance
  mesurée si disponible, pas temps × TDP.
- Résidu vrai et quantités physiques comparables, pas identité binaire de
  champs après réductions parallèles. Le contour protégé, lui, reste exact.
- Si le coût et le temps complets ne gagnent pas, garder CPU. Aucune raison
  établie de louer plusieurs GPU pour le domaine actuel de 0,8 million de cellules.

[PETSc PCAMGX](https://petsc.org/release/manualpages/PC/PCAMGX/) avertit des
transferts récurrents quand le KSP reste CPU. AmgX ne porte pas l'assemblage
ou la physique d'OpenFOAM automatiquement. Un témoin doit extraire **A et b**,
pas utiliser un second membre par défaut. L'adaptateur Foundation14 reste à qualifier.

L'[exemple MFEM ex2p](https://raw.githubusercontent.com/mfem/mfem/v4.10/examples/ex2p.cpp)
accepte `-d cpu|cuda` avec chaîne assemblée/Hypre à vérifier ; ses exports à huit
chiffres ne suffisent pas à une comparaison FP64 serrée.
[ex16p](https://raw.githubusercontent.com/mfem/mfem/v4.10/examples/ex16p.cpp)
n'offre pas cette CLI CUDA. Ces témoins ne remplacent pas contacts, plasticité
et fatigue de la culasse. CalculiX reste la référence envisagée pour ces modèles.

Le [pilote PhysicsNeMo-Mesh exécuté](M64_PHYSICSNEMO_MESH_PILOT_20260912.md)
mesure des opérations sur une surface de référence quatre sièges, pas la
dernière culasse M64 complète. L'adaptateur de produit vectoriel ne répare pas
le polyMesh. Un futur modèle réduit PhysicsNeMo exigera des cas de référence
acceptés, des régimes/géométries exclus de l'entraînement et un contrôle hors
domaine ; les photos et températures censurées ne sont pas une vérité physique.

## Piston et soupapes : sources pour la prochaine intégration

Foundation14 possède un [tutoriel moteur mobile](https://raw.githubusercontent.com/OpenFOAM/OpenFOAM-14/master/tutorials/XiFluid/engine2Valve2D/constant/dynamicMeshDict)
avec bielle-manivelle, levées et remapping périodiques sur 720°.
[multiValveEngine](https://cpp.openfoam.org/v14/classFoam_1_1fvMeshMovers_1_1multiValveEngine.html)
**impose** le mouvement, sans résoudre ressorts, affolement ou rebond. Fermeture
et interfaces non conformes exigent conservation de masse/énergie et volumes
positifs. Ce tutoriel deux soupapes n'est pas un cas M64 quatre soupapes prêt.

Dans l'[exemple Cantera 3.2](https://cantera.org/3.2/examples/python/reactors/ic_engine.html),
les soupapes sont des connecteurs de débit et la vitesse du piston est imposée.
L'exemple diesel ne définit pas notre essence turbo. Séparer cycle réduit,
CFD mobile et dynamique mécanique, puis contre-vérifier leurs échanges.
Omniverse montrera mouvements et champs issus des solveurs ; le rendu ne
constitue pas une validation physique indépendante.
