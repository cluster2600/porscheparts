# 3dprinting993

Projet ouvert de rétroconception et de fabrication de pièces pour la Porsche
911 type 993, avec un accent particulier sur les pièces en titane fabriquées par
fusion laser sur lit de poudre (LPBF/DMLS).

Le dépôt ne cherche pas à produire immédiatement une voiture numérique complète.
Il construit une bibliothèque traçable de composants : sources, mesures, CAO
paramétrique, prototypes, fichiers de fabrication et preuves de validation.

## Principes

- **Source avant STL** : FreeCAD, OpenSCAD ou STEP restent les formats maîtres.
- **Preuve avant publication** : chaque affirmation de compatibilité ou de
  précision doit être reliée à une mesure ou une source.
- **Prototype avant métal** : tout montage est validé en polymère avant une
  fabrication titane coûteuse.
- **Sécurité explicite** : une pièce critique reste bloquée tant que son analyse,
  son procédé et ses essais ne sont pas approuvés.
- **Outils accessibles** : la chaîne locale utilise en priorité des logiciels
  gratuits et open source. La préparation machine LPBF et la fabrication finale
  peuvent dépendre du prestataire industriel.

## Démarrage rapide

Prérequis : Python 3.11 ou plus récent et `make`.

```bash
make check
cp templates/part-record.json catalog/parts/993-xxx-0001.json
```

Compléter ensuite la fiche, ajouter les fichiers CAO autorisés dans
`parts/<part_id>/`, puis relancer `make check`.

## Organisation

```text
catalog/parts/       fiches structurées des pièces
catalog/sources/     registre des sources, droits et niveaux de preuve
catalog/measurements/ séances de mesure, instruments et incertitudes
parts/               géométries et livrables par pièce
schemas/             contrat de données du catalogue
containers/          images de calcul reproductibles, GPU et CPU
templates/           modèles de fiche, mesure et demande de fabrication
docs/                plan, outils, workflows et critères qualité
scripts/             contrôles automatiques sans dépendance externe
tests/               tests du catalogue et de ses garde-fous
```

## État

La **Phase 0 — Fondation** est terminée. La **Phase 1 — Inventaire des
sources** est engagée : catalogues officiels, manuels accessibles et sources de
mesure sont recensés dans `catalog/sources/`
(voir [l’inventaire général](docs/PHASE1_SOURCE_INVENTORY.md) et le
[lot de recherche allemande](docs/research/phase-1-recherche-allemande.md)).
Ce lot germanophone documente vingt candidats supplémentaires ou recoupés.
Aucune pièce n’est encore déclarée imprimable ou validée. Voir
[ROADMAP.md](ROADMAP.md) et
[docs/PROJECT_CHARTER.md](docs/PROJECT_CHARTER.md).

## Avertissement

Ce dépôt fournit des données de recherche et de fabrication sans garantie.
L’impression, le montage et l’utilisation sur route restent sous la
responsabilité de la personne qui fabrique et installe la pièce. Lire
[SAFETY.md](SAFETY.md) avant toute fabrication.

Porsche et 911 sont des marques de leurs détenteurs respectifs. Ce projet est
indépendant et non affilié à Porsche AG.

## Licence

Les contributions originales du dépôt sont sous licence MIT sauf indication
contraire dans la fiche d’une pièce. Les sources et modèles tiers conservent
leur propre licence. Voir [LICENSES.md](LICENSES.md).
