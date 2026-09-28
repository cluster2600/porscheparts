# Données iCloud Porsche — intégration du 6 septembre 2026

Le dossier `iCloud Drive/ Businessai/Porsche` contient un classeur et trois
archives. Cet import conserve les apports documentaires dans le projet, avec
leurs empreintes et leur contexte. Il ne constitue pas une vérification nouvelle
des publications citées ni une autorité de dimensionnement.

## Données intégrées

Le [classeur extrait en JSON](../catalog/reference/icloud-porsche-2026-09-06/workbook-data.json)
conserve neuf feuilles, les adresses réelles des cellules, les unités, variantes,
tolérances, statuts, pages, liens et formules. Les valeurs sont des chaînes pour
préserver les références de pièces, rapports exacts et qualifications textuelles.

| Feuille | Lignes de données | Apport |
|---|---:|---|
| 917_Mesures | 119 | Masses, géométrie documentaire, train mobile, refroidissement et variantes |
| 993_Mesures | 84 | Turbo standard, dimensions, transmission, roues, capacités et divergences |
| Matériaux | 46 | Familles, nuances lorsqu'elles sont renseignées, procédés et limites |
| Adaptations | 14 | Kit MAHLE/LN 3,8 L, séparé des caractéristiques OEM |
| Divergences | 22 | Valeurs incompatibles ou conventions différentes à conserver séparément |
| À_compléter | 18 | Mesures et documents encore nécessaires |
| Sources | 23 | Bibliographie originale et limites d'application |
| Calculs | 14 | Formules et résultats en cache ; valeurs dérivées, pas mesures physiques |

La feuille Accueil conserve le périmètre et les constantes de conversion. La
feuille Images et les médias ne sont pas importés. Les désignations d'exemplaires
historiques dans les variantes sont généralisées ; les liens bibliographiques
restent ceux des sources pour permettre le recoupement.

## Utilisation dans le jumeau

- **917, géométrie documentaire :** `917-075` (longueur du vilebrequin),
  `917-077` (entraxe cylindres) et `917-078` (décalage longitudinal des bancs)
  peuvent alimenter la revue de `dimensional-skeleton-f14.json`. L'entraxe
  de 118 mm existe déjà dans le dépôt : ce n'est pas une nouvelle mesure.
  Le décalage de 24 mm du classeur exige de vérifier la définition du repère
  avant toute comparaison avec `bank_axis_offset_mm` du modèle F1.
- **917, matière :** `MAT-001` distingue le magnésium RZ5 des carters et
  `MAT-002` l'aluminium des culasses ; `MAT-005` cite 17CrNiMo6 pour un
  vilebrequin précis. Ces indications ne fournissent pas de propriétés
  thermomécaniques qualifiées pour une pièce LPBF reconçue.
- **993 Turbo :** conserver les masses DIN/CEE et les gabarits par édition.
  Les rapports de boîte de la brochure et des manuels divergent notamment
  en troisième et cinquième ; aucun rapport actif n'est remplacé par l'import.
- **Kit 3,8 L :** l'alésage de 102 mm, l'emboîtement de 109 mm et le piston
  2618 décrivent la transformation MAHLE/LN. Ils ne démontrent ni les cotes
  ni la matière des pièces OEM du M64.60.
- **Données manquantes :** encombrement complet du moteur équipé, interfaces,
  centre de gravité, masses internes spécifiques Turbo et tolérances complètes
  restent ouverts. Les données Carrera ne comblent pas ces lacunes.

Les références `917-xxx`, `993-xxx`, `MAT-xxx` et `KIT-xxx` sont les identifiants
de lignes du classeur, pas des fiches de pièces libérées. Avant transfert vers
`catalog/parts`, `catalog/measurements` ou un contrat de simulation, recouper la
page primaire, sa variante et la définition de la grandeur. Les statuts
« Documenté » du classeur sont conservés comme déclarations de son auteur.

## Sources et études récupérées

**25 fiches de sources absentes du checkout** ont été ajoutées à
`catalog/sources` : aluminiums LPBF EOS/Constellium/Velo3D, 2618, fatigue du
titane, contrôle et qualification de procédés. Elles portent `not_checked`
et `unrated`, car leurs sources externes n'ont pas été revérifiées ici.
Le manifeste conserve les anciens statuts d'accès et de qualité à titre
historique, ainsi que l'empreinte de chaque fiche d'archive.

L'[étude des demi-carters 917](917_CRANKCASE_MANUFACTURING_STUDY.md) est intégrée
avec une note d'archive. Elle propose une comparaison LPBF aluminium, fonderie
et usinage, puis un secteur palier–registre–galerie avant la paire complète.
Ses références de contrats et son objectif en **hp mécaniques** appartiennent
au commit étudié ; ils ne remplacent pas les conventions du projet actif.

L'étude `Etude_Impression_3D_Automobile_IA_2026.md` de l'archive Documents apporte
aussi des pistes : conduit d'admission mesurable, support titane et collecteur
chaud. Ce sont des propositions de recherche, pas des pièces 993 compatibles
ni une sélection matière. Ses annonces industrielles de 2026 nécessitent une
vérification avant réemploi comme preuve actuelle. L'original reste dans iCloud.

## Comparaison et exclusions

L'export `917-993-donnees-2026-09-06.zip` contient, sous `projet/`, **797 fichiers
identiques**, **56 différents** et **1 102 absents** du checkout avant cet import.
Le [manifeste](../catalog/reference/icloud-porsche-2026-09-06/import-manifest.json)
en donne les chemins pour préparer une éventuelle reprise logicielle distincte.
Les fichiers absents ne sont pas tous des données utilisables isolément : ils
comprennent du code, des contrats, des sorties et des dépendances entre étapes.

Les scripts, patches, workflows, journaux d'exécution et fichiers CAO de cet
autre état du projet ne sont pas activés ou fusionnés. Les journaux archivés ne
prouvent pas une exécution sur le checkout actuel. Aucun scan, manuel
propriétaire, photo ou document fournisseur brut n'est ajouté au dépôt.

Les empreintes des quatre fichiers iCloud permettent de retrouver exactement
les originaux. Les fichiers existants du jumeau et les modifications en cours
ont été préservés.

## Vérifications de l'import

Contrôle réussi des 340 lignes de données des huit tableaux, des 14 formules
conservées, des 25 fiches de sources et des statuts documentaires.
`git diff --check` ne signale pas d'erreur.

`make check` a exécuté la validation et les tests, puis s'est arrêté sur
`pet-993-applicability-check` : le fichier externe `/tmp/kat517-993.txt` est
absent. Ce contrôle PET ne consomme pas le lot iCloud ; le contrôle global
n'est donc pas déclaré réussi. Le journal local est conservé dans
`work/icloud-porsche-import/make-check.log`.
