# Cache des trajectoires de la pièce

Ce passage calcule les 1 034 couches de la pièce seule sur le STL admis, avec la
pose historique : rotation Z de 45°, garde de 10 mm, couche de 0,06 mm et mêmes
paramètres de contours/hachures. `ParallelLayers` conserve quatre processus et
huit tâches en attente au maximum. Aucun support n’est généré ou réutilisé.

```sh
PY parts/993-eng-carrier-0001/source/process-cache-20261016/test_cache.py
PY parts/993-eng-carrier-0001/source/process-cache-20261016/part_cache.py \
  work/part-workflow/run-001/surface/carrier-remeshed.stl WORK_CACHE \
  --identity-receipt work/part-workflow/run-001/surface/meshing.json
PY parts/993-eng-carrier-0001/source/process-slicing-20261016/audit_scanpaths.py \
  WORK_CACHE WORK_AUDIT
```

`PY` désigne le runtime PySLM enregistré dans `work/part-workflow/runtime.json`.
Le constructeur fige ses sources, les dépendances pertinentes et les binaires
natifs avant de démarrer. Le statut final est `part_layers_completed` ; il ne
signifie pas que la préparation LPBF complète est terminée.

Le lecteur s’intègre sans modifier le constructeur de supports :

```python
from part_cache import CachedLayers
layers = CachedLayers(cache_directory, source_stl, core.PARAMETERS)
report = build_pyslm_skins.build(..., layer_generator=layers)
```

L’objet s’appelle comme `layers(part, z)` et restitue `(raw, contours, vectors,
area)` dans l’ordre natif exact. Il exige un cache complet, les empreintes de
chaque fichier, les mêmes paramètres de pièce, les mêmes versions et sources
pertinentes, ainsi que la pose et les tableaux vertices/faces exacts. Chaque
lecture contrôle à nouveau l’empreinte du NPZ et l’identité de la pièce. Une
modification des supports n’invalide pas ce cache de pièce, mais le passage
final devra calculer ses nouveaux vecteurs de supports et publier son propre
audit.
