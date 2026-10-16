# Autoraffinement natif épinglé

Ce parcours Linux compile CGAL 6.1.3, commit
`109ed62eeaa7e38eb383e9444700e6ff7bd4c449`, dans un préfixe neuf, sans
installation système. Il réutilise explicitement un interpréteur d'audit ayant
NumPy et libigl 2.6.3. Il faut déjà disposer de Python 3.12+, CMake, g++, Boost,
GMP, du runtime MPFR, de `systemd --user`, `bwrap`, `apt-get` et `dpkg-deb`.

```sh
python3 parts/993-eng-carrier-0001/source/native-cgal-20261016/setup.py \
  /chemin/neuf/cgal-snap --audit-python /chemin/venv-audit/bin/python

python3 /chemin/neuf/cgal-snap/run.py ENTREE.npz \
  /chemin/neuf/cgal-snap/jobs/essai-001 \
  --grid-bits 51 --iterations 5 --cumulative-grid-bound
```

L'installateur vérifie le SHA256 de l'archive CGAL et du paquet MPFR, extrait
uniquement les fichiers de développement dans son propre préfixe, compile à
deux CPU au plus, 4 Gio, sans swap, pendant 600 s au plus. Le reçu enregistre
compilateur, dépendances, bibliothèques chargées, sources et binaire. Les mêmes
bornes s'appliquent aux appels natifs ; leur réseau est isolé et le nettoyage
du scope possédé est vérifié.

La précision et le budget sont des entrées explicites. `51/5` est le choix
figé pour la campagne du support. Le pas par axe est celui du code amont :
`2**(frexp(max(abs(bbox_min),abs(bbox_max))).exponent + 1 - grid_bits)`.
Le domaine n'est pas recentré. La borne reprise par le dossier est
`iterations * norm(grid_steps) / 2` ; elle n'est jamais élargie après mesure.

Chaque dossier conserve la filiation `autorefine_input_face`, les attributs
de face transférables et le résultat, y compris en cas de refus. Le retour
CGAL vrai ne suffit pas : la topologie peut rester non manifold
([cas amont #9192](https://github.com/CGAL/cgal/issues/9192)).

La mesure libigl de dérive du premier worker est conservée pour l'historique.
Un témoin de triangle très mince en a démontré une erreur. Pour admettre une
sortie de la campagne, employer ensuite le réauditeur exact séparé
[`native-cgal-distance-20261016-v2`](../native-cgal-distance-20261016-v2/README.md),
sans relancer ni modifier le snap. Le reçu initial conserve son refus.

CGAL autorefinement : GPL-3.0-or-later ou licence commerciale ; noyau CGAL :
LGPL-3.0-or-later ou licence commerciale ; MPFR : LGPL-3.0-or-later. Les
archives et binaires restent hors du dépôt. Sources primaires :
[API figée](https://github.com/CGAL/cgal/blob/109ed62eeaa7e38eb383e9444700e6ff7bd4c449/Polygon_mesh_processing/include/CGAL/Polygon_mesh_processing/autorefinement.h),
[implémentation du snap](https://github.com/CGAL/cgal/blob/109ed62eeaa7e38eb383e9444700e6ff7bd4c449/Polygon_mesh_processing/include/CGAL/Polygon_mesh_processing/internal/triangle_soup_snap_rounding.h).
