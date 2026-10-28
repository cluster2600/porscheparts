# Préparation LPBF ouverte avec PySLM

Cette version est conservée comme **témoin initial refusé sur le carrier**.
Le passage `run-001` a été interrompu après 526 couches sur 1 034 : une région
de support était omise et des erreurs natives de correspondance de sommets,
de normalisation et de transfert de paramètres ont été identifiées. Les
fichiers et leurs empreintes sont conservés ; ils ne constituent pas une
préparation complète admise. La correction est développée dans la version
séparée `source/process-coverage-20261016/`, avec contrôles par région et
témoins supplémentaires. Le
[dossier de reprise](../../../../docs/reports/993_CARRIER_WORKFLOW_20261016.md)
conserve les décisions de chaque version.

Ce pilote produit les sections de **toutes les couches de 60 µm**, les contours
compensés, les hachures et les surfaces de supports dentés du berceau fourni.
L'entrée est un STL fermé dont le SHA-256 est obligatoire. Seuls les sommets
exactement identiques sont réindexés ; aucune face ni coordonnée n'est corrigée.
Les sections natives Trimesh doivent être fermées avant leur conversion en
polygones et en chemins PySLM. Le remplissage implicite `fill_gaps()` de
`Part.getTrimeshSlice` est ainsi évité ; une section ouverte interrompt le calcul.
La pose est conservée : rotation `[0, 0, 45]`, espace de support de 10 mm et
plaque de 500 × 500 × 20 mm. La plaque occupe `z = -20…0 mm`.

## Moteur et installation

