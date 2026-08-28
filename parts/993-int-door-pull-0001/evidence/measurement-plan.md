# Plan de mesure — 993-INT-DOOR-PULL-0001

Catégorie phase 2 : pièce organique nécessitant photogrammétrie ou scan.

## Objet

- Pièce : poignée de tirage de porte intérieure
- Référence Porsche : à relever avant la séance
- Variante et année : à confirmer sur le véhicule mesuré
- Véhicule ou pièce mesurée : pièce déposée, hors véhicule
- Responsable : contributeur
- Date :

## Instruments

| Instrument | Plage | Résolution | Étalonnage connu |
|---|---:|---:|---|
| Pied à coulisse | 0–150 mm | 0,01 mm | contrôle du zéro |
| Appareil photo | | | focale fixe, mise au point verrouillée |
| Barre d'échelle certifiée | 100 mm | | valeur certifiée à déclarer |

## Repères

Origine au centre du plan d'appui de fixation. Axe X selon la longueur de la
poignée, Z normal au plan d'appui. La photogrammétrie ne donne pas d'origine :
c'est le recalage sur les interfaces mesurées qui la fixe.

## Dimensions critiques

Ces cotes ne viennent pas du scan. Elles sont mesurées séparément et servent à
vérifier, puis à mettre à l'échelle, la reconstruction.

| ID | Description | Valeur mm | Incertitude mm | Méthode | Répétitions |
|---|---|---:|---:|---|---:|
| D01 | Entraxe des fixations | | | direct | 3 |
| D02 | Diamètre des perçages de fixation | | | direct | 3 |
| D03 | Longueur hors tout | | | direct | 3 |
| D04 | Épaisseur au droit de la prise en main | | | direct | 3 |
| D05 | Hauteur du plan d'appui à la face supérieure | | | direct | 3 |

## Interfaces

- Panneau de porte : plan d'appui, vis, écrous ou inserts
- Dégagement main entre poignée et garniture
- Sens et amplitude de l'effort appliqué en fermeture

## Acquisition 3D

- Méthode : photogrammétrie, `scripts/capture_photoset.py`
- Échelle : barre certifiée dans le champ, valeur consignée dans le manifeste
- Conditions : éclairage diffus, fond mat, surface dépoussiérée ; si la pièce est
  brillante ou noire, prévoir un traitement matifiant amovible
- Format brut : JPEG plus manifeste, conservés hors dépôt
- Alignement : recalage sur D01 et D02, puis contrôle de D03 à D05
- Écart scan/mesures critiques : à consigner, seuil d'acceptation à définir avant
  l'acquisition

## Résultat

- Mesures acceptées : oui / non
- Contradictions :
- Mesures manquantes :
- Fichiers de preuve : `catalog/measurements/meas-993-int-door-pull-0001.json`
