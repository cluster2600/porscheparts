# Frontière plongée, indice un et non-recouvrement des intérieurs

## Domaine et représentation

Cette preuve s'applique à chaque valeur de **tout** l'intervalle fermé
`[18685771944522017155/18446744073709551616,
9345323731508729405/9223372036854775808]` de v, avec u égal au q_m source.
Il s'agit de l'enveloppe des 153 boîtes PR239, sans suppression des deux boîtes
aux déterminants indécis. Aucune valeur ponctuelle de v n'est choisie.

Une face est représentée par l'éventail à la moyenne arithmétique de ses
sommets, partagé exactement entre ses deux cellules. Une cellule est la réunion
des tétraèdres joignant cet éventail à la moyenne de ses sommets distincts.
Ces points auxiliaires sont ceux de PR241, pas des centres natifs libres.
Les triangles gauchis ne sont pas remplacés par une face plane. Les conclusions
ci-dessous portent sur ces ensembles géométriques et leurs chaînes orientées.

## 1. Les côtés sont plongés

Les 2304 faces latérales donnent 9216 triangles fixes en v. Les coordonnées
rationnelles et les labels de chaque triangle sont reconstruits séparément par
les deux lecteurs. Ils sont non dégénérés. Pour chaque paire parmi 42462720,
soit une séparation **stricte** des boîtes englobantes ferme le contrôle, soit
l'intersection exacte est calculée. Les 59462 paires restantes donnent 2630
intersections vides, 43520 sommets et 13312 arêtes. Dans tous les cas,
l'intersection est exactement le simplexe commun annoncé par les labels.
Une égalité de boîtes englobantes n'est jamais utilisée pour séparer une paire.

Le premier lecteur coupe les triangles par leurs plans, puis intersecte les
segments; il découpe les polygones coplanaires dans une projection injective.
Le second utilise les intersections arête/triangle par déterminants rationnels,
les coordonnées barycentriques et les intersections d'arêtes coplanaires.
Il exige l'égalité de l'ensemble obtenu avec le simplexe commun, et relit le
parcours complet des paires. Ces méthodes n'importent pas le code l'une de l'autre.

La réalisation du complexe latéral fini est donc injective, y compris sur les
arêtes et sommets. Les liens de ses sommets sont des cercles à l'intérieur,
des intervalles au bord; chaque arête a respectivement deux ou une incidence.
Il forme deux surfaces compactes plongées à bord, de 3072 et 6144 triangles.
Leurs quatre cercles de bord contiennent au total 1024 arêtes.

## 2. Raccord aux fermetures et surface fermée

La preuve PR240, dans le même domaine et la même représentation, établit que
chaque fermeture est exactement l'anneau polygonal fermé entre ses deux boucles
convexes fixes strictement emboîtées. Les triangles positifs de sa chaîne ont
une multiplicité un sur cet anneau hors des arêtes. Nous utilisons ici cet
**ensemble annulaire** et sa chaîne, pas une déduction de plongement fondée
seulement sur une somme d'aires ou sur Euler.

Tous les triangles latéraux restent dans la bande entre les deux plans des
fermetures. Aucun n'est entièrement dans un de ces plans. Leur intersection
avec chaque plan est exactement constituée des sommets et arêtes des deux
boucles correspondantes : 512 arêtes par fermeture. Les lecteurs comparent
ces arêtes, leurs labels et coordonnées avec les boucles fixes PR240.
Ainsi les côtés ne rencontrent ni l'intérieur des anneaux ni une autre partie
de leur bord. Les deux anneaux, dans des plans distincts, sont disjoints.

Le recollement des surfaces latérales et des anneaux le long de ces quatre
cercles donne une surface S compacte, plongée, sans bord. Les colliers locaux
des surfaces à bord se recollent en disques, également aux sommets. La
connexité du graphe des triangles est vérifiée. L'orientation est cohérente :
chaque arête de la chaîne extérieure s'annule avec l'incidence opposée.
Les 8960 liens de sommets du complexe de frontière sont aussi contrôlés, sans
utiliser ce contrôle combinatoire comme substitut aux intersections ci-dessus.
S est une surface polyédrique finie, donc localement contractile. Son ensemble
géométrique reste fixe sur tout le domaine : côtés fixes et anneaux fixes.

## 3. Les deux composantes du complément

Nous utilisons la dualité d'Alexander pour un compact localement contractile K
non vide et propre de S³ : H_0 réduit du complément est isomorphe à H² réduit
de K, à coefficients entiers. Pour notre surface fermée, connexe et orientable,
H²(S;Z)=Z. Le complément de S dans S³ a donc exactement deux composantes.
Dans R³, l'une est non bornée et l'autre, notée Ω, est bornée. La structure
locale de surface plongée donne les deux côtés et la frontière de Ω est S.
Ce raisonnement ne suppose pas que S soit une sphère; un théorème limité aux
sphères serait insuffisant ici.

