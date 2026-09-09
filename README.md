# porscheparts

Projet ouvert de rétroconception pour Porsche 911 **964** et **993**.

Ce que le dépôt produit n'est pas une bibliothèque de fichiers à imprimer. Ce
sont des **données sourcées** et des **calculs réfutables** : chaque affirmation
de compatibilité, de masse ou de raideur est reliée à une mesure, à une source
vérifiable ou à un calcul qu'on peut rejouer — et retirée quand elle ne tient
plus. Le dépôt en compte plusieurs, retirées ici même, plus bas.

La phase active **ne fabrique rien**.

## Ce que fait le projet aujourd'hui

### 1. Calcul de structure sur la caisse 964

Le chantier principal. Un modèle coque de plancher, de caisson et de cellule
complète, en éléments finis, sert à répondre à des questions **relatives** :
entre changer de matériau et fermer la caisse, lequel rapporte le plus ? Que
vaut un élément de superstructure au kilo ? Où passe l'effort en torsion ?

Résultats qui tiennent — voir [`twins/964-chassis/fea/`](twins/964-chassis/fea/) :

- le **longeron** porte la torsion, pas le plancher, ce qui converge avec la
  planche 50-013 du manuel qui y place l'acier haute résistance ;
- **fermer un anneau ne fait pas qu'ajouter de la raideur, cela change le
  mécanisme qui la porte** — flexion sur le plancher nu, cisaillement sur la
  cellule fermée ;
- du plancher nu à la cellule fermée, **K × 3,77 pour une masse × 2,3** ;
- pavillon et cadre de baie ensemble valent **1,63 fois** la somme de leurs
  apports séparés : le pavillon ne travaille qu'une fois l'anneau fermé.

Un **corpus de 3 000 cas** CalculiX, en coques quadratiques, est constitué pour
entraîner plus tard un substitut de conception, avec son lot de validation gelé
avant qu'aucun modèle n'existe. Chaîne et état :
[docs/MONOCOQUE_964_993_CHAINE_CALCUL.md](docs/MONOCOQUE_964_993_CHAINE_CALCUL.md).

Le [programme monocoque](docs/MONOCOQUE_964_993_PROGRAMME.md) définit ce qu'il
faudrait établir pour concurrencer une offre existante sur le seul axe où elle
est nue : la donnée publiée. Il **contredit le périmètre écrit** de
[ROADMAP.md](ROADMAP.md), et le dit.

### 2. Pièces candidates

Les panneaux **boulonnés** — ailes, capots, becquet, portes — sont un objectif
légitime ; la structure autoportante ne l'est pas. Le catalogue d'usine trace la
frontière en numéros de pièce :
[docs/research/993-964-panneaux-carbone.md](docs/research/993-964-panneaux-carbone.md).

Mais ces panneaux se commandent déjà chez plusieurs préparateurs. La pièce
retenue est donc celle que personne ne vend : l'**habillage de planche de bord**,
`993-INT-DASHBOARD-TRIM-0001`, restreint aux véhicules **sans airbag passager**
— sur les autres, il porte le volet de déploiement, donc une pièce de retenue des
occupants. Son [plan de mesure](parts/993-int-dashboard-trim-0001/evidence/measurement-plan.md)
commence par une porte d'entrée qui peut arrêter le projet.

Trois pilotes d'habitacle plus simples restent en attente d'une séance de mesure
physique : [docs/MEASUREMENT_CAMPAIGN.md](docs/MEASUREMENT_CAMPAIGN.md).

### 3. Le catalogue, et son contrat de données

**318 fiches de sources** qualifiées par provenance, droits et niveau de preuve ;
9 fiches de pièces, 4 composants, 2 assemblages, 3 zones de jumeau. Tout est
validé par un schéma JSON et des tests :

```bash
make check
```

Une fiche enregistre séparément l'accès technique, la méthode de lecture et le
droit de réutilisation. Une page accessible n'est pas redistribuable ; une page
lue dans un navigateur n'est ni un téléchargement autorisé ni une validation de
précision.

## Les règles

- **Source avant STL** : FreeCAD, OpenSCAD, build123d ou STEP restent les formats
  maîtres.
- **Preuve avant publication** : toute affirmation de compatibilité ou de
  précision est reliée à une mesure ou à une source.
- **Numérique avant prototype** : la phase active ne fabrique rien.
- **Interface avant apparence** : une zone mesurée permettant un contrôle de jeu
  vaut mieux qu'un scan complet sans précision connue.
- **Sécurité explicite** : en cas de doute, la pièce est abaissée à
  `prohibited_pending_engineering`. Voir [SAFETY.md](SAFETY.md).
- **Pas de moissonnage de vendeurs** : un site fermé aux robots n'est pas
  interrogé, voir [docs/decisions/0003-no-vendor-harvesting.md](docs/decisions/0003-no-vendor-harvesting.md).
- **Outils accessibles** : chaîne locale gratuite et open source.

## Ce que le dépôt a retiré de ses propres résultats

C'est la partie la plus utile de son historique, et elle est publique.

