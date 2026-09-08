# M64 — contacts de guides et préparation géométrique

**Le candidat BRep sauvegardé passe les cinq modes BOP sélectionnés ;
les 136 contrôles de non-recouvrement du gaz passent également.** Le nouveau
diagnostic complet des frontières termine 104 soustractions : 102 passent,
deux restent averties sur le même groupe de trois faces. Les différences de
resérialisation sont maintenant attribuées sur Linux comme sur macOS, sans
preuve d'équivalence globale des solides ni levée du refus historique.
Le maître `21c9c40b…` reste inchangé, sans promotion du candidat `450ba081…`.
Les contacts nominaux des guides sont mesurés, sans qualification à chaud.
La partition du gaz reste refusée : validité et non-recouvrement sont contrôlés,
mais la couverture des frontières et le bilan de volumes ne sont pas encore
acceptés globalement. Un nouveau contrôle du 8 septembre attribue les huit
faces des deux groupes mixtes aux rôles source. Leur rattachement aux preuves
antérieures permet un registre des **124 faces externes**, sans revalidation
physique des étiquettes. Un premier maillage du **solide V5**, distinct du gaz,
est obtenu puis rejeté : **4 871 éléments sur 271 001 sous le seuil de qualité**.

Ce point suit les [contrôles de matière et de logements](M64_EXHAUST_MATERIAL_CONTROLS_20260908.md)
et la [localisation des défauts du maillage](M64_ANNULAR_MESH_LOCALISATION_20260908.md).
Les [empreintes des reçus](../twins/m64-cylinder-head/evidence/geometry-checkpoint-20260908.json)
séparent les opérations successives et conservent les échecs. Les unités restent
celles du scan, sans certification de l'échelle ou des interfaces M64.

## Appui des inserts : mesure sur la géométrie, pas sur une pièce fabriquée

Les quatre guides du STEP V2 sont identifiés parmi ses douze solides par leurs
surfaces cylindriques, axes, longueurs et volumes, puis recoupés avec les
identifiants enregistrés. Leur transformation de repère est appliquée une fois.
Les modèles d'inserts ne sont pas remplacés par les boîtes des logements.

Pour chaque guide, `Common(face extérieure du guide, corps)` fournit un patch
exporté en privé. Son aire est rapportée à la surface latérale extérieure du
guide de longueur nominale 35 unités. Soixante-quatre sections natives,
strictement intérieures et régulièrement espacées, mesurent ensuite les arcs
d'appui. L'union des arcs évite de compter deux fois les superpositions.

| Guide CAO | Aire du patch, unités scan² | Fraction de la surface extérieure | Sections sans / partielles / complètes |
|---|---:|---:|---:|
| Échappement 1 | 817,779374 | 67,6123 % | 17 / 5 / 42 |
| Échappement 2 | 817,528516 | 67,5915 % | 17 / 5 / 42 |
| Admission 1 | 794,822941 | 65,7143 % | 22 / 0 / 42 |
| Admission 2 | 794,822941 | 65,7143 % | 22 / 0 / 42 |

Les 256 sections sont des **échantillons**, pas une preuve de couverture
continue entre les plans. La moyenne des sections diffère légèrement du
rapport d'aires ; elle ne le remplace pas. Les deux admissions concordent avec
le diagnostic historique 23/35 ; cette concordance ne qualifie pas leur tenue.

Les quatre intersections `Common(guide solide, corps)` ont un volume
numériquement nul. Ce n'est ni une preuve de jeu strictement nul à toute
échelle, ni une prescription de serrage. Les opérations utilisent les
tolérances natives d'OCCT. Pression de contact, conductance thermique,
dilatation différentielle et rétention restent à déterminer. Une fraction
d'appui inférieure à 100 % ne suffit, à elle seule, à conclure à un défaut.

Le premier témoin échoue avant tout cas pour une collision de noms lors de
l'import Python d'OCP. Après correction limitée à cet import, quatre témoins
natifs passent : appui entier, demi-longueur, demi-circonférence et aucun
contact, avec 32 sections conformes. Le contrôle des quatre guides suit avec
code natif/wrapper 0, en 7,761 s / 8,196 s nettoyage compris. Aucun corps modifié.

## Courbes : restriction exacte et candidat segmenté, acceptation non acquise

Les six supports existants des deux arêtes signalées C0 sont divisés en quinze
supports : cinq courbes 3D et dix p-curves. Pour ces B-splines non rationnelles,
les identités polynomiales sont contrôlées en arithmétique rationnelle sur
chaque intervalle ; les coefficients sont réassemblés exactement. Les quinze
supports construits dans OCP sont au moins C1 à l'intérieur de leur domaine.
Les 495 comparaisons supplémentaires de points natifs donnent un écart nul ;
cet échantillonnage n'est pas, à lui seul, la preuve globale.

