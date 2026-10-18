# Région droite corrigée — image des données réelles

La [page illustrée](../right-supports.html) montre la région source 008 du
passage `real-support-source-008-full-004`. Son graphe matériel passe :
112 898 faces, 897 groupes et 20 composantes avec contacts supérieur et
inférieur. Les admissions globales et l'audit des couches restent séparés.

Le rendu charge le checkpoint avec `PreparedRegion`, qui contrôle les
identités des entrées, sources, runtime, surfaces, métadonnées et graphe.
La grille détaillée est le groupe `grid-1-49-3` ; ses triangles sont projetés
dans leur plan réel Y = 92,445 mm. L'assertion du plan passe, sans déplacement.

```sh
work/part-workflow/runtimes/pyslm-coverage-011/env/bin/python -B \
  scripts/render_carrier_region.py \
  work/carrier-process-20261016/real-support-source-008-full-004 \
  work/part-workflow/region-images-new
```

Le premier rendu, dont la vue de dessus était illisible pour des feuilles
verticales, reste conservé et refusé éditorialement dans
`work/part-workflow/region-images-001`. Le présent rendu et sa page ont été
examinés ; leurs empreintes sont enregistrées dans `visual-qa.json`.
