# Booléens exacts natifs à partir du runtime conservé

Ce bootstrap Linux reconstruit un préfixe neuf depuis **l'archive Docker
exacte conservée**, SHA256
`536dc79c0bddeeffe2d86b85441179774cc515ce1d8f130eb62c06c1f72eba56`.
Elle provient de l'image
`sha256:ecf699d33793efe612b66c36b2a7d3954085af55999cc3f631748fcf1671eb4e`.
Le bootstrap ne remplace pas cette entrée par un téléchargement `latest`.
L'archive fait 439 278 729 octets ; le rootfs extrait environ 1,1 Go. Elle
reste hors du dépôt. Aucun paquet système n'est installé.

```sh
python3 parts/993-eng-carrier-0001/source/native-pymesh-20261016/setup.py \
  /chemin/neuf/pymesh --rootfs-archive /chemin/rootfs.tar.gz

python3 /chemin/neuf/pymesh/run.py CHAIN.npz MASK.npz PART.npz \
  /chemin/neuf/pymesh/jobs/essai-001 --timeout-seconds 600
```

La durée doit être explicite : 600 s, ou 1 200 s uniquement pour les cas dont
le plan a autorisé ce budget. Les limites restent deux CPU, 4 Gio, sans swap,
réseau isolé, rootfs et entrées en lecture seule. Le lanceur copie ses sources
et le reçu d'installation avant calcul ; il vérifie les entrées, sources,
bibliothèques, modules Python et liens symboliques avant/après, puis l'arrêt
du scope possédé.

L'opération est la voie v4 déjà testée :
`intersection(difference(chain, part), mask)`. Un seul `pymesh.CSGTree`
conserve les constructions exactes intermédiaires ; `.mesh` n'est lu qu'à
la racine. L'ordre de filiation est donc **chain, part, mask**. Le résultat
float64 final, ses attributs `source_face` et `source` et leurs SHA restent
à contrôler par les audits géométriques séparés. Le booléen seul n'admet pas
une enveloppe pour la suite.

`original_v4.py` conserve le lanceur initial byte pour byte, SHA256
`40d7c2d11586abc84c500ec010561f867fac59cbb1c523b367ae282b649d5901`.
Le nouveau `run.py` rend le préfixe reproductible, impose le budget explicite
et ajoute la provenance du runtime ; l'expression CSG est conservée.

La reproduction complète et un témoin de deux prismes superposés ont été
exécutés. Après découpe de Z8 à Z12 : volume 3 200 mm³, deux composantes
fermées et orientées, aucun bord libre/non manifold, aucune paire
d'intersection libigl, occupation Z4/Z9/Z10/Z11/Z16 : vrai/faux/faux/faux/vrai.

Runtime : PyMesh 0.3, Python 3.6.11, NumPy 1.19.0 ; binaire natif SHA256
`17cd2bb3a74539b1f913501f49a362f65cb395a62ab65bc5a6e8815ccc585d8a`.
La métadonnée PyMesh indique MPL sans numéro de version. Les composants
embarqués conservent leurs licences. Le commit C++ installé exact n'est pas
exposé par l'image et reste inconnu ; les identités de l'image, de l'archive
et du binaire sont enregistrées. Sources primaires de l'API :
[PyMesh CSGTree](https://github.com/PyMesh/PyMesh/blob/main/tools/Boolean/IGL/IGLCSGTree.cpp),
[libigl CSGTree](https://github.com/libigl/libigl/blob/main/include/igl/copyleft/cgal/CSGTree.h).
