# Faces nulles et égalité de la surface encodée

`exact_zero_face_coverage.py` ne nettoie pas un maillage. Il vérifie si une
face d'aire **exactement nulle** n'ajoute aucun point à la surface XYZ déjà
couverte par les triangles non nuls du **même groupe**.

Ses sommets IEEE sont interprétés en rationnels. Le segment entier entre
les extrêmes, ou le point si tous les sommets coïncident, est intersecté avec
les triangles candidats. La réunion des intervalles fermés doit couvrir
entièrement `[0,1]`. Des extrémités couvertes et un milieu vide sont refusés ;
un autre triangle nul ne peut servir de matière couvrante. Les boîtes servent
seulement de présélection, sans tolérance.

Le [témoin réel droit012](zero-face-coverage-result-001.json) prouve la
couverture des 44 faces nulles repérées : 18 dans les grilles et 26 dans les
peaux. La preuve compte 290 intersections rationnelles et garde les identités
des 25 groupes concernés. Six tests ciblés passent.

Cela permettrait de retirer **ces seules faces couvertes** sans changer
l'ensemble des points de la surface XYZ encodée. Aucun retrait n'a été effectué
par ce témoin. La preuve ne conserve pas à elle seule l'aire intrinsèque d'une
carte 2D déjà effondrée lors du remappage ; elle n'admet ni topologie, ni
contacts, ni trajectoires. Ces contrôles restent obligatoires ensuite.

```sh
AM_PYTHON -B -m unittest discover -s tests -p test_carrier_zero_face_coverage.py -v
```
