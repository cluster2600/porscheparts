# Vérification et limites

Les sources et tous les payloads des deux cas parents sont vérifiés avant calcul de lecture. Aucun Docker run, checkMesh ou solveur n'est exécuté dans cette phase. Les conteneurs et archives précédents restent conservés.

`reproduce_planes.py` reproduit l'exploration précédente ; son rapport conserve le libellé exploratoire de sa source. `audit_transitions.py` reconstruit ensuite les centres par volumes signés de pyramides, les angles de faces internes et les paires du test de plans pour trois états archivés. Les sets de labels natifs concordent exactement ; maxima angulaires à moins de 1e-9 degré. Les CSV entre premier et dernier instantané sont byte-identiques, leurs empreintes figurent dans `diagnostic-pair.json`. `read_stage_order.py` conserve les lignes et l'empreinte du journal montrant quand les instantanés ont été écrits. Les répertoires numériques ne sont pas des temps CFD.

Tests turbo : 109 exécutés, 108 réussis et un ignoré en 15,464 s. `PATH=work/bionic-tools/bin:$PATH make check` : 3 896 tests en 211,139 s, 172 ignorés ; deux échecs flottants WE43/fan_stator et trois erreurs de dépendances rtree/networkx hors turbo déjà connus. Le contrôle global local reste non vert.

L'archive de cette phase contient les lecteurs, références, résultats, CSV et journaux ; les gros maillages natifs ne sont pas dupliqués, leurs archives immuables figurent dans `dependencies.json`. Tous les payloads du paquet sont relus localement. Les cinq actifs GitHub sont vérifiés par taille et digest ; pas de second téléchargement distant intégral revendiqué.

La distribution des scores autour de +1e-6 est uniquement descriptive. Aucun seuil d'admission n'est changé : le contrôle natif continue de rejeter les scores >−1e-6. La reconstruction des labels n'est ni une certification de concavité stricte ni une attribution de cause unique. Aucun maillage corrigé, repos, convergence, performance ou calibration physique nouveau.
