# Validation

- Docker et reçus inspectés avant les évaluations ; aucun calcul turbo actif et aucun nouveau conteneur créé. Aucun maillage natif modifié ni relancé.
- Le préparateur vérifie tous les payloads sources 063/091, puis construit une seule topologie spécifiée dans preflight.md. Les seuils restent inchangés ; le précontrôle calculé refuse 512 déterminants.
- Le lecteur indépendant scalaire vérifie à nouveau les sources et reconstruit points, faces des prismes, cycles opposés, chaînes d'arêtes, volumes, centres, critères de plans, déterminants et angles. Les 384 quads MRF correspondent exactement aux intervalles sources ; les 768 quads entre étapes sont partagés. Le volume concorde avec l'intégrale analytique polygonale. Cette vérification ne constitue pas une admission native ou une preuve complète d'absence d'intersections.
- Les 512 refus se répartissent en deux groupes de 256 cellules de transition axiale aux fermetures, chacune avec trois faces internes contributrices. Aucune cause unique ou correction implicite n'est revendiquée.
- Tests turbo : 109 exécutés en 15,415 s, 108 réussis et un ignoré.
- `PATH=work/bionic-tools/bin:$PATH make check` : 3 896 tests en 213,957 s, 172 ignorés. Deux échecs flottants WE43/fan_stator et trois erreurs rtree/networkx hors turbo, déjà présents dans les phases parentes. Ce contrôle local général n'est pas vert. Les journaux complets sont archivés.

Aucun blockMesh/checkMesh natif, repos, solveur, débit ou puissance. Les résultats favorables de quelques métriques ne remplacent pas le refus global au précontrôle. Le repos 084 reste incomplet.
