# Validation 080/081

Les deux cas natifs sont terminés, code zéro sans OOM, sans solveur d’écoulement. Les entrées ont été sauvegardées avant exécution. Le lecteur v2 vérifie tous les payloads, les sélections issues des cartes 078, la topologie, les points gelés, les volumes et les métadonnées. Les deux maillages passent checkMesh sans seuil modifié.

Le lecteur indépendant de distance v2 contrôle les distances ponctuelles par projection barycentrique/segments, cas analytiques à quatre échelles et recherches exhaustives. La preuve paired-surface-bound borne séparément les surfaces explicitement triangulées et remplace l’argument antérieur de quadrilatères parents. Les refus des premiers lecteurs et le témoin de dépendance à l’échelle de trimesh sont conservés. La source installée de la fonction et sa licence MIT sont archivées. L’avertissement natif sur le déplacement demandé reste dans le journal ; les coordonnées finales gelées sont vérifiées indépendamment.

- Tests turbo : 109 exécutés en 22,391 s, 108 réussis et un ignoré.
- `PATH=work/bionic-tools/bin:$PATH make check` : 3 896 tests en 302,934 s, 172 ignorés ; deux échecs flottants WE43/fan_stator et trois erreurs rtree/networkx hors turbo déjà connus. Le contrôle global local n’est donc pas vert.
- Syntaxe AST des scripts et lecture JSON des rapports : réussies.

Aucune répétition native, aucun calcul de repos ou de performance. Les points mobiles sont proches de la cible, mais la surface et le volume ne sont pas identiques. La borne symétrique de 22,433753 µm concerne les deux triangulations appariées, pas une distance de Hausdorff mesurée ni une tolérance physique. Protection du raffinement, couches et vrai turbo restent non qualifiés.
