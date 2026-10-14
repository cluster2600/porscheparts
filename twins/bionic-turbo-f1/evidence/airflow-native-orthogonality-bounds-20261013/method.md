# Orthogonalité additive : prescription mathématique

Cette phase applique O=D/(sqrt(Q)+r), D=delta·S signé, Q=|delta|²|S|²>0 et r=Fraction du littéral binary64 1e-150, sous hypothèse de source WM_DP. sqrt(Q)=|delta|*|S| est une identité réelle ; elle ne suppose pas l'égalité des chemins d'arrondi natifs. Le seuil mathématique est sqrt(kappa), avec l'encadrement de kappa publié par PR233, sans modifier le seuil de 70 degrés. La configuration mutable, degToRad, libm, le binaire et leurs arrondis restent ouverts.

## Domaine et couverture

Les 153 boîtes PR239 fermées sont conservées, u=q_m source, v de 18685771944522017155/18446744073709551616 à 9345323731508729405/9223372036854775808. Aucun ratio v ponctuel, subdivision ou retrait d'extrémité. Les deux indécisions de déterminants demeurent.

Ordre figé : 9470 entrées de la matrice PR239 par boîte et rang existants ; deux témoins PR236 par boîte et rang existants ; 4224 faces constantes sur l'enveloppe entière, par labels triés. Les 4864 walls non couplées ont la valeur source 1 et ne sont pas ajoutées aux faces internes. Le lecteur vérifie l'union disjointe 9470+2+4224=13696 et les 384 faces MRF internes constantes, ainsi que toutes les incidences opposées. La reconstruction des gabarits concerne les incidences ; les moments ne sont évalués que pour les cellules constantes.

## Encadrements nouveaux

Les D,Q PR239 sont hérités en entiers /2^192 ; aucune ancienne géométrie variable n'est recalculée. Les deux témoins ont D et R=D²/Q−kappa. Puisque D_lo>0 et R_lo+kappa_lo>0, Q appartient à [D_lo²/(R_hi+kappa_hi), D_hi²/(R_lo+kappa_lo)]. Les fractions de cette récupération restent exactes. La perte de dépendance peut élargir l'intervalle : toute indécision est conservée, sans retour aux moments variables.

Pour x>=0 et N=2^p, n=floor(sqrt(floor(x*N²))) donne [n/N,(n+1)/N], avec extrémité supérieure n/N si son carré vaut exactement x. Les comparaisons rationnelles de carrés vérifient l'encadrement. Le primaire utilise isqrt à p=160 ; le lecteur une itération entière de Newton à p=192, avec vérification n²<=floor(x*N²)<(n+1)². Cette opération applique l'encadrement de racine, sans modifier les noyaux de moments épinglés.

On ajoute r EXACTEMENT aux deux extrémités des racines, puis on prend le minimum et maximum des quatre quotients D_endpoint/den_endpoint. Les quotients sont rationnels exacts avant arrondi externe à 160 ou 192 bits. Un zéro de borne dyadique de racine laisse un dénominateur rationnel r strictement positif ; r ne disparaît jamais avant la division. D reste signé. Les bornes finales ne sont pas tronquées artificiellement à [-1,1].

Le primaire classe positif seulement si D_lo>0 et O_lo>=seuil_hi ; refus si D_hi<=0 ou O_hi<seuil_lo ; sinon indécis. Le lecteur encadre à nouveau avec produits par réciproques rationnelles et confirme toute borne publiée par inclusion et tout signe revendiqué. Les classifications indécises du primaire restent indécises même si le lecteur resserre l'encadrement. Aucun statut ne constitue une admission native.

Pour les constantes, les coordonnées liées à u sont substituées exactement et celles liées à v ne sont pas construites. Seules les cellules dont tous les labels sont constants sont évaluées. Les moments PR236 centrés sont importés à leur hash ; une translation algébrique par un sommet réduit l'amplitude, puis le centre est retranslaté. Le lecteur emploie les six gabarits réduits, moments indépendants PR236 et noyau PR238 à 192 bits. Il vérifie inclusion de D,Q puis O. Ce calcul est la première application additive certifiée à ces constantes, pas une certification des CSV flottants PR231.

## Références et limites

Quatorze références par programme précèdent l'application : trois projections signées, cas à l'échelle ROOTVSMALL, quatre racines avec comparaisons exactes de carrés, quotient à très petit dénominateur, récupération de Q connue, rejet d'un dénominateur nul et trois paires de cubes adjacents cohérents. Pour ces cubes, volumes, centres, aires, D et Q sont confrontés aux expressions exactes issues de leurs sommets. Les autres références sont explicitement arithmétiques.

La vérification de la matrice et des témoins est indépendante pour la nouvelle application arithmétique et sa jointure, pas une nouvelle reconstruction de leur géométrie héritée. La reconstruction géométrique indépendante est limitée aux constantes. Les 17 manifestes/419 entrées sont vérifiés avant les parcours. Les warnings native severeNonOrth et errorNonOrth sont distincts ; un retour booléen false peut coexister avec severeNonOrth. Ne pas qualifier sur le seul retour.

checkFaceTets, contacts internes de dimension inférieure, fermeture flottante, conversion writePrecision 16, configuration et binaire restent ouverts, ainsi que repos, convergence, stabilité, indépendances maillage/temps, CFD et calibration. Aucun candidat ni natif ni solveur dans cette phase.
