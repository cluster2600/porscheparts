# Cutter local dans un seul arbre exact

Cette voie conserve l'expression du volume libre, tout en limitant la taille
du cutter. Pour A=chain, C=part et M=mask, elle calcule
`(A \ (C ∩ B)) ∩ M`, où B contient strictement A. L'identité
`A \ (C ∩ B) = A \ C` est exacte dès que A⊂B.

```sh
python3 parts/993-eng-carrier-0001/source/native-pymesh-clip-20261016/setup.py \
  /chemin/neuf/pymesh-clip --pymesh-runtime /chemin/pymesh

python3 /chemin/neuf/pymesh-clip/run.py CHAIN.npz MASK.npz PART.npz \
  /chemin/neuf/pymesh-clip/jobs/essai-001 --timeout-seconds 1200
```

Le runtime PyMesh fourni doit avoir été construit et vérifié par
`native-pymesh-20261016/setup.py`. Le nouveau préfixe réutilise ce rootfs
explicite en lecture seule, sans copie supplémentaire ni installation
système. Tous ses modules Python, bibliothèques ELF et liens sont vérifiés
avant/après chaque calcul. Chaque dossier de sortie doit être neuf.

Le worker calcule les six bornes des coordonnées originales de chain et
applique exactement un `np.nextafter` vers l'infini extérieur sur chacune.
Ce sont les valeurs IEEE adjacentes, sans épaisseur arbitraire. Il vérifie
que toutes les coordonnées des sommets de chain sont strictement dedans et
que la chaîne est fermée et orientée par ses arêtes indexées. La boîte est
convexe : elle contient donc ses triangles et le matériau borné qu'ils
délimitent. Le fichier `clip-bbox.npz` et son SHA conservent la construction.
La boîte est utilisée dans l'arbre CGAL exact, puis `.mesh` est lu seulement
à la racine ; aucun résultat intermédiaire n'est converti en doubles.

L'ordre de filiation devient **chain, part, clip_bbox, mask**, avec les
nombres de faces par feuille dans `receipt.json`. La boîte strictement
englobante ne doit pas devenir une paroi du volume libre. Le résultat float64
final reste soumis au snap51/5, à la topologie, aux contacts exacts et à la
borne de dérive initiale. Le CSG brut n'est pas admis par son seul volume.

Les budgets de 600 ou1 200 s sont explicites. La voie utilise au plus deux
CPU, 4 Gio, sans swap et aucun réseau, puis vérifie l'arrêt de son scope.
La précision du snap n'est jamais un paramètre de ce booléen.

Témoin exécuté : deux prismes triangulaires superposés, soustraction entre
Z8 et Z12. Le CSG conserve3 200 mm³ mais son export brut comporte des alertes
de contact. Après snap51/5 : même volume, coordonnées exactement IEEE, zéro
intersection non conforme selon Epeck, topologie fermée/orientée/manifold,
deux intervalles attendus et dérive exacte admise. Les15 alertes libigl
restantes sont15 contacts ponctuels dans le simplexe déjà partagé, selon
une adjudication rationnelle indépendante liée au SHA du maillage et des
paires. Tous les refus bruts et rapports sont conservés.

Le moteur et ses licences restent ceux du runtime PyMesh épinglé ; le commit
C++ installé non exposé reste inconnu. Le bootstrap conserve le SHA exact de
l'image et du binaire et n'utilise pas une autre image.
