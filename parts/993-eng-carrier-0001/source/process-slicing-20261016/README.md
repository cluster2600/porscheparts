# Tranchage ordonné et contrôle des trajectoires

Cette branche conserve les cas d'intersection et les hachures natifs
Trimesh/PySLM. Elle prépare les bornes Z de chaque triangle, puis calcule les
couches indépendantes dans **quatre processus**, avec au plus huit résultats
en attente. La publication des fichiers et la section des supports restent
ordonnées dans le processus parent. La pose est fixée avant la préparation des
bornes ; les workers ne modifient ni les sommets ni les paramètres de hachure.

## Vérifications exécutées

Les huit plans de couches 0, 166, 167, 299, 518, 701, 900 et 1033 ont été
fixés avant le benchmark du vrai carrier. Les coordonnées des contours, leur
ordre, les vecteurs de hachure et les aires sont **exactement égaux** à la voie
séquentielle initiale. Le
[benchmark à quatre processus](parallel-benchmark.json) mesure 32,282 s contre
11,808 s, démarrage compris ; le maximum observé par worker est 178 Mo et le
groupe est fermé après calcul. Ce résultat sur huit couches n'est pas présenté
comme un temps de préparation complet.

La [présélection seule](serial-filter-benchmark.json) conserve aussi les huit
résultats, mais ne procure pas de gain temporel sur ce témoin. Ce résultat est
conservé : l'accélération observée vient du travail simultané sur les couches.

Les [dix tests natifs](native-tests.json) couvrent les trous, les plans aux
frontières, le refus d'une section ouverte, l'ordre des processus, leur
fermeture, les anneaux imbriqués et les segments dupliqués. Le contre-exemple
d'un segment dont les deux extrémités sont dans la matière mais qui traverse
un trou est explicitement refusé.

## Audit des vecteurs

`audit_scanpaths.py` reconstruit le domaine des sections avec la parité des
anneaux, ce qui conserve les trous et les îlots, quelle que soit leur
orientation. Il vérifie les **segments entiers** des hachures et contours avec
[Shapely covers](https://shapely.readthedocs.io/en/stable/reference/shapely.covers.html).
Aucun buffer ne déplace la frontière et aucun segment extérieur n'est admis.
Les longueurs nulles et doublons exacts sont refusés. La tolérance relative
de 1e−10 concerne seulement la comparaison de l'aire reconstruite avec le CSV,
pas la couverture des trajectoires. L'API `symmetric_difference_all`, marquée
incorrecte et dépréciée par son éditeur, n'est pas utilisée.

Le [premier témoin de trajectoires](part-scanpath-witness.json) passe sur cinq
couches enregistrées du passage initial refusé. Il ne constitue ni un audit
complet des 1 034 couches ni une admission de ses supports. Le rapport complet
doit porter `complete_build_audited: true` pour couvrir un nouveau passage.

## Entrée de la nouvelle préparation

```sh
CHEMIN_DU_PYTHON_AM parts/993-eng-carrier-0001/source/process-slicing-20261016/build_parallel.py \
  work/PASSAGE/surface/carrier-remeshed.stl work/NOUVELLE_PREPARATION \
  --identity-receipt work/PASSAGE/surface/meshing.json --workers 4

CHEMIN_DU_PYTHON_AM parts/993-eng-carrier-0001/source/process-slicing-20261016/audit_scanpaths.py \
  work/NOUVELLE_PREPARATION work/NOUVEL_AUDIT_TRAJECTOIRES
```

Le générateur de régions et de peaux de `process-skins-20261016` reste soumis
à ses propres contrôles d'enveloppes, contacts et collisions. Cette entrée
ne dispense pas de leur admission. Le passage initial et ses sources restent
inchangés.