Les discontinuités de tangente initiales restent aux jonctions. Il ne s'agit
pas d'un lissage. Aucun corps BRep n'est lu ou écrit pendant cet essai de
supports de 0,613 s. À ce stade, leur réintégration dans une copie topologique
et le contrôle du corps complet restent à faire, sans changer les surfaces.
L'ancien refus de réduction de multiplicité reste distinct et conservé.

### Réintégration : trois arrêts logiciels avant remplacement des arêtes

| Essai natif | Durée native | Premier arrêt | Travail réellement atteint |
|---|---:|---|---|
| V2 | 2,135 s | `topological_occurrence_location_not_identity` | Lecture et contrôles du corps source ; copie non créée. |
| V3 | 2,542 s | `copy_placement` | Copie créée en mémoire ; correspondance des entités non terminée. |
| V4 | 2,897 s | `Standard_NoSuchObject` | Bijections des entités copiées contrôlées ; revue racine/hiérarchie non terminée. |

Les deux premiers gardes confondaient représentation interne d'une
localisation et transformation effective. V4 autorise seulement, pour les
sommets copiés, un changement de représentation si les deux matrices sont
exactement identitaires et si coordonnées brutes, coordonnées effectives et
tolérances sont identiques. Les autres localisations restent comparées sans
cette exception. Les 4 938 changements de représentation observés en V4 ne
sont donc pas 4 938 déplacements de sommets.

L'exception V4 ne démontre pas un défaut de la pièce : le reçu la situe après
la bijection, mais ne contient pas de traceback permettant d'identifier
l'appel précis. Aucun de ces trois essais ne reconstruit les arêtes,
n'exporte de BRep, ne relit un candidat ou n'exécute BOP. Les champs de modes
BOP décrivent le calcul prévu ; `stage=complete` signifie fin du programme,
pas réussite géométrique. Les entrées et le programme restent inchangés durant
chaque essai, sorties 2 sans OOM ni timeout. Aucun ancien refus n'est effacé.

