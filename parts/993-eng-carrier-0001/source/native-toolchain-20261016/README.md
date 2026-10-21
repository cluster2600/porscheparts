# Reconstruction froide des noyaux natifs

Depuis un checkout contenant les huit dossiers sources voisins, cette
commande Linux reconstruit les cinq outils actuels et son propre venv
d'audit, sans chercher un environnement dans `work` :

```sh
python3.12 parts/993-eng-carrier-0001/source/native-toolchain-20261016/bootstrap.py \
  /chemin/neuf/carrier-native \
  --python /usr/bin/python3.12 \
  --rootfs-archive /archives/rootfs.tar.gz \
  --copy-rootfs-archive
```

`--python` est un CPython 3.12 explicite. Le préfixe doit être neuf. Le
bootstrap télécharge uniquement les roues Linux x86_64 épinglées de NumPy
2.2.6, SciPy 1.15.3 et libigl 2.6.3, puis les installe hors réseau dans son
venv avec `--require-hashes --no-index --no-deps`. Ce sont les versions déjà
employées ; SciPy est une dépendance déclarée de libigl. Le manifeste donne
leurs URLs PyPI primaires et leurs SHA256. Un témoin simple vérifie le
chargement des modules, la distance et le détecteur natif d'intersections.

Le Linux hôte doit être glibc x86_64, avec Python 3.12/venv/pip, g++, CMake,
Boost, les fichiers de développement GMP, le runtime MPFR, `tar`,
`apt-get`, `dpkg-deb`, `bwrap`, une session `systemd --user` et les contrôleurs
cgroup CPU/mémoire. Le dépôt APT doit fournir le paquet exact
`libmpfr-dev=4.2.2-3`, SHA conservé dans l'installateur CGAL. Celui-ci est
seulement téléchargé et extrait dans le préfixe : aucun paquet système n'est
installé ou modifié. Les versions effectivement présentes du compilateur et
des bibliothèques sont enregistrées dans les reçus. Cette commande cible le
backend Linux de la campagne ; elle ne prétend pas installer sur macOS.

L'ordre est :

1. venv d'audit propre et roues vérifiées ;
2. rootfs PyMesh reproduit depuis l'archive exacte ;
3. CGAL 6.1.3 compilé pour le snap ;
4. mesure exacte accélérée par triangles témoins, version3 ;
5. preuve exacte de dominance ;
6. wrapper du cutter local qui réutilise le rootfs PyMesh explicite.

Les préfixes et leurs reçus sont reliés par `runtime.json` ; les sources des
huit dossiers sont empreintées avant/après. Les versions historiques de
distance1 et2 restent dans le checkout avec leurs refus et ne sont pas
recompilées pour le parcours actuel. Les appels de calcul gardent leurs
bornes par outil : deux CPU, 4 Gio, sans swap, réseau nul et durée explicite.
Ce bootstrap n'exécute aucune pièce ou enveloppe de production.

## Archive logicielle à fournir avec un paquet autonome

Le rootfs exact est un artefact logiciel hors Git de 439 278 729 octets :

`SHA256 536dc79c0bddeeffe2d86b85441179774cc515ce1d8f130eb62c06c1f72eba56`

Avec `--copy-rootfs-archive`, il est copié et revérifié dans
`PREFIX/sources/rootfs.tar.gz`. Sans ce drapeau, le chemin explicite reste
référencé. Le paquet de réinstallation doit donc inclure cette archive, les
sources du checkout et les prérequis Linux ; aucun fichier d'une ancienne
campagne n'est nécessaire. Les téléchargements publics CGAL/MPFR et les
roues restent aussi conservés dans le préfixe construit.

L'inspection locale de Docker a réellement rapporté séparément :

- `RepoDigests`: `pymesh/pymesh@sha256:ecf699d33793efe612b66c36b2a7d3954085af55999cc3f631748fcf1671eb4e` ;
- `Id`: `sha256:ecf699d33793efe612b66c36b2a7d3954085af55999cc3f631748fcf1671eb4e`.

Leur égalité est une observation locale, pas une vérification de disponibilité
du digest dans un registre distant. L'archive et son SHA sont l'entrée de
réinstallation effectivement testée ; le bootstrap n'effectue aucun pull.

## Preuves et licences

Les installateurs individuels ont tous été exécutés dans des préfixes neufs,
avec des témoins natifs. Les résultats gelés sont dans
`reproduction-results.json` de chaque dossier concerné. La création froide
du nouveau venv d'audit a aussi été exécutée et vérifiée indépendamment.
L'orchestration consolidée ne prétend pas avoir rejoué tous les compilateurs
et témoins après leur gel ; elle compose ces mêmes installateurs sans les
modifier.

CGAL autorefinement, AABB et Polygon_set_2 : GPL-3.0-or-later ou licence
commerciale ; noyau exact : LGPL-3.0-or-later ou commercial ; MPFR :
LGPL-3.0-or-later. PyMesh2 indique MPL sans numéro dans son image ; le
commit C++ installé non exposé reste inconnu. libigl Python : MPL-2.0 ;
NumPy et SciPy : BSD-3-Clause. Tous les composants embarqués conservent leurs
propres licences. Le code, les archives et les binaires ne sont pas
réétiquetés comme ayant la licence du dépôt.

Sources primaires des trois roues : [NumPy](https://pypi.org/project/numpy/2.2.6/),
[SciPy](https://pypi.org/project/scipy/1.15.3/),
[libigl](https://pypi.org/project/libigl/2.6.3/).
