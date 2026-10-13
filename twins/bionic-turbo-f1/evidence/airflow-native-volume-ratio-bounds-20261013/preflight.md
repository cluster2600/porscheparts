# Contrôle prescrit : rapports de volumes natifs mathématiques

Avant calcul : même enveloppe fermée des 153 boîtes PR245, u=q_m source.
Aucun ratio ponctuel de géométrie, subdivision ou recalcul des anciens volumes.
Ordre des 18560 faces : labels triés lexicographiquement. Pour chaque face
interne, réutiliser les bornes exactes de volume natif mathématique PR241,
après contrôle du domaine, des incidences et de leur lecture indépendante.

Source officielle v2406 : polyMeshTools::volRatio calcule
min(Vown,Vnei)/(max(Vown,Vnei)+VSMALL), initialisation 1 ailleurs et branche
séparée pour patches couplés. Le test checkVolRatio refuse strictement sous
le seuil d'appel 0.01. VSMALL et seuil : rationnels exacts des littéraux décodés
binary64 sous hypothèse WM_DP, sans inspection d'un binaire. Ne pas substituer
ROOTVSMALL et ne pas omettre le terme additif.

Les 4864 frontières sont les murs non couplés du contrat PR229 : vérifier
les faces et l'unique déclaration wall du dictionnaire ARCHIVÉ, uniquement
en lecture. Ne jamais l'exécuter ni en préparer une nouvelle version. Les
384 faces MRF doivent rester internes à deux cellules, pas des patches couplés.

Pour Vown dans [a,b], Vnei dans [c,d], a,c>0 : encadrement conservateur
[min(a,c)/(max(b,d)+s), min(b,d)/(max(a,c)+s)], s=VSMALL>0.
C'est une application monotone de bornes héritées, pas une reconstruction des
volumes. Fraction rationnelle exacte; pas de nouvel arrondi d'intervalle.
Une borne positive au-dessus du seuil suffit seulement pour ce critère.
Toute indécision sera conservée, sans subdivision ni ancien parcours rejoué.

Lecteur indépendant prescrit avant application : six gabarits hex réduits,
cycles orientés opposés, reconstruction des incidences, comparaison aux murs
archivés, mêmes volumes/domaines hérités et sources tar, calcul indépendant
des min/max via (x+y +/- |x-y|)/2, puis produits croisés entiers pour vérifier
les quotients de chaque certificat. Quatorze manifestes ancrés à PR245,
332 entrées attendues. Aucun import du nouveau calculateur primaire.

Références avant application : volumes égaux, ordre inversé, intervalles qui
se touchent et volumes à l'échelle VSMALL, où l'additif ne peut être ignoré.
Aucune de ces références n'est une sélection du paramètre géométrique v.

Poids et skewness exigent leurs centres natifs et leurs propres termes/branches;
ils restent ouverts. Ce contrôle isolé ne couvre pas arrondis OpenFOAM,
conversion writePrecision 16, décomposition native, contacts internes, repos,
CFD ou admission. Docker vide au précontrôle; aucune ancienne phase relancée.
