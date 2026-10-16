# Connexions entre les feuilles de support

`material_connections.connected_material(vertices, faces, groups)` lit les
vrais triangles float64 et les groupes de matière générés. Chaque groupe
doit couvrir sa plage de faces sans omission ni doublon et être connexe avant
que ses contacts puissent être regroupés avec ceux d'une autre feuille.

La fonction réutilise le classifieur rationnel du projet. Les boîtes et
l'index Rtree servent seulement à trouver les candidats : les décisions
portent sur les coordonnées IEEE exactes, sans distance de soudure.

- Deux plans distincts sont reliés par un segment de longueur positive.
- Deux groupes coplanaires sont reliés par une intersection d'aire positive.
- Un point seul, ou un jeu d'un seul ULP, ne relie pas les groupes.
- À l'intérieur d'un même groupe, les arêtes partagées exactes relient aussi
  les triangles et les morceaux d'une carte découpée.

La sortie conserve une forêt de témoins suffisante pour établir les
connexions ; elle ne prétend pas énumérer toutes les intersections. Chaque
composante certifiée doit hériter d'un contact supérieur et inférieur. Les
identités des contacts proviennent des interfaces du générateur ; l'audit
complet des expositions reste obligatoire pour les couches réellement
construites.

Les triangles exactement dégénérés sont refusés avant le graphe. Pour éviter
un calcul rationnel inutile sur chaque triangle ordinaire, un filtre prouve
seulement la non-nullité : avec M le maximum absolu des coordonnées, dans
`[2^-400, 2^400]`, une composante du produit vectoriel flottant dépassant
`32 * eps * M²` ne peut provenir d'une aire exacte nulle. Cette borne absolue
conservative inclut les erreurs de soustraction et de produit ; tous les
autres cas sont recalculés en rationnels. Les intersections elles-mêmes sont
toujours rationnelles.

Neuf tests natifs couvrent les liaisons, les faux contacts, les groupes
disjoints, les triangles nuls ou minuscules et la copie autonome des sources :

```sh
AM_PYTHON -B -m unittest discover -s tests -p test_carrier_material_connections.py -v
```

Une copie plate doit inclure le fichier gelé
`design-20261016/classify_mesh_contacts.py` à côté de ce module. Le reçu garde
ses deux identités de source et celle des tableaux de géométrie.
