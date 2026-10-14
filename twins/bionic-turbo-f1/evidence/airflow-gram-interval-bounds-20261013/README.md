# Encadrements polynomiaux du Gram

**Faisabilité toujours non résolue.** Aucun nouveau ratio retenu ou évalué ponctuellement, candidat, dictionnaire, cas natif, conteneur ou solveur. La restriction u=q_m, les stations, les deux fermetures, les incidences et tous les critères restent ceux de PR233. Les sources et certificats antérieurs restent immuables.

## Preuve préalable

Les identités proposées après PR233 sont maintenant dérivées dans `derivation.md`, vérifiées puis publiées AVANT usage pour réencadrer les feuilles. Les six actifs préalables et leurs empreintes distantes figurent dans `preliminary-publication.json`.

Avec v=q_m+(q_ext-q_m)t, chaque coordonnée est affine en t. L'aire vectorielle (1/2) sum p_i×p_{i+1} égale exactement la somme des triangles de l'éventail natif : les termes contenant le point de référence télescopent. L'égalité est vérifiée coefficient par coefficient sur les 16 faces internes des quatre cellules sélectionnées. Cette identité d'aire ne certifie pas la planéité ou la non-intersection.

Pour G=sum S_i S_i^T, l'identité de Cauchy–Binet donne det(G)=sum_{i<j<k}[S_i·(S_j×S_k)]². Les quatre égalités polynomiales complètes sont vérifiées, ainsi que neuf références rationnelles à trois échelles, dont un cas de rang déficient. Un lecteur distinct reconstruit les aires par éventail et le déterminant par les six permutations de la matrice ; les mêmes coefficients sont retrouvés. Deux références analytiques contrôlent les coefficients de Bernstein et la restriction de Casteljau.

## Même domaine, mêmes boîtes

Le calcul porte exclusivement sur les **827 feuilles indécises archivées PR233**, sans subdivision supplémentaire. Les quatre témoins restent les cellules 955, 5019, 2036 et 6027, avec seulement leurs faces internes contributrices. Les centres et les deux contraintes angulaires ne sont pas modifiés.

Les coefficients de Bernstein exacts donnent des bornes sur chaque boîte entière, par convexité de la base. L'encadrement du polynôme det(G) est intersecté avec la somme des bornes des carrés des produits triples et la positivité du Gram. Les normes sont bornées par leurs polynômes quadratiques au carré, puis par des racines isqrt dirigées à 160 bits fractionnaires. E est toujours la somme des normes internes. Le résidu demeure 125 m^6 det(G)/E^6−1, équivalent au seuil natif de déterminant 0,001. Aucun seuil ou couplage modifié.

**380 boîtes supplémentaires sont exclues**, sur les mêmes feuilles. Avec les exclusions antérieures conservées, les 2 351 feuilles se répartissent maintenant en **1 904 exclues et 447 indécises**. En mesure de largeur de cette seule restriction, la part exclue vaut exactement **3649/4096 = 89,0869140625 %**, contre 3269/4096 précédemment. La part indécise est **447/4096 = 10,9130859375 %**. Ces nombres ne sont pas des probabilités et ne décrivent pas le système complet à deux inconnues.

Sur les 3 308 déterminants encadrés : les 2 234 signes précédemment positifs restent positifs ; 489 passent d'indécis à positifs, 581 d'indécis à refusés et quatre restent indécis. Plusieurs déterminants peuvent exclure une même boîte, d'où la différence entre 581 et 380. **Aucune boîte ne passe les six seules contraintes sélectionnées.** Parmi les 447 restantes, 445 ont les quatre déterminants positifs mais des angles indécis ; les deux autres gardent aussi un déterminant indécis. Cela localise les limites du certificat, pas une cause physique ni une admission.

Les 3 022 nouveaux intervalles comparables sont tous inclus dans les anciens ; les 286 autres n’avaient pas de borne finie dans PR233 parce que ses encadrements de moments contenaient une singularité. Cela décrit une limite de calcul, pas une dégénérescence démontrée du maillage. Les premières raisons des 380 exclusions nouvelles sont le déterminant axial bas 955 (99 boîtes) et le déterminant hex bas 2036 (281).

La réunion des statuts comporte désormais trois plages : exclusion en dessous, une plage centrale indécise, puis exclusion au-dessus. Toute solution éventuelle de cette restriction doit se trouver entre **18676403301138619465/18446744073709551616** et **9345323731508729405/9223372036854775808**, soit environ **1,012449851665497 à 1,0132220292282106**. Les boîtes adjacentes exclues couvrent aussi les deux bornes ; aucune de ces valeurs n'est choisie comme candidate. Cette condition nécessaire ne certifie ni monotonie ni faisabilité à l'intérieur.

## Lecture indépendante et limites

`verify_refinement.py` reconstruit les bornes par restriction rationnelle de Casteljau, avec racines à 192 bits, sans importer le calculateur principal. Il vérifie les 3 308 encadrements, les 380 nouvelles exclusions, la couverture des mêmes 827 feuilles et les largeurs cumulées. Les produits triples sérialisés sont reconstruits et leur somme des carrés comparée au polynôme du Gram. Les 163 boîtes déclarant positifs les deux angles hérités sont relues sur les boîtes complètes par le lecteur indépendant PR233 épinglé ; aucune évaluation de nouveau ratio ponctuel.

Le certificat concerne les expressions mathématiques avec erreurs d'encadrement contrôlées, et non les arrondis d'une exécution OpenFOAM. Les seuils restent inchangés, mais aucune admission native n'en découle. Les autres angles, déterminants, plans, volumes et obligations de couverture orientée, non-intersection, planéité, bilan, partage et qualité native restent à vérifier pour toute solution. Aucun résultat d'impossibilité générale.

Les polynômes et certificats complets sont conservés dans l'archive. `comparison.json` compare les bornes anciennes et nouvelles et fusionne seulement les statuts contigus, sans revendication de monotonie. Les parois gauchies 086/091, les surfaces physiques, les couches et le repos global restent distincts. 084 n'est pas relancé. Aucun débit, puissance, convergence, stabilité, indépendance maillage/temps ou calibration physique validé.
