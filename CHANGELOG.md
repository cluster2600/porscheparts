# Journal des versions

Toutes les évolutions notables du projet sont consignées dans ce fichier.

## Non publié

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
