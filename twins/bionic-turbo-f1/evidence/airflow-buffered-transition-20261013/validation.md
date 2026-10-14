# Validation

- Worktree propre sur la branche préparée, Docker inspecté avant les évaluations : aucun calcul turbo actif, aucun nouveau conteneur ni opération native. Cas finis non relancés, sources inchangées.
- Une seule nouvelle topologie prescrite avant calcul, sans balayage ni changement de critère. Le préparateur et le lecteur scalaire indépendant concordent : déterminants admis au précontrôle, mais 1 024 angles excessifs, donc refus global. Le dictionnaire candidat n'a pas été exécuté.
- Tous les payloads 063/091 et de l'archive PR227 sont vérifiés. Les points, faces partagées, types de cellules, centres volumiques et métriques sont reconstruits. Les frontières latérales exactes et la couverture orientée des fermetures sont vérifiées séparément, avec convexité des parents, inclusion et arêtes annulées. Volume calculé concordant avec l'intégrale polygonale ; pas d'admission géométrique complète implicite.
- Le lecteur détaillé du pire angle v1 échoue parce qu'il transmet des tableaux NumPy à des fonctions de listes cycliques. Source et traceback conservés. La v2 corrige seulement les conteneurs, vérifie le maximum et publie le tuple de centres/face/normale. Aucune simulation rejouée.
- Tests turbo : 109 exécutés en 15,360 s, 108 réussis, un ignoré.
- `PATH=work/bionic-tools/bin:$PATH make check` : 3 911 tests en 212,185 s, 172 ignorés. Deux échecs flottants WE43/fan_stator et trois erreurs rtree/networkx hors turbo, comme précédemment. Le nombre total inclut les autres travaux fusionnés sur main avant cette branche. Le contrôle local général n'est pas vert ; journal complet conservé.

Aucun checkMesh natif, repos, convergence, stabilité, indépendance maillage/temps, débit, puissance ou calibration nouveaux. Le repos084 reste incomplet ; les rejets091, PR226 et PR227 ne sont pas requalifiés.
