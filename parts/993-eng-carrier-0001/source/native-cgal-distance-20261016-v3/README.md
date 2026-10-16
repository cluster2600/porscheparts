# Bornes exactes de distance par triangles témoins

Ce réauditeur garde les NPZ et les reçus de snap initiaux intacts. Il remesure
les deux directions avec CGAL 6.1.3 Epeck, puis compare les distances **au
carré, exactement**, au carré de la même borne IEEE du reçu initial. Pour
chaque échantillon, un triangle réel de la cible est recherché à partir de la
filiation. Sa distance exacte est une borne supérieure rigoureuse de la
distance au maillage entier. Si elle respecte le seuil, le point est certifié
sans rechercher le minimum global. Sinon un arbre AABB exact prend le relais.
Le code compte séparément ces témoins et les appels AABB. La filiation est
seulement une aide à la recherche : le PASS résulte toujours d'une vraie
distance vers un triangle appartenant à la cible. Il ne refait aucun booléen
ou snap.

```sh
python3 parts/993-eng-carrier-0001/source/native-cgal-distance-20261016-v3/setup.py \
  /chemin/neuf/cgal-distance --cgal-runtime /chemin/cgal-snap

python3 /chemin/neuf/cgal-distance/run.py ENTREE.npz \
  /chemin/cgal-snap/jobs/essai-001 \
  /chemin/neuf/cgal-distance/jobs/mesure-001
```

Le préfixe d'installation et le dossier de mesure doivent être neufs. Le
préfixe CGAL et son interpréteur d'audit sont explicites ; aucune dépendance
Python ou système n'est modifiée. Compilation et mesure ont une limite de
deux CPU, 4 Gio, sans swap et 600 s ; la mesure n'a pas de réseau. Le lanceur
copie ses sources et les reçus d'origine avant exécution, vérifie leurs SHA
avant/après, puis vérifie l'arrêt de son scope.

Toutes les faces d'aire **strictement positive** restent des triangles,
quelle que soit leur finesse. Seules les faces exactement collinéaires sont
représentées par leur plus long segment exact, ou par un point si leurs trois
sommets coïncident. Elles ne sont pas passées comme primitives dégénérées à
l'arbre de triangles. Aucun seuil d'aire n'est employé. Les indices int32 ou
int64 sont convertis en int64 seulement après contrôle entier/bornes et preuve
de conversion sans perte ; les coordonnées float64 ne changent pas.

Les requêtes couvrent tous les sommets et les barycentres rationnels exacts
de toutes les faces. C'est une mesure échantillonnée explicite, et non un
certificat continu de distance de Hausdorff. Le reçu natif enregistre les
fractions exactes des maxima des **bornes supérieures** au carré et de la
borne admise, les coordonnées des pires échantillons et les nombres de
primitives de chaque type. Ces maxima ne sont pas présentés comme les vrais
minima globaux de distance lorsque les témoins locaux suffisent.

`audit.json` relie `input_sha256`, `result_sha256`,
`origin_native_sha256`, `origin_audit_sha256` et
`origin_execution_receipt_sha256`. Il vérifie de nouveau la topologie indexée
et la filiation des faces, et expose `native_geometry_gate_pass`,
`topology_gate_pass`, `drift_gate_pass` et `pass`. Un refus initial dû au seul
mesureur reste présent dans `origin_geometry_execution_status` et
`origin_libigl_drift_gate_pass` ; le nouveau reçu constitue une mesure
indépendante liée à cette même géométrie.

Les témoins exécutés et leurs verdicts sont conservés dans le manifeste de
campagne, avec ceux des versions antérieures. La version 1, qui refusait trop
strictement les indices int32, reste dans `native-cgal-distance-20261016` ; la
version 2 exacte mais lente reste dans `native-cgal-distance-20261016-v2`.

Licences des dépendances : CGAL AABB GPL-3.0-or-later ou commercial ; noyau
exact et MPFR LGPL-3.0-or-later (noyau également disponible sous licence
commerciale). Le reçu conserve également les licences
du runtime CGAL réutilisé. Référence primaire :
[AABB_tree figé](https://github.com/CGAL/cgal/blob/109ed62eeaa7e38eb383e9444700e6ff7bd4c449/AABB_tree/include/CGAL/AABB_tree.h).
