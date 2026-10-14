# Validation locale

- 104 tests turbo exécutés : 103 réussis, un ignoré (15,802 s).
- `make check` : 3 817 tests exécutés en 215,093 s, 170 ignorés ; les deux
  comparaisons flottantes et trois erreurs de dépendances rtree/networkx
  hors turbo déjà connues restent présentes. Les journaux complets sont conservés.
- 040 et 041 terminent nativement avec code zéro, sans OOM, mais échouent
  au contrôle de maillage. Aucun solveur n'est lancé.
- Tous les payloads sont relus localement. Les cinq actifs distants sont
  vérifiés par taille et SHA-256 GitHub ; pas de second téléchargement intégral.
- Aucun ancien fichier source ou preuve épinglé n'est modifié.

Les nouveaux modules sont des préparateurs et auditeurs de témoins ; ils ne
modifient pas les équations, tolérances, configurations de CI ou dépendances.
Les seuls appels ajoutés sont les scripts de reproduction et tests conservés.
La conservation géométrique ne qualifie ni maillage ni performance physique.
