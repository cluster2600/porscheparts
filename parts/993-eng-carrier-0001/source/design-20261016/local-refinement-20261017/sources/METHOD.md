# Campagne adaptative locale version002 — non armée

Cette version part de la référence mesh-7 originale, sans reprendre ni promouvoir le maillage de la campagne001 refusée. Elle garde les mêmes deux boîtes, les deux cibles h/2, les six groupes, les anciennes lignes NODE/coordonnées NPZ, les gardes CAD/STEP, Gmsh minDetJac/volume non régressif et le mesureur8e38. Aucune FEA, aucun déplacement d’ancien nœud, aucun élargissement de boîte ni changement de seuil.

La seule évolution algorithmique est une boucle sur le **maillage courant** : `compact_t10` → `mark_t4` → vrai `MeshTet1.refined` tracé → `lift_t10`. Tant que `mark_t4` trouve des arêtes trop longues dans son domaine de mesure, une nouvelle passe est proposée. La campagne termine quand ce marquage est vide, ou refuse sur les mêmes facettes protégées, le plafond500000 nœuds/éléments, une absence de progression, une erreur ou les ressources. Ce n’est pas une relance automatique de budget.

Chaque passe contrôle l’utilisation et les IDs/XYZ de TOUS les nœuds d’entrée, les facettes extérieures et leur ascendance, puis refuse toute subdivision de facette dont les trois anciens coins appartiennent à un même groupe de charge/appui. Les groupes restent les listes originales. Les parents/fermetures/facettes enregistrés sont **relatifs au maillage de la passe immédiatement précédente** ; aucun raccourci vers l’original n’est prétendu. Les preuves successives sont liées par leur SHA.

`passes.jsonl` reçoit `pass_start` puis `pass_finish`, flush/fsync. Chaque `pass-NNNN.json` conserve ledger d’arêtes, parents des éléments, fermeture, parents des facettes, différences midpoint natif/ancien et contrôles de facettes protégées. La seule autorité de passe terminée est sa ligne `pass_finish` complète. Un artefact de preuve partiel reste répertorié comme artefact, sans être déclaré terminé. Même en refus, les journaux et preuves déjà écrits restent en place ; aucun mécanisme de reprise n’est introduit.

Après convergence du marquage, les dernières arrays sont écrites une seule fois en INP/NPZ, en préservant séparément les blocs originaux. Les quatre fichiers parents CAD sont copiés byte-exacts et liés au catalogue. Gmsh4.15.2 reçoit un modèle discret de ces arrays relues, avec la permutation native vérifiée3707 et son inverse ; aucun import CAD/remeshing. Les contrôles finaux de volume/Jacobien/perçages/oldXYZ et les mesures h/2 restent obligatoires : mark vide ne remplace pas le mesureur indépendant.

Bornes inchangées : superviseur1200s, alarme1150s, CPU1100/1101s, un thread, zéro worker, nice10. Plafonds500000 nœuds/éléments ; RSS mesurée, aucun hard cap universel de mémoire promis. Aucun allongement ni retry de budget. `pending-plan.json` reste `launch_ready=false` et GO null ; aucun launch-plan n’est armé ici. Les anciens gros inputs gardent leurs SHA déjà attestés ; cette préparation ne les relit pas. Root fera le prévol complet avant son GO.

La campagne001 réelle reste immuable : RC1, tous les contrôles autres que h/2 passés ; closure3d6e75 lie source915559, assessmenta7a395 et supervision26e1fe. Cette histoire motive la nouvelle boucle, sans modifier le résultat refusé.

## Vérification de préparation

```sh
python3 -I -B work/carrier-process-20261017/bounded-webs-discrete-real-preparation-002/selfcheck.py
```

Les14 contrôles stdlib précédents sont conservés, plus trois doubles d’ordonnancement : deux passes/ordre du journal/chaîne des preuves, refus de facette protégée sans commit de passe, plafond conservant le préfixe terminé. Ces doubles ne simulent aucune preuve géométrique ; le bridge natiffaeb et le traceur restent byte-exacts, déjà vérifiés séparément sur les fixtures natives. Aucun import scientifique ou vrai maillage n’est exécuté par ces tests.
