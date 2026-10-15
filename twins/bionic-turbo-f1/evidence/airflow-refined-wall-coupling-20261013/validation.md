# Validation de 087/088

Deux exécutions natives, code zéro sans OOM, Mesh OK ; aucun solveur et aucun cas antérieur rejoué. Les deux lecteurs relisent tous les payloads et les copies préparées avant lancement. Les cartes natives 078 sont revalidées dans leur périmètre ; la correspondance finale est reconstruite indépendamment à partir de 078 tournant et 086 fixe.

Les preuves couvrent chaque point, cellule et face orientée, owner/neighbour, rotorZone, fermeture par cellule, volumes positifs, quads du raccord, métadonnées initiales et retrait des seuls patches vides. Les maillages intermédiaires fusionné et raccordé sont conservés. Aucune carte héritée n’est présumée globale finale.

- Tests turbo : 109 exécutés en 15,840 s ; 108 réussites et un ignoré.
- `PATH="$PWD/work/bionic-tools/bin:$PATH" make check` : 3 896 tests en 221,181 s, 172 ignorés, deux échecs et trois erreurs hors turbo. Le contrôle local complet n’est pas vert.
- Problèmes connus : comparaisons flottantes des preuves WE43/fan_stator ; dépendances rtree/networkx des tests thermiques et contre-essai PicoGK. Journaux conservés, aucune correction opportuniste.

Le source officiel createPatch.C est référencé avec SHA dans preparation-readback.json. L’archive conserve sources, inputs préalables, résultats, intermédiaires, journaux et reçus. Tous ses payloads sont relus localement ; les cinq actifs GitHub sont vérifiés par tailles et digests avant intégration du reçu distant, sans second téléchargement intégral revendiqué.

Ce contrôle géométrique ne qualifie ni repos, convergence, stabilité, indépendance au maillage ou au temps, couches physiques, débit, puissance ou calibration. 084 reste incomplet au budget, sans champs finaux. Aucune modification des pièces, jeux ou connexions réels.
