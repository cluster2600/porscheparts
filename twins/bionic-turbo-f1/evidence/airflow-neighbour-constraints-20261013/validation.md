# Validation

Lecture seule du candidat PR229 après vérification de tous ses payloads. Docker inspecté avant les calculs ; aucun conteneur actif. Aucun nouveau candidat, cas natif ou solveur.

Les 6 144 centres analytiques sont comparés aux moments scalaires par pyramides signées, puis les 6 144 cellules et 13 696 faces internes sont vérifiées par un lecteur distinct à tétraèdres orientés. Les mêmes 1 024 faces dépassent 70°. Toutes les fermetures et les contributions internes sont identifiées, sans voisin fictif ni changement de seuil. Aucun natif rejoué.

Tests turbo : 109 exécutés en 15,489 s, 108 réussis et un ignoré. make check : 3 911 tests en 213,646 s, 172 ignorés ; deux échecs flottants connus WE43/fan_stator et trois erreurs de dépendances rtree/networkx hors turbo. Le contrôle général local reste non vert ; journal conservé. Aucune correction de ces problèmes hors périmètre.

Les avertissements NumPy du premier lecteur sont conservés. Aucun échec d'assertion dans cette phase. Sources précédentes immuables, nouveau lecteur autonome ; aucun paramètre de géométrie ou résolution choisi. Aucune admission native, convergence, performance CFD ou calibration physique.
