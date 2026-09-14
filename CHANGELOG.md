# Journal des versions

Toutes les évolutions notables du projet sont consignées dans ce fichier.

## Non publié

Support d'intercooler 993 Turbo/GT2 Ti-6Al-4V F0, 8 septembre 2026 :

- création d'une fiche de jumeau F1 limitée à l'enveloppe fournisseur et aux
  identités PorscheFanatics/PET ;
- exécution de trois maillages quadratiques Gmsh/CalculiX sur le STEP exact,
  avec convergence de régression obtenue sur le p95 et la flèche ;
- conversion OpenUSD et validation minimale par le workflow NVIDIA verrouillé,
  sans attribution physique, GPU ni PhysicsNeMo ;
- choix LPBF ramené à un candidat conditionnel face aux voies CNC et tôlerie,
  toutes les portes de fabrication et de montage restant fermées.

Sous-ensemble de refroidissement moteur 993 F0, 8 septembre 2026 :

- composition du carter et de la turbine F0 dans un jumeau d'interface dédié ;
- calcul de jeu froid et libre à chaud, contrôle exact d'intersection BRep et
  rejet explicite de la collision de 40 388,378651 mm³ ;
- conversion des deux STEP et composition de l'assemblage en OpenUSD minimal
  sous Linux AMD64, avec préflight NVIDIA et validations minimales réussies
  sans GPU ;
- propriétés SimReady, PhysicsNeMo, fabrication, rotation et démarrage moteur
  maintenus fermés.

Culasse 917-inspired F34 quatre soupapes refroidie par air, 2 septembre 2026 :

- CAO paramétrique et STEP de procédé générés localement à partir des seules
  interfaces observables dans les deux scans, sans republier les scans bruts ;
- refroidissement externe calculé séparément par OpenFOAM 14 (volumes finis)
  et FluidX3D (LBM), cycle recoupé par Cantera et Wiebe, puis séquence de trois
  maillages CalculiX ;
- images `linux/amd64` de la chaîne CAE et de FluidX3D construites et testées ;
- toutes les portes d'impression métallique et de démarrage moteur restent
  fermées, notamment pour l'échelle, la matière à chaud, la convergence,
  la fatigue/TMF et l'absence de corrélation physique.

Phase 1, lot 1 — catalogues officiels, manuels accessibles et mesures :

- treize nouvelles fiches de sources vérifiées une à une le 28 août 2026 ;
- statuts d’accès réels consignés, y compris les refus, paywalls et URL mortes ;
- journal d’inventaire et liste motivée des sources écartées.

Phase 1, lots 2 et 5 — recherche allemande, scans et passation de mesure,
30 août 2026 :

- registre porté à 225 fiches de sources valides, avec fabricants, forums,
  mesures déclarées et pistes CAO/CT/LiDAR évalués séparément ;
- aucun scan 993 étalonné et librement réutilisable ajouté, et aucun fichier
  tiers copié sans licence établie ;
- ajout de deux pistes allemandes distinctes : supports de pare-chocs 964/993
  avec cotes commerciales déclarées, et réparation amateur du déflecteur de toit
  ouvrant avec référence de pièce ;
- campagne de mesure priorisée pour les trois pilotes polymères, avec procédure
  de passation, règles de confidentialité et brief CT optionnel.

Environnement de calcul :

- deux images conteneurs, `recon` (CUDA) et `cadsim` (CPU), avec test de fumée ;
- chaîne d’outils réorientée vers des commandes et API scriptables (ADR 0002) ;
- procédure de déploiement sur machine GPU louée et règles d’hygiène des données.

Phase 1, lot 7 — manuel et données Porsche Fanatics, 30 août 2026 :

- pont de provenance vers l’index public Porsche Fanatics : 235 procédures,
  195 couples de serrage et 111 données techniques ;
- cartographie française des pages et valeurs du manuel, avec séparation des
  variantes ROW/USA, Carrera/Carrera 4/Carrera 4S et Carrera RS ;
- ajout d’une piste Printables pour la patte d’interrupteur de console 964/993,
  sans copie du fichier et avec licence encore non vérifiée ;
- registre quantitatif exhaustif ajouté : 111 données techniques, 195 couples et
  2 190 occurrences OCR avec page, contexte court et statut de contrôle.
- import de ces 2 496 spécifications dans `catalog/measurements/` comme fiche
  documentaire séparée ; aucune séance physique n'est créée sans pièce,
  instrument et lectures brutes.

Traçabilité des mesures :

- schéma, validateur et registre des séances de mesure ;
- capture directe depuis un instrument à sortie données, ou saisie manuelle
  explicitement marquée comme telle ;
- prise de vue photogrammétrique avec manifeste et référence d’échelle obligatoire.

## 0.1.0 — 2026-08-28

Première fondation publique du projet :

- charte, feuille de route, règles de sécurité et portes qualité ;
- chaîne d’outils gratuite et open source ;
- schémas et modèles pour les pièces, sources, mesures et fabrications titane ;
- validateurs locaux, tests automatisés et intégration continue GitHub ;
- registre initial de cinq sources et workflow de contribution.

Aucune pièce n’est déclarée imprimable, ajustée ou validée dans cette version.
