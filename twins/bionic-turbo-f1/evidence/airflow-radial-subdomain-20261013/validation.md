# Validation et limites

Tous les payloads natifs 077–079 sont relus par empreintes, ainsi que le parent
063. Les entrées sont copiées avant lancement. La nouvelle subdivision n'affecte
que les comptes radiaux des blocs fixes ; les autres fichiers système sont
identiques à 063. Le lecteur indépendant reconstruit les points, cellules et
faces orientées attendus et compare les propriétaires/voisins. Il vérifie les
volumes positifs, la frontière, les zones et les quadrilatères MRF.

Les cartes de 078 sont relues avec leur convention signée à partir de un pour
les faces. Les deux régions couvrent exactement toutes les cellules ; les seules
faces dupliquées sont celles de l'interface, en sens opposés. Les coordonnées
originales sont exactement conservées après réindexation. 079 conserve la
connectivité de domain1 et tous ses points. Aucune carte héritée n'est copiée.

La formule du déterminant des seules faces internes/couplées est reproduite
sans changer les seuils. Les deux membres officiels sont comparés aux octets de
l'archive OpenFOAM-v2406.tgz épinglée. Les valeurs reconstruite/native concordent
et les 13 568 cellules ont chacune une face radiale interne. Cette lecture ne
qualifie ni une physique d'écoulement ni une géométrie réelle autour des pales.
Les assertions de cycle orienté et de déterminant d'un cube complètent les
comparaisons exhaustives des maillages natifs ; aucun calcul n'est rejoué.

Tests turbo : 109 exécutés en 17,741 s, 108 réussis et un ignoré.
make check : 3 896 tests en 273,463 s, 172 ignorés ; mêmes deux échecs flottants
WE43/fan_stator et trois erreurs rtree/networkx hors turbo. Le contrôle local
complet reste non vert ; journaux conservés. Les lecteurs et leurs assertions,
la relecture des sources officielles et la syntaxe Python/JSON passent.

Les trois conteneurs sont terminés sans OOM avec code zéro. Le code zéro de la
séparation 078 ne vaut pas admission d'une région : celle du sous-domaine fixe
est obtenue séparément par checkMesh étendu dans 079. Aucun solveur d'écoulement,
aucun champ final p/T/U, aucun repos ni calcul forcé dans cette phase. Ne pas
transposer les résultats 064/076 à ce nouveau domaine isolé.
