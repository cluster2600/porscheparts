# Système simultané de contraintes, sans solution choisie

PR231 a terminé la lecture des voisinages du candidat PR229. Cette phase formule les prédicats algébriques à satisfaire ensemble, sans choisir de ratio ou de subdivision. Le seul point évalué est celui de PR229, qui reste refusé. Aucun nouveau dictionnaire, maillage, cas natif ou solveur. Les deux archives parentes sont intégralement vérifiées.

## Deux inconnues, géométrie dépendante

La topologie, les stations, les ruptures et les faces partagées du témoin restent fixées. Les ratios des deux anneaux fixes internes deviennent les inconnues u et v, soumises à 1<u<v<q_ext. Les anneaux intérieur, MRF et extérieur gardent leurs coordonnées archivées : 3 328 points fixes. Les 2 816 autres points ont x et y multipliés par u/q_m ou v/q_a ; leur z reste constant.

`system.json` référence le maillage source et donne les coefficients rationnels exacts de ces dépendances, calculés depuis les valeurs binary64 décodées. Aux ratios archivés, chaque coordonnée est restituée exactement en arithmétique rationnelle. Aucun fichier de nouvelles coordonnées n'est produit. Ce sont deux variables non assignées d'une famille mathématique, pas deux dimensions proposées pour le turbo.

Les cellules et faces conservent leur incidence combinatoire. Cela ne prouve pas la validité de leur géométrie pour tout u,v. Notamment, déplacer les points internes aux fermetures impose de reprouver la couverture orientée, la planéité et l'absence d'intersections avant un éventuel candidat. La seule relation 1<u<v<q_ext ne constitue pas une admission.

Les centres ne sont pas des degrés de liberté. Pour une géométrie donnée, les centres de faces proviennent de l'éventail autour de la moyenne des sommets ; les centres/volumes cellulaires proviennent des pyramides signées autour de la moyenne des centres de faces, comme dans la définition native déjà publiée. Les moments analytiques PR230/231 restent des expressions vérifiées pour leurs familles, pas un droit de déplacer librement les centres.

## Contrainte angulaire, avec signe

Pour chaque face interne orientée du propriétaire vers le voisin, S est le vecteur aire, Δ la différence des centres et D=Δ·S. Il faut des normes non nulles et :

`D > 0` et `D² − κ*(Δ·Δ)*(S·S) >= 0`, où κ=cos²(70°).

Le signe D>0 est indispensable : mettre au carré seul admettrait aussi une normale retournée. Avec ce signe, l'inégalité est exactement équivalente à l'angle <=70°. κ est la racine unique dans (116/1000,118/1000) du polynôme `64κ³−96κ²+36κ−3=0`. Le lecteur indépendant vérifie rationnellement les signes aux bornes et la positivité de la dérivée dans l'intervalle. La formule du triple angle identifie cette racine à cos²(70°).

La régression compte 13 696 contraintes internes. Au point archivé, 1 024 échouent, exactement les paires déjà refusées. Le minimum du résidu divisé par `(Δ·Δ)*(S·S)` vaut −0,071772871637. Ce résidu est sans dimension et n'est ni une tolérance physique ni une nouvelle limite d'admission.

## Déterminant avec les seules faces internes

Pour une cellule, soit m le nombre de faces internes contributrices, `G=sum(S_f outer S_f)` et `E=sum(|S_f|)>0`, uniquement sur ces faces. G est un tenseur de Gram positif semi-défini. Le déterminant natif vaut `m^6*det(G)/(8*E^6)`. Le seuil inchangé 0,001 devient exactement :

`125*m^6*det(G) − E^6 >= 0`.

L'identité utilise `1/(8*0,001)=125`. Les normes peuvent être représentées par des variables auxiliaires positives l_f avec l_f²=S_f·S_f ; elles ne sont pas des variables physiques libres. Aucune paroi non couplée n'entre dans G ou E. Les neuf contrôles rationnels couvrent trois références, dont un tenseur de rang déficient, à trois échelles. Ce sont des tests d'identité, pas des essais de maillage.

Les 6 144 cellules archivées passent. Le minimum du résidu divisé par E^6 vaut 0,270423231239, soit exactement `1000*determinant−1` à l'arrondi. Ce résultat ne supprime pas le refus angulaire.

## Critère des paires de plans, sans perte du signe

Pour chaque paire ordonnée de faces distinctes d'une cellule, δ=C_g−C_f et L=S_f·δ. Pour des normes non nulles, le score normalisé doit rester <=−ε avec ε=1e−6. Son écriture équivalente est :

`L < 0` et `L² − ε²*(S_f·S_f)*(δ·δ) >= 0`.

Le signe négatif est obligatoire ; la mise au carré seule admettrait des scores positifs. Les 138 240 paires ordonnées sont contrôlées, sans exclusion des fermetures. Aucune ne refuse le point archivé. Le critère natif incluant les configurations planaires reste inchangé ; il ne devient pas une affirmation de concavité stricte.

## Réduction par dépendances, sans valeur nouvelle

`verify_invariants.py` vérifie les ensembles de labels : les seuls blocs dont aucun sommet ne dépend de u,v sont les 1 152 blocs tournants. Leurs volumes, plans et déterminants restent donc ceux du point archivé, à incidences inchangées. Les 1 920 angles entre deux cellules rotor restent également constants. Une recherche future peut conserver leurs preuves au lieu de recalculer ces expressions constantes.

Il reste 11 776 contraintes angulaires, 4 992 déterminants et 115 200 paires ordonnées de plans dépendant potentiellement des inconnues, contre respectivement 13 696, 6 144 et 138 240 au total. Les 23 040 paires de plans des cellules tournantes sont constantes.

Les 384 quads MRF ont tous leurs sommets fixes, mais leur voisin fixe appartient à la famille angulaire dépendant de u. Leur normale inchangée ne suffit donc pas à fixer leur angle : ces 384 contraintes restent dans le système dépendant. Cette analyse est combinatoire et conservative ; elle n'évalue aucun nouveau ratio et n'affirme pas que toute dépendance syntaxique est une variation non nulle partout.

## Vérification et limites de ce système

Les trois CSV contiennent chaque prédicat au seul point archivé. Le lecteur indépendant vérifie les 2 816 dépendances de coordonnées et les 3 328 points fixes, reconstruit les faces autrement et reprend les moments par tétraèdres orientés de PR231, via deux fonctions épinglées sans exécuter leur module principal. Il compare toutes les classifications et tous les résidus de déterminants et de plans. Pour les angles, toutes les valeurs reconstruites de D²/(|Δ|²|S|²) se trouvent hors de l'intervalle isolant de κ ; les classifications sont donc retrouvées numériquement sans acos ni atan2. Cela n'est pas un certificat par arithmétique d'intervalles de toute la géométrie flottante.

Ce système fixe les dépendances et les prédicats de qualité simultanés ; sa faisabilité pour de nouveaux u,v n'est PAS résolue. Aucun point nouveau n'a été essayé, aucun balayage, aucune optimisation et aucun nombre de subdivisions choisi. Il ne constitue pas à lui seul une preuve complète d'admission : volumes/aires positifs, frontières compatibles, non-intersection, conservation du MRF, planéité et bilan géométrique, puis contrôle natif restent requis pour toute solution éventuelle. Les obligations sont explicites dans `system.json`.

Une incompatibilité éventuelle de cette famille à deux ratios ne prouverait pas l'impossibilité d'une autre topologie. Les parois gauchies 086/091, les surfaces physiques, les couches, le repos global, la convergence et la performance CFD restent distincts. Ne pas relancer 084 ; aucun débit ou gain de puissance validé.
