# Validation

Docker et reçus inspectés avant les lectures. Aucun nouveau cas natif, conteneur, candidat de couronne ou solveur. Tous les payloads du paquet PR229 sont vérifiés, sources immuables.

Identités planes : coefficients polynomiaux rationnels exacts pour les produits normaux/tangentiels des deux diagonales, rectangle et cisaillement affine. Douze références cartésiennes vérifiées par centres/volumes indépendants, erreur maximale de tangente5,42e−16 ; huit bornes vérifiées directement par centres triangulaires, erreur maximale1,43e−14 degré. Ce sont des tests analytiques, pas un balayage de paramètres de maillage.

Moments angulaires : tous les2 304 prismes axiaux existants relus ; centres à1,64e−17m et volumes à1,94e−13 relatif près.4 352 faces partagées,1 024 mêmes paires>70°,maximum77,724389811°. Lecteur v1 refusé sur comparaison acos/atan2 près de zéro, source/traceback conservés. V2 compare atan2 aux deux reconstructions et publie aussi tous les écarts au CSV ; critère d'admission70° inchangé.

Tests turbo :109 exécutés en15,657s,108 réussis et un ignoré. make check :3 911 tests en211,795s,172 ignorés ; mêmes deux échecs flottants WE43/fan_stator et trois erreurs rtree/networkx hors turbo. Journal conservé, contrôle général local non vert.

Aucune résolution de couronne choisie, aucune qualité native ou CFD qualifiée. Les refus PR227/229 et091, et le repos incomplet084 restent en vigueur.