Un diagnostic local séparé reproduit une recherche de sous-forme absente avec
les localisations non cumulées. En cumulant les localisations, comme le fait
[OCCT lors de la copie](https://github.com/Open-Cascade-SAS/OCCT/blob/V7_9_3/src/BRepTools/BRepTools_Modifier.cxx),
le parcours complet effectue 75 186 recherches sans erreur, sur 25 069 formes.
Ce diagnostic ne reconstruit rien et ne modifie pas le corps, en mémoire ou
sur disque. Il identifie une correction du programme à tester, pas une
correction du corps déjà acquise.

### V5 : candidat sauvegardé et relu, resérialisation différente

La correction limitée des deux parcours de hiérarchie est exécutée sur Kali.
Elle produit un candidat binaire privé : un solide, une coque, 4 900 faces,
10 078 arêtes et 5 179 sommets. Cela ajoute trois arêtes et trois sommets,
sans changer les supports des surfaces ni leurs localisations/tolérances
dans la copie en mémoire. Les occurrences orientées des contours correspondent
aux remplacements prévus. Il ne s'agit pas d'un lissage du contour Porsche.

Après sauvegarde/relecture, les nombres d'entités restent identiques,
`BRepCheck` exact passe, les tolérances des sommets/arêtes/faces sont conservées
et les coefficients des quinze supports segmentés correspondent exactement.
Le corps source reste inchangé en mémoire et sur disque.

Le garde suivant refuse pourtant le candidat : son empreinte de sérialisation
binaire en mémoire diffère après relecture (`reread_serialized_representation_equal=false`).
Les contrôles précédents n'identifient pas encore la différence ; elle ne doit
être ni assimilée sans diagnostic à une déformation, ni écartée comme anodine.
Les quadratures comparatives et les cinq modes BOP prévus ne sont pas atteints.
Aucun critère n'est dispensé et le candidat n'est pas promu comme maître.
Durées 8,307 s natives / 8,905 s nettoyage compris, sorties 2, sans OOM ni timeout.
Pour V5, les plafonds demandés sont enregistrés, mais la sonde de ressources a
échoué avant inspection : aucune mesure effective CPU/RAM n'est revendiquée.
Suppression et absence du conteneur sont vérifiées séparément.

### BOP indépendant du candidat sauvegardé : cinq modes réussis

Un contrôle distinct relit directement le binaire `450ba081…` sur Kali/OCP
7.9.3.1, sans reconstruire ni exporter le corps. `SelfInterMode`,
`SmallEdgeMode`, `RebuildFaceMode`, `ContinuityMode` et `CurveOnSurfaceMode`
sont tous activés et terminés : **zéro défaut, erreur ou avertissement**.
Les quatre autres modes restent désactivés et sont consignés dans le reçu.
Ce résultat concerne ces cinq modes, pas tous les critères possibles d'OCCT.

`BRepCheck` exact passe avant et après. Les tolérances brutes/effectives et les
empreintes binaires du même objet chargé restent identiques durant le contrôle.
Le fichier source est inchangé ; l'ancien refus de resérialisation n'est pas
effacé. Durées : 173,501 s pour BOP, 178,128 s pour le worker et 178,849 s
nettoyage compris. Sorties 0, sans OOM ni expiration. Les plafonds effectifs
2 CPU/4 Gio, le système de fichiers racine en lecture seule et l'absence de
réseau sont vérifiés. Conteneur supprimé, absence revérifiée séparément.

### Sérialisation : les 1 114 octets différents sont localisés sur macOS

Une lecture par chemin suivie de deux écritures **en mémoire** reproduit une
différence de 1 114 octets sur 5 205 080, sans changement de longueur. Les deux
écritures successives du même objet sont identiques. Un lecteur du format OCCT
V3 attribue ensuite toutes les différences ; il vérifie les limites des tables,
les références topologiques, les orientations, les drapeaux et la fin du fichier.

| Champs modifiés après lecture/écriture | Octets différents | Écart maximal par composante |
|---|---:|---:|
| Directions des courbes 2D | 90 | `1,11023e−16` |
| Directions des courbes 3D | 366 | `2,22045e−16` |
| Directions des repères de surfaces planes/cylindriques | 374 | `2,22045e−16` |
| Caches des extrémités UV de 101 arêtes | 284 | `4,26326e−14` en coordonnées UV |

Aucun octet différent ne reste non attribué. Les localisations, points,
coefficients des B-splines, rayons, intervalles, tolérances, références et
drapeaux topologiques sérialisés ne changent pas dans cette comparaison.
Les directions sont sans dimension ; un écart UV **n'est pas** une distance 3D.
Les 32 correspondances exactes à une normalisation simple parmi 45 groupes de
directions 2D modifiés ne justifient pas d'attribuer tous les écarts à cette seule
opération. Le format reconstruit des directions/repères et recalcule des caches
UV lors de la lecture ; ce sont des mécanismes à distinguer.
[Lecture des directions](https://github.com/Open-Cascade-SAS/OCCT/blob/V7_9_3/src/BinTools/BinTools_Curve2dSet.cxx),
[lecture et écriture des arêtes](https://github.com/Open-Cascade-SAS/OCCT/blob/V7_9_3/src/BinTools/BinTools_ShapeSet.cxx).

Ces diagnostics de 0,756 s, 1,343 s et 1,683 s utilisent **macOS arm64**, pas le
conteneur Linux. L'empreinte après lecture y est `7f3cc7e4…`, contre `37eda433…`
dans l'audit BOP Linux, avec le même format V3. L'attribution macOS ne prouve
donc pas celle de Linux. Les empreintes avant/après chaque audit ne sont
comparées qu'au sein de la même exécution. Aucun BRep n'est exporté, aucune
tolérance augmentée et aucun candidat promu. Une première sonde atteint son
plafond CPU sans checkpoint ; deux essais du lecteur s'arrêtent sur des erreurs
de séparateurs avant correction d'après le format source. Leurs reçus privés
sont conservés ; ils ne sont pas des échecs physiques de la pièce.

### Linux : empreinte BOP reproduite et 175 octets attribués

Un lot distinct utilise la même image OCP 7.9.3.1 linux/amd64 que l'audit BOP.
La lecture du fichier puis l'écriture V3 en mémoire reproduisent exactement
son empreinte `37eda433…`. Deux écritures du même objet chargé concordent.
Le corps comporte toujours 5 205 080 octets : 175 diffèrent du fichier source,
contre 1 114 sur macOS. Aucun nouveau BOP ni export CAO n'est exécuté.

| Champs Linux modifiés | Octets différents | Entités concernées |
|---|---:|---:|
| Directions de lignes 2D | 64 | 32 courbes |
| Directions de coniques 3D | 40 | 15 courbes |
| Repères de plans et cylindres | 58 | 23 surfaces |
| Caches d'extrémités UV | 13 | 10 arêtes de la table TShapes |

Tous les octets différents sont attribués. Points, coefficients des B-splines,
rayons, intervalles, tolérances, localisations, références et drapeaux
topologiques sérialisés restent inchangés dans cette comparaison. Les 32
directions 2D modifiées correspondent à la formule de normalisation simple
testée ; ce constat ne décrit pas tous les mécanismes de reconstruction des
repères 3D. L'écart maximal des caches reste une grandeur UV (`1,42109e−14`),
pas une distance spatiale. Le résultat Linux n'efface pas le résultat macOS.

Durées : 1,360 s natives / 1,955 s nettoyage compris, sorties 0, pas d'OOM ni
expiration. Plafonds effectifs 2 CPU/4 Gio, racine en lecture seule et réseau
absent contrôlés ; conteneur supprimé et absence revérifiée. Le fichier source,
les décodeurs et les entrées restent intacts. Le candidat n'est pas promu.

### Borne des représentations Linux : portée locale explicite

Un calcul séparé, sans appel OCP, traite les valeurs binary64 comme des
rationnels exacts et arrondit les majorants vers l'extérieur. Il encadre les
32 lignes 2D sur leurs intervalles complets, les 15 coniques 3D et les 23
repères de surfaces modifiés. Pour les plans, les contours définissent une
enveloppe UV finie ; les B-splines utilisées sont non périodiques, à extrémités
bloquées et poids positifs. Leur enveloppe de pôles fournit un encadrement.

Le maximum des bornes par composante spatiale vaut
**`1,0854592454916939e−14` unité scan**, sur une ellipse 3D. Par exemple, la
variation d'une ligne est bornée par `max|t| × |Δdirection|` ; celle d'une
conique par `rayon1 × |Δaxe1| + rayon2 × |Δaxe2|`. Les repères et changements
de paramètres sont pris en compte pour les contours projetés sur les plans.

Une revue indépendante reproduit les 72 bornes spatiales et 32 bornes UV,
vérifie les offsets et les deux décodeurs importés. Ces derniers ne sont pas
directement épinglés dans le script de bornes : leurs hashes ont été contrôlés
séparément, comme ceux du corps et du rapport Linux. Durée du calcul initial :
1,241 s ; aucun natif ni fichier CAO créé.

Cette borne porte sur les **représentations analytiques et contours décrits**,
pas sur la distance de Hausdorff entre solides, les erreurs d'évaluation
flottante d'OCCT ou les caches UV d'extrémités. Le budget de représentation
provisoire `1e−9` unité scan, fixé avant le calcul, n'est ni une tolérance
d'usinage ni une levée automatique du refus historique. Aucune précision
physique, équivalence globale ou autorisation de fabrication n'en est déduite.

## Partition du gaz : refus conservé

Sur le domaine d'admission `fab1338a…`, le calcul natif obtient en mémoire
seize blocs annulaires à six faces, douze arêtes et huit sommets, plus un cœur.
Les contrôles d'ascendance des frontières et d'interfaces partagées précèdent
le refus `native_partition_volume_sum_failed`. Le seuil relatif `1e−9` n'est
pas modifié. Aucun export BRep de cette partition ni `gmsh.generate` exécuté.

La somme des dix-sept volumes enregistrés lors de ce premier essai vaut
`995961.7204052373` unités scan³. Le volume initial de **cet appel** n'ayant
pas été consigné avant le refus, l'écart exact du garde n'est pas reconstructible.
Il faut instrumenter les deux intégrales et leurs estimations de quadrature
avant de conclure à une erreur de partition ou d'intégration. Les valeurs
d'anciens reçus ne remplacent pas la valeur manquante.

### Deuxième essai : intégration instrumentée, sans changer la partition

Un nouvel appel consigne désormais le volume initial, les dix-sept volumes et
leur somme avant la décision. Il retrouve le refus : `995961.70449802` contre
`995961.7204052373` unités scan³, soit un écart relatif `1.59717e−8`, supérieur
au seuil inchangé `1e−9`. Le premier reçu n'est ni corrigé ni remplacé.

Les mêmes formes en mémoire sont ensuite intégrées à trois précisions
adaptatives, avec la surcharge `Eps` explicite d'OCCT :

| Eps demandé | Volume du domaine, unités scan³ | Somme des 17 volumes, unités scan³ | Écart relatif |
|---:|---:|---:|---:|
| `1e−7` | 995964,5780437368 | 995964,5779154756 | `1,28781e−10` |
| `1e−9` | 995964,5870689296 | 995964,5870742635 | `5,35549e−12` |
| `1e−11` | 995964,5869731805 | 995964,5869750070 | `1,83387e−12` |

Cet accord est un indice de sensibilité à la quadrature, **pas une preuve de
conservation géométrique** : l'estimation retournée pour le domaine reste
proche de `1,054e−7`, malgré les précisions plus strictes demandées. Les
estimations OCCT ne sont pas des bornes garanties ; accord somme/domaine et
convergence absolue sont deux contrôles différents.
[API OCCT 7.9.3](https://github.com/Open-Cascade-SAS/OCCT/blob/V7_9_3/src/BRepGProp/BRepGProp.hxx)

Le deuxième essai dure 5,099 s natifs, 5,654 s nettoyage compris ; sortie 2,
sans OOM ni timeout. Un BRep **diagnostic privé** est exporté avant la décision,
avec cinq checkpoints. À l'issue de cet essai, sa relecture indépendante et le
non-recouvrement restent à contrôler. Aucun maillage ni solveur lancé ; le refus
non adaptatif reste actif. Sources et entrées inchangées, conteneur exact
supprimé et absence revérifiée hors du lanceur.

### Relecture indépendante : validité réussie, audit incomplet

Un auditeur distinct relit le domaine source et le BRep diagnostic sauvegardé.
Les 19 contrôles `BRepCheck` exacts passent : domaine, composé et 17 solides.
Aucune arête non dégénérée ne manque du drapeau `SameParameter`. Les incidences
retrouvent 16 blocs annulaires et un cœur, avec huit interfaces cœur/blocs.

L'intégration alternative Gauss–Kronrod sur le domaine et les 17 solides
donne `995964.5863888268` contre `995964.5863979517` unités scan³, soit
`9.16178e−12` d'écart relatif. Ce calcul utilise `IsUseSpan=True` et `Eps=1e−9` ;
il ne remplace pas le refus historique ni ne transforme une estimation en
borne garantie.

Les ensembles de signatures de supports et d'orientations des frontières
concordent. Le premier groupe passe les deux soustractions sans résidu de face
ou d'arête. L'auditeur s'arrête ensuite sur
`support_group_has_ambiguous_physical_roles` : son regroupement par support
rencontre plusieurs rôles physiques. Cela ne prouve pas une différence de
géométrie. La couverture des frontières est **partielle**, les 136
intersections entre solides ne sont **pas exécutées**, et la comparaison
finale des instantanés mémoire n'est **pas atteinte**.

Sorties natives/lanceur 2, en 1,082 s / 1,647 s, sans OOM ni timeout ; fichiers
d'entrée et programmes inchangés. Le candidat n'est pas admis au maillage.

### Séparation des rôles : 16 groupes contrôlés, puis arrêt booléen

La version suivante distingue couverture géométrique et attribution des rôles.
Elle enregistre deux groupes plans mêlant `walls_chamber` et `walls_seat`, sans
les traiter comme un défaut géométrique ni les déclarer correctement classés.
Les opérations booléennes et leurs critères restent inchangés.

Cette fois, 16 groupes passent, soit 32 soustractions réussies documentées,
sans résidu de face ni d'arête. Une opération du groupe suivant déclenche
`native_boolean_error_or_warning` ; son sens exact et le total des soustractions
réussies ne sont pas enregistrés. Le reçu ne
distingue pas erreur et avertissement, et ne consigne pas le type de message :
aucune cause géométrique précise ne peut en être déduite. Les 19 contrôles de
validité et les 18 intégrations GK sont répétés avec les mêmes résultats.
Les 136 intersections entre solides et le contrôle mémoire final ne sont
toujours pas exécutés. Les deux versions refusées restent disponibles.

Durées 1,375 s natives / 1,934 s nettoyage compris ; sorties 2, sans OOM ni
timeout, sources et entrées inchangées, absence du conteneur vérifiée hors
lanceur. La suite doit enregistrer le groupe, le sens et les messages natifs
de chaque opération ; le non-recouvrement peut faire l'objet d'un lot distinct,
sans prétendre que la couverture des frontières est acquise.

### Lot indépendant : les 136 intersections entre solides sont terminées

Les mêmes quatre entrées gelées sont relues, sans nouvelle partition, sans
soustraction de frontières et sans quadrature. Les 19 contrôles `BRepCheck`
exacts passent de nouveau. Les `17 × 16 / 2 = 136` paires font chacune l'objet
d'un `Common` non destructif et d'un journal avant/après l'opération.

**136 résultats valides, zéro solide d'intersection, zéro erreur, avertissement
ou résultat inconnu.** Les fichiers d'entrée et les instantanés mémoire
texte/tolérances sont inchangés ; l'empreinte texte n'est pas une preuve complète
de tous les coefficients binaires. Le non-recouvrement est contrôlé dans le
cadre des tolérances natives. Ce lot ne contrôle ni l'auto-intersection interne
de chaque solide ni la couverture totale du domaine.

Durées : 5,256 s natives / 5,796 s nettoyage compris ; pas d'OOM ni expiration,
plafonds effectifs 2 CPU/4 Gio et conteneur absent après suppression. Le code
retour 2 est prévu même si les 136 paires passent : les refus antérieurs sur
frontières, rôles physiques et volumes restent en vigueur. Aucun maillage lancé.

### Diagnostic complet des frontières : un seul groupe reste averti

Les 52 groupes de supports orientés sont tous examinés dans les deux sens,
soit 104 `CUT` terminés. **102 résultats sont valides, sans face ni arête
résiduelle et sans message natif.** Les deux autres opérations, sur le groupe
17 des faces source/candidat 28, 29 et 35 (`walls_port`), retournent chacune
quatre `BOPAlgo_AlertFaceBuilderUnusedEdges`, sans erreur. Leurs résultats ne
sont pas examinés après l'avertissement : aucun résidu nul n'est supposé.

Le diagnostic conserve les paramètres booléens et critères précédents. Il
vérifie 19 formes BRep, les incidences et les instantanés mémoire avant/après.
Un contrôle distinct recompte les 86 faces source, toutes les faces externes
candidates, 208 événements de journal et les empreintes de 312 sorties natives.
Cela prouve l'exécution exhaustive du diagnostic, pas la couverture géométrique
des deux opérations averties. À ce stade du diagnostic, les deux groupes plans
aux rôles physiques mélangés restent sans attribution résolue ; le nouveau
contrôle du 8 septembre présenté ci-dessous les traite séparément.

Durées : 1,984 s natives / 2,550 s nettoyage compris ; sortie 2 intentionnelle,
pas d'OOM ni expiration. Aucun nouveau `Common`, GK, BRep ou maillage.
Les plafonds 2 CPU/4 Gio sont vérifiés après la fin du processus, sans mesure
de mémoire de pointe. Sources/entrées inchangées, conteneur retiré, absence
revérifiée indépendamment. La capture native complète a réussi ; une limite
du programme est conservée dans le reçu : la résolution de `GetReport().Dump`
précède son bloc de capture d'exception. Aucun échec de capture n'est observé.

### Identité complémentaire des trois faces : test strict refusé

Un contrôle séparé sérialise chaque face entière, contours compris, en V3
binaire en mémoire. Les six contrôles BRep passent et les placements racines
et orientations correspondants concordent. Cependant, les faces 28 et 29 ont
des représentations différentes, malgré des longueurs respectivement égales
à 21 237 et 21 605 octets. La bijection exacte des trois faces est donc refusée.

La face 35 a le même SHA enregistré, mais la fonction de comparaison des
octets s'arrête au premier non-appariement : aucun succès global ni test
distinct complet de la face 35 n'est inventé. Cette différence binaire ne
prouve pas, à elle seule, une différence de forme. Il faut en identifier les
champs avant de décider d'une comparaison géométrique pertinente.

Durées : 0,461 s natives / 1,034 s nettoyage compris ; sorties 2, aucune
normalisation demandée, aucun lissage, `CUT`, BOP ou export. Entrées et objets
chargés inchangés, plafonds 2 CPU/4 Gio vérifiés, absence du conteneur confirmée.
Les deux soustractions averties ne sont pas renommées en réussites.

### Différences des faces 28/29 : données auxiliaires, géométrie définissante inchangée

Le décodeur complet localise ensuite **deux octets par face**, quatre au total.
Seules les directions X/Y d'un plan auxiliaire changent, avec un écart maximal
par composante de `1,23260e−32`, sans dimension. Aucun autre champ sérialisé
ne diffère. Les empreintes des quatre faces source/candidates reproduisent
celles du test précédent ; les décodeurs restent inchangés.

Le parcours de toutes les références montre que ces plans sont utilisés
**exclusivement par des représentations d'arête de type 4, « Regularity »**.
Ils ne sont référencés ni par les faces, ni par leurs p-curves ou sommets.
Chaque face possède un support B-spline principal inchangé. Ce lien est
établi par les références du fichier, pas supposé à partir des numéros de
surfaces. [Lecture du type 4 et du support de face dans OCCT](https://github.com/Open-Cascade-SAS/OCCT/blob/V7_9_3/src/BinTools/BinTools_ShapeSet.cxx#L976-L1054).

Le sous-graphe sérialisé définissant les deux faces est donc identique dans
cette relecture Linux/OCP : support principal, courbes 3D, p-curves et plages,
contours orientés, sommets, localisations et tolérances. Une revue pure des
dépendances, reproduite indépendamment, rejette aussi deux témoins altérés :
plan modifié utilisé par une p-curve et modification d'un champ de sommet.

Ce résultat explique **pourquoi le test d'identité binaire stricte refusait
ces deux faces**. Il ne démontre pas la cause des avertissements `CUT`, ne
modifie aucun octet de CAO et ne qualifie pas toute la partition. Les caches
ou champs non sérialisés, une autre architecture et la précision physique ne
font pas partie de cette preuve. Les refus historiques sont conservés.

Durées : 0,450 s natives / 0,995 s nettoyage compris, sorties 2 ; revue du
graphe sans nouvel appel natif. Entrées inchangées, conteneur exact supprimé,
absence revérifiée. Aucun nouveau `CUT`, maillage ou solveur physique lancé.

### Nouveau résultat du 8 septembre : huit faces, deux groupes de rôles résolus

Le domaine `fab1338a…`, la partition `c9eceb77…` et leur manifeste gelé sont
relus sans nouvelle opération géométrique. Les deux groupes plans mixtes sont
retrouvés dans les inventaires natifs, puis chaque face candidate est comparée
à **toutes** les faces source de son groupe : `5² + 3² = 34` comparaisons.
Huit appariements uniques réussissent et **26 appariements croisés sont
refusés** ; ces derniers ne sont pas des défauts de la partition.

Les huit réussites portent sur les **octets complets de chaque face chargée,
BinTools VERSION_3**, contours et tolérances compris, avec contrôle séparé du
placement racine exact, de l'orientation et de l'empreinte du support.
**Aucune exclusion de donnée auxiliaire n'est nécessaire ici.** Un même plan,
une aire, un centre ou un numéro identique ne suffit pas à l'appariement.
L'égalité des numéros ci-dessous est un résultat, pas une hypothèse.

| Groupe | Face candidate | Face source | Rôle source transféré |
| --- | ---: | ---: | --- |
| 2 | 2 | 2 | `walls_chamber` |
| 2 | 3 | 3 | `walls_seat` |
| 2 | 4 | 4 | `walls_chamber` |
| 2 | 9 | 9 | `walls_seat` |
| 2 | 15 | 15 | `walls_chamber` |
| 3 | 5 | 5 | `walls_chamber` |
| 3 | 6 | 6 | `walls_seat` |
| 3 | 14 | 14 | `walls_seat` |

Une contre-lecture vérifie l'unicité et l'exhaustivité des lignes et des
comparaisons, ainsi que les rôles dans le manifeste relu et rehaché séparément.
Cette vérification couvre une limite connue du superviseur : sa conversion
en dictionnaires/ensembles ne rejetterait pas à elle seule des doublons
fabriqués dans un reçu. Aucun doublon n'existe dans le reçu natif obtenu ;
le programme exécuté reste gelé, sans correction rétroactive.

Durées : **0,614 s natives / 1,214 s nettoyage compris**, sorties 2 prévues
pour conserver les autres refus. Plafonds effectifs 2 CPU/4 Gio, budget total
120 s dont 30 s réservées au nettoyage ; sans OOM ni expiration, sans mesure
de mémoire de pointe. Entrées, sources et objets chargés inchangés ; conteneur
supprimé, absence vérifiée indépendamment. Les **11 tests ciblés passent**.
Le contrôle logiciel global `make check` termine aussi avec le code 0 ;
ses tests natifs optionnels ignorés ne constituent pas une validation de pièce.
Les empreintes complètes des huit paires, du rapport `625be76c…`, du processus
`50b3d0e6…` et de la contre-lecture `d1e997de…` figurent dans la
[capsule de preuves](../twins/m64-cylinder-head/evidence/geometry-checkpoint-20260908.json).

Ce résultat transfère des étiquettes source existantes, sans nouvelle
validation physique. Les huit correspondances sont des faces entières :
aucune preuve générale de couverture de faces subdivisées n'est extrapolée.
Les `CUT` avertis et le refus volumique restent enregistrés et inchangés.
Aucun `CUT`, `Common`, GK, BRep, maillage ou solveur supplémentaire n'est produit.

Les lots booléens Kali enregistrent une valeur `FuzzyValue()` effective
de `1e−7` unité scan, pour une demande à zéro. OCCT impose un plancher dans
[`SetFuzzyValue`](https://github.com/Open-Cascade-SAS/OCCT/blob/V7_9_3/src/BOPAlgo/BOPAlgo_Options.cxx).
Ils ne sont donc pas décrits comme des opérations booléennes en arithmétique
exacte ou à tolérance effective nulle. Cela ne modifie pas les tolérances
stockées dans les entrées.

### Registre dérivé des 124 rôles extérieurs du gaz

Un traitement JSON sans nouvel appel natif relie les reçus précédents :
113 faces par couverture bidirectionnelle de groupes mono-rôle, huit par
identité complète, deux par identité du sous-graphe définissant les faces
28/29 et une par empreinte entière et placement exact de la face 35.
Le registre `ebd58991…` couvre une fois chacune des 124 faces externes des
52 groupes, avec un seul propriétaire ; les 32 faces internes en sont exclues.
La racine a réexécuté ce traitement et retrouvé exactement le même registre.
Les rôles proposés antérieurement pour la source sont transférés, pas validés
physiquement. Ni les avertissements du groupe 17 ni le refus volumique ne sont
réécrits. Aucun nouveau calcul de couverture ou de volume n'est lancé.

### Premier maillage diagnostic du solide V5

Le fichier `450ba081…` est relu dans OCP 7.9.3.1 puis transmis à Gmsh 4.15.2
par un BRep ASCII V3 privé. L'empreinte de la racine est contrôlée **avant**
extraction de son unique solide ; les deux empreintes restent distinctes.
Le pont relu est BRep valide : un solide, une coque, 4 900 faces.
La conversion attribue 118 octets différents dans le pont ASCII et 101 dans
la relecture de l'export Gmsh, notamment des repères, sommets, intervalles et
caches UV. Ces comptes ne sont pas une distance géométrique.

L'essai est explicitement autorisé comme **diagnostic d'import non qualifié** :
comparaison géométrique globale `false`, borne spatiale cumulée `null`, aucune
autorisation CAE ou fabrication. Cela ne réduit pas le budget géométrique
`1e−9` et ne le déclare pas respecté. Avant génération, la réimportation
reproduit exactement le BRep exporté et l'inventaire Gmsh examinés. Le fichier
V5 original reste intact ; aucune réparation intentionnelle, décimation ou
réutilisation d'anciens groupes anatomiques n'est appliquée.

| Contrôle du maillage `763a2ad9…` | Résultat |
| --- | --- |
| Éléments / nœuds / triangles frontières | 271 001 / 65 735 / 91 300 |
| Connexité et frontière | Une composante, frontière complète, aucune face CAO sans triangles |
| Jacobiennes et volumes signés | Tous strictement positifs |
| Qualité `minSICN ≥ 0,1` | **Refus : 4 871 éléments (1,7974 %), minimum 0,0000406853** |
| Écart de volume au BRep importé | 0,24615 %, sous le seuil grossier de 1 % |
| Relecture MSH | Tags et connectivité conservés ; qualité toujours refusée |

Le contrôle composite `mesh_export_roundtrip=false` inclut le critère de
qualité : ce n'est pas une corruption du fichier. L'écart maximal de coordonnées
après relecture est `5,7396e−14` unité scan. Les 4 871 éléments trop déformés
comprennent 2 916 éléments adjacents à une face frontière et 1 955 sans face
frontière ; leur localisation privée ne leur attribue pas un rôle anatomique.

Une projection de 46 583 centroïdes de triangles sur leurs supports Gmsh
donne un maximum de **0,38760 unité scan**. C'est un diagnostic échantillonné,
pas une borne sur toutes les facettes, une preuve d'appartenance aux contours
de découpe ou une tolérance d'usinage. Le contrôle du helper après maillage
porte sur entités, volume et descripteurs, pas sur une identité BRep complète.

Un seul essai : 9,333 s pour les trois stades d'import et 27,440 s pour le
maillage, nettoyage compris, soit 36,773 s cumulées. Plafond 4 CPU/4 Gio sans
swap supplémentaire, 1 200 s cumulées dont 60 s de réserve, stade maillage
limité à 600 s. Le producteur configure deux threads de maillage ; quatre CPU
sont une limite du conteneur, pas une mesure d'utilisation. Sorties d'import 0,
maillage 2 attendu, sans OOM ; les quatre conteneurs ont été supprimés et leur
absence revérifiée. Huit tests purs du wrapper et 21 du producteur passent.
Aucune nouvelle dépense Vast, charge moteur, simulation thermique ou mécanique.

## Suite et périmètre d'exécution

Priorités : établir la décision d'admission à partir des preuves distinctes
de représentation, de frontières et du registre des 124 rôles ; conclure la
couverture et le bilan de volumes avant admission du domaine gazeux.
Pour le solide, exploiter la localisation des 4 871 éléments trop déformés
pour choisir une correction de maillage ciblée, puis recontrôler frontière,
qualité et conformité CAO. Ne pas retoucher la silhouette pour masquer ces
défauts numériques. L'attribution des
quatre octets auxiliaires est terminée : elle n'appelle ni nouvelle correction
de ces faces ni répétition de leur test binaire strict.
Le BOP du candidat et le lot des 136 paires n'ont pas à être relancés sur les
mêmes entrées inchangées. Les contacts de
sièges, l'assemblage complet, les parois, la thermique, la résistance et le
procédé LPBF restent des contrôles distincts. Aucune puissance de 700 ch ni
aucune aptitude à la fabrication ne sont démontrées par ces diagnostics.

```mermaid
flowchart LR
    A[Corps V5 sauvegardé] --> B[5 modes BOP réussis]
    A --> C[Écarts attribués sur Linux et Mac]
    C --> D[Borne locale calculée<br/>Équivalence globale à conclure]
    A --> J[Maillage solide diagnostic<br/>271 001 tétraèdres]
    J --> K[Qualité refusée<br/>4 871 éléments à traiter]
    E[Partition du gaz] --> F[136 paires sans recouvrement détecté]
    E --> G[102 CUT réussis sur 104<br/>Preuves complémentaires liées<br/>124 rôles source tracés]
    G --> H[Admission globale encore refusée<br/>Couverture et volumes à conclure]
    H --> I[Maillage puis calculs physiques]
```

Les essais utilisent Kali et l'image OCP existants, sans réseau dans les
conteneurs et avec sources/entrées en lecture seule. Les budgets sont
respectivement 90 s/2 Gio pour les supports, 60 s/2 Gio pour chaque témoin,
300 s/4 Gio pour les guides et 90 s/4 Gio pour la partition, avec deux CPU et
le même plafond pour RAM et RAM+swap. Les réintégrations sont bornées à
300 s/4 Gio, les audits du gaz à 150 s/4 Gio et le BOP indépendant à
240 s au total/4 Gio, toujours deux CPU.
Aucun OOM ni timeout pour ces essais Kali ; conteneurs exacts
supprimés et absence vérifiée. Aucune nouvelle dépense Vast pour ce lot.
