# Validation

Le parcours principal se termine sans assertion refusée : 159 boîtes sources exactes, ordre de 9470 contraintes prescrit avant lancement, 1 448 960 évaluations avec arrêt au premier refus certain. Toutes les boîtes sans refus atteignent la fin de l'ordre. Aucune subdivision ni ratio ponctuel nouveau.

Le lecteur indépendant Fraction 192 bits vérifie l'ordre, les cycles orientés opposés, la couverture et les six témoins d'exclusion sur les boîtes entières. Les bornes de centres, volumes, D et résidus sont incluses dans celles du calcul principal. Les autres signes positifs/indécis ne sont pas tous recalculés : leurs comptes restent descriptifs. Six manifestes de dépendances sont ancrés au commit PR236 exact et tous leurs payloads sont relus. Identités et références analytiques sont réutilisées à leurs empreintes, pas redémontrées.

Tests turbo : 108 réussis, un ignoré, 109 tests en 15,384 s, code zéro. `make check` : 3911 tests en 210,369 s, 172 ignorés ; mêmes deux échecs flottants WE43/fan_stator et trois erreurs rtree/networkx hors turbo. Code make 2, la suite locale globale n'est pas déclarée verte. Journaux et empreintes conservés. Commandes : `work/bionic-tools/bin/python -m unittest discover -s tests -p 'test_bionic_turbo*.py'` et `PATH="$PWD/work/bionic-tools/bin:$PATH" make check`.

Aucun natif ni solveur. Aucun calcul d'écoulement, de convergence, d'indépendance maillage/temps, de performance ou de calibration qualifié. Les 153 boîtes non exclues restent non admises. CI PR et main doivent être contrôlées séparément sur les commits exacts avant clôture de livraison.
