# Mesure directe de la géométrie initiale vers une réparation finale

Ce lanceur réutilise explicitement le binaire de distance exact Epeck/AABB de
[la version 3](../native-cgal-distance-20261016-v3/README.md). Il ne réinstalle
rien et ne construit aucune géométrie. Il vérifie le manifeste, le binaire,
les sources, les bibliothèques et les en-têtes CGAL de ce runtime avant et
après le calcul. Ses sources sont copiées avant exécution.

```sh
python3 parts/993-eng-carrier-0001/source/native-cgal-mesh-remeasure-20261016/run.py \
  ORIGINAL_FLOAT.npz REPAIR_CANDIDATE.npz FINAL_SNAP_JOB REPAIR_PLAN.json \
  /nouveau/dossier/distance --distance-runtime /runtime/distance-v3
```

`FINAL_SNAP_JOB` doit posséder ses vrais reçus natifs, sa topologie stricte
admise et son résultat. Les refus de l'ancien mesureur libigl restent
conservés. Le plan fixe la borne originale et l'empreinte de l'export float
initial, avant la réparation. Aucun faux reçu d'origine n'est fabriqué pour
faire passer cette nouvelle étape pour un snap direct.

La mesure compare **directement** tous les sommets et barycentres rationnels
de l'export float original au résultat final, puis l'inverse. Elle couvre
ainsi les deux contrôles snap et la réparation locale dans une seule mesure
géométrique. Les triangles collinéaires initiaux sont traités comme des
segments ou points exacts. Les anciens indices composés servent seulement
d'accélération : chaque distance au triangle témoin est contrôlée exactement,
avec recherche AABB exacte si nécessaire. Ils ne prouvent aucun parent ou
ancrage de la face réparée.

`audit_composed_repair.py` vérifie séparément toutes les coordonnées et les
indices de l'ancien couple exact/float, puis compose sa borne E avec la
nouvelle mesure directe D. Le module de conversion existant est fourni
explicitement, empreinté et inchangé :

```sh
AUDIT_PYTHON audit_composed_repair.py ORIGINAL_NATIVE_JOB FINAL_SNAP_JOB \
  DIRECT_DISTANCE_JOB ORIGINAL_FROZEN_SNAP_JOB REPAIR_PLAN.json \
  /nouveau/dossier/composition --conversion-module FROZEN_COMPOSITION_MODULE.py
```

La comparaison `sqrt(D²)+sqrt(E²) <= L` est rationnelle, sans arrondir ces
racines pour décider. La borne L reste celle d'origine. Le résultat final
porte sur tous les sommets et barycentres déclarés dans les deux sens ; il
ne constitue pas un certificat continu de Hausdorff du résultat réparé.

Le vrai cas gauche a été exécuté : 381 852 échantillons initiaux et 381 651
finaux, en 6,66 s pour le lanceur borné. D vaut au plus 1,310e−13 mm ; la
composition vérifiée donne 1,712e−13 mm, sous l'ancienne borne 8,164e−13 mm.
Le résultat natif final est fermé, orienté et manifold, sans intersection ni
triangle collinéaire. Les quatorze paires libigl sont uniquement des contacts
ponctuels dans leur simplexe partagé. Les neuf faces modifiées restent
explicitement sans preuve positive de parent ou d'ancrage héritée.

Bornes d'exécution : 2 CPU, 4 Gio, zéro swap, réseau nul et 600 s. Aucun CSG
n'a été relancé pour cette mesure. Les licences et versions du noyau restent
celles du runtime de distance vérifié.
