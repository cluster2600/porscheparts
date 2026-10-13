# Validation

Deux protocoles préalables, aucun nouveau ratio ponctuel ni subdivision. Les lecteurs indépendants confirment tous les encadrements enregistrés : déterminants par polynômes creux/éventail/permutations/Casteljau à 192 bits ; plans et volumes par gabarits réduits et moments indépendants PR236, avec représentation entière équivalente au noyau Fraction 192 bits. Les reçus scientifiques et le résumé distinguent conditions nécessaires et admission.

Tous les payloads de sept manifestes parents sont relus et ancrés au commit PR237 exact. Les sources et preuves antérieures restent inchangées. Deux lancements prématurés avec reçu absent, puis l'interruption du lecteur Fraction des plans, sont conservés ; aucune de ces exécutions n'est présentée comme une validation achevée. Les contrôles d'équivalence de représentation précèdent l'application v2 : 624 comparaisons arithmétiques et neuf références géométriques, bornes exactement identiques.

Tests turbo : 108 réussis, un ignoré, 109 tests en 15,536 s, code zéro. `make check` : 3911 tests en 209,874 s, 172 ignorés ; mêmes deux échecs flottants WE43/fan_stator et trois erreurs rtree/networkx hors turbo, liste comparée exactement au journal précédent. Code make 2 : la suite locale globale n'est pas déclarée verte. Les lecteurs scientifiques sont validés par leurs exécutions dédiées, distinctes des tests du dépôt. Commandes : `work/bionic-tools/bin/python -m unittest discover -s tests -p 'test_bionic_turbo*.py'` puis `PATH="$PWD/work/bionic-tools/bin:$PATH" make check`.

Aucun natif, conteneur ou solveur créé. Aucun écoulement, convergence, stabilité, indépendance maillage/temps, puissance ou calibration qualifié. CI PR et main doivent être vérifiées séparément sur les commits exacts avant clôture de livraison.

Relecture terminée : 42851 bornes de déterminants, 7142400 paires de plans et 238848 volumes enregistrés, tous contrôlés. Les 10496 paires indécises sur l’enveloppe des 1536 hex restent enregistrées ; les contrôles locaux correspondants passent. La relecture v2 des plans dure 633,125 s, sans prétention de benchmark. Aucun ratio ou candidat admis.
