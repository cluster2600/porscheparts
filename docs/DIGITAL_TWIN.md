# Jumeau numérique de la Porsche 993

## Objectif

Le jumeau sert à éliminer tôt les erreurs de montage et, lorsque les preuves le
permettent, à étudier le comportement mécanique ou thermique. Il ne prétend pas
être une copie certifiée de toutes les 993.

Le modèle est construit par zones : tableau de bord, porte, siège, baie moteur,
train roulant et carrosserie. La précision est déclarée par composant et par
interface, car une même zone peut combiner un habillage visuel `F0` et des
fixations mesurées `F2`.

## Première tranche — tableau de bord

Le MVP assemble :

1. le cache d'interrupteur candidat ;
2. l'ouverture et l'épaisseur du panneau qui le reçoit ;
3. le volume libre derrière le panneau ;
4. les marges minimales d'insertion, de recouvrement, de clipsage et de recul.

Le script
`twins/993-cabin-dashboard-switch-0001/source/check_fit.py` lit une fiche de
mesure et refuse de calculer si une cote manque. Il produit un rapport JSON avec
la marge nominale et la marge garantie au pire cas, incertitudes comprises.

```bash
python3 twins/993-cabin-dashboard-switch-0001/source/check_fit.py \
  --measurements catalog/measurements/meas-993-dashboard-switch-zone-0001.json \
  --out twins/993-cabin-dashboard-switch-0001/derived/fit-report.json
```

## Ordre de construction

| Tranche | Zone | Premier test |
|---|---|---|
| DT-01 | Tableau de bord | insertion et clipsage du cache d'interrupteur |
| DT-02 | Porte | montage et débattement de la poignée |
| DT-03 | Glissière de siège | symétrie, collision et accès aux fixations |
| DT-04 | Baie moteur | interfaces du berceau, sans validation structurelle |
| DT-05 | Repère caisse | rattachement des zones aux points de référence carrosserie |

La carrosserie complète et les scans visuels viennent ensuite comme contexte.
Cette séquence permet de tester une première pièce sans attendre plusieurs mois
de reconstruction de la voiture entière.

## Ce que signifie « testé dans le jumeau »

- `geometry_ready` : toutes les géométries et incertitudes requises existent ;
- `digitally_checked` : toutes les règles déclarées ont été exécutées et le
  rapport est versionné ;
- `physically_correlated` : un montage réel a été comparé aux prédictions.

Un succès numérique ne remplace pas l'essai physique. Pour une pièce critique,
il ne remplace ni la revue d'ingénierie ni les essais matière et fatigue.

