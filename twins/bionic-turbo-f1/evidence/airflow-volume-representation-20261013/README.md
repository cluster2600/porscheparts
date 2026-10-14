# Éventail partagé et lien exact au volume natif

Une représentation de preuve est vérifiée sur l'enveloppe FERMÉE des 153 boîtes PR240, u=q_m fixé. Elle conserve les deux boîtes aux déterminants indécis. Aucun ratio ponctuel, subdivision, candidat, dictionnaire, cas natif ou solveur. **Le non-recouvrement volumique et l'admission native restent ouverts.**

## Représentation prescrite

Les 18560 faces uniques sont reconstruites depuis les 6144 cellules sources. Chaque face utilise un éventail à la moyenne ARITHMÉTIQUE de ses sommets. Une face interne reçoit exactement les mêmes triangles dans les deux cellules, en sens opposés. Chaque cellule utilise comme point auxiliaire la moyenne de ses sommets DISTINCTS : ce point affine prescrit n'est pas le centre volumique natif, n'est pas ajusté et n'est pas ajouté au maillage.

Les 68864 triangles de face uniques donnent 119808 tétraèdres de preuve dans les cellules incidentes. Tous leurs six-volumes ont une borne inférieure strictement positive sur l'intervalle entier, par Bernstein rationnel : minimum 4,786565022414144e−13 m³. La borne minimale de volume signé d'une cellule est 1,915504103483313e−12 m³. Les coefficients et rationnels exacts sont conservés dans models.jsonl.gz ; ces valeurs décimales ne sont pas des tolérances.

Domaine exact : v entre 18685771944522017155/18446744073709551616 et 9345323731508729405/9223372036854775808, soit t entre 3405/4096 et 1779/2048 dans v=u+(q_ext−u)t. Dix manifestes parents sont ancrés au commit PR240 28f6b174d61906e27bfd407c58e3992e9a6ef881 ; leurs 237 entrées sont relues. Les noyaux polynomiaux PR235 sont réutilisés à leurs empreintes, sans refaire les anciennes dérivations ni les parcours angulaires/cellulaires.

## Faces non planes et volume natif

11144 faces ont un polynôme de coplanarité identiquement nul ; 7416 quads ont un produit triple de signe strict sur tout le domaine. Les faces non exactement planes ne sont donc pas remplacées par des faces planes. Cette propriété concerne les coordonnées rationnelles issues des binary64 sources ; elle ne mesure pas une déformation physique.

La spécification préalable demande de borner ε=F−S·(C_f−c), différence du flux de l'éventail et du flux représenté par le centre natif. Les poids normiques natifs forment une combinaison convexe : les polynômes e_i=F−S·(g_i−c) suffisent à encadrer ε, sans approximation des centres. Tous les e_i calculés s'annulent EXACTEMENT, et la lecture indépendante le confirme.

L'explication dans quad-identity.md, rédigée après ce constat et distincte de la spécification préalable, montre pourquoi cette annulation vaut pour les triangles et les quads : leurs centroïdes d'éventail appartiennent au plan vectoriel perpendiculaire à S autour de la moyenne des sommets, même lorsque le quad est gauchi. Les faces fermées donnent alors **V_fan=V_native mathématique**, cellule par cellule, par annulation des vecteurs aire. Ce résultat concerne cette représentation et ces faces à trois/quatre sommets. Il ne donne aucune égalité des premiers moments ou des centres volumiques, ni des arrondis OpenFOAM ou branches ROOTVSMALL/VSMALL.

La somme des volumes signés est le polynôme CONSTANT exact 2487269102255605635770776230514877811598816531259/18389946490390666300300164325803710203424869466203226112 m³, environ 1,352515682171932e−7 m³. Les différences avec les anciennes sommes flottantes ne sont pas un changement géométrique. read_totals.py additionne les coefficients déjà vérifiés ; c'est une lecture structurelle, pas une nouvelle reconstruction.

## Vérification et limites

verify_representation.py reconstruit séparément les faces par six gabarits hex réduits, les polynômes par algèbre creuse et leurs bornes par Casteljau. Les tétraèdres sont reconstruits par déterminants de permutations et le volume de cellule par une somme à origine fixe, distincte du point auxiliaire du premier calcul. Les écarts de flux utilisent une double somme différente. **282240 polynômes et encadrements concordent exactement**. Calcul 61,050 s ; lecture 63,271 s. Aucune assertion refusée, installation ou calcul natif. Ce ne sont pas des benchmarks CFD.

Une somme de tétraèdres positifs et une égalité de volumes ne démontrent pas l'absence de recouvrement de leurs intérieurs. Il faut encore établir l'indice de la frontière 3D avec cette représentation, ou une autre preuve complète de plongement. La couverture plane PR240 reste limitée aux deux fermetures ; elle n'est pas étendue implicitement aux côtés gauchis. Les 113 boîtes passantes aux prédicats nécessaires restent NON admises. Planéité/bilan globaux, qualité native et repos global restent requis ; les centres natifs devront être conservés dans leurs contrôles.

Archive et journaux : https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-volume-representation-2026-10-13 . Voir validation.md et next-scope.md. Aucun débit, puissance ou calibration validé. Les parois physiques, couches et le vrai turbo restent distincts ; 084 n'est pas relancé, prolongé, raccourci ou réglé.
