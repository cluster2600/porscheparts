# Validation et limites

Le primaire et le lecteur indépendant ont terminé avec le code 0, en 3523,875779 s et 4590,349953 s. Ce sont des durées d'application arithmétique, pas des benchmarks CFD. Le primaire chevauchait les tests.

Le lecteur reconstruit les incidences et centres natifs séparément : 13 696 faces internes, 4 864 parois non couplées et 384 MRF internes. Il vérifie les domaines, l'ordre, toutes les bornes finies et tous les signes revendiqués. Les 141 608 tétraèdres sans bornes restent indécis, sans inclusion numérique affirmée. Le résumé read_summary.py est une lecture structurelle de couverture, pas une troisième reconstruction géométrique.

Les 19 références de chaque évaluateur ont réussi AVANT application. La première version du lecteur de qualité utilisait une API vectorcross absente et a produit AttributeError pendant la préparation. Ses sources et son journal sont conservés. La version v2 corrige seulement cet appel en vector, avant toute application turbo. Aucune assertion scientifique refusée lors des deux parcours achevés.

Tests déjà exécutés : 108 réussis, un ignoré, en 15,470 s. make check : 3992 tests en 210,978 s, 178 ignorés, deux échecs et quatre erreurs. Les six labels hors turbo sont identiques à PR252 selon test-comparison.json ; le code global reste 2. Aucun test ni ancien parcours n'a été rejoué pour cette livraison.

Les constantes et branches sont des faits conditionnels de source sous WM_DP. La tolérance couvre le carré réel de SMALL et son arrondi au plus proche ; les autres arrondis d'exécution, la conversion writePrecision 16, la configuration et le binaire ne sont pas qualifiés. Aucun candidat, dictionnaire, maillage natif ou solveur nouveau n'a été lancé. Docker et le volume source sont préservés.
