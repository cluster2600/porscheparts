# Validation

Tous les cas sont terminés et conservés. 068 passe la qualité native mais
échoue à la conservation de frontière et à la tangence requise. 069 échoue
à la conservation et à la qualité native. 070 passe la conservation de ce
maillage déjà conforme à sa cible et le contrôle natif étendu. Aucun solveur
ni champ p/T/U/rho/phi d'écoulement n'est créé.

Les lecteurs et préparateurs comprennent des assertions de provenance,
coordonnées du STL, topologie, labels, immutabilité et comparaison des entrées.
Le critère de conservation de 1e−16 m reprend la comparaison de points du
raccord précédent ; 070 obtient zéro écart, sans changement de critère.
Les seuils de qualité restent ceux des sources précédentes.

Le premier auditeur de patches refusait la suppression du patch defaultFaces
de zéro face. La v2 vérifie explicitement cette seule suppression et l'identité
des métadonnées du patch walls ; aucune géométrie n'est corrigée par ce lecteur.
Le refus initial est enregistré séparément, sans réexécution du maillage.

Les journaux des tests et de make check sont dans l'archive. Utiliser Python
3.11 du projet ; pour make, PATH=work/bionic-tools/bin:$PATH. Les limites du
contrôle local sont décrites dans README.md et ne sont pas des gains physiques.

Tests turbo : 109 exécutés en 15,551 s, 108 réussis, un ignoré.
make check : 3 896 tests en 218,940 s, 172 ignorés ; mêmes deux comparaisons
flottantes WE43/fan_stator en échec et trois erreurs rtree/networkx hors turbo.
Le contrôle global local reste non vert ; ces problèmes ne sont pas modifiés.

Les commandes natives réécrivent des entrées polyMesh. recover_initial.py
matérialise donc séparément chaque fichier préparé : octets inchangés du cas,
octets du parent 063 haché, ou déclaration pointZones reconstruite depuis ses
labels. Chaque fichier doit avoir exactement le SHA-256 du manifeste préparé
avant lancement. Toutes les entrées sont ainsi conservées séparément des sorties,
sans relancer une opération native. La provenance de chaque récupération est
explicitée dans initial-readback.json ; il ne s'agit pas d'un instantané pris
avant lancement. La version 2 du paquet ajoute ces copies exactes, sans changer
les résultats ; le premier paquet et ses reçus restent conservés localement.
