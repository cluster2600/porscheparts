# Raccord natif de la couronne — 065 à 067

La séparation puis le réassemblage natifs de la couronne 063 conservent toutes
ses cellules, les coordonnées décodées, les faces orientées et leurs paires
propriétaire/voisin, ainsi que la zone tournante. Le cas final 067 passe le
contrôle natif étendu. Aucun solveur d'écoulement n'est lancé.

Ce contrôle porte sur le raccord entre les deux régions existantes du témoin,
à son interface MRF. Il ne construit pas le cœur autour des pales. Aucun
traitement des surfaces physiques n'intervient entre séparation et raccord.
Les parois latérales et avant restent synthétiques ; rotor et ports absents.

## Opérations et refus conservé

- **065** : `splitMeshRegions -cellZones -overwrite` sur une copie de 063.
  Deux régions : 20 352 cellules tournantes et 6 784 fixes. Leurs 6 784 faces
  communes sont dupliquées en patches ; les cartes natives conservent les
  parentés de points, faces signées et cellules. Fin zéro, sans OOM, 0,609 s.
- **066** : `mergeMeshes`, puis `stitchMesh -perfect -overwrite` sur deux
  copies des régions 065. Le maillage intermédiaire fusionné est conservé.
  La réunion termine, mais `checkMesh` s'arrête avec le code 1 : les deux
  patches `mappedWall` devenus vides référencent encore `domain1`. Les contrôles
  géométriques imprimés avant cette erreur ne constituent pas une admission.
  Cas conservé et refusé, 1,271 s, sans OOM.
- **067** : nouvelle copie de 066, `createPatch -overwrite` avec
  `pointSync false; patches ();`, puis contrôle étendu. Cette opération native
  retire les patches vides obsolètes. Points, faces, owner/neighbour et labels
  de zone sont identiques à 066 après lecture. Fin zéro, sans OOM, 0,888 s.

## Vérification indépendante

`compare_topology.py` vérifie tous les payloads des quatre cas 063/065/066/067.
Chaque cellule source apparaît une seule fois dans 065 ; chaque face commune
apparaît exactement deux fois, toutes les autres une fois. Les cartes natives
reproduisent les cycles orientés de sommets et les cellules parentes.

Une bijection géométrique puis topologique indépendante retrouve toutes les
27 136 cellules et 81 920 faces dans 067, sans trou, double paroi ni modification
de voisinage. Les coordonnées décodées de 065 et 067 sont exactement celles du
parent natif 063 après appariement. Cette égalité numérique n'affirme pas
l'identité octet pour octet des fichiers renumérotés.

`read_geometry.py` réutilise le lecteur de 063 dans une nouvelle version :
27 648 points, 21 376 faces de frontière, 6 784 quadrilatères MRF,
20 352 prismes tournants et 6 784 hexaèdres fixes. Arêtes orientées fermées par
cellule, volumes positifs, positions vérifiées contre 062. Volume indépendant
4,611377236219329e−6 m³ ; intégrale analytique concordante. Planéité maximale
1,44199e−17 m ; normale géométrique de rotation maximale 2,28795e−12 m/s ;
bilan géométrique maximal par cellule tournante 1,49078e−19 m³/s.
Ces métriques ne sont pas des débits d'air.

067 : `Mesh OK`, une région, aucune concavité ni petit déterminant ; déterminant
minimal 0,03808565604766382, non-orthogonalité maximale 47,8173518952406°.
Le volume natif imprimé vaut 4,611377236219304e−6 m³.

## Limites et prochaine étape

Le source officiel v2406 de `perfectInterface` utilise une tolérance de
0,001 fois l'arête minimale pour apparier points et centres. Le mot `perfect`
ne prouve donc pas une égalité exacte ; la comparaison indépendante ci-dessus
est nécessaire. Sources de séparation, fusion, raccord et nettoyage hachées.

La lecture de `snappySnapDriver` et `makeDisplacementField` montre que les
patches non adaptés commencent avec un déplacement de type `slip`, pas une
immobilisation générale. Ce n'est ni une preuve de mouvement effectif ni une
condition physique d'écoulement. Il reste à préserver les faces latérales
pendant le maillage des sous-domaines physiques, puis à prouver leur raccord.

Pas de nouveau contrôle au repos : le résultat 064 reste attaché au parent,
sans qualification de convergence linéaire. Aucun gain de débit ou puissance,
aucune stabilité de perturbations ni calibration de jumeau n'est démontré.
Les preuves antérieures, y compris les rejets, restent immuables.

## Archive

L'[archive 065–067](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-collar-coupling-2026-10-12)
contient 147 fichiers, 6 160 422 octets, SHA-256
`5e5c369bf323c4e06e614015677f9fa8f68f215e93d0c4ef513fd3e7705dd0a7`.
Les cinq actifs GitHub sont vérifiés par tailles et digests. Tous les payloads
sont relus localement ; aucun second téléchargement distant intégral n'est
revendiqué. Les trois conteneurs et les sources antérieures sont conservés.
