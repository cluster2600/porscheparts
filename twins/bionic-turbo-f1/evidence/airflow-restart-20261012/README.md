# Preuves de relance CFD — 12 octobre 2026

Les essais 008 sont rejetés pour températures absolues négatives. Leurs anciens reçus `running` sont périmés : aucun conteneur correspondant n'est présent. Les historiques natifs sont préservés ; le motif exact d'arrêt des conteneurs reste inconnu.

L'essai 009 s'est arrêté avec une erreur native explicite sur `rhoFinal`. Le reçu terminal et l'état Docker confirment cet échec. L'essai 010 corrige cette entrée et tourne avec `rhoPimpleFoam`, MRF fixe, pas adaptatif limité et arrêt automatique sur historique non physique ou après deux heures. Les fichiers suffixés `.snapshot` constituent uniquement un instantané horodaté du démarrage, pas une preuve de calcul terminé.

Les paramètres physiques et maillages restent identiques aux deux variantes 008. Aucune convergence, comparaison débit/puissance ou validation physique n'est acquise. Le classement de performances demeure interdit pour ce pilote à frontières en escalier.

L'[archive GitHub](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-airflow-restart-2026-10-12) contient les fichiers retenus de 008, toutes les sorties de 009 et les entrées immuables de 010. Les sorties 010 évoluent encore localement et sont exclues de l'archive initiale. Consulter `README-RESTORE.md`, `file-manifest.json` et `archive-receipt.json` pour la restauration et les empreintes. Les 106 copies initiales sont listées dans `snapshot-index.json`.

Vérifications locales : 52 tests turbo découverts, 51 réussis, un test natif ignoré car `BIONIC_DOTNET` et l'assembly compilé n'étaient pas configurés pour cette exécution. `make check` a exécuté 3 696 tests (163 ignorés), avec deux erreurs de dépendances facultatives (`rtree`, `networkx`) et deux comparaisons flottantes exactes en échec dans les études WE43/stator. Ces quatre échecs existaient avant cette relance ; les tests de l'étude des supports moteur passent après intégration du correctif `Runner.cs` déjà présent dans `main`.

Le reçu `launch-transient.json` décrit un lancement, pas l'état courant. L'état courant se lit via `docker inspect` et, après arrêt normal du superviseur, `native-exit.json`.
