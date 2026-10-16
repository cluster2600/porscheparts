# Images du travail en cours — 16 octobre 2026

Ouvrir `index.html` pour parcourir les cinq planches hors ligne. Les fichiers
PNG restent disponibles individuellement à leur définition complète.

Les deux nouvelles vues utilisent le STL retenu et les triangles des supports
de l'essai `real-support-source-008-015`. Les cotes, le comparatif du maillage
et la couche 518 sont des copies identiques des figures calculées auparavant.
Le [reçu](figures.json) conserve leurs empreintes et celles des entrées.

La pièce pèse 1,262212621 kg pour une limite de 1,30 kg. L'essai de supports
perforés montré est refusé : 26 composantes, soit 35,66 mm² de surfaces,
n'ont pas les deux ancrages requis. Il représente la région droite seule,
pas une préparation complète admise. La vue du détail projette les triangles
dans leur plan réel ; aucune surface supplémentaire ne comble les écarts.

Régénération depuis la racine du dépôt, avec le runtime PySLM reproduit :

```sh
work/part-workflow/runtimes/pyslm-coverage-reproduced-012/env/bin/python \
  scripts/render_carrier_progress.py \
  work/part-workflow/run-001 \
  work/carrier-process-20261016/real-support-source-008-015 \
  work/part-workflow/progress-images-new
```

Le répertoire de sortie doit être neuf. Le rendu refuse les divergences
d'identité entre STEP, masse, audit CAD/maillage et STL, ainsi qu'entre le
graphe d'ancrage et les triangles qu'il colore. VisPy utilise un tampon de
profondeur pour les vues 3D ; Matplotlib trace le détail dans le plan réel.

Les cinq images ont été relues visuellement ; les empreintes des copies et
le test ciblé de coloration du graphe passent. Les cadrages intermédiaires
sont conservés dans `work/part-workflow/progress-images-001` à `003` avec
leur motif de refus éditorial.
