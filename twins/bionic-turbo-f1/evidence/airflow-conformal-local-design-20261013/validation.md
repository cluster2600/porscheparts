# Validation

- Docker inspecté avant évaluation : aucun conteneur actif. Aucun nouveau conteneur créé, aucun cas natif relancé.
- Tous les payloads du reçu 091 sont vérifiés avant le calcul. Aucun maillage source modifié.
- Les deux propositions sont calculées séparément avec un sommet fixé au centre volumique source. Toutes les bases et coordonnées initiales sont conservées, chaque triangle interne apparié en sens opposé, chaque chaîne d'arêtes fermée.
- Le lecteur scalaire indépendant relit les parents et voisins complets, vérifie chaque donnée candidate, puis reproduit déterminants, volumes, centres, scores de plans et angles. Deux cas analytiques (cube et pyramide) vérifient ses formules. Les deux candidats restent refusés, sans ajustement de seuil ou de sommet.
- La concordance des sommes algébriques de volumes ne constitue pas une preuve complète d'absence d'intersections ; aucun succès d'admission n'est revendiqué.
- 109 tests turbo en 15,508 s : 108 réussis, un ignoré.
- `PATH=work/bionic-tools/bin:$PATH make check` : 3 896 tests en 212,141 s, 172 ignorés. Deux échecs flottants WE43/fan_stator et trois erreurs rtree/networkx hors turbo, identiques aux phases parentes. Journal complet conservé ; ce contrôle local général n'est pas vert.

Aucun nouveau checkMesh, repos, solveur ou débit. Les rejets natifs 091 et le repos incomplet 084 restent en vigueur.
