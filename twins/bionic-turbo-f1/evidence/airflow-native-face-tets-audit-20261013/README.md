# Encadrement mathématique natif de checkFaceTets

Cette phase applique les expressions de checkFaceTets OpenFOAM v2406 sur les 153 boîtes fermées héritées, avec les centres natifs PR236. Elle conserve les éventails signés autour de Cf, les bases communes owner/neighbour, les branches du rayon circonscrit, GREAT et ROOTVSMALL. La méthode et les programmes ont été figés avant application dans before-application.json.

Le primaire conserve 1 455 536 lignes de faces et 14 892 704 enregistrements tétraédriques, y compris les bases essayées. L'enveloppe donne 9 168 faces positives et 9 392 indécises, sans refus certain. Les 1 436 976 reprises locales sont toutes positives. Les indécisions initiales restent dans la matrice ; aucun domaine ni aucune extrémité n'est supprimé.

Le lecteur indépendant à 192 bits confirme tous les signes revendiqués et l'inclusion des 59 004 384 intervalles finis dans les bornes primaires à 160 bits. Les 141 608 enregistrements tétraédriques nuls restent sans prétention d'inclusion numérique ; aucune ligne de face entière n'est nulle. Les comptes ne sont ni un nombre de tétraèdres uniques du maillage ni le compteur natif nErrorTets.

La base certifiée est un témoin valable sur le domaine fermé entier. Ce résultat ne revendique pas le premier choix du futur binaire point par point. Les preuves tétraédriques PR241 ne remplacent pas cette décomposition native.

Lire method.md, preflight.md, source-audit.json, quality-reference-readback-v2.json, preparation-attempts.json, readback.json, independent-readback.json, summary.json et validation.md. La matrice complète et les membres natifs sont destinés à l'archive ; les fichiers légers sont conservés dans Git.

Aucune admission native, CFD, débit, puissance ou calibration. Les deux indécisions de déterminants aux fermetures restent présentes. Voir next-scope.md.
