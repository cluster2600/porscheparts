# Passage de la multiplicité un à l'absence de contacts parasites

Ce texte est écrit AVANT les nouveaux contrôles. Sa conclusion est conditionnelle à leur réussite et aux certificats PR240/241/243 épinglés. Il ne modifie pas leurs conclusions historiques.

## Complexe et application

K est le complexe simplicial abstrait engendré par les ensembles de quatre labels des tétraèdres PR241. Toutes leurs faces sont incluses ; deux simplexes abstraits se rencontrent par définition suivant leurs labels communs. Les labels v, f et c sont disjoints. Le nouveau contrôle exige l'unicité des tétraèdres et les incidences triangulaires une/deux avec orientations opposées. B est le sous-complexe engendré par les triangles à incidence unique. On exige son identité avec la frontière PR243, y compris les fermetures PR240.

Pour v arbitraire dans le domaine fermé prescrit, F_v est affine sur chaque tétraèdre, donné par ses quatre positions PR241. Le partage exact des fonctions de coordonnées le rend continu sur K. Les six-volumes strictement positifs hérités rendent chaque restriction affine injective. On ne suppose pas encore l'injectivité globale et on ne suppose pas que K est une variété à partir de son seul Euler.

## Lemme local de chaîne positive (dimensions deux ou trois)

Soit x un point de |K| hors |B|, et sigma son unique simplexe porteur minimal (x est dans son intérieur relatif). Considérons la chaîne de tous les simplexes maximaux contenant sigma. Toute facette contenant sigma a deux incidences opposées dans cette chaîne : la seconde incidence contient elle aussi sigma. Une facette de frontière contenant sigma placerait x dans B, cas exclu. Le bord résiduel est donc porté par des facettes ne contenant pas sigma.

L'image de x n'appartient à aucune de ces facettes résiduelles. En effet, chaque telle facette appartient à un simplexe maximal contenant x, où F_v est injective. La famille est finie : il existe une boule ouverte autour de F_v(x) disjointe de ce bord résiduel. Aucun rayon uniforme en v n'est nécessaire ; v a été fixé arbitrairement, extrémités comprises.

Dans cette boule, la multiplicité de la chaîne locale, hors des facettes images, est constante. Pour le voir, joindre deux points génériques par un chemin polygonal générique restant dans la boule. Les sauts sont les coefficients orientés du bord ; ils sont nuls. Les plans confondus sont regroupés et les passages évitent les intersections de codimension deux. C'est le même argument élémentaire de chaînes que PR243, appliqué à une sous-chaîne finie. Dans la dimension deux, remplacer facettes/planes par arêtes/droites.

Cette constante est au moins un : l'intérieur de n'importe quel simplexe incident contient des points arbitrairement proches de F_v(x), et tous les simplexes ont orientation positive. Donc un antécédent abstrait hors B impose une multiplicité positive sur TOUTE une boule de points génériques, même si x est sur une arête ou un sommet.

## Injectivité hors B et séparation du bord

PR243 donne la multiplicité globale un dans Ω et zéro à l'extérieur, hors des facettes, avec réunion fermée exactement adhérence de Ω. Si deux points abstraits distincts x,z hors B avaient même image, aucun simplexe maximal ne pourrait contenir les deux, par injectivité affine. Leurs deux familles de simplexes incidents seraient donc disjointes. Les deux lemmes locaux imposeraient une multiplicité globale au moins deux sur une boule commune, contradiction.

Un point hors B ne peut pas non plus avoir son image sur S=F_v(B) : sa boule locale contient des points génériques extérieurs à Ω, puisque S est la surface plongée frontière PR243, alors que la multiplicité globale y vaut zéro. Ainsi F_v est injective sur |K|\|B| et son image y est disjointe de S.

## Injectivité de B, fermetures comprises

Les côtés sont injectifs jusque sur leurs labels d'arêtes/sommets par le parcours exact PR243. Pour une fermeture, appliquer le lemme en dimension deux à son complexe triangulaire, après choix de l'orientation positive dans son plan. Les nouvelles incidences une/deux doivent donner exactement les deux boucles PR240 comme bord abstrait. Les aires positives, l'annulation orientée et la multiplicité un sur l'anneau sont héritées de PR240. Le lemme exclut deux antécédents intérieurs et exclut qu'un point intérieur s'envoie sur les boucles, puisque chaque point de ces boucles a des points extérieurs à l'anneau arbitrairement proches. Les deux boucles elles-mêmes sont injectives et disjointes par leur convexité stricte et leur inclusion stricte PR240. La fermeture est donc injective sur tout son complexe fermé.

Les deux fermetures occupent des plans distincts. PR243 établit que les côtés rencontrent ces plans exactement aux boucles fixes, avec mêmes labels et coordonnées. Les nouveaux contrôles identifient ces boucles comme sous-complexes communs, pas seulement comme ensembles égaux en position. L'injectivité de chaque morceau implique donc celle du recollement B entier. Il n'est pas nécessaire de supposer une sphère, ni de retirer les bords.

## Contacts de toutes dimensions

Les trois étapes donnent l'injectivité de F_v sur |K| entier. Pour tous sous-complexes A,C, F_v(|A|) ∩ F_v(|C|) = F_v(|A∩C|) : tout point commun a un unique antécédent, appartenant aux deux. Appliquer cela aux sous-complexes des cellules PR241. Leurs labels c sont propres à chaque cellule et leurs labels f sont communs exactement lorsqu'elles ont la même face source. Une intersection sans sommet source commun est donc impossible. Les contacts permis sont précisément les simplexes abstraits partagés, sans contact ponctuel ou linéique supplémentaire entre cellules non incidentes.

La preuve vaut pour CHAQUE v du domaine fermé par les mêmes certificats de positivité ; aucune valeur de v n'a été choisie pour l'application, aucune subdivision géométrique ou paramétrique n'est effectuée. Ce résultat concerne la réalisation PR241 uniquement. Il ne prouve pas une égalité de surface avec une autre triangulation native, une égalité de centres ni une admission OpenFOAM.

## Référence de contexte et limites de validation

L'inversion globale des applications simpliciales positives avec bord bijectif est étudiée par Yaron Lipman, *Bijective Mappings of Meshes with Boundary and the Degree in Mesh Processing*, SIAM J. Imaging Sciences 7(2), 2014, théorème 1 : https://www.wisdom.weizmann.ac.il/~ylipman/2014_SIIMS_bijective_93975.pdf . Son cadre suppose un maillage de variété. Ici, l'argument local de chaînes est écrit explicitement : le seul comptage d'incidences n'est pas présenté comme vérification automatique de toutes les hypothèses de ce théorème externe. Les lecteurs contrôlent les hypothèses finies et leur provenance, pas la validité formelle de cette démonstration rédigée.

Aucune admission native, CFD, débit, puissance ou calibration. Les deux indécisions de déterminants et toutes les autres obligations restent inchangées.
