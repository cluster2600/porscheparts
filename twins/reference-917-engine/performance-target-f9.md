# Contrat de cible de puissance 917/30 F9

## Portée

F9 traduit des déclarations documentaires de puissance en besoins algébriques
reproductibles. Il calcule, pour plusieurs régimes indépendants, le couple, le
BMEP et la vitesse moyenne du piston nécessaires pour atteindre une puissance
donnée. Ce modèle 0D n'est ni un solveur thermodynamique, ni une courbe moteur,
ni un résultat de banc.

Le contrat reste volontairement bloqué pour toute revendication de puissance.
Il ne calcule aucun débit d'air ou de carburant, aucune pression de
suralimentation, aucune température, aucune vitesse de turbo et aucune tenue
thermomécanique.

## Séparation des preuves et des scénarios

Les faits sourcés sont conservés dans `source_evidence` :

- la fiche Porsche Museum déclare 5 374 cm³ et 882 kW / 1 200 PS ;
- l'article Porsche Newsroom USA décrit une puissance **rapportée** de
  1 600 HP en configuration de qualification ;
- la géométrie 90 × 70,4 mm provient de la source secondaire auto motor und
  sport. Son calcul donne 5 374,385 cm³, cohérent par arrondi avec les
  5 374 cm³ officiels.

Ces déclarations ne fournissent ni courbe couple-régime, ni durée de
qualification, ni base de puissance, ni correction atmosphérique, ni
incertitude. Elles ont donc le rôle `documentary_only` et ne sont jamais
utilisées comme calibration.

Deux scénarios de calcul restent séparés :

1. scénario primaire Porsche USA : 1 600 horsepower mécaniques, avec
   `1 hp = 745,6998715822702 W`, soit 1 193,119795 kW ;
2. sensibilité d'unité : 1 600 PS métriques, avec `1 PS = 735,49875 W`, soit
   1 176,798 kW.

Les deux scénarios possèdent leurs propres lignes de couple et de BMEP. Le
second ne corrige ni ne remplace la déclaration Porsche en horsepower.

## Calcul reproductible

```bash
make 917-performance-envelope-f9
```

La sortie locale est écrite dans
`work/917-performance-f9/power-requirement-envelopes.json`. Le dossier `work/`
reste hors Git.

Les équations sont :

- cylindrée : `π / 4 × alésage² × course × nombre de cylindres` ;
- couple requis : `puissance × 60 / (2 × π × régime)` ;
- BMEP quatre temps : `4 × π × couple / cylindrée` ;
- vitesse moyenne du piston : `2 × course × régime / 60`.

À 7 000 tr/min, le scénario primaire de 1 600 hp exige algébriquement
1 627,636 Nm et 38,057 bar de BMEP. La sensibilité 1 600 PS exige séparément
1 605,370 Nm et 37,537 bar. Ces valeurs décrivent une exigence à un point de
calcul ; elles ne montrent pas que le moteur peut l'atteindre. La grille de
6 000 à 8 000 tr/min n'est pas déclarée comme plage de fonctionnement.

## Gate fail-closed

Le rapport conserve `performance_claim_authorized = false` tant que manquent
notamment :

- un solveur thermodynamique identifié, sa version et son jeu d'entrées ;
- les bilans de masse et d'énergie ;
- les jeux de calibration et de validation indépendante ;
- une trace dynamométrique régime-couple et la calibration du banc ;
- la base de puissance et la norme de correction ;
- la durée de qualification, les conditions ambiantes et le budget
  d'incertitude.

PhysicsNeMo reste réservé à un surrogate construit après validation d'un
solveur de référence et corrélation sur des essais physiques tenus à l'écart de
la calibration. F9 ne prouve donc jamais une puissance de 1 600 hp ou
1 600 PS et n'autorise aucune fabrication ou mise en charge d'un moteur.
