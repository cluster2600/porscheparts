# Validation

Les tests du dépôt sont terminés : 109 tests turbo exécutés, 108 réussis, un ignoré, 15.378 s. make check : 3976 tests, 214.886 s, 178 ignorés, deux échecs et quatre erreurs hors turbo. test-comparison.json vérifie les mêmes six labels que PR248 : WE43/fan_stator et rtree/networkx, y compris carrier correction. Ce résultat local n'est pas une CI verte.

Les dix références de fonctions par programme passent avant l'application primaire. La mention initiale de cubes était incorrecte pour six entrées analytiques : voir reference-clarification.md. Six cubes cohérents supplémentaires par programme passent après le démarrage primaire et avant le lecteur complet ; ne pas antidater cette validation. Aucun code figé n'a été changé après lancement.

verify_sources.py relit six membres de l'archive officielle et leurs empreintes, normalised et son seuil, les formules et le seuil de skewness par défaut. Il s'agit de provenance/structure, pas d'un contrôle de binaire ou de configuration effective. L'incident initial d'interpréteur système est consigné dans preparation-attempts.json ; aucune installation.

Le parcours primaire est terminé en 1164.017 s : 1400456 enregistrements, 9528 faces positives et 9032 indécises sur l'enveloppe ; les 1381896 contrôles locaux sont tous positifs. Le lecteur indépendant termine avec code 0 en 1124.974 s. Il confirme 6985400 intervalles numériques et tous les signes positifs ; 3376 lignes sans borne finie sur l’enveloppe restent des indécisions conservées, sans affirmation d’inclusion numérique. Le superviseur a vérifié le reçu final et les sources figées puis créé reader-launch.json par ouverture exclusive. Aucun second lecteur n'est lancé. Le contrôle structurel read_summary.py termine : chaque boîte est couverte pour les 18560 faces. Maximum supérieur positif 3.984917228923439 environ, enveloppe rang 523. Aucune assertion scientifique refusée. Les durées chevauchent les tests pour le primaire et ne sont pas des benchmarks CFD.

Aucune admission native, aucun débit ou puissance, aucune calibration validés. Aucun solveur, dictionnaire ou nouveau cas natif exécuté. Aucun seuil modifié. Les conteneurs étrangers sont préservés.
