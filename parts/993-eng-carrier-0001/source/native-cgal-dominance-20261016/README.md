# Réduction exacte par dominance de prismes

Le helper supprime seulement des prismes verticaux dont l'inclusion dans
l'union des autres est certifiée. Tous ont un fond commun Z=0 et un toit
affine triangulaire à Z≥0. Les coordonnées ne sont ni déplacées ni arrondies.

```sh
python3 parts/993-eng-carrier-0001/source/native-cgal-dominance-20261016/setup.py \
  /chemin/neuf/cgal-dominance --cgal-runtime /chemin/cgal-snap

python3 /chemin/neuf/cgal-dominance/run.py TOITS.npz \
  /chemin/neuf/cgal-dominance/jobs/essai-001 --floor-z-mm 0
```

Le NPZ contient `vertices` float64 et `faces` entiers, plus éventuellement
`source_face_ids` uniques. Ce sont les **toits**, et non la soupe des faces
des prismes déjà construits. Le résultat `retained-roofs.npz` conserve le
tableau de coordonnées byte pour byte et les indices des faces retenues.
L'assembleur reconstruit ensuite les mêmes prismes pleins positifs, avec le
même fond. Le helper préserve leur **union ensembliste** ; il ne préserve ni
les multiplicités d'une chaîne orientée ni la somme des volumes superposés.

Pour chaque hauteur H exactement horizontale, CGAL Epeck construit l'union
polygonale P_H de tous ses triangles XY. Un candidat T est supprimé seulement
si `max(Z(T)) ≤ H` et si la différence exacte du triangle XY entier avec P_H
est vide. Le maximum d'un toit affine sur un triangle se trouve à un sommet ;
cela donne `Prisme(T) ⊂ P_H × [0,H]`. Le test porte sur toute la surface et
détecte les trous et les concavités, même si les trois sommets sont dedans.

Pour un candidat horizontal, H doit être **strictement supérieur** à sa
hauteur. Les patches sont construits avant toute suppression et conservent
leurs IDs sources. Si une face d'un patch est ensuite supprimée, son propre
certificat renvoie à une hauteur strictement plus grande. Une chaîne finie
de hauteurs croissantes aboutit donc à des horizontaux retenus ; il n'y a pas
de cycle.

La différence régularisée de `Polygon_set_2` suffit pour un triangle d'aire
positive et une union polygonale fermée : un point de T hors de cette union
fermée aurait un voisinage extérieur qui rencontre l'intérieur de T avec
une aire positive. Les projections XY dégénérées ne relèvent pas de cet
argument et restent explicitement conservées. Aucun seuil d'aire n'existe.

`certificates.json` donne les indices et IDs sources retirés, la hauteur
exacte de chaque patch, ses faces sources, le maximum Z exact et le résultat
de couverture. `audit.json` relie entrée, résultat et certificats par SHA256,
et vérifie l'identité des coordonnées et indices conservés. Sources,
bibliothèques et binaire sont épinglés avant/après. Les appels utilisent au
plus deux CPU, 4 Gio, sans swap, 600 s et aucun réseau, avec nettoyage du
scope vérifié. Le préfixe et chaque dossier de calcul doivent être neufs.

Six témoins natifs sont fournis par `witnesses.py` : couverture par une union,
domaine percé, domaine non convexe, chaîne de hauteurs, débordement positif
d'un seul ulp et refus d'un toit sous le fond. Ils ont été exécutés avec les
verdicts attendus. La preuve et le code ont reçu une relecture indépendante.
Ce helper n'a exécuté aucune pièce réelle lors de ces témoins.

CGAL 6.1.3 est réutilisé depuis le préfixe explicitement fourni. Le paquet
`Polygon_set_2` est GPL-3.0-or-later ou sous licence commerciale ; le noyau
exact est LGPL-3.0-or-later ou commercial. Source primaire :
[Polygon_set_2 figé](https://github.com/CGAL/cgal/blob/109ed62eeaa7e38eb383e9444700e6ff7bd4c449/Boolean_set_operations_2/include/CGAL/Polygon_set_2.h).
