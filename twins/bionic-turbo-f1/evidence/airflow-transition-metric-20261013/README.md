# Contrainte analytique de référence pour les transitions

Cette phase reproduit et vérifie la note exploratoire après PR229. Aucun nouveau candidat de couronne, dictionnaire, maillage natif, conteneur ou solveur. Les témoins PR227 et PR229 restent refusés. Tous les payloads de l'archive PR229 sont relus et vérifiés avant les contrôles.

## Rectangle et extrusion cartésienne

Soient W>0, H>0 et les sommets de section A=(0,0), B=(0,H), D=(W,0), M=(W,H/2), C=(W,H). Les triangles ABM, AMD et BCM forment le rectangle. Leurs centres d'aire sont respectivement (W/3,H/2), (2W/3,H/6), (2W/3,5H/6). Une extrusion cartésienne à épaisseur constante conserve ces deux coordonnées du centre volumique.

Pour la face issue de AM, la différence des centres vaut (W/3,−H/3), la tangente non normalisée (W,H/2) et la normale orientée (H/2,−W). Les produits sont WH/2 dans la direction normale et (2W²−H²)/6 dans la direction tangentielle. Leur quotient donne exactement :

`tan(angle) = |2W²−H²|/(3WH)`.

La paire supérieure donne le même résultat par symétrie. Avec r=W/H et t=tan(70°), les deux angles passent le critère angulaire si et seulement si :

`(sqrt(9t²+8)−3t)/4 <= r <= (sqrt(9t²+8)+3t)/4`.

Cette condition ne vérifie pas les autres faces, le déterminant ou les fermetures.

## Extension à un cisaillement affine

Appliquons x'=x+s*z à toute la section, où s est sans dimension. La largeur reste W à chaque z. Les centres suivent la même transformation affine. Pour la paire inférieure, les produits normal et tangentiel non normalisés sont WH/2 et `[2W²−sWH−(1+s²)H²]/6`. Pour la paire supérieure, le signe devant sWH devient positif. Le contrôle exact des coefficients dans W,H,s vérifie ces quatre identités, avec arithmétique rationnelle.

Le maximum des deux tangentes est donc :

`(|2r²−(1+s²)| + |s|*r)/(3r)`.

En posant K=3t−|s|, l'admission de ces DEUX angles impose K>=0 et :

`(sqrt(K²+8(1+s²))−K)/4 <= r <= (sqrt(K²+8(1+s²))+K)/4`.

Si K<0, aucune largeur positive ne satisfait les deux angles de cette référence. Si K=0, l'intervalle se réduit à une valeur. Ce résultat concerne seulement cette organisation triangulaire plane, pas une impossibilité générale de maillage.

## Vérification indépendante et limites

Le lecteur reconstruit les faces de prismes cartésiens puis calcule centres de faces, moments volumiques et angles avec les fonctions scalaires épinglées de PR226, indépendamment des identités polynomiales. Douze contrôles analytiques : rectangle, cas orthogonal W/H=1/sqrt(2), cisaillements +1/2 et −1/2, chacun aux échelles 1, 1e−3 et 1e−6. Ces valeurs sont des tests d'identités et d'invariance d'unité, pas une recherche de paramètres de maillage. Tous les centres concordent avec les centroïdes analytiques et tous les volumes sont positifs. Les erreurs numériques figurent dans readback.json.

La couronne utilise une extrusion ANGULAIRE, des rayons variables et des parois éventuellement gauchies. Les moments volumiques et les normales tridimensionnelles n'y suivent pas directement cette formule. Aucun nombre de subdivisions, largeur de couronne ou marge physique n'est choisi ou admis ici. Les centres réels ne sont jamais des paramètres indépendants.

Les déterminants des cellules de fermeture, le partage des faces, la conservation de la frontière, la qualité native, les parois physiques, les couches, le repos global, la convergence et la performance CFD restent distincts. Aucune conclusion de débit, puissance ou calibration.

`verify_bounds.py` contrôle séparément les deux bornes par centres directs de triangles, pour s=0, +1/2, −1/2 et le cas limite K=0. Les huit maxima retrouvent 70° à 1,43e−14 degré près. Le contrôle volumique des douze références retrouve les tangentes à 5,42e−16 près. Ces arrondis sont des erreurs de vérification numérique, pas des tolérances physiques ou un relâchement du critère.

## Moments exacts d'un prisme angulaire polygonal

Pour un triangle méridional de sommets (r_i,z_i), r_i>0, d'aire A, extrudé entre deux angles séparés par 2α<π, avec des faces droites (pas une surface cylindrique courbe), utiliser les coordonnées locales `x=r*cos(α), y=u*r*sin(α), z=z`, −1<=u<=1. Le jacobien vaut r*cos(α)*sin(α). En posant S=sum(r_i), Q=sum(r_i²)+sum_{i<j}(r_i*r_j), Z=sum(z_i), P=sum(r_i*z_i), l'intégration du triangle donne :

- volume `V=sin(2α)*A*S/3` ;
- centre sur la bissectrice `x_c=cos(α)*Q/(2S)`, `y_c=0` ;
- coordonnée axiale `z_c=(S*Z+P)/(4S)`.

Les identités utilisées sont `integrale(r)=A*S/3`, `integrale(r²)=A*Q/6` et `integrale(r*z)=A*(S*Z+P)/12`. La normale et les centres sont ensuite exprimés dans le même repère avant le calcul de l'angle. Ceci décrit les prismes axiaux à faces planes du candidat PR229, pas une facettisation arbitraire de faces gauchies.

Le lecteur relit les 2 304 prismes axiaux existants de PR229 et tous les payloads du paquet. Il vérifie les rayons et z correspondants entre faces angulaires avant application. Comparaison indépendante avec les moments par pyramides signées : centres à 1,6366e−17 m près, volumes à 1,931e−13 relatif près. Les 4 352 faces partagées entre ces prismes sont relues : maximum 77,724389811°, exactement les 1 024 mêmes paires dépassent 70°. Aucun maillage modifié ou créé.

Le premier lecteur conserve un refus d'assertion : comparaison à 1e−9 degré avec le CSV en acos, près d'angles nuls. La v2 compare les deux reconstructions avec atan2 et retrouve les angles à 5,003e−12 degré près. L'écart maximal au CSV reste publié : 1,20742e−6 degré ; pour les angles du CSV au-dessus de 0,001 degré, 4,989e−12. Ce dernier seuil est une partition descriptive des écarts d'arrondi, PAS un critère d'admission. Aucun seuil de qualité changé ; refus initial et source conservés.

Ces formules donnent les moments des prismes axiaux de cette famille polygonale. Elles ne sont pas encore une contrainte suffisante pour choisir un maillage : faces entre les autres familles, frontières, déterminants et contraintes de raccord restent à traiter ensemble. Aucun nombre de subdivisions ni nouveau candidat choisi.
