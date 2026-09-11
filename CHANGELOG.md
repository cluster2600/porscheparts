# Journal des versions

Toutes les évolutions notables du projet sont consignées dans ce fichier.

## Non publié

Triages titane du catalogue d'usine, 11 septembre 2026 :

- constat que le criblage titane portait sur 32 fiches, soit 0,51 % des 6 259
  références distinctes du catalogue 993 : « appliqué au catalogue » était une
  surestimation du périmètre, corrigée en addendum de la décision 0007 ;
- `screen_pet_zones_for_titanium.py` trie les 239 illustrations du squelette
  avec les seules données du dépôt, 23 zones retenues sur 1 538 références ;
- `screen_pet_parts_for_titanium.py` trie 1 026 désignations depuis un relevé
  tenu hors du dépôt, 70 retenues, en ne publiant que la liste courte ;
- l'embout d'échappement ressort dans les quatre premiers du triage élargi, les
  deux désignations qui le devancent tombant sur la température d'échappement ;
- règle d'exclusion par planche corrigée : elle ne joue que si toutes les
  planches d'une désignation sont critiques, faute de quoi `oil pipe`
  disparaissait à tort.

Décision 0007, première pièce titane sélectionnée par grille, 11 septembre 2026 :

- `scripts/screen_titanium_candidates.py` applique la grille de `TITANIUM.md`
  et les trois familles additives aux 32 fiches, en refusant de tourner si une
  fiche n'est pas jugée ; cinq pièces seulement sont éligibles ;
- `993-EXH-OVAL-TIP-TI-F1-0001` retenue à +6, le collecteur d'échappement étant
  écarté malgré son +7 parce que 900 °C est un cas nickel ;
- générateur d'embout paramétré par `--material`, une géométrie et trois cartes
  matière, avec export STL et verdict de température ;
- étape 02 `passed`, étape 03 `completed_screening` à 4 936 couches de 30 µm ;
- deux cartes de route titane mutuellement exclusives : le Ti-6Al-4V est
  disponible partout et bloqué par une marge de −27 °C, le Ti-6242 passe la
  température et n'a ni machine, ni épaisseur de couche, ni fournisseur ;
- porte de température générique ajoutée à `build_process_route_card.py` ;
- constat : la décision tient à 427 °C jamais mesurés, et un thermomètre
  infrarouge tranche ce que douze mille lignes de calcul ne trancheront pas.

Décision 0006, la bague sera tournée en 6063 T6, 11 septembre 2026 :

- carte de route tournage `cnc-turning-6063-t6-bright-anodised.json`, nuance
  choisie sur l'aspect avec le 6061 T6 en repli et le 6262 écarté pour son plomb ;
- générateur `scripts/build_turning_route_card.py` et devis tournage associé,
  cibles `turning-trim-ring` et `turning-trim-ring-check` ;
- `preferred_process` de la bague passé de `undecided` à `CNC`, le LPBF restant
  un candidat screené ;
- jumeau renommé `twins/993-switch-trim-ring-f1`, le nom de dossier n'affirmant
  plus une matière que le dépôt a écartée ;
- constat enregistré : changer de procédé n'a fermé aucune des deux portes qui
  comptent, la cote d'ajustement non tolérancée et les arêtes non définies.

Décision 0005, la matière de la bague n'a jamais été choisie, 11 septembre 2026 :

- constat que l'AlSi10Mg est hérité de la seule carte procédé du dépôt, et que
  la bague est le seul candidat LPBF `non_critical` du catalogue ;
- deux sources sur l'anodisation : l'AlSi10Mg s'anodise gris-brun du fait de ses
  9 à 11 % de silicium, quand le 6063 T6 est excellent en anodisation brillante ;
- conséquence enregistrée : pour cette pièce la question matière et la question
  procédé n'en font qu'une, et la réponse probable est une barre 6xxx tournée.

Première passe de sourcing LPBF en Chine, 10 septembre 2026 :

- quatre fiches de sources qualifiées pour Unionfab, JLC3DP et Eplus3D ;
- Unionfab retenu comme unique candidat, JLC3DP écarté faute d'AlSi10Mg
  au catalogue métal ;
- trois contradictions enregistrées et non lissées : trois épaisseurs de
  couche pour le même sujet dont deux chez le même fournisseur, une carte
  matière prestataire très inférieure aux coupons EOS, et une règle de paroi
  minimale que la bague passe chez l'un et pas chez l'autre.

Carte matière-machine-procédé de la bague de commodo, étape 04, 10 septembre 2026 :

- ajout de `scripts/build_process_route_card.py`, générateur générique d'une
  carte de route et d'un dossier de demande de devis lié aux fichiers par
  SHA-256, avec onze portes évaluées et un mode `--check` ;
- première étape 04 du pipeline AM, sur `993-INT-SWITCH-TRIM-RING-F1-0001`,
  conclue `blocked_missing_input` avec sept portes fermées ;
- mise au jour d'une incohérence interne : le criblage de l'étape 03 tranche à
  50 µm quand la seule route AlSi10Mg publiée sur EOS M 290 est à 30 µm ;
- cibles `route-trim-ring` et `route-trim-ring-check`, et garde
  `tests/test_993_switch_trim_ring_route_f1.py` qui échoue si une porte
  s'ouvrait sans coupon, traitement thermique ni lot de poudre.

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
