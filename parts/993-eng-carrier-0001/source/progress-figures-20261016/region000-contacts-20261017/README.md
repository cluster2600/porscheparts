# Contacts attestés de la région 000 — couche native 0

Préparation locale de la planche 19 : tous les 129 026 intervalles rationnels Q
retenus et les 129 023 intervalles encodés E positifs reclipés sont dessinés,
sans décimation, dans une vue XY complète et un zoom aux mêmes coordonnées.
Les intervalles, leur ordre et leurs doublons proviennent d'une seule lecture
ijson des preuves terminales ; aucune coupe ni contact n'est recalculé.

Le diagnostic réel concerne Z = 0,030 mm, 337 groupes et 171 694 faces de la
seule région 000. Les 70 144 segments Q ancrés donnent 70 141 vecteurs E
ancrés par le contrat `own_source_parametric_encoded_contact_1`. Les trois
autres coupes Q deviennent des points à l'encodage : elles ne transmettent
aucune ancre à leur vecteur couvrant. Le chevauchement littéral E, distinct,
avait 68 246 vecteurs ancrés. Le haut est absent à cette couche, avant le
début de la pièce à Z = 10 mm. Aucune admission sur 1 034 couches ou sept
régions n'est revendiquée.

Le NPZ contient les seuls intervalles positifs attestés, pas les 94 734
vecteurs machine complets. Les trois symboles creux repèrent les contacts Q
devenus points, à leurs vraies coordonnées. Le zoom choisit celui le plus
proche du centre de l'emprise ; aucune différence Q/E n'est amplifiée.

## Rejeu

Copier ce dossier avec ses sous-dossiers `data`, `evidence`, `reference` dans
un emplacement neuf, puis utiliser les versions de `inputs.json` :

```sh
CARRIER_RENDER_PYTHON=/chemin/work/part-workflow/runtimes/pyslm-coverage-011/env/bin/python
CARRIER_FIGURE=/chemin/vers/cette-copie
CARRIER_OUTPUT=/chemin/vers/une-sortie-neuve
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
  "$CARRIER_RENDER_PYTHON" -I -B "$CARRIER_FIGURE/render.py" "$CARRIER_OUTPUT"
```

La limite de rendu est 60 secondes, sans solveur, worker de section ou accès
aux métadonnées de 2,4 Go. Les chemins existants ou à ancêtre symbolique sont
refusés. Palette, barre de 10 mm et contrôle d'échelle XY 1:1 reprennent le
renderer de la première couche existant. Dates et sel SVG fixes rendent les
trois formats reproductibles. Toutes les primitives sont rendues à 180 dpi ;
SVG/PDF embarquent les collections rasterisées et gardent axes/textes
vectoriels. Ce choix de sortie ne supprime aucun intervalle.

Les fichiers `evidence/*.py.txt` sont des sources historiques inertes. Leur
extraction initiale dépend des grosses preuves terminales non embarquées ;
le rendu des seules données compactes est autonome. La contre-vérification
indépendante des 129 023 certificats est copiée sans modification, avec ses
liaisons aux sources originales. Le reçu de rendu relève les SHA avant/après,
les deux barres et les nombres d'éléments de chaque panneau.
