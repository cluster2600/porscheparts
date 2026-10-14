# Transition avec rangée extérieure — refus sur les angles

Une nouvelle topologie synthétique est évaluée hors natif : une rangée hexaédrique sépare les prismes de transition axiale de la paroi extérieure. Elle donne de vraies faces internes supplémentaires aux cellules de fermeture, mais reste **refusée** : 1 024 faces dépassent 70°, maximum 77,724389811°. Aucun nouveau cas natif, blockMesh, checkMesh, conteneur ou solveur. Ne pas lancer le dictionnaire candidat archivé.

## Construction prescrite avant calcul

Les trois intervalles 49–51 de 063, leurs stations, rayons et ruptures de pente sont ceux du témoin staged-transition publié par PR227. Même frontière intérieure, extérieure et mêmes deux extrémités ; aucune extension ni suppression de fermeture. La région tournante et le raccord angulaire fixe restent inchangés. La moitié extérieure fixe est maintenant partagée en deux : un quart pour les prismes axiaux, un quart pour les hex. Le ratio ajouté est `1 + 3*(q_ext−1)/4` ; la répartition moitié–quart–quart reprend le motif de bisection extérieure de086, appliqué ici à la section homothétique non projetée. Elle ne reproduit pas les coordonnées gauchies de086.

Ce choix unique figure dans preflight.md avant évaluation. Aucun autre ratio ou résolution essayé. Les hex sont partagés avec les prismes sur chaque demi-station axiale et sur les 256 secteurs angulaires. La diminution de largeur des prismes était explicitement identifiée comme susceptible de dégrader leurs angles. Aucun seuil modifié.

6 144 cellules : 1 152 prismes tournants, 1 152 prismes angulaires fixes, 2 304 prismes axiaux fixes et 1 536 hex fixes. 6 144 points, 13 696 faces internes, 4 864 frontières, 384 quads MRF et 768 quads entre transitions angulaire/axiale. Les cycles partagés sont opposés, les arêtes annulées par cellule et les volumes calculés positifs. Volume 1,352515682172014e−7 m³, concordant avec l'intégrale analytique polygonale et le témoin précédent à l'arrondi. La concordance de volumes seule n'est pas une preuve complète d'absence d'intersections.

## Frontières vérifiées indépendamment

Les 4 352 anciens points ont des coordonnées décodées exactement conservées après réindexation. Les 2 304 faces latérales, leurs cycles orientés et les 384 quads MRF sont exacts. Les 2 048 faces des deux fermetures deviennent 2 560 : 1 536 intactes et 512 divisées en deux. Les 512 nouveaux points de fermeture sont des milieux d'arêtes parentes uniques, écart maximal 6,993e−18 m. Le lecteur vérifie planéité, convexité des parents, inclusion des faces descendantes et annulation orientée des arêtes intérieures. Il n'utilise pas l'égalité des volumes comme preuve de couverture.

La paroi extérieure reste celle du témoin synthétique PR227 à 256 secteurs, pas celle de063 à 128 secteurs ni celle projetée de086/091. Rotor et ports physiques absents. Aucun changement de pièce ou de connexion réelle.

## Refus et voisinage

Tous les déterminants calculés passent 0,001 ; minimum 0,001270423231. Les 512 rôles de cellules auparavant refusés ont chacun quatre faces internes contributrices, contre trois auparavant. Cette correspondance porte sur les rôles du stencil ; elle n'est pas une carte de parenté géométrique ou de remappage de champs, puisque les prismes axiaux changent de forme.

Aucun critère de plans >−1e−6. Toutefois, 1 024 faces entre prismes axiaux dépassent 70° : 512 dans chacun des deux premiers intervalles. Maximum 77,724389811°. Pour la pire paire de centres volumiques (cellules3182/3184), séparation normale58,521600µm et tangentielle268,954300µm. Tous les tuples d'angles sont dans angles.csv ; centres, face et normale détaillés dans worst-angle.json. La relation tangentielle <= tan(70°) × normale positive est une contrainte sur la géométrie réelle des cellules, pas une permission de déplacer indépendamment leurs centres ou une nouvelle dimension physique.

Planéité maximale 3,07134e−18 m, normale MRF 7,83418e−13 m/s et bilan géométrique tournant 5,42101e−20 m³/s. Pas des débits d'air. Le passage des déterminants n'efface pas le refus des angles, et ce contre-exemple ne prouve pas l'impossibilité de toute autre transition.

Le lecteur indépendant scalaire reconstruit les faces des prismes et hex, centres, volumes, déterminants, plans et angles séparément du préparateur vectorisé. Tous les payloads sources063/091 et ceux de l'archive PR227 sont vérifiés. Le premier lecteur du pire angle transmet à tort des tableaux NumPy à une fonction attendant des listes cycliques : son assertion et sa source sont conservées. La v2 corrige seulement les conteneurs des sommets, retrouve le maximum et les centres ; aucun natif rejoué.

Aucun repos, convergence linéaire, stabilité, indépendance au maillage/temps, performance CFD ou calibration qualifiés. Le refus091 et le repos incomplet084 restent inchangés.
