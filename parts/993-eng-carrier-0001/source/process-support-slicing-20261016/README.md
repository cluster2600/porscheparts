# Coupes exactes des supports en parallèle

Ce module appelle le hook rationnel `exact_support_section.py` sans le modifier.
Quatre processus calculent des couches entières ; le parent consomme les régions
dans leur ordre d'origine, à la hauteur exacte de chaque couche. Huit couches au
maximum sont en attente. Les fichiers, le hook et le répartiteur sont vérifiés
par SHA-256 avant et après le calcul. Le groupe de processus est fermé aussi
en cas de refus.

```python
with ParallelSupportSections(ordered_npz_paths, exact_layer_heights, workers=4) as cuts:
    core.support_section = cuts
    # Exécuter le CORE gelé, avec les mêmes surfaces et le même ordre de couches.
receipt = cuts.receipt()
```

Le reçu doit indiquer toutes les couches consommées et la fermeture du groupe.
Il ne remplace ni l'admission de la géométrie des supports, ni l'audit indépendant
de toutes leurs trajectoires.

`benchmark.py` conserve l'essai initial interrompu sur une coupe rationnelle non
nulle impossible à encoder en un segment float64 non nul. `benchmark_v2.py`
enregistre chacun des dix plans fixés à l'avance : les refus restent des refus,
les tableaux et leur ordre doivent être identiques sur les plans encodables.
Les anciennes feuilles utilisées pour cet essai restent rejetées.

```sh
AM_PYTHON -B -m unittest discover -s tests -p test_carrier_parallel_supports.py -v
AM_PYTHON -B parts/993-eng-carrier-0001/source/process-support-slicing-20261016/benchmark_v2.py \
  work/part-workflow/run-001/process work/carrier-process-20261016/support-benchmark-new
```

`AM_PYTHON` désigne le Python du runtime PySLM installé par le projet.
