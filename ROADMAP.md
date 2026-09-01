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
- [x] Classer les références par variante, année et disponibilité
- [x] Identifier les pièces manquantes ou difficiles à obtenir
- [x] Évaluer chaque source : provenance, licence, précision, réutilisation

Critère de sortie : vingt candidats documentés, sans importer de contenu non
autorisé. Avancement : 294 fiches de sources valides dans `catalog/sources/` ;
l'acquisition de mesures directes reste à faire.

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

Plan d'exécution et dossier de passation :
[docs/MEASUREMENT_CAMPAIGN.md](docs/MEASUREMENT_CAMPAIGN.md).

Les spécifications de préparation issues du manuel et de Porsche Fanatics sont
cartographiées dans [docs/993_MANUAL_DATA_MAP.md](docs/993_MANUAL_DATA_MAP.md).
Le registre exhaustif page par page est dans
[`catalog/manual/993-workshop-manual-measurements.json`](catalog/manual/993-workshop-manual-measurements.json).

Critère de sortie : trois prototypes montés, photographiés et mesurés.
**Conditionné à un contributeur disposant des pièces** : voir la contrainte
d'exploitation dans [docs/PROJECT_CHARTER.md](docs/PROJECT_CHARTER.md).

### Piste carrosserie ouverte en parallèle

`993-BODY-FRONT-LID-0001`, capot avant en composite. Retenu comme premier pilote
de carrosserie parce qu'il cumule quatre avantages : panneau **boulonné**, sans
fonction structurale ni barre anti-intrusion ; **surface unique à courbure
douce**, donc le moule le plus simple de la voiture ; **panneau d'origine en
acier**, donc gain réel, avec une référence à battre déjà établie par Porsche
Motorsport à 8 kg en aluminium ; et un **panneau donneur d'occasion peu coûteux**
pour prendre l'empreinte, contrairement aux pièces mécaniques rares.

Masses d'origine établies par une table comparative allemande
(`SRC-FEDERLEICHTE-ELFER-993-WEIGHTS`), ce qui permet enfin de chiffrer le
programme au lieu de l'estimer :

| Pièce | Origine | Carbone | Gain |
|---|---:|---:|---:|
| Capot avant | 14,0 kg | 4,1 kg | **9,9 kg** |
| Ailes avant, la paire | 14,4 kg | 4,4 kg | 10,0 kg |
| Becquet arrière | 12,5 kg | 4,8 kg | 7,7 kg |
| Pare-chocs arrière | 5,05 kg | 3,1 kg | 2,0 kg |
| Rétroviseurs, la paire | 1,8 kg | 0,25 kg | 1,6 kg |
| Bandeau de feux arrière | 1,26 kg | 0,26 kg | 1,0 kg |
| **Total** | **49,0 kg** | **16,9 kg** | **32,1 kg** |

Trente-deux kilos sans toucher à une seule pièce structurale ni supprimer un seul
élément de sécurité — contre 0,45 kg pour le berceau moteur en titane.

Deux lignes de cette table sont volontairement écartées. Les **portes**, 32,0 kg
contre 5,9 kg, affichent le plus gros gain du tableau, mais la version allégée est
une porte de course : le gain vient de la suppression des barres anti-intrusion,
du lève-vitre et du vitrage, pas de la matière. Le **pavillon**, 22,0 kg contre
2,5 kg, est un panneau soudé structural. Ni l'un ni l'autre n'est un remplacement
équivalent.

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

## Objectif transverse — couverture du jumeau numérique

L'avancement du jumeau se mesure en part de masse à vide décrite par des pièces
documentées et sourcées, via `make twin`.

| Jalon | Couverture | État |
|---|---:|---|
| Premier relevé | 30,5 % | atteint le 28 août 2026, 417,5 kg sur 1 370 kg |
| Carrosserie et habillage complets | ~45 % | en cours |
| Groupe motopropulseur détaillé | ~60 % | moteur global connu, pièces à détailler |
| Train roulant et freins | ~75 % | non commencé |
| Reste | 100 % | non commencé |

### Squelette d'assemblage — fait

Le catalogue d'usine a fourni l'ossature : dix systèmes, 239 illustrations,
12 864 références situées (`catalog/reference/993-assembly-skeleton.json`).

| Système | Références | Illustrations |
|---|---:|---:|
| 8xx Carrosserie et habillage | 4 553 | 85 |
| 1xx Moteur | 2 398 | 34 |
| 9xx Électricité et équipements | 1 499 | 29 |
| 3xx Boîte de vitesses | 1 368 | 34 |
| 6xx Freinage et hydraulique | 820 | 13 |
| 4xx Direction et train avant | 624 | 14 |
| 2xx Carburant et échappement | 611 | 11 |
| 7xx Commandes et embrayage | 494 | 8 |
| 5xx Train arrière et transmission | 326 | 7 |
| 0xx Consommables | 171 | 4 |

Deux couvertures cohabitent, et elles ne disent pas la même chose : **0,18 % des
références** portent une masse documentée, mais ces quelques pièces représentent
**30,5 % de la masse à vide**. Le jumeau se remplit par la masse avant de se
remplir par le nombre.

### Position — amorcé par une enveloppe de référence

Une masse sans position ne donne ni centre de gravité, ni répartition, ni
inertie. Une première cage 3D d'encombrement et de repères, basée sur sept
dimensions du manuel Porsche, est disponible dans
[`twin/993/`](twin/993/). Elle sert de datum visuel pour le profil USA, mais ne
reconstruit pas la carrosserie et ne positionne pas encore les pièces.

La suite est de remplacer cette cage par une géométrie de caisse sous licence ou
par un relevé à l'échelle, puis de rattacher les ancrages et sous-ensembles à
des mesures vérifiables.

## Phase 4 — Catalogue public

- [ ] Publier uniquement les pièces ayant franchi leurs portes qualité
- [ ] Générer les pages de catalogue depuis les fiches JSON
- [ ] Ajouter vues, plans cotés et instructions de fabrication
- [ ] Suivre versions, véhicules testés et retours terrain

## Hors périmètre initial

- Commercialisation de pièces
- Homologation routière
- **Remplacement de la structure autoportante**, notamment par un monocoque
  composite. La caisse porte le numéro de châssis, la protection des occupants et
  l'absorption de choc ; un monocoque se conçoit comme tel et ne se traduit pas
  depuis une caisse en tôle ; sa validation passe par des essais de choc
  physiques.

  Précision nécessaire : un tel monocoque **existe commercialement** pour 964 et
  993 (`SRC-ZESAD-CARBON-MONOCOQUE-964-993`), de 129 990 à 219 990 €. Il n'est
  donc pas exclu du périmètre parce qu'il serait impossible, mais parce que ce
  dépôt ne peut ni le documenter, ni le vérifier, ni le reproduire : la fiche
  produit ne publie ni masse, ni raideur en torsion, ni essai de choc, ni
  homologation. Une structure de sécurité sans donnée structurelle publiée est
  exactement ce que `docs/QUALITY_GATES.md` interdit d'inscrire au catalogue.

  Les panneaux de carrosserie, eux, restent un objectif légitime : voir
  `SRC-GUNTHER-WERKS-CARBON-993`, où le restomod de 993 le plus poussé du marché
  habille l'auto de carbone tout en conservant et renforçant la caisse acier.
- Hébergement de manuels ou scans protégés
- Publication de pièces critiques non qualifiées
- Achat ou exploitation d’une machine LPBF
- Modèle IA de substitution avant l’existence d’un corpus FEA/CFD cohérent
