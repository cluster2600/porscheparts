# Prescription avant calcul

Base PR247 efc7b2488dde73e5a1ae21b86fe2347f40d0ab0f. Branche native-weight-bounds propre, Docker sans conteneur actif. Même restriction u=q_m et même enveloppe fermée des 153 boîtes PR239 ; aucune subdivision, ratio ponctuel ou sélection de candidat. Préserver toutes extrémités et les deux indécisions des déterminants.

Source v2406 polyMeshTools::faceWeights : dOwn=abs(S·(Cf-Co)), dNei=abs(S·(Cn-Cf)), poids=min(dOwn,dNei)/(dOwn+dNei+VSMALL). Initialisation 1 sur parois non couplées ; MRF interne. Seuil checkFaceWeight 0.05, littéral binary64 conditionnel WM_DP. VSMALL conservé exactement dans l'application rationnelle finale. Les centres de faces et cellules viennent des moments natifs PR236 épinglés, jamais des tétraèdres de preuve.

Ordre lexicographique des labels de faces ; enveloppe d'abord, puis les seuls poids indécis sur chaque boîte source par ordre parent_leaf. Pour les moments dont le dénominateur n'a pas de borne strictement positive, conserver un statut indécis sans division ; reprendre sur les boîtes existantes. Ne pas traiter cette indécision d'encadrement comme un refus physique.

Les projections signées sont encadrées par le noyau160 PR233 ; pour un intervalle [l,h], abs donne [max(0,l,-h),max(abs(l),abs(h))]. Pour a dans [a0,a1], b dans [b0,b1], non négatifs, s=VSMALL>0 :
L=min(a0/(a0+b1+s),b0/(b0+a1+s));
H=min(1/2,a1/(a1+b0+s),b1/(b1+a0+s)).
Ces bornes suivent l'identité poids=min(a/(a+b+s),b/(a+b+s)) et la monotonie de chaque fraction. s est une Fraction exacte, même si plus petit que le quantum. Arrondir L/H vers l'extérieur à160bits seulement après les quotients. Garder les bornes des deux projections signées et du poids. Un intervalle entièrement sous le seuil est un refus nécessaire, pas une instabilité CFD ; conserver tous les résultats.

Lecteur prescrit : reconstruction indépendante des six gabarits hex réduits et cycles opposés ; moments indépendants PR236 et dyadic192 PR238 épinglés, sans importer le primaire. Recalcul des projections, abs et quotients rationnels par écriture complémentaire 1-(b+s)/(a+b+s), puis encadrement192 ; inclusion dans chaque borne160 et confirmation des statuts positifs/refus. Si une division de moment reste indécise dans le primaire, vérifier cette trace avec son noyau160 sur cette cellule seulement, sans attribuer de conclusion géométrique. Contrôler ordre, domaines, incidences, frontières wall,384MRF internes, couverture des153boîtes et empreintes. Quinze manifestes parents attendus,357entrées, ancrés PR247.

Références avant application : projections positives/négatives, intervalle traversant zéro, échange des voisins, volumes de projection à échelle VSMALL pour vérifier l'additif. Géométrie analytique de deux cubes adjacents à trois échelles pour vérifier moments, projections et poids. Ne pas refaire les dérivations des noyaux.

Il s'agit de nouvelles applications des moments, pas d'un parcours angulaire ou cellulaire ancien rejoué. Aucun maillage natif/solveur/dictionnaire. Arrondis natifs, conversion writePrecision16, skewness, orthogonalité additive, décomposition native, contacts internes et bilan flottant restent distincts. Les113boîtes non admises et les153boîtes sont conservées ; repos/couches/CFD/calibration restent ouverts.084 jamais relancé.
