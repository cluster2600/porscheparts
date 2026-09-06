# F53 — diagnostic de sérialisation STEP

Deux exports du maître natif 2V F50 ont été réellement exécutés sur Kali le
6 septembre 2026, puis relus et contrôlés par OCCT. Le maître source est lié
au SHA-256 `1574eb58b7af09bcadab6c9cfcdd9a56940d479a5aa1b1eb807d31d41d4f7c36`.

| Export AP242 | Mode relu dans OCCT | Défauts CurveOnSurface après réimport |
|---|---:|---:|
| Courbes paramétriques conservées | 1 | 8 |
| Courbes paramétriques omises | 0 | 131 |

Le constructeur STEP est initialisé avant les réglages, leur succès est
contrôlé et le mode est relu avant export. Aucun changement de surface,
épaississement, réparation automatique ou augmentation de tolérance n'est
appliqué par ce diagnostic. Les rapports conservent les empreintes, le contrôle
BRepCheck, la topologie et les écarts de propriétés après réimport.

La voie « omettre les p-curves » est rejetée pour ce maître. La suite consiste
à localiser les huit raccords fautifs du contrôle, examiner leurs surfaces et
leurs courbes 3D, puis reconstruire localement les raccords responsables avant
un nouvel audit. Ces essais ne prouvent aucune réparation et ne libèrent
aucune pièce. Le maître 4V, les épaisseurs, le maillage, les fonctions d'usinage,
le procédé LPBF, le CHT, la distorsion et PhysicsNeMo restent à traiter dans le
programme demandé.

Le script reproductible est
`twins/reference-917-engine/source/probe_step_serialization_f53.py`.
Les deux fichiers STEP et rapports détaillés restent dans l'espace privé de
travail ; les maîtres F50 ne sont pas écrasés. Le code retour 2 de ces deux
essais représente un rejet numérique attendu, pas une exécution inachevée.
