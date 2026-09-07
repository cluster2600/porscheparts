# 3dprinting993

Projet ouvert de rétroconception et de fabrication de pièces pour la Porsche
911 type 993, avec un accent particulier sur les pièces en titane fabriquées par
fusion laser sur lit de poudre (LPBF/DMLS).

Le dépôt construit un **jumeau numérique fonctionnel** de la 993 par zones
d'interface. Il ne cherche pas d'abord une carrosserie visuellement complète :
il assemble des géométries hôtes, des pièces candidates, leurs mesures,
tolérances et règles de contrôle afin de tester le montage avant impression.
Chaque zone validée rejoint progressivement le jumeau global.

Deux vues complémentaires structurent ce travail :

- le **jumeau structurel** décrit chaque pièce par sa référence, sa place dans
  l'assemblage, sa variante, sa masse, sa matière et son encombrement, tous
  reliés à des sources vérifiables ;
- le **jumeau géométrique** porte les interfaces et la CAO nécessaires au
  contrôle d'ajustement. Il exige des mesures physiques ou une donnée acquise et
  progresse donc pièce par pièce.

La couverture documentaire se mesure avec :

```bash
python3 scripts/twin_coverage.py
```

La géométrie rectangulaire F34 de culasse quatre soupapes refroidie par air est
retirée comme produit et conservée uniquement comme régression numérique dans
[docs/917_AIRCOOLED_4V_F34.md](docs/917_AIRCOOLED_4V_F34.md). Elle réunit la CAO
paramétrique, les calculs OpenFOAM/FluidX3D, CalculiX, Cantera/Wiebe et le prévol
Omniverse, sans preuve transférable à une vraie culasse. La correction
[F36](docs/917_SCAN_CONFORMING_4V_F36.md) conserve la morphologie du scan 935,
remplace le coeur par une architecture quatre soupapes et ferme toutes les
portes de calcul physique jusqu'à la revue de forme.
La [définition F37](docs/917_F37_MANUFACTURING_DEFINITION.md) ajoute les STEP
fonctionnels, la lubrification, le porte-axes, les criblages et leurs preuves
SHA-256, tout en maintenant l'impression métal et le démarrage interdits.
Son [audit Omniverse / SimReady](docs/917_F37_OMNIVERSE_SIMREADY.md) publie le
rendu GPU final et conserve l'avertissement topologique NVIDIA comme blocage.
L'[audit moteur mobile](docs/917_F37_ICE_ENGINE_FOAM.md) exécute le remplaçant
OpenFOAM 13 disponible sur un tutoriel deux soupapes, sans le présenter comme
une simulation de la géométrie F37.

La couverture massique dit quelle part de la masse à vide est décrite par des
pièces dont la masse est documentée et sourcée. Elle ne vaut ni validation
géométrique, ni preuve de montage.

Pour le circuit de suralimentation, voir aussi
[docs/TURBO_AIRFLOW_SIMULATION_DATA.md](docs/TURBO_AIRFLOW_SIMULATION_DATA.md) :
il rassemble l'identification K16, les interfaces PET, les dimensions
fournisseurs et la première enveloppe de débit calculée avec ses hypothèses.

## Principes

- **Source avant STL** : FreeCAD, OpenSCAD ou STEP restent les formats maîtres.
- **Preuve avant publication** : chaque affirmation de compatibilité ou de
  précision doit être reliée à une mesure ou une source.
- **Numérique avant prototype** : la phase active ne fabrique rien ; composants
  et assemblages sont d'abord construits à partir de dimensions, matière, masse
  et relations sourcées.
- **Interface avant apparence** : une zone mesurée permettant un contrôle de jeu
  vaut plus qu'un scan complet sans précision connue.
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
catalog/manual/      registre quantitatif dérivé du manuel 993, avec pages
catalog/specifications/ spécifications documentaires et provenance d'extraction
catalog/measurements/ mesures physiques et valeurs documentaires qualifiées
catalog/reference/   ossature documentaire et données de référence déclarées
catalog/twins/       fiches des zones du jumeau et règles d'acceptation
catalog/components/  composants dont taille, matière et masse sont sourcées
catalog/assemblies/  relations de montage sourcées entre composants
parts/               géométries et livrables par pièce
twin/                enveloppes et repères paramétriques globaux
twins/               zones fonctionnelles, scripts et rapports numériques
schemas/             contrat de données du catalogue
containers/          images de calcul reproductibles, GPU, CPU et Physics ML
templates/           modèles de fiche, mesure et demande de fabrication
docs/                plan, outils, workflows et critères qualité
scripts/             contrôles automatiques sans dépendance externe
tests/               tests du catalogue et de ses garde-fous
```

## État

La **Phase 0 — Fondation** est terminée. La **Phase 1 — Inventaire des
sources** a dépassé son seuil quantitatif avec 294 fiches valides, mais la
qualification croisée et l'acquisition de mesures directes restent ouvertes
(voir [l’inventaire général](docs/PHASE1_SOURCE_INVENTORY.md) et le
[lot de recherche allemande](docs/research/phase-1-recherche-allemande.md)). La
[cartographie du manuel 993](docs/993_MANUAL_DATA_MAP.md) relie désormais les
données publiques de Porsche Fanatics aux pages techniques du manuel. Les
spécifications sont importées dans le registre de mesures avec leur statut
documentaire, sans importer le PDF ni les présenter comme des relevés physiques.

La **Phase 2 — Inventaire physique et assemblage du jumeau** est menée en mode
numérique. Une première enveloppe paramétrique de référence est disponible dans
[`twin/993/`](twin/993/) et les premières zones fonctionnelles sont suivies dans
[docs/DIGITAL_TWIN.md](docs/DIGITAL_TWIN.md). Ces géométries ne prétendent pas
reconstruire la carrosserie ni prouver un montage.
Aucun jumeau n'est encore au niveau `F2_interface` et aucune pièce n'est encore
déclarée imprimable ou validée. L'impression est volontairement suspendue. Le
premier inventaire physique est décrit dans
[docs/COMPONENT_INVENTORY.md](docs/COMPONENT_INVENTORY.md). Voir
[la stack logicielle vérifiée](docs/SOFTWARE_STACK.md),
[la suite libre LLM/CAO et son déploiement Vast.ai](docs/AI_DIGITAL_TWIN_STACK.md),
[ROADMAP.md](ROADMAP.md) et
[docs/PROJECT_CHARTER.md](docs/PROJECT_CHARTER.md).

![État sourcé du jumeau numérique 993](diagrams/digital-twin-993-etat.svg)

Ce schéma représente les relations logiques actuellement sourcées, pas la
position réelle des composants dans la voiture. La recherche des modèles CAO,
scans et fichiers communautaires est suivie dans
[docs/research/phase-2-cao-forums-993.md](docs/research/phase-2-cao-forums-993.md).

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
