# Validation

Les 108 tests turbo réussissent, avec un test ignoré, en 15,409 s. `make check` exécute 3911 tests en 210,663 s, avec 172 ignorés, deux échecs et trois erreurs : ce journal n'est pas vert. Les cinq noms de tests en échec/erreur sont comparés exactement à ceux de PR238, sans modification hors périmètre : flottants WE43/fan_stator et dépendances rtree/networkx. `validation.json` contient les noms et les empreintes des journaux.

La validation scientifique est distincte des tests du dépôt. `verify_angles.py` effectue la reconstruction indépendante complète des centres et angles sur les boîtes prescrites, avec les kernels et moments épinglés. `read_certificate.py` relit ensuite chaque ligne enregistrée, l'ordre, les signes et les comptes ; il ne prétend pas effectuer une autre reconstruction géométrique.

Les preuves de représentation, noyaux et références analytiques PR238/236 sont réutilisés à leurs empreintes ; ils ne sont pas présentés comme des nouveaux tests de cette phase. Aucun ancien parcours, aucun cas natif et aucun solveur ne sont relancés. Les résultats portent sur des expressions mathématiques à arrondi extérieur, pas sur les arrondis ou branches de dégénérescence d'OpenFOAM, ni sur un écoulement physique.
