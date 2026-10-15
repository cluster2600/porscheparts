# Préparation d'un témoin à deux transitions prismatiques

Le domaine synthétique reprend les trois intervalles axiaux 49, 50 et 51 de 063 : celui qui contient le centre de la face diagnostique 93362 de 091, et ses voisins. Les stations, rayons et ratios intérieur/extérieur viennent exactement de construction.json de 063. Toutes les ruptures de pente présentes sont conservées. Cela ne reproduit pas les parois projetées de 086/091.

La région tournante conserve le stencil intérieur de 060/063, avec 256 secteurs intérieurs et 128 secteurs MRF. La région fixe est partagée radialement en deux parties égales par le ratio médian (1+q_ext)/2. Premier raccord : 128 vers 256 secteurs angulaires, trois triangles extrudés suivant z, stencil de 058. Second raccord : chaque intervalle axial grossier vers ses deux moitiés, trois triangles dans le plan (rayon,z) extrudés entre deux angles, 256 secteurs. Les quads entre raccords doivent être identiques, sans faces pendantes. Aucun autre ratio ou subdivision essayé.

La frontière extérieure polygonale sera différente de celle de 063, qui n'avait que 128 secteurs. Les deux fermetures sont des coupes synthétiques ; le rotor et les ports physiques sont absents. Aucun changement du vrai turbo. Ne pas appeler ce témoin une correction de 091 ou une conservation de ses faces gauchies.

Avant lancement natif : vérifier toutes les faces partagées, cycles et arêtes, centres/volumes, déterminants >=0,001, angles <=70°, critère de plans >−1e−6 non déclenché, tangence MRF <1e−8 m/s et bilan tournant <1e−16 m³/s, seuils hérités. Aucun balayage après refus. Les paramètres de blockMesh restent une cellule par bloc, grading unitaire, writePrecision16. Aucune simulation d'écoulement prévue dans cette étape.
