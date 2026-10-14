# Une interface protégée ne suffit pas à admettre ses transitions — 056

Le nouveau témoin conserve l'interface MRF de 038 pendant un raffinement
local axial, mais **le maillage est rejeté** : 5 888 petits déterminants et
10 240 cellules signalées concaves par le contrôle natif. Aucun solveur
d'écoulement n'est lancé. Ce témoin ne contient ni pales, ni rotor physique,
ni ports du turbo.

## Contrôle borné

Le parent 038 possède 20 480 hexaèdres et 5 120 faces MRF planes et tangentes.
Le préparateur protège les 10 240 cellules qui possèdent une de ces faces,
des deux côtés de l'interface. Seules les 10 240 autres cellules sont choisies.
`refineMesh` reçoit une seule direction globale z, sans projection de points,
sans coupure purement géométrique et sans raffinement hexagonal isotrope.
Le pas axial est divisé par deux dans ces cellules. Les critères de qualité
native, les surfaces et les équations ne sont pas retouchés.

Le contrôle est local, un CPU, 2 Gio, réseau désactivé, borne de 240 s.
Il termine en 3,556 s, code zéro sans OOM. La sortie zéro de checkMesh ne
vaut pas admission : son journal contient `Failed 2 mesh checks`.

La carte native `0/polyMesh/cellMap` est relue : chaque parent sélectionné
possède exactement deux descendants, chaque parent protégé un seul.
Il reste 20 480 hexaèdres et apparaît 10 240 polyèdres à sept faces, soit
30 720 cellules, dont 15 360 tournantes. Le maillage a 108 544 faces et une
seule région fluide. Les propriétaires et voisins de l'interface restent
issus des mêmes parents protégés.

## Interface et bilan géométrique

Les 5 120 faces MRF conservent exactement leurs ensembles de labels de
sommets. La sérialisation native à 16 chiffres arrondit les coordonnées
parentes écrites à 17 chiffres : écart maximal de composante 5,2042e-18 m,
explicitement mesuré. Les coordonnées ne sont donc pas dites identiques
octet pour octet. La normale géométrique de rotation maximale reste
1,5234e-11 m/s et la planéité maximale 3,6321e-17 m. Le bilan géométrique
maximal par cellule tournante vaut 1,7788e-20 m³/s. Ce n'est pas un débit
physique. Ces propriétés n'annulent pas le rejet du maillage.

## Parois et conservation

Les 20 480 nouveaux points correspondent chacun au milieu d'une arête
parente unique, avec écart maximal 6,3145e-18 m. Les 22 528 faces de paroi
se rattachent chacune à une facette parente : 2 048 facettes restent entières,
10 240 sont divisées en deux. Tous leurs sommets restent dans la facette
parente, à 2,6971e-17 m au plus du plan.

La version 2 du lecteur vérifie l'annulation orientée des arêtes intérieures
et l'égalité exacte de la chaîne de bord avec les arêtes parentes subdivisées.
La somme des vecteurs d'aire concorde à 1,376e-13 relatif ; le volume de
frontière est 1,6210567639956794e-7 m³. La version 1 et son rapport sont
conservés, mais son assertion de couverture fondée sur les seules aires
est retirée comme certificat : elle n'excluait pas à elle seule un
recouvrement compensé par un trou. Seule la version 2 sert à conclure sur
la subdivision. Aucune pièce réelle n'est modifiée.

## Localisation des refus

Les 5 888 cellules sous le déterminant minimal de 0,001 sont toutes des
descendantes des cellules raffinées. Le minimum est 0,000940368509363037.
Aucun seuil n'est abaissé pour accepter cette faible différence.

Les 10 240 labels de `concaveCells` appartiennent tous aux parents protégés,
devenus des polyèdres à sept faces au raccordement. La formule officielle
`primitiveMesh::checkConcaveCells` est reproduite face par face et retrouve
exactement tous les labels natifs. Elle classe aussi les paires de faces
coplanaires distinctes : critère produit normalisé > −1e-6, avec le commentaire
natif « Concave or planar face ». Les scores de ces cellules vont de
−1,913e-13 à 6,108e-13. Il ne faut donc pas traduire ces 10 240 labels en
preuve de concavité stricte de même ampleur. Leur rejet natif reste conservé.

Cette tentative établit une protection topologique de l'interface, mais
pas une transition admissible. La suite demande une transition conforme
avec des cellules de forme adaptée ; raffiner plus finement dans z ou
court-circuiter un contrôle ne résout pas ces deux refus. Ne pas appliquer
ce procédé au turbo complet. Le jeu roue–écrou de 033 et les surfaces
physiques restent à préserver dans la reconstruction future.

[Archive 056](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-protected-interface-2026-10-12) : 59 fichiers, 3 286 925 octets, SHA-256
`4e577c89244522422f993e7a0a2e17671ebe98d5194f92b151c32ac8961c1435`.
Tous les payloads natifs sont relus localement. Les cinq actifs GitHub sont
vérifiés par tailles et SHA-256 distants, sans second téléchargement intégral.
Aucun débit maximal, gain de puissance ou jumeau calibré n’est validé.
