# Périmètre des cartes de parenté

Les fichiers *RegionAddressing de 065 sont les cartes natives valides utilisées
par compare_topology.py. Les copies présentes dans les dossiers polyMesh de
066/067 ne sont PAS des cartes globales du maillage réassemblé : mergeMeshes
laisse ces fichiers auxiliaires hérités de la région maître. En 067, leurs
longueurs restent 20 736 points, 61 440 faces, 20 352 cellules et deux patches,
alors que le maillage final contient 27 648 points et 27 136 cellules.

Ces copies héritées sont conservées dans les payloads pour la provenance,
sans servir à la preuve de bijection finale ni au contrôle natif. Ne pas les
utiliser pour remapper des champs ou cellules après réunion. La comparaison
finale établit une nouvelle bijection indépendante par coordonnées et cycles
orientés, puis vérifie chaque owner/neighbour et la zone tournante.

Une éventuelle préparation d'écoulement doit utiliser les cartes explicitement
qualifiées pour le maillage final ; elle ne doit pas importer aveuglément les
fichiers auxiliaires hérités. Aucun solveur ni remappage de champs physiques
n'a été lancé sur 066/067. Les sources et archives existantes ne sont pas modifiées.
