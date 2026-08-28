# Plan de mesure — 993-ENG-CARRIER-0001

Pièce structurale. La mesure sert d'abord à décrire des **interfaces**, pas une
silhouette : c'est la position relative des fixations qui conditionne le montage.

## Objet

- Pièce : berceau moteur, référence 993 115 021 53
- Variante et année : à confirmer sur le véhicule
- État : pièce déposée, nettoyée, non déformée — vérifier l'absence de choc ou de corrosion perforante
- Responsable : contributeur
- Date :

## Instruments

| Instrument | Plage | Résolution | Étalonnage connu |
|---|---:|---:|---|
| Pied à coulisse | 0–150 mm | 0,01 mm | contrôle du zéro |
| Réglet ou mètre à ruban rigide | 0–1000 mm | 0,5 mm | |
| Marbre ou surface de référence | | | planéité déclarée |
| Jauge de profondeur | | | |
| Appareil photo + barre d'échelle | | | valeur certifiée |

Une traverse dépasse la plage d'un pied à coulisse : l'entraxe global se mesure
au réglet, ou par photogrammétrie recalée sur des cotes courtes mesurées, jamais
en additionnant des mesures locales sans contrôle.

## Repères

Origine sur l'axe du premier perçage de fixation à la caisse. X selon l'axe
longitudinal du véhicule, Y transversal, Z vertical. Poser la pièce sur le marbre
et déclarer la face d'appui : toutes les cotes de hauteur s'y rapportent.

## Dimensions critiques

| ID | Description | Valeur mm | Incertitude mm | Méthode | Répétitions |
|---|---|---:|---:|---|---:|
| D01 | Entraxe des fixations caisse, gauche-droite | | | direct | 3 |
| D02 | Entraxe des fixations caisse, avant-arrière | | | direct | 3 |
| D03 | Diamètre des perçages de fixation caisse | | | direct | 3 |
| D04 | Entraxe des fixations de support moteur | | | direct | 3 |
| D05 | Diamètre des perçages de support moteur | | | direct | 3 |
| D06 | Hauteur du plan d'appui au plan des supports moteur | | | direct | 3 |
| D07 | Épaisseur de matière aux zones de fixation | | | direct | 3 |
| D08 | Défaut de planéité du plan d'appui | | | gauge | 3 |
| D09 | Section courante de la traverse | | | direct | 3 |

## Interfaces

- Caisse : nature du logement, écrous soudés ou traversants, classe et couple de vis
- Supports moteur : type, raideur, orientation
- Dégagements : échappement, transmission, câblage, passage d'outil au montage
- Repères de position et sens de montage

## Identification de la matière d'origine

Avant toute comparaison de procédé, établir ce qu'est la pièce :

- aimant : acier ou non
- masse pesée : ____ g
- épaisseurs mesurées et mode d'obtention apparent (tôle emboutie, soudée, moulée)
- marquages, numéros de moule, cordons de soudure

Une matière supposée invalide toute comparaison de masse ultérieure.

## Acquisition 3D

- Méthode : photogrammétrie pour la forme générale, `scripts/capture_photoset.py`
- Échelle : barre certifiée dans le champ
- Le scan ne fixe pas les interfaces : D01 à D07 restent mesurés au contact et
  servent à contrôler la reconstruction.

## Résultat

- Mesures acceptées : oui / non
- Contradictions :
- Mesures manquantes :
- Fichiers de preuve : `catalog/measurements/meas-993-eng-carrier-0001.json`
