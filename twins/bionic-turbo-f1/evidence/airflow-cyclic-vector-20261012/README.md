# Traces vectorielles cycliques et lecture locale du stator

Ce contrôle complète 047/048 avec des champs manufacturés non nuls. Il ne
lance aucun solveur d'écoulement et ne modifie aucun ancien cas, aucune
pièce ou paroi du turbo réel. Les cas 049 et 050 dérivent du maillage 047,
qui contient 12 480 cellules et deux coupes cycliques de 80 faces chacune.

## Vérification native des traces

Trois champs constants égaux aux vecteurs de base et un champ variable
identifiant les cellules sont écrits, sans dimension physique. Le champ
variable dépend du label natif selon trois composantes distinctes.
Le post-traitement natif produit les centres C/Cx/Cy/Cz. Le convertisseur
foamToVTK exporte les valeurs de frontière, puis séparément les valeurs
des cellules propriétaires avec nearCellValue. Les 80 faces de chaque
patch sont relues ; leurs identifiants de patch sont contrôlés.

Le lecteur calcule indépendamment la trace attendue : interpolation entre
la valeur propriétaire et la valeur voisine tournée de ±2π/128, avec les
poids obtenus des centres natifs et des distances normales à la face.
Les poids sont voisins de 0,5 à 1,4e-13 près. Les centres et leurs trois
composantes sont relus et concordants sur les 12 480 cellules. Les valeurs
exportées des propriétaires vérifient aussi l'adressage du champ variable.

Le critère déclaré avant le calcul vaut huit fois l'epsilon Float32,
multiplié par max(1, composante attendue maximale). Il concerne uniquement
la lecture des traces VTK ; les seuils de repos de 048 restent inchangés.

049 écrit du VTK ASCII avec une précision décimale insuffisante : le champ
variable dépasse ce critère sur les deux patches, erreur de trace jusqu'à
5,023e-6 et erreur propriétaire 5,052e-6. Ce refus est conservé. Les sorties
montrent six chiffres significatifs, malgré writePrecision16 dans le cas.
Il ne s'agit pas d'une divergence d'écoulement puisqu'aucun solveur ne tourne.

050 change uniquement l'encodage des deux exports : VTK binaire Float32.
Les entrées préparées sont identiques octet pour octet à 049 et le critère
ne change pas. Les huit comparaisons réussissent : erreur maximale
2,657e-8 pour les vecteurs transverses, zéro pour le vecteur axial,
1,190e-7 pour le champ variable. Les valeurs propriétaires concordent à
1,180e-7. Le même lecteur gère les deux formats.

L'absence de rotation donne des écarts allant jusqu'à 0,07426 sur le champ
variable, et une rotation inversée jusqu'à 0,14670. Ces contrôles négatifs
sont rejetés à plus de cent fois la tolérance ; un champ nul ou uniquement
axial ne permettrait pas cette distinction.

La [source officielle v2406](https://gitlab.com/openfoam/core/openfoam/-/raw/OpenFOAM-v2406/src/finiteVolume/fields/fvPatchFields/constraint/cyclic/cyclicFvPatchField.C)
est référencée avec son empreinte. Aucun code OpenFOAM n'est modifié.
La portée est la trace vectorielle interpolée par le champ cyclique natif ;
ce test ne qualifie pas indépendamment les contributions de couplage à la
matrice, la convergence linéaire ou la stabilité d'une perturbation.

## Stator : distinguer position et orientation

La lecture en mémoire bornée des parois de 033 est reproduite après
vérification de toutes ses empreintes. Sur 121 288 faces stator, 18 882
ont un propriétaire tournant. La somme absolue géométrique de flux de
repère est 8,9933752e-5 m³/s ; ce n'est pas un débit d'air.
La pire normale de rotation vaut 43,1723444 m/s sur la face 6650409,
cellule propriétaire 375513. Son centre de face, calculé par la formule
polygonale native, est (0,749573675 ; -4,122655214 ; -3,6875) mm.
Ce n'est pas un centre volumique de cellule.

Le STL CFD exact est relu et son empreinte vérifiée. Une recherche utilise
les distances minimales aux boîtes de toutes les 1 540 619 facettes stator,
puis les distances exactes aux triangles restant dans une borne supérieure
connue. Deux triangles doivent être examinés. Le triangle 716705 est le
plus proche du seul point étudié : distance 0,000439899113 mm. Ses sommets,
le point projeté et sa normale sont sauvegardés. La composante normale de
rotation en ce point source vaut 1,9877568 m/s ; son orientation diffère
fortement de celle de la face du maillage rejeté.

Cette comparaison ne borne ni l'écart de toute la face ni celui de toute
la paroi. Une distance ponctuelle faible ne certifie pas l'orientation,
le jeu euclidien/thermique ou la qualité du maillage. Le maillage 033 est
sans projection et reste rejeté. Le résultat ne prouve pas qu'il faut
retirer toutes les parois fixes de MRF, ni une cause unique de dérive.

## Vérification et conservation

108 tests turbo réussissent et un est ignoré. make check exécute
3 850 tests, avec 172 ignorés, les deux échecs flottants et trois erreurs
rtree/networkx hors turbo déjà connus.

Tous les champs, exports VTK, journaux, entrées et reçus sont conservés.
Les deux conteneurs terminent avec code zéro, sans OOM. Aucun solveur
physique n'est lancé, aucune performance du turbo n'est validée.
Les règles de rotation et le lecteur VTK ont des tests dédiés, comprenant
un fichier binaire tronqué refusé et une rotation distincte de son inverse.

[Archive native 049–050](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-cyclic-vector-2026-10-12) : 78 fichiers,
1183629 octets ; SHA-256
`f425525ae6a4214507db37ab7b92257d849462105d1fb2a3e2c1063ec3e432c7`.
Tous les payloads du TAR sont relus localement. Les cinq actifs GitHub
sont vérifiés par tailles et SHA-256 distants, sans second téléchargement
intégral revendiqué. Les champs manufacturés sont sans dimension et ne
représentent pas une vitesse physique.
