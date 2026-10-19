# Reprendre le maillage depuis le STEP

Le passage reproductible `bounded-webs`, lancé après autorisation du plafond de
1,30 kg, utilise une taille minimale de **0,25 mm**. La valeur de 0,5 mm avait
échoué sur un rayon de 0,5 mm avec 0,07447 mm d'écart inverse au STEP. Les
autres paramètres et le seuil de 0,06 mm sont conservés. Dans `run-001`, les
587 404 triangles donnent zéro aiguille et zéro intersection, avec des maxima
échantillonnés de 0,018988 / 0,047388 mm dans les deux sens.

Le [dossier de reprise](../../../../docs/reports/993_CARRIER_WORKFLOW_20261016.md)
et la [recette](../../../../manufacturing/workflows/993-carrier.json) décrivent
ce passage. Les résultats 008 ci-dessous sont les essais antérieurs conservés
dans `results.json`, et ne désignent pas cette nouvelle sélection.

## Essais conservés avant la sélection bounded-webs

Le maillage de présentation V6f contenait 74 triangles aiguilles et s'écartait
localement du STEP. Un point situé à 0,371 mm de la surface exacte a été
contrôlé avec OpenCascade. Ce défaut appartenait au STL, pas au STEP.

Le parcours retenu reconstruit donc le STL avec **Gmsh 4.15.2**, depuis un STEP
figé par SHA-256. Il ne déplace aucune interface dans le CAD. Les paramètres
sont fixes : éléments linéaires, taille 0,5–3 mm, courbure 96, frontal Delaunay,
sans lissage explicite.

| Essai | Résultat conservé | Décision |
|---|---|---|
| PyMesh, nettoyage exact | aucun doublon ou sommet isolé à retirer ; 74 aiguilles restantes | insuffisant |
| Diagonales locales coplanaires | la conservation des aires refuse les diagonales traversant les contours concaves | refusé |
| PyMesh/Triangle, PSLG | 11 aiguilles, 439 arêtes ouvertes | refusé |
| PyMesh/Triangle, raffinement des triangles sources | 17 aiguilles, volume et surface conservés | refusé |
| Gmsh depuis le STEP V6f | 348 208 triangles, zéro aiguille, maillage fermé | représentation géométrique retenue |
| Gmsh depuis l'essai CAD aux peaux de 1,5 mm et appuis restaurés | 349 898 triangles, zéro aiguille, maillage fermé | géométrie admise ; essai de conception conservé après rejet mécanique séparé |

Les critères initiaux et les essais refusés restent dans
`work/carrier-remesh-20261016/`. Aucun seuil de distance n'a été augmenté pour
faire passer la comparaison avec l'ancien STL : cette comparaison est restée
refusée. La référence a ensuite été contrôlée directement dans le STEP, avec
le même seuil de corde de **0,06 mm demandé par l'exporteur d'origine**.

Pour le dernier essai de géométrie, le contrôle donne 0,01524 mm du STL vers
le STEP sur 3 072 sondes, et 0,04373 mm du STEP vers le STL sur 8 108 points
classés dans les faces découpées. Ce sont des maxima échantillonnés. Les quatre
alésages centraux, les deux alésages d'extrémité et les faces d'appui font aussi
l'objet d'un contrôle indépendant dans `audit.py`.

Le diagnostic de paroi n'est pas confondu avec l'absence d'aiguilles : le même
essai conserve 31,677 % de surface mesurée sous 1,5 mm, avec un percentile 1 %
à 1,3499 mm. Les valeurs restent dans [results.json](results.json).

## Installer le runtime local

L'installateur crée `work/part-workflow/runtimes/geometry/` et produit son
`runtime.json`, directement utilisable par le lanceur de recettes. Fournir
explicitement le Python CAD existant : il doit déjà contenir build123d 0.11.1,
OCP 7.9.3.1 et NumPy 2.0.2.

```sh
python3 parts/993-eng-carrier-0001/source/remesh-20261016/setup_runtime.py \
  --cad-python "$CAD_PY"
```

Seul Gmsh 4.15.2 est installé dans le nouvel environnement ; les roues officielles
sont vérifiées par SHA-256. Les bibliothèques CAD sont empruntées en lecture
seule par un fichier `.pth`. L'ancien environnement n'est ni modifié ni recopié.
La provenance enregistre les versions, l'ABI Python, les hachages des modules
natifs et le rapport d'installation. Une seconde invocation vérifie le runtime
complet et refuse les changements de versions, de sources ou d'empreintes.
Un dossier préexistant sans reçu complet est préservé et refusé.

Le Python commun à `gmsh_remesh.py` et `brep_audit.py` devient :

```sh
PY="$PWD/work/part-workflow/runtimes/geometry/bin/python"
```

Le Python CAD fourni reste donc une dépendance locale explicite. Pour une
installation entièrement autonome, il faudrait distribuer séparément ce
runtime CAD et ses dépendances.

Le backend d'audit indépendant s'installe par :

```sh
python3 parts/993-eng-carrier-0001/source/remesh-20261016/setup_mesh_audit.py
```

Il produit `work/part-workflow/runtimes/mesh-audit/runtime.json` avec le champ
`mesh_audit_python`. Son lanceur `bin/python` exécute un conteneur Linux ARM64
local : Python 3.11.15, NumPy 2.2.6, SciPy 1.15.3, libigl 2.6.3,
trimesh 4.8.3 et rtree 1.4.1. L'image de base et toutes les roues sont figées
par SHA-256, sans compilation. L'exécution utilise deux CPU, 4 Gio, aucun
swap et aucun réseau ; le dépôt est monté en lecture seule et `work/` permet
les nouvelles sorties. Docker doit être disponible. Les binaires, licences
et rapports d'installation restent dans le runtime externe au dépôt.

