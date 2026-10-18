# Sept enveloppes natives — vues historiques du 16 octobre 2026

Ces planches montrent les **enveloppes volumiques de construction**, avec la
vraie pièce dans sa pose conservée. Elles ne représentent ni les grilles, ni
les dents, ni les couches finales. Le statut visible reste : **« Enveloppes de
construction — surfaces de supports et couches encore en cours »**.

`reference/` conserve les exports et reçus exacts de la référence 004 : les deux
vues globales 003 et une planche distincte des petites régions 003/009. Les
quatre fichiers de `sources/` sont copiés sans modification. Les grands NPZ et
le magasin de preuves ne sont pas dupliqués dans ce dossier.

## Reproduction

Le lanceur `render.py` n'utilise que la bibliothèque standard pour vérifier et
charger ces sources. Les renderers et le lecteur de magasin utilisent le
runtime AM du projet : Python **3.11.15**, NumPy **1.26.4**, Matplotlib
**3.11.2**, VisPy **0.17.0**, avec le backend graphique disponible lors du rejeu.
Depuis la racine de l'espace de travail :

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
work/part-workflow/runtimes/pyslm-coverage-011/env/bin/python -B \
parts/993-eng-carrier-0001/source/progress-figures-20261016/sealed-envelopes-20261016/render.py \
"$PWD" /tmp/993-sealed-envelopes-replay-001
```

Le premier argument est l'espace de travail contenant les données historiques ;
le second doit être un dossier neuf. Le bundle peut être extrait ailleurs et
le lanceur appelé par son chemin absolu depuis n'importe quel répertoire.
Il ne construit aucune enveloppe et ne génère aucune surface ou couche de support.

Ce rejeu est volontairement limité au magasin historique exact
`work/carrier-process-20261016/sealed-envelopes-v2-001/envelopes.json`
(`63391aa2…13ec4`) et au STL retenu
`work/part-workflow/run-001/surface/carrier-remeshed.stl`
(`443b5ae2…a6e`). Les quatre sources copiées et le renderer de base sont
épinglés. Les renderers conservent leurs contrôles du magasin complet, du STEP,
du cache de pièce et des tableaux de pose. Un autre magasin n'est pas accepté.

Le lanceur ne modifie que les chemins des modules privés et lie le renderer de
détails au **nouveau** reçu global. Il vérifie les sources et entrées avant et
après, compare les deux PNG aux références, et écrit `replay-receipt.json` avec
des chemins relatifs. Les reçus historiques de `reference/` restent intacts ;
leurs chemins absolus décrivent l'exécution d'origine et ne sont pas ouverts
par le lanceur. Les nouveaux reçus internes des sources inchangées conservent
leur format historique.

Le [contrôle de portabilité](portable-validation.json) lie le rejeu depuis
`cwd=/`, l'identité des deux PNG, le refus d'une sortie existante, d'un lien
symbolique pendant et d'une source altérée. Le lien est refusé avant résolution
du chemin et création de sa cible. `validation-001/` conserve les reçus du
premier rejeu, avant cette correction de la garde de sortie.
Les quatre contrôles de projection utilisent la matrice
et la transformation installées de VisPy pour un segment monde de 100 mm ;
les barres affichées sont de 100 mm sur les globales et 10 mm sur les détails.
La borne d'arrondi de cette vérification concerne uniquement l'affichage.
Les dates internes des SVG/PDF peuvent varier ; aucune identité binaire de
ces nouveaux exports vectoriels n'est revendiquée.
