# Validation locale

Identités : quatre annulations de coefficients exactes, deux références à poids signés, six cellules analytiques et trois quadrilatères gauchis aux échelles prescrites. Source officiel v2406 et noyaux hachés. Les cinq actifs préalables sont vérifiés par tailles/digests avant le réencadrement.

Réencadrement : 447 boîtes sources exactes, aucune nouvelle subdivision, 894 angles. Lecteur Fraction indépendant à 192 bits : toutes les bornes contenues dans les bornes principales, mêmes classifications, 1 788 encadrements positifs de volumes et neuf références analytiques. Quatre déterminants hérités exactement du certificat PR235, non recalculés ici. Toutes les dépendances sont relues avant calcul. Couverture combinée sans trou, largeurs rationnelles exactes.

Le lecteur v1 est conservé avec une empreinte de noyau erronée dans sa métadonnée ; v2 corrige uniquement cette provenance et le nom de sortie. Source et résultats comparés par `verify_provenance.py`, résultats scientifiques identiques. Aucune assertion scientifique refusée. Aucun natif, solveur ou ratio ponctuel nouveau.

Tests turbo : **108 réussis, un ignoré**, 109 exécutés en 15,432 s, code zéro. `make check` : **3 911 tests en 211,914 s**, 172 ignorés ; les mêmes deux échecs flottants WE43/fan_stator et trois erreurs rtree/networkx hors turbo, code make 2. Les journaux complets et empreintes sont archivés. La validation locale globale n'est pas déclarée verte ; CI PR et main seront vérifiées séparément sur leurs commits exacts.

Commandes : `work/bionic-tools/bin/python -m unittest discover -s tests -p 'test_bionic_turbo*.py'`, puis `PATH="$PWD/work/bionic-tools/bin:$PATH" make check`. Pas de remplacement PYTHON.

Six contraintes satisfaites ne valent pas admission : tous les autres critères et obligations géométriques restent requis, puis contrôle natif. Aucune qualification d'écoulement, de convergence, d'indépendance maillage/temps, de débit/puissance ou de calibration.
