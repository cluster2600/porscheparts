# Plan de mesure — 993-BODY-FRONT-LID-0001

Pièce de peau. Ce ne sont **pas** les cotes de la surface qui décident du
résultat, ce sont les **interfaces** : charnières, serrure, butées, et les jeux
avec les ailes et le pare-chocs.

## Objet

- Pièce : capot avant, panneau d'origine en acier
- Référence Porsche : à relever avant la séance
- Variante et année : à confirmer sur le véhicule
- État : panneau sain, non accidenté, non redressé — un capot déformé donnerait un moule faux
- Responsable : contributeur
- Date :

## Étape zéro, avant tout le reste : peser

| ID | Description | Valeur kg | Incertitude kg | Méthode | Répétitions |
|---|---|---:|---:|---|---:|
| M01 | Capot acier nu, sans charnières ni serrure | | | direct | 3 |
| M02 | Ferrures déposées, ensemble | | | direct | 3 |

Sans M01, aucun gain ne peut être annoncé. Une balance de salle de bain suffit,
et c'est la mesure la moins chère de tout le projet. Référence connue à battre :
le capot aluminium Porsche Motorsport, annoncé à 8 kg.

## Instruments

| Instrument | Plage | Résolution | Étalonnage connu |
|---|---:|---:|---|
| Balance | 0–120 kg | 0,1 kg | contrôle avec masse connue |
| Pied à coulisse | 0–150 mm | 0,01 mm | contrôle du zéro |
| Réglet | 0–1000 mm | 0,5 mm | |
| Jeu de cales d'épaisseur | | | pour les jeux de carrosserie |

## Repères

Capot posé sur un plan, face extérieure vers le haut. Origine sur l'axe de la
charnière gauche, X selon l'axe longitudinal du véhicule, Y transversal.

## Dimensions critiques — interfaces uniquement

| ID | Description | Valeur mm | Incertitude mm | Méthode | Répétitions |
|---|---|---:|---:|---|---:|
| D01 | Entraxe des deux charnières | | | direct | 3 |
| D02 | Entraxe des vis sur chaque platine de charnière | | | direct | 3 |
| D03 | Diamètre des perçages de charnière | | | direct | 3 |
| D04 | Position de la gâche de serrure par rapport aux charnières | | | direct | 3 |
| D05 | Épaisseur de tôle aux zones de fixation | | | direct | 3 |
| D06 | Jeu périphérique avec les ailes, capot fermé | | | gauge | 3 |
| D07 | Affleurement avec les ailes, capot fermé | | | gauge | 3 |

D01 à D04 conditionnent le montage. D06 et D07 conditionnent l'acceptation
visuelle, et ce sont eux qui font échouer la plupart des panneaux de rechange.

## Acquisition 3D

- Méthode : photogrammétrie ou scan de surface, `scripts/capture_photoset.py`
- Échelle : barre certifiée dans le champ, obligatoire
- La surface extérieure vient du scan. Les interfaces viennent des mesures au
  contact, et priment sur le scan en cas d'écart.

## Ce que ce plan ne couvre pas

Le moule. Prendre une empreinte sur le panneau d'origine est une opération de
moulage, pas de mesure : elle a ses propres règles, notamment le retrait et
l'agent démoulant. Le scan sert ici à contrôler le moule obtenu, pas à le
remplacer.

## Résultat

- Mesures acceptées : oui / non
- Contradictions :
- Mesures manquantes :
- Fichiers de preuve : `catalog/measurements/meas-993-body-front-lid-0001.json`
