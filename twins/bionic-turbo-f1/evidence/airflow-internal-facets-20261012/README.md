# Faces intérieures et bilan de rotation — 040/041 rejetés

La cartographie du vrai maillage 033 et deux nouveaux témoins locaux montrent
que la tangence MRF, la fermeture du bilan de rotation et la qualité des
cellules sont trois contrôles distincts. Aucun solveur n'a été lancé sur 040
ou 041 ; les deux maillages sont rejetés. Les anciennes preuves restent intactes.

## Cartographie du turbo 033, en lecture seule

Les 6 747 117 faces et 2 127 165 cellules natives ont été relues après
vérification de toutes les empreintes du reçu. 1 775 143 cellules sont
rotatives. Le lecteur par lots utilise la formule polygonale déjà épinglée ;
un test indépendant la compare à cette formule sur des triangles et des
polygones gauchis de trois à neuf sommets.

Le maximum du résidu géométrique de rotation est 7,2967236e-11 m³/s dans
une cellule tournante **hors interface**, notamment la cellule 138890,
au milieu de boîte (−19,6716034 ; −18,7388571 ; 4,3902778) mm. Ce point
n'est pas un centre volumique natif. Le défaut de planéité atteint
7,8173166e-7 m à l'intérieur et 1,7128186e-7 m sur la frontière.
Les 12 416 faces MRF restent planes mais non tangentes : 4,1119223 m/s.
La fermeture des vecteurs d'aire par cellule est de 3,3952e-21 m² au maximum.
Ces flux sont géométriques, pas des débits d'air ; 033 reste rejeté.

## 040 : subdiviser seulement les faces gauchies

040 reprend le témoin 035. Aucun point ne bouge. Les 12 288 faces de paroi,
les 5 120 quadrilatères MRF, les cellules et leur zone sont conservés.
20 480 faces intérieures gauchies sont découpées selon une diagonale commune
aux deux cellules adjacentes. Les faces protégées restent intactes ; la
numérotation des patches est adaptée. Le seuil de planéité de 1e-14 m sert
uniquement à choisir le découpage, sans changer un critère natif.

Le maillage compte 20 480 cellules et 88 064 faces. Le bilan géométrique
maximal en cellule tournante passe de 1,2572946e-11 à 1,1726112e-20 m³/s.
Toutes les faces sont planes à 6,237e-17 m. La normale MRF reste
3,1690206e-12 m/s. La frontière est exactement identique.

Mais `checkMesh -allTopology -allGeometry` rejette **17 920 cellules
concaves**. Il signale aussi des cellules voisines partageant plusieurs
faces et 40 960 faces non ordonnées dans son diagnostic détaillé.
La sortie native zéro (0,620 s) ne vaut pas admission. Aucun test de repos
n'est autorisé sur ce maillage.

## 041 : subdiviser les cellules autour d'un point intérieur

041 reprend les faces planes de 040. Chaque cellule est divisée en huit
volumes, tétraédriques ou pyramidaux, reliant une face à la moyenne de ses
sommets. Le préparateur refuse un centre hors du noyau géométrique, une base
non plane ou une chaîne d'arêtes non fermée. Les faces entre les nouvelles
cellules sont partagées, orientées et ordonnées ; les labels de zone et les
ensembles de cellules sont remappés. Les anciens diagnostics de faces sont
conservés hors du maillage actif, avec la copie complète du parent.

Les 26 880 points d'origine, les faces de paroi et les quadrilatères MRF
restent identiques. 20 480 points intérieurs sont ajoutés. Le maillage a
163 840 cellules, dont 81 920 tournantes, et 374 784 faces. Le volume de
frontière relu vaut exactement le même nombre que pour 035,
1,6210567639956897e-7 m³. Les fichiers des équations et champs initiaux
sont identiques. Le résidu géométrique maximal descend à 1,1434945e-20 m³/s.

La concavité est éliminée, mais le contrôle natif rejette **61 440 cellules
avec un déterminant inférieur à 0,001** ; minimum 0,0001356918.
143 360 faces dépassent 70° de non-orthogonalité, maximum 82,0556° ; cet
avertissement est conservé même si ce contrôle seul n'entraîne pas le rejet.
Sortie native zéro, 2,015 s, sans solveur. La subdivision augmente ici le
nombre de cellules par huit et ne donne pas une recette admissible.

## Reproduction, conservation et suite

Les préparateurs, le lecteur de 033, le lecteur des deux témoins, les entrées,
les journaux et les reçus sont conservés. Les fichiers natifs de points,
faces, propriétaires, voisins et zones sont relus. `readback.json` atteste
la conservation de la frontière, de l'interface et des champs initiaux ;
aucun champ d'écoulement final n'existe puisqu'aucun solveur n'a été lancé.
Les conteneurs sont terminés et conservés, sans dépassement mémoire.

La suite doit traiter la forme des sous-cellules et préserver les mêmes
preuves de frontière et de tangence. Une étude locale de l'anisotropie et
d'une subdivision dirigée est nécessaire avant toute nouvelle reconstruction
complète. Ne pas réutiliser 041 comme entrée de solveur, ne pas abaisser
le déterminant minimal et ne pas appliquer la subdivision à 033 en bloc.
La séparation roue–écrou rétablie dans 033 reste à préserver. Aucun gain de
débit ou puissance, convergence, indépendance au maillage ou jumeau calibré
n'est validé.

## Archive native

[Archive 040–041](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-internal-facets-2026-10-12) :
79 fichiers, 7 099 187 octets, SHA-256
`8fbe73c814a9a612596d1b21383000fe829927a77c588c9d84ff69f3e7f7b1f2`.
Tous les payloads sont relus localement ; les tailles et SHA-256 des cinq
actifs distants sont vérifiés. Aucun second téléchargement distant intégral
n'est revendiqué. Les données complètes de 033 restent dans son archive
antérieure ; seule sa nouvelle cartographie est ajoutée ici.
