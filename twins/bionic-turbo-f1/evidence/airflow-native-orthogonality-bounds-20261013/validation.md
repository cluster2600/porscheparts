# Validation locale achevée

Primaire et lecteur : code 0, chacun lancé une seule fois par run_once.py après gel. Les 1 453 440 bornes et leurs signes revendiqués sont relus ; les 8 448 intervalles D,Q des constantes sont inclus dans les primaires. Le résumé est une lecture structurelle, pas une troisième reconstruction. Tous les programmes gelés et les 14 références de chacun précèdent l'application ; aucune assertion scientifique refusée, aucune installation. Les sources officielles et leurs limites figurent dans source-audit.json.

Tests turbo : Ran 109 tests in 17.100s ; OK (skipped=1). make check : Ran 3992 tests in 247.218s ; FAILED (failures=2, errors=4, skipped=178). Les six labels sont identiques à PR250 : deux échecs WE43/fan_stator et quatre erreurs carrier/rtree/networkx hors turbo. Ce n'est pas un make check entièrement vert. Les journaux et exit codes restent conservés ; aucun diagnostic hors périmètre n'est corrigé.

Les calculs mathématiques et les tests se chevauchent. La branche de base avait sa CI exacte verte ; la publication, la CI du nouveau head, la fusion et la CI main se vérifient séparément après ce dossier local. Aucune qualité native ou CFD n'est déduite de ces validations.
