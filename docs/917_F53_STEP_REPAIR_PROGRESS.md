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

## Localisation et première correction

L'inspection de 1 001 paramètres par raccord trouve huit arêtes B-spline
sur cinq faces (quatre supports cylindriques et un support B-spline). Aucun
des huit couples n'est une couture périodique. Les deux écarts les plus élevés
échantillonnés valent `1,9849185e-5` et `7,0727442e-5` unité du scan.
Ces valeurs échantillonnées ne constituent pas une borne globale certifiée.

Une copie profonde du STEP de contrôle a ensuite reçu une correction
`FixSameParameter` uniquement sur les huit arêtes repérées. Le réglage demandé
est `1e-7`. Le diagnostic passe de huit à six défauts avant export et conserve
six défauts après réimport. Les tolérances des arêtes traitées n'augmentent pas.
BRepCheck reste valide ; l'écart relatif de volume est `-1,9732054e-11` et
l'écart maximal de boîte englobante `4,2632564e-14` unité du scan. Ces métriques
globales ne remplacent pas le contrôle spatial des surfaces et l'audit BOP
complet, encore requis. La copie corrigée n'est pas promue comme nouveau maître.

Le STEP candidat privé a l'empreinte
`52f637bc348c765b1e39476df8206d31f0d636527b34cf815f993a3d794889c5`.
Les scripts `inspect_step_faults_f53.py` et
`probe_step_same_parameter_f53.py` reproduisent ces opérations avec contrôle
de l'empreinte d'entrée et refus d'écraser les sorties existantes.

## Reprojection précise et contrôle des deux défauts persistants

Sur la copie à six défauts, la reprojection locale à `1e-7`, suivie de
SameParameter, réduit le résultat à **deux défauts avant et après export**.
Les maxima des tolérances de faces et d'arêtes après réimport valent `1e-7`.
BRepCheck reste valide. Le STEP privé obtenu est lié au SHA-256
`0ba32a920749a6ae9d4fde04ba2b04b470d5b9a555c68f0c3b06ba02e2bc31c1`.

L'inspection relancée confirme que les deux raccords restants sont les deux
supports cylindriques présentant les écarts `1,9849185e-5` et `7,0727442e-5`.
Une reconstruction expérimentale des courbes 3D à partir des p-curves sur une
nouvelle copie ne réduit pas ce nombre : deux défauts persistent après STEP.
Cette voie n'est donc pas retenue comme amélioration. Les déplacements
échantillonnés avant SameParameter sont inférieurs à `9,78e-8` unité du scan ;
ils ne prouvent pas une borne après l'ensemble des opérations.

La prochaine correction doit examiner le raccordement entre ces cylindres et
leurs faces voisines. Le seuil de tolérance n'a pas été élargi pour obtenir
une acceptation. Les défauts concernent toujours le candidat 2V ; aucune
acceptation STEP 2V ou 4V n'est revendiquée à ce stade.

## Supports voisins et projection directe

Le contrôle des faces voisines révèle deux intersections cylindre/cylindre.
Sur 101 paramètres par arête, la distance minimale de la courbe 3D à chacun
des quatre supports reste inférieure à `4,97e-8` unité du scan. Ce contrôle
échantillonné indique une incohérence de représentation paramétrique ; il ne
certifie pas l'intégralité des courbes.

Une projection directe `GeomProjLib.Curve2d`, sans refit SameParameter, réduit
les maxima échantillonnés après STEP à `4,1126721e-7` et `5,7000656e-7`, contre
`1,9849185e-5` et `7,0727442e-5` avant cette opération. Le nombre de défauts
reste deux. À la réimportation, OCCT porte les tolérances de ces arêtes à
`1,1897365e-7` et `1,4998458e-7`, insuffisantes pour les écarts observés.
Le rapport expose cette augmentation automatique ; elle n'est pas présentée
comme une réparation validée.

Les précisions de projection demandées `1e-9` puis `1e-12` donnent les mêmes
comptages et métriques globales. Réduire ce seul paramètre ne résout donc pas
les défauts. La suite devra contrôler la représentation 2D sur les intervalles
de nœuds des splines, puis reconstruire celle-ci avec un contrôle d'erreur
adaptatif avant le prochain round-trip.
