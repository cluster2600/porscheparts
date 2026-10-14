# Raccord prismatique dans la zone tournante — 060 et 061

060 place la transition conforme dans MRF : 3 840 prismes tournants et
1 280 hexaèdres fixes. Le témoin extérieur 058 avait la disposition
inverse. Les équations et critères ne changent pas ; ces deux domaines
synthétiques ne sont toutefois pas identiques et ne contiennent aucune
pale, pièce ou entrée/sortie du turbo.

## Construction et admission

La section reste homothétique : R(z) = 32 mm + 0,4 (z − 6 mm), entre
z = 6 et 7 mm, dix intervalles ; rapports radiaux 63/64, 1 et 33/32.
Le nouvel anneau intérieur a 256 secteurs, l'interface et l'anneau extérieur
128. Dans chaque secteur, trois triangles extrudés relient les deux
arêtes fines intérieures à l'arête grossière MRF. blockMesh emploie les
hexaèdres dégénérés avec fermetures encodées comme dans la correction 058.
Aucun mailleur général ni solveur natif n'est modifié.

La facettisation des parois intérieure et extérieure diffère de 058.
Le volume vaut 3,066901565878825e-7 m³, contre 3,086839304608924e-7 m³
pour 058. Il ne faut donc pas présenter l'essai comme une permutation de
zones sur un domaine strictement identique ou comme une amélioration de
performance à géométrie physique constante.

060 termine en 5,316 s, code zéro sans OOM. CheckMesh donne Mesh OK :
5 120 cellules, 5 632 points, 15 872 faces, une région fluide ; aucun
petit déterminant ni concavité. Déterminant minimal 0,002328585925,
non-orthogonalité maximale 43,6074°, critères natifs inchangés.

La lecture indépendante apparie tous les points, retrouve toutes les
4 864 faces de paroi construites et les 1 280 quadrilatères MRF, ferme
les chaînes d'arêtes de chaque cellule et vérifie leurs volumes positifs.
L'intégrale analytique donne 3,066901565878826e-7 m³. Le lecteur v2 ajoute
le contrôle des types par zone : toutes les cellules tournantes ont deux
faces triangulaires et trois quadrilatères, toutes les cellules fixes six
quadrilatères. Les deux versions et leurs sorties sont conservées.

Les 1 280 quadrilatères MRF ont exactement les mêmes coordonnées natives
que dans 058, après réindexation des faces. Normale géométrique de rotation
maximale 2,8635e-12 m/s ; planéité maximale de toutes les faces 1,2773e-17 m.
Bilan géométrique maximal de rotation dans les cellules tournantes :
2,3717e-20 m³/s. Aucun de ces flux n'est un débit physique d'air.

## Contrôle de repos

061 réutilise le maillage 060 et les mêmes entrées physiques et numériques
que 059, y compris la déclaration empty de zéro face. compare_inputs.py
vérifie les empreintes : seules cinq listes natives du maillage changent
(points, faces, owner, neighbour, cellZones). Les entrées initiales,
conditions aux limites, thermodynamique, schémas, pas, tolérances et critères
sont identiques octet pour octet hors maillage.

Le contrôle est borné à 1 200 s, un CPU, 2 Gio, sans réseau, 200 pas de
0,1 µs jusqu'à 20 µs. Les critères restent 0,001 Pa, 1e-6 K et 1e-8 m/s.
Le solveur termine en 169,348 s, code zéro sans OOM. Les 200 pas
respectent les seuils : erreur p 8,8767e-10 Pa, T 4,3769e-12 K et vitesse
maximale 4,4377e-12 m/s. Les champs finaux p/T/U des 5 120 cellules sont
relus et finis ; la vitesse maximale finale égale le maximum historique.
Le Courant maximal vaut 0,0860192.

Les 800 résolutions de pression atteignent encore 1 000 itérations :
le repos est respecté, mais aucune convergence linéaire n’est qualifiée.
Ce résultat complète le contrôle des hexaèdres tournants 059 par celui
de prismes tournants ; il ne qualifie pas toutes les topologies adaptées.

Ce témoin ne certifie pas le passage du vrai turbo. La géométrie
homothétique, ses fermetures et ses marges restent à vérifier contre les
surfaces et bandes sources ; le jeu roue–écrou et les pièces sont intacts.
Ni stabilité de perturbation, indépendance au maillage/temps, comparaison
de puissance ou débit maximal, ni calibration physique n'est établie.

[Archive native](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-inner-transition-2026-10-12) : 63 fichiers, 1141087 octets, SHA-256 `d11435a68055a9bc5543d56995654bfbcb412584667ac6072faedd8e2865f80a`. Les payloads sont relus localement ; les cinq actifs GitHub sont vérifiés par tailles et SHA-256, sans second téléchargement distant intégral.
