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

- [x] Recenser catalogues officiels, manuels légalement accessibles et mesures
- [ ] Recenser les modèles 3D avec licence vérifiable
- [ ] Classer les références par variante, année et disponibilité
- [ ] Identifier les pièces manquantes ou difficiles à obtenir
- [ ] Évaluer chaque source : provenance, licence, précision, réutilisation

Critère de sortie : vingt candidats documentés, sans importer de contenu non
autorisé. Avancement : dix-huit fiches valides dans `catalog/sources/`.

## Phase 2 — Pilotes polymères

Trois pièces non critiques sélectionnées, fiches créées au statut `concept` :

| Catégorie | Pièce | Fiche |
|---|---|---|
| Géométrique simple, pied à coulisse | Cache d'emplacement d'interrupteur | `993-INT-SWITCH-BLANK-0001` |
| Organique, photogrammétrie | Poignée de tirage de porte | `993-INT-DOOR-PULL-0001` |
| Symétrique ou absente | Cache de glissière de siège | `993-INT-SEAT-RAIL-COVER-0001` |

- [x] Sélectionner trois pièces non critiques
- [x] Écrire un plan de mesure par pièce
- [x] Écrire la géométrie maîtresse pilotée par les mesures (pièce 1)
- [ ] Mesurer les trois pièces sur véhicule
- [ ] Imprimer et monter les prototypes
- [ ] Photographier et consigner les écarts

Critère de sortie : trois prototypes montés, photographiés et mesurés.

Les trois dernières puces demandent l'accès physique au véhicule et aux pièces.
Aucune cote n'est estimée en attendant : `parts/993-int-switch-blank-0001/source/switch_blank.py`
refuse de se construire tant que les sept cotes qu'il exige ne sont pas mesurées.

## Phase 3 — Pilote titane

Candidat à l'étude : **berceau moteur `993-ENG-CARRIER-0001`** (993 115 021 53).
Pièce présumée critique au sens de `SAFETY.md`. Le bénéfice du titane n'est pas
acquis : à géométrie identique, la pièce serait environ deux fois plus souple
qu'en acier. Cas de charge et comparaison de procédés à remplir dans
`parts/993-eng-carrier-0001/evidence/load-cases.md` avant toute géométrie.

- [ ] Choisir une pièce où Ti-6Al-4V apporte un bénéfice réel
- [ ] Comparer LPBF, CNC, tôle et fonderie
- [ ] Définir charges, interfaces, environnement et durée de vie
- [ ] Réaliser FEA et revue de fabricabilité avec un prestataire
- [ ] Prototyper en polymère puis, si utile, en aluminium économique
- [ ] Fabriquer un premier exemplaire Ti-6Al-4V traçable

Critère de sortie : rapport matière, fabrication, contrôle et essai disponible.

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
