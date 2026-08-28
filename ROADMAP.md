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

- [ ] Recenser catalogues officiels, manuels légalement accessibles et mesures
- [ ] Recenser les modèles 3D avec licence vérifiable
- [ ] Classer les références par variante, année et disponibilité
- [ ] Identifier les pièces manquantes ou difficiles à obtenir
- [ ] Évaluer chaque source : provenance, licence, précision, réutilisation

Critère de sortie : vingt candidats documentés, sans importer de contenu non
autorisé.

## Phase 2 — Pilotes polymères

Sélectionner trois pièces non critiques :

1. une pièce géométrique simple mesurable au pied à coulisse ;
2. une pièce organique nécessitant scan ou photogrammétrie ;
3. une pièce symétrique ou absente reconstruite depuis son environnement.

Critère de sortie : trois prototypes montés, photographiés et mesurés.

## Phase 3 — Pilote titane

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
