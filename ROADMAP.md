# Feuille de route

## Phase 0 — Fondation

Statut : **terminée le 28 août 2026** (`v0.1.0`).

Objectif : rendre le projet contributif avant d’ajouter une pièce.

- [x] Charte et limites de sécurité
- [x] Chaîne d’outils gratuite et ouverte
- [x] Schéma de fiche pièce
- [x] Modèles de mesure et de fabrication titane
- [x] Validation automatique du catalogue
- [x] Templates GitHub de contribution

Critère de sortie : `make check` réussit sur un dépôt propre.

## Phase 1 — Inventaire des sources

Journal détaillé : [docs/PHASE1_SOURCE_INVENTORY.md](docs/PHASE1_SOURCE_INVENTORY.md).

Recherche complémentaire : [lot germanophone de vingt candidats](docs/research/phase-1-recherche-allemande.md).

- [x] Recenser catalogues officiels, manuels légalement accessibles et mesures
- [x] Recenser les modèles 3D avec licence vérifiable
- [ ] Classer les références par variante, année et disponibilité
- [ ] Identifier les pièces manquantes ou difficiles à obtenir
- [ ] Évaluer chaque source : provenance, licence, précision, réutilisation

Critère de sortie : vingt candidats documentés, sans importer de contenu non
autorisé. Avancement : cinquante-neuf fiches valides dans `catalog/sources/` ;
le seuil quantitatif est atteint, mais la qualification croisée reste ouverte.

## Phase 2 — Inventaire physique et assemblage du jumeau

Architecture : [docs/DIGITAL_TWIN.md](docs/DIGITAL_TWIN.md).

Mode actif : **aucune impression**. Le jumeau est alimenté par les composants
dont la taille, la matière, la masse et l'application sont toutes sourcées. Les
relations de montage sont enregistrées séparément des transformations spatiales.

- [x] Définir les niveaux de fidélité `F0` à `F4`
- [x] Créer le registre, le schéma et les validations des sous-jumeaux
- [x] Créer les registres de composants physiques et d'assemblages
- [x] Admettre le premier lot taille + matière + masse : roues Fuchs 17 pouces
- [x] Assembler logiquement les paires avant et arrière documentées
- [x] Ajouter les roues Fuchs 18 pouces et leur interface 5x130 / 71,5 mm
- [x] Compléter l'interface des roues Fuchs 17 pouces depuis les homologations KBA
- [x] Documenter le blocage des pneus Michelin PS2 N3 faute de matière et masse fabricant cohérentes
- [x] Qualifier les disques Carrera Brembo/ATE et documenter leur blocage faute de masse nette et nuance complète
- [x] Rechercher les travaux CAO/3D communautaires et qualifier les gabarits de pare-brise, la bague de siège et un scan complet
- [ ] Étendre l'inventaire par familles de sous-ensembles
- [ ] Compléter les interfaces nécessaires au positionnement spatial
- [ ] Générer les assemblages STEP/FreeCAD lorsque les transformations sont connues
- [ ] Calculer masse et centre de gravité des assemblages positionnés

Critère de sortie : un premier sous-ensemble multi-composants positionné dans le
repère véhicule, avec masse, matière, interfaces, incertitudes et relations
sourcées pour chaque composant.

### Prototypes physiques — suspendus

Trois pièces non critiques sélectionnées, fiches créées au statut `concept` :

| Catégorie | Pièce | Fiche |
|---|---|---|
| Géométrique simple, pied à coulisse | Cache d'emplacement d'interrupteur | `993-INT-SWITCH-BLANK-0001` |
| Organique, photogrammétrie | Poignée de tirage de porte | `993-INT-DOOR-PULL-0001` |
| Symétrique ou absente | Cache de glissière de siège | `993-INT-SEAT-RAIL-COVER-0001` |

- [x] Sélectionner trois pièces non critiques
- [x] Écrire un plan de mesure par pièce
- [x] Écrire la géométrie maîtresse pilotée par les mesures (pièce 1)
- [ ] Reprendre uniquement après décision explicite de sortir du mode numérique

Les plans existants sont conservés comme backlog ; ils ne pilotent plus la phase
active et aucun fichier de fabrication n'est généré.

Les plans historiques demandent l'accès physique au véhicule et aux pièces.
Aucune cote n'est estimée en attendant : `parts/993-int-switch-blank-0001/source/switch_blank.py`
refuse de se construire tant que les sept cotes qu'il exige ne sont pas mesurées.

## Phase 3 — Jumeau d'ingénierie titane, sans fabrication

Candidat à l'étude : **berceau moteur `993-ENG-CARRIER-0001`** (993 115 021 53).
Pièce présumée critique au sens de `SAFETY.md`. Le bénéfice du titane n'est pas
acquis : à géométrie identique, la pièce serait environ deux fois plus souple
qu'en acier. Cas de charge et comparaison de procédés à remplir dans
`parts/993-eng-carrier-0001/evidence/load-cases.md` avant toute géométrie.

- [ ] Choisir une pièce où Ti-6Al-4V apporte un bénéfice réel
- [ ] Comparer LPBF, CNC, tôle et fonderie
- [ ] Définir charges, interfaces, environnement et durée de vie
- [ ] Réaliser FEA et revue de fabricabilité avec un prestataire
- [ ] Intégrer géométrie, charges et résultats au niveau `F3_engineering`
- [ ] Corréler au moins un cas de calcul à un essai physique
- [ ] Construire le composant titane virtuel avec matière et procédé documentés
- [ ] Comparer numériquement les variantes acier, aluminium et Ti-6Al-4V

Critère de sortie : rapport matière, masse, rigidité, fatigue et fabricabilité
numérique disponible. Toute fabrication reste hors de la phase active.

## Phase 4 — Catalogue public

- [ ] Publier uniquement les pièces ayant franchi leurs portes qualité
- [ ] Générer les pages de catalogue depuis les fiches JSON
- [ ] Ajouter vues, plans cotés et instructions de fabrication
- [ ] Suivre versions, véhicules testés et retours terrain

## Hors périmètre initial

- Commercialisation de pièces
- Homologation routière
- Hébergement de manuels ou scans protégés
- Publication de pièces critiques non qualifiées
- Achat ou exploitation d’une machine LPBF
- Modèle IA de substitution avant l’existence d’un corpus FEA/CFD cohérent
