# Méthode prescrite avant application

Cette application encadre les expressions mathématiques de checkFaceTets v2406. Les huit membres officiels et les 18 manifestes parents (460 entrées) sont vérifiés dans source-audit.json. Elle ne qualifie pas les erreurs flottantes, le futur binaire, sa configuration ou la conversion writePrecision 16.

## Domaine et représentation

Les 153 boîtes fermées PR239 sont conservées intégralement, avec u=q_m source et v entre 18685771944522017155/18446744073709551616 et 9345323731508729405/9223372036854775808. Aucun ratio ponctuel ni subdivision. Les deux boîtes aux déterminants indécis restent présentes. Le primaire construit les faces de prismes/hex ; le lecteur les reconstruit par les six gabarits hex réduits et vérifie les cycles opposés, 13696 internes, 4864 walls et 384 MRF internes. Le contrat non couplé des walls est hérité de PR247.

Chaque cycle orienté est tourné vers sa rotation lexicographiquement minimale. Cette rotation conserve l'ensemble des arêtes et des bases possibles. Les indices de base se rapportent à ce cycle abstrait ; aucune identité avec l'ordre d'un futur maillage OpenFOAM n'est revendiquée. L'owner est la première cellule incidente dans l'ordre des labels.

Les centres Cf et C proviennent des moments natifs PR236, avec translation par un sommet archivé constant pour les calculs locaux. Les moyennes auxiliaires des tétraèdres de preuve PR241 ne sont pas utilisées. Les noyaux 160/192 bits et leurs preuves sont hérités, sans nouvelle dérivation.

## Qualité et branches

Pour quatre points a,b,c,d : V=((b-a)×(c-a))·(d-a)/6 est signé. Posons u=b-a,v=c-a,w=d-a ; lambda=|w|²-u·w, mu=|v|²-u·v, N=lambda*(v×u)-mu*(w×u), D=w·(v×u). Si |D|<ROOTVSMALL, le rayon vaut GREAT. Sinon il vaut |(u+N/D)/2|. Une branche indécise produit une ligne nulle, sans division par un intervalle contenant zéro.

La qualité est V/[8/(9sqrt(3))*min(rayon,GREAT)^3+ROOTVSMALL]. Les normes/racines sont encadrées par les noyaux épinglés. Le quotient final emploie des bornes Fraction et ajoute ROOTVSMALL exactement avant l'arrondi externe. Le lecteur emploie les produits par les bornes réciproques exactes. Le plafond GREAT et la garde du rayon sont conservés. La branche circumCentre dégénérée est différente et n'est pas utilisée.

Sous l'hypothèse WM_DP, SMALL, GREAT et ROOTVSMALL sont les rationnels exacts des littéraux binary64 1e-15, 1e15 et 1e-150. Pour tol=sqr(SMALL), l'intervalle de comparaison contient à la fois le carré réel et son arrondi binary64 au plus proche, vérifié par les milieux rationnels adjacents. Une certification positive utilise l'extrémité supérieure : aucun seuil n'est assoupli. Ceci ne qualifie pas les autres arrondis natifs, notamment 1/6 et sqrt(3).

## Quantificateurs et ordre

Toutes les arêtes de chaque face sont évaluées autour de Cf. La qualité owner doit être <= -tol ; celle du voisin doit être >= tol. L'égalité est admise pour ces éventails. Les tétraèdres de base utilisent (C,p_base,p_j,p_next), avec inversion des deux derniers points côté voisin. Chaque qualité doit être strictement > tol pour une base positive ; une face interne exige une même base pour les deux côtés.

Les sommets de base sont examinés dans l'ordre du cycle canonique. Arrêt au premier témoin certifié positif sur tout le domaine. Cela prouve l'existence d'une base commune, sans prétendre reproduire le premier choix natif point par point. Si aucun témoin positif n'est établi, toutes les bases sont enregistrées. Un refus certain de l'existence exige une qualité certainement insuffisante dans chaque base. Une base indécise n'est pas un refus.

Ordre : toutes les 18560 faces triées par labels sur l'enveloppe, puis seulement les faces indécises sur chacune des 153 boîtes sources, dans leur ordre hérité. Les refus éventuels sont conservés, sans nouvelle sélection de candidat. Tous les éventails et toutes les bases effectivement essayées sont enregistrés. Les nombres de tétraèdres ou faces refusés ne sont pas présentés comme le compteur natif nErrorTets, qui peut compter plusieurs diagnostics pour une face.

Le lecteur indépendant n'importe pas le primaire. Il reconstruit les points, incidences et moments, vérifie l'ordre exhaustif des lignes et chaque intervalle numérique fini par inclusion à 192 bits, puis confirme les signes revendiqués. Les lignes nulles restent indécises sans prétention d'inclusion numérique. Un résumé ultérieur sera structurel, pas une troisième reconstruction.

## Références et limites

19 références par évaluateur ont réussi avant application : tétraèdres droits/inversés à trois échelles, trois paires de vrais cubes avec volume/centres/aire contrôlés et tous leurs éventails/bases, tétraèdre coplanaire, branches et comparaisons de fonctions distinctes. L'erreur préparatoire d'API du lecteur v1 est conservée ; v2 corrige seulement vectorcross en vector. Aucun calcul turbo n'a précédé cette correction.

Aucune admission native, CFD, débit, puissance ou calibration. Contacts internes de dimension inférieure, fermeture flottante et conversion/binaire restent ouverts. Les résultats des anciens critères ne sont pas rejoués. Le cas 084 demeure interdit de relance ou modification.
