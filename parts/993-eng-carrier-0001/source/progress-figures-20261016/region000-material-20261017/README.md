# Surfaces réelles des supports — zone 000

La [planche PNG](render/carrier-supports-zone-000.png) montre les **171 694 triangles**
du fichier généré, dans deux vues. Les 322 grilles sont dorées et les 15 peaux
de support bleues. Les sommets, les triangles et les attributs restent ceux de
la génération originale. Toutes les faces sont affichées, sans simplification.
Les deux vues ont leur propre cadrage.

Le graphe matériel vérifié contient 337 groupes dans une composante avec les
deux ancrages requis. Le découpeur strict refuse encore une coupe de la grille
`grid-0-9-0` à Z = 0,030 mm : la correction de triangulation est en cours.
La planche conserve cet état original ; elle porte sur la zone 000 seule.

- [PDF, une page](render/carrier-supports-zone-000.pdf) et [SVG](render/carrier-supports-zone-000.svg).
- [Fichiers et provenance](inputs.json), [graphe matériel](material-connections.json),
  [checkpoint original](region-checkpoint.json) et [refus du découpeur](original-strict-refusal.json).
- [Index exact des groupes](owners.json) et [extraction contrôlée](owner-extraction.json).
- [Rendu réellement exécuté](render-execution.json), [exports](render/figures.json)
  et [contrôle de publication](publication-validation.json).

L’index conserve cinq champs par groupe. Son extraction a parcouru entièrement
les 2 589 891 988 octets du rapport original et vérifié son SHA, la partition
des 171 694 faces et leurs attributs. Ce grand rapport reste externe ; la planche
embarque les tableaux géométriques et les preuves compactes utilisées.

Avec NumPy, Matplotlib et VisPy installés, lancer depuis ce dossier ou depuis
un autre répertoire courant :

```sh
python /chemin/vers/ce/dossier/render.py --check
python /chemin/vers/une/copie/du/dossier/render.py
```

La copie de travail doit conserver tous les fichiers liés par `inputs.json` et
ne pas contenir de sous-dossier `render`. Le script refuse une divergence de SHA,
de partition, d’attributs ou de rattachement du graphe. Le rendu de publication
a été exécuté depuis une copie séparée avec Python 3.11.15, NumPy 1.26.4 et
Matplotlib 3.11.2 ; les sources et reçus gardent leurs chemins historiques.