[PySLM](https://github.com/drlukeparry/pyslm) est conservé à la révision
`8fa03f1eb98b1fbc8e617eb3119d669f356a2f0b` du 1er février 2026, sous LGPL-2.1.
Les empreintes sont dans `upstream.json`, et la licence auteur dans
`LICENSE.pyslm`. Le runtime exécuté est Python 3.11 sur macOS arm64. Les
dépendances effectivement installées sont conservées dans
`requirements-macos-arm64-python311.lock.txt`.

Installation durable depuis la racine du dépôt :

```sh
python3.11 parts/993-eng-carrier-0001/source/process-20261016/setup_pyslm.py \
  work/part-workflow/runtimes/pyslm
```

`runtime.json` indique le chemin de l'interpréteur à fournir au workflow. Le
script refuse un dossier existant, vérifie le correctif et le code installé,
contrôle les versions, puis tranche réellement une boîte de section 200 mm².

```sh
python3.11 -m venv /path/to/pyslm-env
/path/to/pyslm-env/bin/python -m pip install -r requirements-macos-arm64-python311.lock.txt
git clone https://github.com/drlukeparry/pyslm /path/to/pyslm-source
git -C /path/to/pyslm-source checkout 8fa03f1eb98b1fbc8e617eb3119d669f356a2f0b
git -C /path/to/pyslm-source apply /absolute/path/to/pyslm-support-projection.patch
/path/to/pyslm-env/bin/python -m pip install --no-deps /path/to/pyslm-source
```

NumPy est limité à **1.26.4** : les conversions de tableaux en scalaires du
générateur de dents échouent avec NumPy 2.4. Un correctif séparé réutilise
`geometry.extrudeFace` pour conserver les correspondances de sommets lors de la
projection des supports. Sans ce correctif, le berceau provoquait une erreur
de taille : 1 523 hauteurs pour 1 519 sommets fusionnés en XY.

## Exécution

Depuis la racine du dépôt, avec un nouveau dossier de sortie :

```sh
/path/to/pyslm-env/bin/python parts/993-eng-carrier-0001/source/process-20261016/build_pyslm.py \
  /absolute/path/to/carrier.stl work/new-carrier-build --sha256 INPUT_SHA256
/path/to/pyslm-env/bin/python parts/993-eng-carrier-0001/source/process-20261016/render_pyslm.py \
  work/new-carrier-build
/path/to/pyslm-env/bin/python -m unittest discover -s tests -p test_carrier_process_20261016.py -v
```

Pour enchaîner directement le remeshing sans recopier son empreinte, remplacer
`--sha256 INPUT_SHA256` par `--identity-receipt /path/to/meshing.json`.
Ces options sont mutuellement exclusives. Le champ exact
`candidate_STL_sha256` doit correspondre au STL d'entrée ; le reçu est figé
dans `source/meshing.json` et recontrôlé à la fin.

Le rendu peut écrire dans un nouveau dossier avec `--output DOSSIER` pour
conserver les vues précédentes. Ses légendes sont en français ; la couche
calculée est fournie en PNG et en SVG vectoriel pour le dossier imprimé.

Le générateur utilise la grille de 5 mm, l'intervalle de dents de 1,5 mm et
la paroi de 1 mm de l'exemple auteur. La sélection des régions conserve les
autres réglages auteur, consignés dans le rapport ; la simplification par
spline est désactivée. Les hachures utilisent les valeurs par défaut PySLM :
pas de 0,08 mm, angle de 45°, un contour externe et un interne. Ces valeurs
sont les paramètres explicites de cette étude numérique.

## Fichiers livrés

- `part-build.stl`, `plate.stl`, `support-*.stl` et `build.glb` : géométrie
  effectivement générée, dans le même repère.
- `support-*.npz` : surfaces originales avec les identifiants d'ordre et de
  type nécessaires à leur réinspection.
- `layers/layer-*.npz` : altitude, contours bruts fermés, contours compensés,
  segments de hachure et segments de support ; tableaux numériques sans pickle.
- `layers.csv` : aire de pièce, nombres et longueurs de segments par couche.
- `report.json` : entrée, versions, paramètres, empreintes, volume intégré
  sur les couches et encombrement. Le code du lanceur et les versions sont
  figés dans `source/` avant le calcul ; leurs empreintes sont recontrôlées
  avant le reçu final.
- `build-supports.png`, `support-teeth.png`, `layer-contours-hatches.png` : vues
  de la géométrie générée et d'une couche réellement calculée ; `figures.json`
  conserve leurs empreintes et les coordonnées de la vue détaillée.

Les supports PySLM sont des **surfaces de parois et de grilles**. Le moteur ne
fournit pas leur fusion en solide ; leur masse reste donc `null`. Les dents
pénètrent nominalement de 0,2 mm dans la pièce ; les dents inférieures peuvent
descendre dans la zone de plaque.
L'algorithme auteur peut omettre une peau périphérique lorsqu'il ne sait pas
apparier ses contours ; l'avertissement demeure dans le journal. Aucune
épaisseur volumique ou accessibilité d'outil n'est déduite d'une coque ouverte.

Les sections des supports utilisent `trimesh.intersections.mesh_plane`, la
même intersection que le trancheur PySLM, directement sur les surfaces
générées. Cela conserve les segments sans le tri quadratique du trancheur
auteur. Les triangles éloignés de la couche sont exclus par leurs bornes en Z,
avec la tolérance native Trimesh ; `local_faces` et `cached_dots` alimentent la
même intersection native. L'égalité bit à bit est contrôlée sur un témoin denté,
y compris les plans passant exactement par un sommet ou une arête.
Les segments nuls et doublons exactement identiques sont comptés et
retirés ; aucune grille d'arrondi ne modifie leurs coordonnées. L'ordre machine,
la puissance, la vitesse et les stratégies propres à une machine restent à
attribuer. Les traducteurs commerciaux `libSLM` ne sont pas installés.

`support-stage.json` permet une reprise avec `--reuse-supports DOSSIER` : les
paramètres, la pose et chaque fichier de support sont vérifiés avant copie.
Les nouveaux résultats gardent l'empreinte du générateur ayant produit ces
supports. Cette reprise conserve les résultats d'une préparation longue sans
faire passer une tentative interrompue pour une exécution complète.

Un témoin interrompu conserve `partial.json` et ses couches calculées ; il
n'a pas de reçu `report.json` complet. Le rendu avec `--layer INDEX` l'affiche
explicitement comme `PARTIAL WITNESS`.