La roue officielle libigl 2.6.3 macOS ARM64 a bien été essayée mais son import
a échoué avec `std::bad_cast`. Cet essai est conservé séparément ; le backend
Linux ci-dessus a passé l'import natif et les tests connus de distance et
d'intersection. Une seconde invocation vérifie son identité sans le reconstruire.

## Exécuter les outils

Depuis la racine du dépôt, dans un environnement possédant Gmsh 4.15.2 :

```sh
"$PY" parts/993-eng-carrier-0001/source/remesh-20261016/gmsh_remesh.py \
  "$STEP" "$FRESH_OUT" --identity-receipt "$GEOMETRY_JSON"
```

Le dossier de sortie doit être nouveau. Les sorties sont le STL, le maillage
Gmsh et `meshing.json`. `remesh.py` conserve le parcours expérimental PyMesh
avec son nettoyage exact et son raffinement plan ; il ne remplace pas cette
commande retenue.

`--identity-receipt` lit strictement `geometry_sha256["carrier.step"]` du reçu
CAD. L'alternative `--expected-step-sha256` est exclusive. Le reçu `meshing.json`
contient `candidate_STL_sha256` et `candidate_STL`, chemin relatif du STL produit.

Le contrôle des topologies, des cylindres et des distances bidirectionnelles
entre STL utilise les bibliothèques libigl 2.6.3 et NumPy :

```sh
"$AUDIT_PY" parts/993-eng-carrier-0001/source/remesh-20261016/audit.py \
  "$REFERENCE_STL" "$CANDIDATE_STL" "$FRESH_AUDIT_OUT" --criteria "$CRITERIA_JSON"
```

Cette comparaison STL–STL conserve son propre verdict, y compris lorsque le
STL de référence est imparfait. Le contrôle suivant emploie le STEP exact et
produit aussi les points CAD nécessaires au contrôle de la direction inverse :

```sh
"$PY" -B parts/993-eng-carrier-0001/source/remesh-20261016/brep_audit.py \
  "$STEP" "$REFERENCE_STL" "$CANDIDATE_STL" "$FRESH_BREP_OUT" \
  --identity-receipt "$GEOMETRY_JSON"
"$AUDIT_PY" -B parts/993-eng-carrier-0001/source/remesh-20261016/cad_mesh_audit.py \
  "$CANDIDATE_STL" "$FRESH_BREP_OUT/brep-audit.json" \
  "$FRESH_BREP_OUT/exact-CAD-surface-samples.npz" "$FRESH_CAD_MESH_OUT"
```

Ici `AUDIT_PY` est `work/part-workflow/runtimes/mesh-audit/bin/python`.
Le premier contrôle écrit l'empreinte des points CAD et le volume exact ; le
second vérifie cette empreinte et celle du STL, puis mesure CAD→STL, topologie,
intersections et alésages/appuis. Les deux directions conservent le seuil
0,06 mm, sans le comparer au STL ancien défectueux. Les commandes retournent
le code 2 si leur contrôle est refusé et conservent le rapport. Pour les anciens
reçus sans empreinte des points CAD, seule l'option explicite
`--expected-samples-sha256` permet de fournir cette identité.

## Localiser les faibles rayons d'épaisseur

`analyze_thickness.py DUMP OUT` relit la carte binaire existante du checker,
sans relancer celui-ci. Il additionne les aires par régions géométriques et
conserve les plages connexes sous 1,4 mm avec leurs coordonnées. Sur l'essai
008, les peaux planes sont à 1,5 mm ; les parois courbes totalisent
52 609,27 mm² dans [1,49 ; 1,5). `probe_thickness_brep.py` a confirmé trois
rayons normaux exacts de 1,493869 / 1,494898 / 1,497042 mm. La construction
ancienne translate les courbes suivant Y : elle ne réalise pas un décalage
normal constant. Le rayon de 0,278061 mm à (83,313 ; 14,882 ; −13,502) devient
0,278144 mm sur le STEP : cette réduction locale est aussi réelle.

Les bords proches des arêtes demandent une interprétation séparée : certains
rayons courts suivent la normale d'une facette plutôt que celle d'une face
analytique. `render_thickness.py` trace les centres réels des faces et les aires
concernées ; il n'interpole pas la carte. Le seuil de 1,5 mm et son refus restent
conservés. Ces outils ne retirent aucune languette des interfaces figées.

`render_comparison.py` trace les vraies sections du STEP et des deux STL, dans
les mêmes coordonnées. Il requiert build123d/OCP, NumPy et Matplotlib.

## Provenance des logiciels

PyMesh 0.3/Python 3.6.11 a été exécuté dans l'image externe
`pymesh/pymesh@sha256:ecf699d33793efe612b66c36b2a7d3954085af55999cc3f631748fcf1671eb4e`.
Son nettoyage suit l'[API officielle](https://pymesh.readthedocs.io/en/latest/api_local_mesh_cleanup.html)
et le raffinement emploie le [wrapper Triangle officiel](https://pymesh.readthedocs.io/en/latest/api_mesh_generation.html).
L'image reste externe ; aucune bibliothèque binaire n'est copiée au dépôt.

Gmsh natif ARM64 4.15.2 a été installé dans un environnement de travail séparé.
Ses métadonnées indiquent GPLv2+ ; les hachages de la bibliothèque, du module
Python et des métadonnées sont conservés. Les réglages sont décrits par la
[documentation Gmsh](https://gmsh.info/doc/texinfo/).
Les distances et intersections utilisent libigl 2.6.3 ; le calcul de distance
point–triangle relève de [MPL-2.0](https://raw.githubusercontent.com/libigl/libigl/main/include/igl/point_mesh_squared_distance.h).
