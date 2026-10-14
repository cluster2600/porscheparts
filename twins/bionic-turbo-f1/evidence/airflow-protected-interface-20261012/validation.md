# Vérifications

108 tests turbo réussissent, un est ignoré. make check exécute 3 859 tests
en 217,131 s, avec 172 ignorés, les deux échecs flottants cooling_impeller_we43
et fan_stator et les trois erreurs rtree/networkx hors turbo déjà connues.
Les journaux complets sont conservés ; aucun contrôle n'est assoupli.

Le cas natif 056 termine sans OOM, mais checkMesh rejette explicitement
les déterminants et les cellules signalées concaves. Aucun solveur n'est
lancé. La lecture indépendante de cellMap vérifie les descendants de tous
les parents, celle du critère de concavité retrouve exactement les labels
natifs, et la version 2 du lecteur de paroi vérifie les chaînes d'arêtes.
Tous les payloads, reçus et métadonnées utilisés sont relus par empreinte.

La version 1 du lecteur de parois reste archivée mais n'est pas retenue
comme preuve de couverture. Les aires seules ne suffisaient pas ; la
version 2 ajoute le contrôle topologique orienté sans modifier le maillage.
Un premier contrôle trop large d'immuabilité incluait le fichier hérité
0/polyMesh/cellMap ; la carte native est justement réécrite par refineMesh.
Cette exception topologique est explicitée dans input-invariants.json,
sans exception pour les champs physiques ou équations.

Les 59 fichiers de l'archive sont relus localement ; cinq actifs GitHub
sont vérifiés par tailles et SHA-256 distants. Aucune deuxième lecture
intégrale distante n'est revendiquée. Sources et preuves antérieures
inchangées, conteneurs conservés, aucune suppression. Les espaces natifs
des journaux sont préservés pour leurs empreintes.
