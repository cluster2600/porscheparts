# Contraintes de tous les voisinages du témoin existant

Cette lecture complète PR230 sur les 6 144 cellules du candidat PR229, sans créer de candidat ou de maillage. Aucun natif, solveur ou changement de résolution. Les 1 024 faces refusées restent refusées. Tous les payloads du paquet PR229 sont vérifiés avant lecture.

## Moments des quatre familles

Les moments axiaux angulaires de PR230 sont réutilisés. Pour chaque triangle méridional de rayons positifs, le volume et le centre suivent les intégrales pondérées par le rayon publiées. Pour les hex de la rangée extérieure, une diagonale partage le quadrilatère méridional en deux triangles ; les volumes et premiers moments s'additionnent. Le lecteur vérifie les rayons et les coordonnées axiales correspondants aux deux extrémités angulaires avant application. Ce calcul décrit des faces polygonales droites, pas des secteurs cylindriques courbes.

Les prismes rotor et angulaires fixes ont une section triangulaire homothétique : à hauteur réduite t=(z−z0)/h, la section inférieure est multipliée par k(t)=1+(λ−1)t, avec λ=R1/R0>0. La section inférieure a une aire A0 et un centre plan c0. Les intégrales exactes sont :

- I2 = intégrale k² dt = (1+λ+λ²)/3 ;
- I3 = intégrale k³ dt = (1+λ+λ²+λ³)/4 ;
- J2 = intégrale t k² dt = (1+2λ+3λ²)/12.

Donc V=A0*h*I2, centre plan c0*I3/I2 et centre axial z0+h*J2/I2. Le code vérifie la mise à l'échelle de tous les sommets, les plans de section et h>0. Les ruptures de pente restent séparées par les cellules existantes ; aucune intégration ne les traverse implicitement.

Les 6 144 centres analytiques concordent à 2,113e−17 m près avec les moments scalaires par pyramides signées. L'écart relatif maximal des volumes est 1,931e−13. Le volume total analytique vaut 1,352515682172014e−7 m³. Ces concordances ne prouvent pas à elles seules l'absence d'intersections.

## Faces partagées et contrainte d'angle

Les blocs archivés donnent 13 696 faces internes et 4 864 frontières. Toutes les faces partagées ont leurs cycles orientés opposés ; les arêtes de chaque cellule s'annulent. L'ensemble des frontières égale exactement celui déclaré dans PR229. Aucun patch ou voisin fictif n'est introduit.

Pour une face orientée du propriétaire vers le voisin, n est sa normale unitaire et Δ la différence de leurs centres volumiques. Chaque séparation normale d_n=Δ·n est positive. La séparation tangentielle vaut d_t=|Δ×n|. L'angle satisfait 70° si et seulement si la marge m=tan(70°)*d_n−d_t est positive ou nulle. Cette marge a l'unité d'une longueur mais n'est ni un jeu physique ni une tolérance de fabrication. Les centres et la normale sont des conséquences de la géométrie, jamais des variables indépendantes.

| Famille partagée | Faces | Maximum calculé | Faces >70° |
|---|---:|---:|---:|
| rotor/rotor | 1 920 | 47,817352° | 0 |
| angulaire/rotor | 384 | 23,016871° | 0 |
| angulaire/angulaire | 1 920 | 67,068909° | 0 |
| angulaire/axiale | 768 | 52,844580° | 0 |
| axiale/axiale | 4 352 | 77,724390° | 1 024 |
| axiale/hex extérieur | 1 536 | 60,877898° | 0 |
| hex extérieur/hex extérieur | 2 816 | 23,276425° | 0 |

La plus petite marge est −108,167525 µm entre prismes axiaux. Toutes les paires refusées sont exactement celles du CSV PR229. Chaque tuple normal/tangent/marge/angle figure dans `faces.csv`. Le contrôle de planéité par distances signées au plan de face donne un maximum de 1,388e−17 m ; les arrondis ne sont pas des marges physiques.

## Fermetures et contributions internes

Une frontière non couplée n'a pas de voisin : aucun angle owner–voisin n'y est inventé. Les faces de frontière sont exclues du tenseur du déterminant, selon la définition déjà vérifiée sur le source officiel. Pour chaque cellule, les aires des seules faces internes sont normalisées par leur aire moyenne et forment le tenseur ; son déterminant absolu est divisé par huit. Le critère de plans garde son seuil −1e−6, incluant les configurations planaires.

`cells.csv` publie chaque volume, déterminant, score de plans, nombre de faces internes et contact avec la fermeture basse, haute ou aucune. Les 256 cellules axiales à chaque fermeture ont quatre faces internes contributrices. Minimum de déterminant en bas : 0,001270423231 ; en haut : 0,004336731885. Tous les déterminants passent 0,001 et aucun score de plans ne dépasse −1e−6.

Certaines cellules rotor aux fermetures ont seulement trois faces internes et passent néanmoins le déterminant. Le nombre de contributions ne suffit donc pas à conclure : leur direction et leur aire comptent. Ni ces résultats favorables ni la conservation de la frontière n'effacent le refus angulaire.

## Vérification indépendante

`verify_neighbours.py` reconstruit les faces depuis les six gabarits de l'hexaèdre avec réduction des sommets répétés, indépendamment de la construction par extrémités et faces latérales du premier lecteur. Il triangule les faces par diagonale puis calcule volumes et moments par tétraèdres orientés autour d'une origine locale. Il n'importe aucune fonction du premier lecteur ni les fonctions scalaires précédentes. Cube à trois échelles et tétraèdre unitaire vérifient ce calcul.

Les 6 144 lignes cellules et 13 696 lignes faces sont relues avec leur incidence réelle. Les écarts maximaux sont : angles 1,633e−11 degré, déterminants 1,388e−15, scores de plans 5,343e−14, volumes 8,682e−14 relatif. Les classifications de tous les critères sont identiques. Les journaux conservent les avertissements NumPy sur le produit vectoriel de vecteurs 2D ; aucune assertion n'a échoué et aucune opération native n'a été rejouée.

Cette phase complète les moments et contraintes de tous les voisinages du témoin existant. Elle ne choisit aucune autre résolution ou topologie et ne qualifie ni surfaces gauchies 086/091, ni parois physiques, couches, repos global, convergence ou performance CFD. Aucun débit ou gain de puissance validé.
