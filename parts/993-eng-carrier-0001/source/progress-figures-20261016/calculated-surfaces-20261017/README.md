# Surfaces réelles de trois régions de supports — 17 octobre 2026

Les deux planches montrent les surfaces calculées des régions **003, 009 et
010**, avec leurs coordonnées et toutes leurs facettes conservées :

- [Vue d'ensemble](reference-002/calculated-surfaces-overview.png) — pièce
  translucide et trois régions dans la pose d'impression ; [PDF](reference-002/calculated-surfaces-overview.pdf)
  et [SVG](reference-002/calculated-surfaces-overview.svg).
- [Détails des grilles, peaux et dents](reference-002/calculated-surfaces-details.png)
  — peaux translucides pour montrer les grilles ; [PDF](reference-002/calculated-surfaces-details.pdf)
  et [SVG](reference-002/calculated-surfaces-details.svg).

La mention **« 3 régions calculées / 7 ; contrôle global encore en cours »**
désigne les trois checkpoints revérifiés pour ces images. Leurs graphes
matériels passent le contrôle local des liaisons haut/bas. Le label historique
de génération est conservé dans le [contrôle indépendant](local-checkpoint-review.json).
Le code retour du processus 010 attend encore sa collecte par le superviseur.
Les admissions collectives et les trajectoires de supports sur toutes les
couches restent en cours.

Les deux PNG et les deux pages PDF ont été relus. Les cinq barres d'échelle
de 100 mm ou 10 mm sont vérifiées dans la projection du moteur de rendu.
Le [reçu du rendu](reference-002/render-receipt.json), la
[revue visuelle](visual-qa-final.json) et la [revue des PNG et empreintes par
l'agent principal](root-review.json) conservent ces contrôles. Les PDF et SVG
contiennent les images raster et des textes/barres vectoriels.

## Reproduire les images

Les sept petits fichiers du renderer et du contrôle local ont été copiés
dans un nouveau dossier `work/`, puis exécutés depuis `/` avec le runtime
AM011 : **retour 0, 7,429 s et deux PNG identiques à l'octet**. Le
[contrôle du rejeu](replay-validation.json) et son
[exécution](replay-execution.json), avec le [reçu du rendu rejoué](replay-render-receipt.json),
restent distincts du rendu initial. La [revue finale](visual-replay-qa-final.json)
lie le contrôle visuel et ce rejeu.

Depuis la racine du projet, utiliser un nom de copie neuf :

```sh
SURFACES=parts/993-eng-carrier-0001/source/progress-figures-20261016/calculated-surfaces-20261017
REPLAY=work/carrier-surfaces-gallery-replay-001
mkdir "$REPLAY" &&
cp "$SURFACES/render_v2.py" "$SURFACES/review_adapter.py" \
  "$SURFACES/source-reuse.json" "$SURFACES/local-checkpoint-review.json" "$REPLAY/" &&
cp -R "$SURFACES/sources" "$REPLAY/" &&
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
work/part-workflow/runtimes/pyslm-coverage-011/env/bin/python -I -B \
  work/carrier-surfaces-gallery-replay-001/render_v2.py \
  --local-review work/carrier-surfaces-gallery-replay-001/local-checkpoint-review.json \
  --local-review-sha256 0a75a5198f37ca34a413a1bff78661948a0853f66e7ef3035631f8bf4ae1ff83
```

Les nouveaux exports sont créés dans `work/carrier-surfaces-gallery-replay-001/reference-002/`.
Le renderer refuse une destination existante ou une empreinte différente.
Il dépend des datasets conservés sous `work/carrier-process-20261016/` et
du runtime AM011 ; ces gros fichiers ne sont pas dupliqués dans cette archive
d'images. Il ne reconstruit aucune région et ne relance aucune admission.

Les trois helpers sous `sources/` sont les fichiers historiques conservés à
l'octet. La [source du contrôle local](review-source/verify_receipts.py) est
archivée pour rendre le reçu inspectable ; sa sortie initiale était le reçu
indépendant lié ci-dessus. Le [manifeste de publication](publication.json)
donne les empreintes des copies présentes dans ce dossier.
