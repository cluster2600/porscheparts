# Validation

Lecture des preuves PR232 et inspection Docker avant calcul. Les manifestes PR229/231/232 et tous leurs payloads sont vérifiés avant l'encadrement puis par le lecteur indépendant. Aucun natif ni solveur relancé, aucun conteneur créé ; le conteneur carrier-corrections-20261013 et le volume bionic-native-source-20261012 sont préservés. execution-scope.json est explicitement un inventaire après calcul, pas une capture initiale reconstituée.

Le premier noyau utilise 160 bits fractionnaires et arithmétique entière dirigée. 106 contrôles exacts d'opérations élémentaires passent. Le lecteur indépendant Fraction à 192 bits vérifie six références analytiques, la sélection des six contraintes, toutes les 1 524 exclusions et la couverture dyadique sans trou des 2 351 feuilles. Aucune assertion refusée dans cette phase. Les sources, le certificat complet et les encadrements sont conservés.

Aucune évaluation ponctuelle d'un nouveau ratio, aucun candidat ou dictionnaire. La mesure exclue 3 269/4 096 concerne uniquement u=q_m. Les 827 feuilles indécises restent non qualifiées ; aucun intervalle ne passe même toutes les six contraintes sélectionnées. La précision arithmétique borne l'erreur du calculateur mathématique, elle ne change aucun critère natif. Les autres contraintes et la validité géométrique complète ne sont pas certifiées.

Tests turbo : 109 exécutés en 15,670 s, 108 réussis et un ignoré. make check : 3 911 tests en 212,149 s, 172 ignorés ; mêmes deux échecs flottants WE43/fan_stator et trois erreurs rtree/networkx hors turbo. Contrôle général local non vert ; journaux complets conservés dans la livraison. Aucune correction opportuniste des tests hors périmètre.

Les centres sont calculés par moments. Aucun seuil assoupli, couplage fictif ou rotation appliquée aux cellules fixes. Aucun débit, puissance, convergence, stabilité, indépendance maillage/temps ou calibration physique qualifiés. Le repos 084 reste incomplet.
