# Jumeau numérique de la Porsche 993

## Objectif

Le jumeau sert d'abord à inventorier, représenter et assembler ce qui est connu.
La phase active ne prévoit aucune impression. Lorsque les preuves le permettent,
il pourra ensuite éliminer des erreurs de montage et étudier le comportement
mécanique ou thermique. Il ne prétend pas être une copie certifiée de toutes les
993.

Un composant n'entre dans le graphe actif que si taille, masse, matière et
application sont sourcées. Un assemblage logique affirme que des pièces vont
ensemble ; un assemblage positionné exige en plus leurs repères et
transformations 3D.

Le modèle est construit par zones : tableau de bord, porte, siège, baie moteur,
train roulant et carrosserie. La précision est déclarée par composant et par
interface, car une même zone peut combiner un habillage visuel `F0` et des
fixations mesurées `F2`.

## Première tranche géométrique — tableau de bord, en attente

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

## Première intégration géométrique — roues et moyeux

Le registre contient maintenant une seconde zone active :
`TWIN-993-WHEEL-HUB-INTERFACES-0001`. Elle référence quatre solides STEP
reproductibles à partir du même maître build123d :

- Fuchs 7J × 17 ET55, avant ;
- Fuchs 9J × 17 ET55, arrière ;
- Fuchs 8J × 18 ET52, avant ;
- Fuchs 10J × 18 ET65, arrière.

Ces objets sont des proxys d'interface `F1_envelope` : cylindre nominal,
largeur nominale et alésage central. Ils rendent les composants visibles et
assemblables dans FreeCAD, mais ne reproduisent ni les branches, ni le profil
réel de jante, ni les sièges de boulons. Les deux moyeux restent des repères
logiques sans géométrie. Le twin est donc au statut `concept`, et non
`digitally_checked`.

Pour passer à `F2_interface`, il faut mesurer ou sourcer la face d'appui, le
centrage du moyeu, le type de siège des fixations, l'enveloppe du frein, les
tolérances et les transformations dans le repère véhicule. Alors seulement un
calcul de collision ou de marge pourra devenir une preuve numérique.

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

La corrélation physique reste un niveau futur. Pour une pièce critique, un
succès numérique ne remplacera ni la revue d'ingénierie ni les essais matière et
fatigue si une fabrication est un jour décidée.
