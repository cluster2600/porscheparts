# Première couche réelle — région 010

[Image PNG](reference-001/first-layer-contacts.png) ·
[PDF](reference-001/first-layer-contacts.pdf) ·
[SVG](reference-001/first-layer-contacts.svg)

La planche conserve les **6 753 vecteurs** de la première couche à
**Z = 0,030 mm** et les **6 658 intervalles de contact au plateau** issus de
4 024 témoins de vecteurs distincts. Les doublons restent dessinés. Les
coordonnées XY sont réelles, avec la même échelle sur les deux axes. Le détail
ne déplace aucun segment. Les deux barres de 10 mm sont contrôlées par
projection dans le [reçu initial](reference-001/render-receipt.json).

Cette image documente le préfixe historique de **14 couches contrôlées sur
1 034**, pour cette seule région, conservé dans `data/layer-assessments.jsonl`.
Les graphes rationnel et encodé de la première couche contiennent chacun une
composante et aucune composante flottante. Chaque coordonnée rationnelle
affichée est vérifiée contre son encodage enregistré.

Un essai ultérieur, avec des recherches de contacts accélérées, a reproduit
les 14 couches à l'octet, puis a terminé 68 couches avant un **refus à
l'indice 68, Z = 4,109999999999999 mm** : une coupe exacte non nulle d'un
triangle devient un segment nul en float64. Le
[résumé de cet échec](later-strict-slicing-failure.json) est conservé.
Cette planche reste donc une preuve locale archivée ; elle ne vaut pas
admission de la région complète. La correction de sa triangulation fait
l'objet d'un candidat et de contrôles séparés.

## Reproduction avec les données incluses

Ce dossier inclut les deux fichiers d'entrée et le renderer. Il ne relance
aucune génération de supports, coupe ou recherche de contact. Le renderer
original est conservé dans `sources/render-historical.py` ; la seule adaptation
de `render.py` concerne les deux constantes de localisation des données.
Les empreintes attendues des entrées restent identiques.

Depuis la racine du projet, choisir une sortie neuve :

```sh
MPLBACKEND=Agg OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
work/part-workflow/runtimes/pyslm-coverage-011/env/bin/python -I -B \
parts/993-eng-carrier-0001/source/progress-figures-20261016/first-layer-contacts-20261017/render.py \
work/carrier-first-layer-contacts-replay-new
```

Le rejeu a été exécuté depuis `/`, avec le runtime AM011 : **retour réel 0,
5,742 s et PNG identique à l'octet**, sans worker de coupe. Le
[reçu d'exécution](replay-execution.json) et le
[reçu du rendu rejoué](replay-render-receipt.json) conservent les preuves.
Le runtime utilise NumPy 1.26.4 et Matplotlib 3.11.2. Il n'est pas inclus
dans cette archive d'images.

La [revue visuelle initiale](visual-review.json) est conservée. Le
[manifeste](publication.json) donne les empreintes de toutes les copies de
ce dossier, sauf lui-même.