Référence : Allen Hatcher, *Algebraic Topology*, chapitre 3,
[dualité d'Alexander, corollaire 3.45, p. 255 de la version Cornell](https://pi.math.cornell.edu/~Hatcher/AT/ATch3.pdf).
La copie du livre disponible à l'Université de Chicago, conservée localement
et hachée dans `source-references.json`, numérote ce résultat **théorème 3.44**,
p. 254–255. Ne pas confondre les numérotations de ces deux versions.

## 4. Multiplicité de la chaîne volumique

Fixons arbitrairement v dans le domaine fermé. PR241 certifie que chacun des
119808 tétraèdres orientés est strictement positif. `verify_gluing.py` ne
recalcule pas ces bornes : il relit leur provenance et additionne exactement
les quatre faces orientées de chaque tétraèdre. Les 479232 occurrences de
faces se réduisent à la chaîne extérieure des 17920 triangles, avec coefficients
unitaires. Les triangles latéraux sont ceux contrôlés ici; les fermetures sont
celles de PR240. Toutes les faces internes s'annulent dans cette représentation.

En dehors de l'union finie des faces tétraédriques, posons m(x) égal au nombre
d'intérieurs de tétraèdres contenant x. Chaque orientation est positive, donc
m(x) est un entier non négatif. Sur un chemin générique, le saut de m à travers
une face est son coefficient dans le bord orienté de la chaîne. Les coefficients
internes annulés donnent un saut nul. Les faces géométriquement coplanaires sont
additionnées avant ce constat; on choisit les passages hors des arêtes et des
intersections de plans non confondus, ensemble exceptionnel de dimension au plus
un. Tout chemin dans une composante ouverte du complément de S peut être
perturbé ainsi. Par conséquent, m est constant, hors des faces, dans chacune
des deux composantes du complément de S.

Cette constante est zéro dans la composante non bornée, puisque la réunion des
tétraèdres est bornée. À un point régulier de S hors des arêtes, la chaîne
extérieure a multiplicité un (PR240 pour les fermetures, intersections exactes
pour les côtés). Le saut a donc valeur absolue un. La constante dans Ω vaut
alors +1 ou −1; la non-négativité de m impose **+1**. La chaîne de frontière
porte ainsi l'orientation extérieure et l'indice un dans Ω, zéro à l'extérieur.
La positivité seule n'aurait pas donné cette conclusion sans la preuve du
plongement de S et l'identité du bord de la chaîne.

## 5. Couverture et non-recouvrement, y compris aux limites du domaine

Si deux intérieurs tétraédriques se recouvraient, leur intersection serait un
ouvert non vide. Elle contiendrait un point hors de toutes les faces, avec
m≥2, contradiction. Chaque point générique de Ω appartient à exactement un
tétraèdre. La réunion finie des tétraèdres fermés est fermée; par densité elle
contient tout l'adhérence de Ω. Réciproquement, un tétraèdre non dégénéré est
l'adhérence de son intérieur, dont les points génériques appartiennent à Ω.
La réunion est donc **exactement l'adhérence de Ω**.

Les cellules définies comme réunions des tétraèdres qui leur appartiennent
couvrent aussi cet ensemble et ont des intérieurs disjoints : un recouvrement
d'intérieurs cellulaires contiendrait un point générique compté deux fois.
L'argument traite les bords par fermeture, pas en les retirant. Il s'applique
pour chaque v de l'intervalle **fermé**, puisque toutes ses hypothèses y sont
vérifiées, et garde les stations, ruptures et deux fermetures.

## Portée exacte

La preuve établit l'indice un de la frontière et la couverture volumique sans
recouvrement des intérieurs dans la représentation partagée PR241. Elle ne
catalogue pas tous les contacts de dimension inférieure entre cellules internes
non incidentes. Elle n'affirme ni égalité des premiers moments avec les moments
natifs, ni invariance des centres. L'égalité de volume signé native PR241 est
héritée dans son seul périmètre mathématique.

Aucun arrondi d'exécution OpenFOAM, branche ROOTVSMALL/VSMALL, contrôle natif,
repos, couche physique ou CFD n'est admis ici. Les 113 boîtes satisfaisant les
prédicats variables nécessaires restent sans admission native; les deux autres
aux déterminants indécis sont conservées. Ni ratio, candidat ni dictionnaire
nouveau. Aucun débit, puissance ou calibration validé.