| affirmation retirée | ce qui l'a défaite |
|---|---|
| « la structure travaille en cisaillement de membrane » | un essai découplant `E` et `G` : le plancher nu travaille en flexion quasi pure |
| « la raideur suit l'épaisseur exactement linéairement » | l'exposant vaut 1,00 en éléments linéaires et **1,10** en quadratiques : l'exactitude était celle de l'élément |
| « le cadre de pare-brise a le meilleur rendement au kilo » | en coques quadratiques, c'est le tunnel central |
| une traverse comptée dans la masse du modèle | un contrôle de connexité : elle n'était rattachée à rien |
| onze cas de calcul perdus, lus comme un système quasi singulier | un défaut du partitionneur du solveur, dont le message partait sur `stderr` |

Trois calculs faux de cette campagne venaient d'un **partage de ressource** —
fichiers de travail laissés en place, maillage commun à deux campagnes, machine
partagée. Aucun n'avait laissé de trace dans une sortie d'erreur.

## Ce que le projet ne prétend pas

- **Aucune valeur absolue de raideur n'est une raideur de 964.** Les sections du
  modèle sont `ASSUMED`, le maillage n'est pas convergé ; seuls les rapports et
  les classements sont exploitables.
- **Aucune pièce n'est déclarée imprimable ni validée.** Aucun jumeau n'atteint
  le niveau `F2_interface`.
- **Aucune mesure physique n'est encore enregistrée** dans
  `catalog/measurements/` : le dépôt n'a accès ni à une 993, ni à une pièce
  déposée, ni à un instrument.
- **Un rendu n'est pas une preuve.** Ni Omniverse, ni une image, ni une photo ne
  démontrent un comportement physique.

## Autres dossiers

- **Culasse 917 refroidie par air** : retirée comme produit, conservée comme
  régression numérique. [F34](docs/917_AIRCOOLED_4V_F34.md) réunit CAO
  paramétrique, OpenFOAM/FluidX3D, CalculiX et Cantera sans preuve transférable ;
  [F36](docs/917_SCAN_CONFORMING_4V_F36.md) conserve la morphologie du scan 935 ;
  [F37](docs/917_F37_MANUFACTURING_DEFINITION.md) ajoute STEP fonctionnels et
  preuves SHA-256, impression métal et démarrage restant interdits.
- **Circuit de suralimentation 993** : identification K16, interfaces et première
  enveloppe de débit —
  [docs/TURBO_AIRFLOW_SIMULATION_DATA.md](docs/TURBO_AIRFLOW_SIMULATION_DATA.md).
- **Couverture documentaire du jumeau** : `python3 scripts/twin_coverage.py`. La
  couverture massique dit quelle part de la masse à vide est décrite par des
  pièces dont la masse est sourcée. Elle ne vaut ni validation géométrique, ni
  preuve de montage.

## Démarrage rapide

Prérequis : Python 3.11 ou plus récent et `make`.

```bash
make check
cp templates/part-record.json catalog/parts/993-xxx-0001.json
```

Compléter la fiche, ajouter les fichiers CAO autorisés dans `parts/<part_id>/`,
relancer `make check`.

## Organisation

```text
catalog/parts/          fiches structurées des pièces
catalog/sources/        registre des sources, droits et niveaux de preuve
catalog/manual/         registre quantitatif dérivé du manuel 993, avec pages
catalog/specifications/ spécifications documentaires et provenance d'extraction
catalog/measurements/   mesures physiques et valeurs documentaires qualifiées
catalog/reference/      ossature documentaire et données de référence déclarées
catalog/twins/          fiches des zones du jumeau et règles d'acceptation
catalog/components/     composants dont taille, matière et masse sont sourcées
catalog/assemblies/     relations de montage sourcées entre composants
parts/                  géométries, plans de mesure et livrables par pièce
twins/964-chassis/      jumeau de châssis 964 : datums, CAO et calculs
twins/964-chassis/fea/  essais de torsion, stratifiés, plan d'expériences
twin/                   enveloppes et repères paramétriques globaux
schemas/                contrat de données du catalogue
containers/             images de calcul reproductibles, GPU, CPU et Physics ML
templates/              modèles de fiche, mesure et demande de fabrication
docs/                   plan, outils, workflows et critères qualité
scripts/                contrôles automatiques sans dépendance externe
tests/                  tests du catalogue et de ses garde-fous
```

## État

Phase 0 terminée. Phase 1 au-delà de son seuil quantitatif, la qualification
croisée et les mesures directes restant ouvertes. Phase 2 menée en mode
numérique, l'impression volontairement suspendue. Détail et critères de sortie :
[ROADMAP.md](ROADMAP.md), [docs/PROJECT_CHARTER.md](docs/PROJECT_CHARTER.md),
[docs/DIGITAL_TWIN.md](docs/DIGITAL_TWIN.md),
[docs/QUALITY_GATES.md](docs/QUALITY_GATES.md).

![État sourcé du jumeau numérique 993](media/diagrams/digital-twin-993-etat.svg)

Ce schéma représente les relations logiques sourcées, pas la position réelle des
composants dans la voiture.

## Avertissement

Ce dépôt fournit des données de recherche et de fabrication sans garantie.
L'impression, le montage et l'utilisation sur route restent sous la
responsabilité de la personne qui fabrique et installe la pièce. Lire
[SAFETY.md](SAFETY.md) avant toute fabrication.

Porsche et 911 sont des marques de leurs détenteurs respectifs. Ce projet est
indépendant et non affilié à Porsche AG.

## Licence

Les contributions originales du dépôt sont sous licence MIT sauf indication
contraire dans la fiche d'une pièce. Les sources et modèles tiers conservent leur
propre licence. Voir [LICENSES.md](LICENSES.md).
