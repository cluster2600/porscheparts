# M64 — contacts de guides et préparation géométrique

**Les contacts nominaux des quatre guides CAO sont mesurés ; la rétention à
chaud et la fabrication ne sont pas qualifiées.** Le corps `21c9c40b…` reste
inchangé. L'extraction des supports de courbes passe, mais leur réintégration
dans un BRep n'est pas encore exécutée. La partition du domaine gazeux est
refusée sur son bilan de volumes ; aucun nouveau maillage n'est produit.

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

## Courbes : restriction exacte réussie, correction du corps non exécutée

Les six supports existants des deux arêtes signalées C0 sont divisés en quinze
supports : cinq courbes 3D et dix p-curves. Pour ces B-splines non rationnelles,
les identités polynomiales sont contrôlées en arithmétique rationnelle sur
chaque intervalle ; les coefficients sont réassemblés exactement. Les quinze
supports construits dans OCP sont au moins C1 à l'intérieur de leur domaine.
Les 495 comparaisons supplémentaires de points natifs donnent un écart nul ;
cet échantillonnage n'est pas, à lui seul, la preuve globale.

Les discontinuités de tangente initiales restent aux jonctions. Il ne s'agit
pas d'un lissage. Aucun corps BRep n'est lu ou écrit pendant cet essai de
supports de 0,613 s. Le prochain essai devra réintégrer les segments dans une
copie topologique et contrôler le corps complet, sans changer les surfaces.
L'ancien refus de réduction de multiplicité reste distinct et conservé.

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
avec cinq checkpoints. Sa relecture indépendante et le non-recouvrement des
solides restent à contrôler. Aucun maillage ni solveur lancé ; le refus
non adaptatif reste actif. Sources et entrées inchangées, conteneur exact
supprimé et absence revérifiée hors du lanceur.

## Suite et périmètre d'exécution

Priorités : réintégrer et contrôler les arêtes, expliquer le refus du bilan de
volumes, puis mailler le domaine avec ses groupes physiques. Les contacts de
sièges, l'assemblage complet, les parois, la thermique, la résistance et le
procédé LPBF restent des contrôles distincts. Aucune puissance de 700 ch ni
aucune aptitude à la fabrication ne sont démontrées par ces diagnostics.

Les essais utilisent Kali et l'image OCP existants, sans réseau dans les
conteneurs et avec sources/entrées en lecture seule. Les budgets sont
respectivement 90 s/2 Gio pour les supports, 60 s/2 Gio pour chaque témoin,
300 s/4 Gio pour les guides et 90 s/4 Gio pour la partition, avec deux CPU et
le même plafond pour RAM et RAM+swap. Aucun OOM ni timeout ; conteneurs exacts
supprimés et absence vérifiée. Aucune nouvelle dépense Vast pour ce lot.
