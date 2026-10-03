# Entrée du scan privé

[Programme](../README.md) · [Outil d'audit](../source/audit_private_scan.py)

Le 3 octobre 2026, le fichier candidat
`Fan+0.5mm+back+not+lined+up+with+center.obj` a été retrouvé dans iCloud Downloads.
La recherche a été limitée à ce dossier et aux noms pertinents de Downloads
local. Un second fichier `Fan+Drive+0.21mm.obj` existe dans Downloads local ;
il n'a pas été traité comme le même composant ni importé.

Deux audits locaux indépendants du candidat donnent les mêmes comptes :

| Contrôle des données originales | Résultat |
|---|---:|
| Taille | 51 575 667 octets |
| Sommets / triangles | 624 492 / 1 240 465 |
| Arêtes de bord | 8 611 |
| Arêtes incidentes à plus de deux triangles | 0 |
| Incohérences d'orientation sur arêtes à deux faces | 0 |
| Composantes de surface | 2 |
| Sommets des composantes | 615 429 et 9 063 |
| Triangles d'aire exactement nulle | 26 |
| Faces dupliquées / sommets non référencés | 0 / 0 |

SHA-256 : `244d4caeb2c4ac4a692b650ec9d766bee2a8124335a0236a55a1d30c1b2b98ba`.
Ce hash identifie le fichier audité ; il n'atteste ni auteur ni droits.

Le fichier OBJ ne contient que des enregistrements `v` et `f` : aucune unité,
licence ou référence de pièce n'y est déclarée. Une acquisition commerciale
Wolfe Classics a depuis été confirmée par les justificatifs privés consultés
dans la tâche d'origine. Le nom de livraison « Fan 0.5mm back not lined up with
center.obj » concorde avec le nom encodé du fichier iCloud. Aucun hash vendeur
ne permet toutefois de vérifier la livraison octet par octet ; le titre
commercial « Porsche 935 Fan 3D Scan » n'identifie pas une référence Porsche.
Les justificatifs, données personnelles et détails de commande ne sont pas
publiés. Ils n'accordent pas de licence de redistribution.

Le nom « 0.5mm » ne constitue
pas une calibration et ne mesure pas l'erreur du scan. Les étendues, la pose
et les vues de diagnostic sont conservées uniquement dans le rapport privé.
L'alignement PCA est une transformation rigide de visualisation, sans datum
mécanique ni mise à l'échelle. Les auto-intersections n'ont pas été contrôlées.

## Décision de reprise

Le scan est **ouvert**. Aucun volume, masse, minimum d'épaisseur, étanchéité
physique, ajustement ni précision dimensionnelle ne peut être qualifié par ces
comptes. Les trous et la petite composante doivent être identifiés sur la pièce
avant suppression ou comblement. Aucune réparation ni géométrie exportée n'a
été effectuée lors de cet audit. Le brut reste à son emplacement d'origine ; les rapports et
aperçus sont sous `work/`, ignoré par Git. Ne pas forcer leur ajout.

Il manque : opérateur et conditions du scan, identité/référence exacte de pièce,
unité/export du logiciel, mesure indépendante avec incertitude, datum d'axe et
explication de l'alignement arrière, permission de réutiliser/publier des dérivés.
Les droits du scan restent `unconfirmed_private_only`. Une demande de ces
informations est en attente ; aucune réponse n'est remplacée par une hypothèse.

Après résolution, conserver un original immuable, définir un repère coté,
traiter séparément les composantes, documenter chaque réparation et comparer la
surface réparée au brut avec une tolérance approuvée. Les coordonnées manquantes
et interfaces fonctionnelles ne doivent pas être inventées.

## Préparation réversible ensuite exécutée

Le [préparateur privé](../source/prepare_private_scan.py) a depuis produit une
copie locale, avec pose PCA orthonormale directe, facteur d'échelle 1 et matrice
inverse. Il conserve l'ordre des sommets et toutes les faces non nulles, retire
uniquement les 26 faces d'aire exactement nulle et enregistre leurs indices pour
réversibilité. Le fichier exporté est relu et retransformé vers les coordonnées
originales pour mesurer l'erreur numérique. Le hash du brut est contrôlé avant
et après, sans écraser celui-ci. Les transformations, index retirés et maillage
de travail sont tous privés sous `work/`.

Cette opération prépare l'inspection ; elle ne ferme aucun trou et n'aligne pas
les deux composantes entre elles. Un recentrage global ne résout pas un
décalage relatif du dos. La méthode de reprise proposée est de segmenter les
prises de vue sans les jeter, identifier un axe/alésage et des zones communes
mesurés, puis enregistrer rigidement les prises avec transformation et erreur
de correspondance. Sans ces correspondances, un ICP automatique risquerait
d'ajuster deux surfaces physiquement différentes. Aucun alignement arrière
fonctionnel n'est inventé.

## Contours ouverts ensuite inspectés

Le graphe des arêtes de bord originales comporte **48 contours**, tous des
cycles simples, sans embranchement. Après retrait des triangles nuls, la copie
compte **58 cycles** et **8 657 arêtes de bord** : retirer une face invalide peut
exposer de nouvelles arêtes. L'auditeur conserve la liste des tailles de contours
dans les rapports privés et un test synthétique distingue les contours pincés
des cycles simples. Les comptes d'arêtes à plus de deux faces ne suffisent donc
pas, seuls, à caractériser les contours.

Un cycle topologique n'est pas automatiquement un trou à reboucher : il peut
correspondre à une ouverture réelle, une frontière de prise de vue ou une
surface manquante. Les rapports ne publient ni positions ni maillage et ne
classent aucun contour sans observation de la pièce. La fermeture volumique et
le recalage relatif des composantes restent à effectuer avec ces références.
