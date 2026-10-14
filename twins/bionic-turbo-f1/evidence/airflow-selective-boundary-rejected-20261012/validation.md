# Validation

Les payloads 065 et les deux nouveaux cas sont relus selon leurs reçus SHA-256.
Les entrées conservées avant lancement correspondent à leurs manifestes. Le
lecteur indépendant vérifie la différence exacte limitée à points, les faces,
owner/neighbour, la cible STL et le déplacement analytique. Les points du raccord
restent identiques ; aucune projection n'a été exécutée. Les fichiers de maillage
restent byte-identiques à leurs entrées après checkMesh.

La reconstruction du déterminant retrouve tous les labels underdeterminedCells,
les minima et moyennes avec une tolérance numérique de comparaison 1e-9 relative,
1e-15 absolue ; le seuil natif 0,001 est inchangé. Un cube isotrope vérifie la
normalisation unitaire. La carte cellRegionAddressing valide de 065 sélectionne
les cellules parentes ; aucune carte héritée de 066/067 n'est utilisée.

Ces témoins ne valident aucun débit, aucune puissance ni jumeau calibré. Aucun
solveur ni champ p/T/U/rho/phi final. Les connexions du turbo réel sont inchangées.

Tests turbo : 109 exécutés en 15,616 s, 108 réussis et un ignoré.
make check : 3 896 tests en 217,802 s, 172 ignorés ; mêmes deux échecs flottants
WE43/fan_stator et trois erreurs rtree/networkx hors turbo. Le contrôle local
complet n'est pas vert. Journaux intégraux archivés ; aucun problème hors périmètre
modifié. Syntaxe Python et documents JSON relus ; assertions des lecteurs passées.
