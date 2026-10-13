# Validation

Le primaire et le lecteur indépendant terminent sans assertion refusée : 18 560 faces, dont 13 696 rapports internes et 4 864 initialisations de parois. Toutes les bornes concordent exactement. Les volumes sont hérités de PR241 ; cette phase vérifie leurs incidences et la nouvelle application arithmétique, sans reconstruire leur géométrie. Six références analytiques par programme précèdent l’application. Le contrôle complémentaire des sources établit que wallPolyPatch hérite coupled() = false.

Durées : primaire 4,864 s, lecteur 5,545 s. Ce ne sont pas des benchmarks CFD. Aucun calcul natif ou solveur, aucune installation, aucun conteneur créé.

Tests turbo : 109 exécutés, 108 réussis et un ignoré, 15,456 s. make check : 3 976 tests, 178 ignorés, deux échecs et quatre erreurs, 216,131 s. Les cinq diagnostics antérieurs hors turbo restent présents. Une erreur supplémentaire concerne test_open_or_inverted_mesh_is_rejected : networkx absent dans l’environnement local. Les deux fichiers concernés sont identiques à la base Git ; leurs empreintes et tous les labels sont conservés dans test-comparison.json. Aucun de ces fichiers n’est modifié par cette phase. Les journaux complets sont archivés. La CI sur le head exact reste nécessaire avant fusion.

Le certificat concerne les expressions mathématiques sous hypothèse WM_DP et le domaine fermé prescrit. Il ne borne ni les arrondis d’exécution ni la conversion writePrecision 16. L’admission native, les poids, la skewness, la décomposition native, le repos, la convergence, l’indépendance et la comparaison débit/puissance restent ouverts.
