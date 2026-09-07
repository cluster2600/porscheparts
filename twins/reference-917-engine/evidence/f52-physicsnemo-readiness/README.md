# Preuve PhysicsNeMo F52

Ce dossier ne publie aucune géométrie, aucun dataset et aucun poids de modèle.
Il prouve seulement que le contrat F52 sait distinguer :

- l’image PhysicsNeMo 2.2.1 et son smoke test d’import ;
- la future voie DoMINO pour les champs CFD/CHT ;
- la future voie GeoTransolver pour les champs thermomécaniques ;
- un dataset réellement libéré, un entraînement et une évaluation, encore absents.

L’audit F50 lié par SHA-256 compte 12/12 exécutions avec reçu solveur : 7/12
passent les portes numériques de débit, mais 0/12 passent une porte énergie et
aucun cas ne contient de CHT. Ces exécutions restent donc à 0 échantillon
admissible pour PhysicsNeMo.

Le statut `PASS_FAIL_CLOSED` signifie que les refus sont cohérents. Il ne valide
ni la physique, ni l’impression, ni le démarrage du moteur.
