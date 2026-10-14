# Transition prismatique en deux étapes — précontrôle refusé

Une seule proposition synthétique est évaluée hors OpenFOAM, sans nouveau cas natif, conteneur ou solveur. Elle est **refusée** : 512 cellules ont un déterminant calculé inférieur au seuil inchangé de 0,001. Le dictionnaire `blockMeshDict` est une donnée candidate non exécutée. Ne pas le lancer.

## Construction bornée

Les trois intervalles 49–51 de la couronne 063 sont retenus : celui contenant le centre de la face diagnostique 93362 de 091, avec ses deux voisins immédiats. Les quatre stations et rayons sources sont conservés, y compris la rupture de pente à 32,1 mm. Le domaine s'étend de 30,538888889 à 32,55 mm. Les ratios intérieur et extérieur sont 0,98584859375 et 1,01415140625 ; le ratio médian fixe est leur demi-largeur extérieure, `(1 + q_ext)/2 = 1,007075703125`.

La région tournante reprend les trois triangles de 060/063, extrudés axialement, de 256 secteurs intérieurs à 128 sur MRF. La première moitié fixe reprend le raccord angulaire à trois triangles de 058, de 128 à 256 secteurs. La seconde moitié fixe utilise trois triangles dans la section rayon–z, extrudés angulairement : chaque intervalle axial extérieur est divisé en deux. Les 768 quadrilatères entre ces deux étapes sont partagés exactement. Aucun autre ratio, sommet ou niveau essayé.

Les 4 608 cellules sont des prismes : 1 152 tournants, 1 152 dans la transition angulaire fixe et 2 304 dans la transition axiale fixe. Il y a 4 352 points, 9 344 faces internes et 4 352 frontières. Les 384 quads MRF sont appariés aux faces exactes de 063. Ce domaine a une frontière extérieure polygonale à 256 secteurs, différente de celle de 063 à 128 secteurs. Fermetures synthétiques, rotor et ports physiques absents. Ce n'est pas une correction du maillage gauchi 086/091 ni une modification du turbo réel.

## Résultat calculé et contrôle indépendant

Les cycles partagés sont opposés et les arêtes s'annulent par cellule. Tous les volumes calculés sont positifs ; volume total 1,352515682171951e−7 m³, concordant avec l'intégrale analytique de la section polygonale. Cette concordance algébrique ne constitue pas à elle seule une preuve d'absence d'intersections.

Aucun indicateur de plans ne dépasse le critère −1e−6 ; aucun angle interne ne dépasse 70°, maximum 67,068909131°. Planéité maximale 4,05221e−18 m, normale géométrique MRF 7,83418e−13 m/s et bilan géométrique tournant 5,42101e−20 m³/s. Ce ne sont pas des débits d'air. Ces indicateurs favorables n'effacent pas le refus du déterminant.

Le minimum du déterminant est 2,541407964e−8. Les 512 cellules sous 0,001 appartiennent toutes à la transition axiale : 256 au début du premier intervalle et 256 à la fin du dernier. Chacune a trois faces internes contribuant à la formule native ; les autres faces sont des frontières non couplées. Cette localisation n'établit pas une cause unique et ne permet pas de remplacer le critère par un calcul incluant les parois. Tous les labels et leurs groupes sont dans `bad-determinants.csv`.

Le lecteur scalaire indépendant reconstruit les faces des prismes séparément des faces hex dégénérées du préparateur, vérifie les points, les cycles, les quads MRF, les volumes et les déterminants, puis les angles entre centres volumiques. Il réutilise les deux fonctions scalaires épinglées de PR226, distinctes du calcul vectorisé du préparateur. Tous les payloads sources 063 et 091 sont vérifiés avant lecture. `independent-readback.json` conserve les empreintes et résultats.

Aucun `checkMesh` natif exécuté, aucun repos, convergence linéaire, stabilité aux perturbations, indépendance maillage/temps, performance CFD ou calibration physique qualifiés. Les rejets 091 et le repos incomplet 084 restent inchangés.
