# M64 — contacts de guides et préparation géométrique

**Un candidat BRep avec les deux arêtes segmentées est sauvegardé, mais reste
refusé : sa resérialisation n'est pas identique.** Les contrôles de validité
avant/après relecture passent ; le contrôle BOP complet n'est pas exécuté.
Le maître `21c9c40b…` reste inchangé, sans promotion du candidat `450ba081…`.
Les contacts nominaux des guides sont mesurés, sans qualification à chaud.
La partition du gaz reste refusée : sa relecture passe les contrôles de
validité, mais frontières et non-recouvrement ne sont pas complètement audités.

Ce point suit les [contrôles de matière et de logements](M64_EXHAUST_MATERIAL_CONTROLS_20260908.md)
et la [localisation des défauts du maillage](M64_ANNULAR_MESH_LOCALISATION_20260908.md).
Les [empreintes des reçus](../twins/m64-cylinder-head/evidence/geometry-checkpoint-20260908.json)
séparent ces trois opérations et conservent les échecs. Les unités restent
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

## Suite et périmètre d'exécution

Priorités : identifier la différence de resérialisation et exécuter le contrôle
BOP du candidat conservé ; diagnostiquer les opérations de frontières, auditer
séparément le non-recouvrement et résoudre l'attribution physique et le bilan
de volumes, puis mailler le domaine. Les contacts de
sièges, l'assemblage complet, les parois, la thermique, la résistance et le
procédé LPBF restent des contrôles distincts. Aucune puissance de 700 ch ni
aucune aptitude à la fabrication ne sont démontrées par ces diagnostics.

Les essais utilisent Kali et l'image OCP existants, sans réseau dans les
conteneurs et avec sources/entrées en lecture seule. Les budgets sont
respectivement 90 s/2 Gio pour les supports, 60 s/2 Gio pour chaque témoin,
300 s/4 Gio pour les guides et 90 s/4 Gio pour la partition, avec deux CPU et
le même plafond pour RAM et RAM+swap. Les réintégrations sont bornées à
300 s/4 Gio et les audits indépendants à 150 s/4 Gio, toujours deux CPU.
Aucun OOM ni timeout pour ces essais Kali ; conteneurs exacts
supprimés et absence vérifiée. Aucune nouvelle dépense Vast pour ce lot.
