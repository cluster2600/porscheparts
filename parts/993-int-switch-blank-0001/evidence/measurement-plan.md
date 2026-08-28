# Plan de mesure — 993-INT-SWITCH-BLANK-0001

Catégorie phase 2 : pièce géométrique simple, mesurable au pied à coulisse.

## Objet

- Pièce : cache d'emplacement d'interrupteur, tableau de bord
- Référence Porsche : à relever dans le catalogue officiel avant la séance
- Variante et année : à confirmer sur le véhicule mesuré
- Véhicule ou pièce mesurée : pièce déposée, hors véhicule
- Responsable : contributeur
- Date :

## Instruments

| Instrument | Plage | Résolution | Étalonnage connu |
|---|---:|---:|---|
| Pied à coulisse | 0–150 mm | 0,01 mm | à déclarer dans la fiche |
| Cales étalon ou pige | | | contrôle du zéro |

## Repères

Origine au centre de la face visible. Axe X selon la largeur, Y selon la hauteur,
Z sortant de la face visible vers l'habitacle. Photographier la pièce avec ces
axes annotés, aux mêmes identifiants que les mesures.

## Dimensions critiques

| ID | Description | Valeur mm | Incertitude mm | Méthode | Répétitions |
|---|---|---:|---:|---|---:|
| D01 | Largeur hors tout de la face visible | | | direct | 3 |
| D02 | Hauteur hors tout de la face visible | | | direct | 3 |
| D03 | Épaisseur de la face visible | | | direct | 3 |
| D04 | Rayon des angles de la face visible | | | gauge | 3 |
| D05 | Longueur des pattes de clipsage | | | direct | 3 |
| D06 | Épaisseur des pattes de clipsage | | | direct | 3 |
| D07 | Entraxe des pattes de clipsage | | | direct | 3 |

Ces sept cotes sont exactement celles qu'exige `source/switch_blank.py` : tant
qu'une manque, le modèle refuse de se construire.

## Interfaces

- Logement du tableau de bord : largeur, hauteur et épaisseur de tôle ou de plastique
- Sens de clipsage et débattement des pattes
- Affleurement attendu avec les garnitures voisines

## Acquisition 3D

Sans objet : la géométrie est descriptible au pied à coulisse. Toute acquisition
3D resterait ici une preuve visuelle, pas une mesure.

## Résultat

- Mesures acceptées : oui / non
- Contradictions :
- Mesures manquantes :
- Fichiers de preuve : `catalog/measurements/meas-993-int-switch-blank-0001.json`
