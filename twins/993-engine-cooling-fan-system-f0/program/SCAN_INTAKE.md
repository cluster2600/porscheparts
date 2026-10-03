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
mécanique ni mise à l'échelle. Les premiers audits ne contrôlaient pas les
auto-intersections ; le contrôle ultérieur de la copie préparée est décrit
ci-dessous.

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

## Diagnostic privé complémentaire et prochain travail

L'inspection des contours conserve leurs index originaux et les parcourt comme
polylignes fermées, sans modifier la surface. Elle calcule en unités source
inconnues un plan PCA, des écarts au plan et un ajustement de cercle purement
indicatif. Le screening utilisé exige au moins 24 arêtes et des RMS radial et
plan inférieurs à 2 % du rayon ajusté : c'est un seuil de diagnostic arbitraire,
pas une tolérance fonctionnelle. Aucun contour ne le satisfait ; cela ne prouve
pas l'absence d'alésage et ne permet pas d'établir un datum à partir d'un bord.
Les 58 contours se répartissent en 56 sur la surface principale et deux sur
le fragment secondaire. Des projections des sommets échantillonnés et des
polylignes exactes ont été inspectées en privé. Le fragment n'est pas identifié
comme une prise arrière complète. Le rapport numérique est reproduit à
l'identique avec une copie portable du script ; aucune coordonnée n'est publiée.

Un contrôle indépendant **OpenFOAM Foundation 13**, build `13-18870c24d21c`,
`surfaceCheck -checkSelfIntersection`, examine la copie préparée dans l'image
locale historique, digest
`sha256:a1db60cbf61bbcca52c171e50cab01ed0b6ec860b227e7c5fc50f7b809659b4f`,
sans réseau, avec plafond 4 CPU / 8 GiB. Il retrouve les deux composantes et
les 8 657 arêtes ouvertes, et signale **89 localisations d'auto-intersection**.
Le code de sortie 0 signifie que l'inspection termine, pas que la surface est
acceptée. Les fichiers de parties, points d'intersection et le journal
natifs restent privés. Aucun solveur n'est lancé. L'entrée est montée en lecture
seule et son hash reste inchangé. Le runtime diffère de Foundation 14 des CFD
#105 ; aucun résultat de l'un n'est assimilé à un calcul de l'autre.
Le label « metre » affiché par cet outil n'est pas une preuve de l'unité OBJ.

Pour répéter cette inspection, monter la copie privée en lecture seule dans
l'image identifiée, monter un répertoire de sortie privé comme `/output`,
choisir `/output` comme répertoire courant, puis exécuter :

```sh
source /opt/openfoam13/etc/bashrc
surfaceCheck -checkSelfIntersection /input/scan.obj
```

Conserver les options Docker `--network none --cpus 4 --memory 8g` et le digest
ci-dessus. L'outil peut écrire des sous-parties et points géométriques : ne pas
utiliser un répertoire versionné pour sa sortie. Enregistrer hash d'entrée,
version/build, journal, code de sortie et disposition QA séparément.

Le prochain travail géométrique consiste à identifier les zones d'acquisition
et interfaces, établir le repère fonctionnel A/B/C, classifier les lacunes et
les intersections, puis reconstruire les surfaces avec écarts mesurés et
transformations traçables. Une fermeture globale, une projection du fragment
ou un ICP libre ne constitue pas cette reconstruction. Unité d'export,
référence du spécimen et deux cotes indépendantes avec outil/incertitude
(diamètre extérieur et alésage) sont les premières données demandées.
La matière n'est pas nécessaire à cette inspection topologique ; propriétés
orientées, état métallurgique et process restent indispensables à une
simulation mécanique ou LPBF défendable.
