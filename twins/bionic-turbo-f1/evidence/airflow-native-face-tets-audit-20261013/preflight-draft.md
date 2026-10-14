# Brouillon avant application — checkFaceTets

Lecture de trois membres officiels pendant la CI de PR252, sans calcul géométrique. Attendre la fusion et la CI main exacte avant la branche propre. Ce document ne constitue pas un gel d’application : programmes, domaines d’encadrement, références, lecteur et constantes numériques restent à prescrire.

checkGeometry appelle checkFaceTets sous allGeometry, avec minTetQuality=sqr(SMALL), puis incrémente noFailedChecks et conserve lowQualityTetFaces en cas de refus. Ne pas transposer le comportement booléen du contrôle d’orthogonalité.

Première famille : pour chaque arête orientée p_i,p_next de chaque face, tetra(p_i,p_next,Cf,C_owner). La source refuse quality > -tol (égalité acceptée). Côté voisin interne, même cycle et C_neighbour : refuse quality < tol (égalité acceptée). Cf et les centres de cellules sont NATIFS, pas les moyennes auxiliaires PR241.

Seconde famille : findBasePoint pour walls et findSharedBasePoint pour faces internes. Chaque sommet de face est essayé dans l’ordre du cycle. L’éventail utilise n-2 triangles issus de ce sommet et le centre de cellule ; côté voisin, les deux sommets non base sont inversés. Une base est acceptée seulement si le minimum des qualités est STRICTEMENT > tol, des deux côtés pour une face interne. Une preuve existentielle sur tout un intervalle devra distinguer une base commune à ce domaine d’un choix qui varie avec v. Aucun essai de ratio ponctuel n’est autorisé. Les couplées sont distinguées dans la source mais absentes du contrat wall hérité.

quality=V_signed/[8/(9*sqrt(3))*min(circumRadius,GREAT)^3+ROOTVSMALL]. mag() du tétraèdre est SIGNÉ : (1/6)*((b-a)×(c-a))·(d-a). Pour le rayon, a=b-a0,b=c-a0,c=d-a0 ; lambda=|c|²-a·c, mu=|b|²-a·b, ba=b×a, ca=c×a, num=lambda*ba-mu*ca, denom=c·ba. Si |denom|<ROOTVSMALL, radius=GREAT ; sinon radius=|0.5*(a+num/denom)|. Ne pas remplacer la qualité par le seul signe de volume, ni omettre la garde, le minimum ou l’additif.

À préciser avant application : literals SMALL/GREAT/ROOTVSMALL et WM_DP, traitement de sqr(SMALL), bornes sqrt(3) et rayons, normes, branches indécises et signes. Réutiliser les noyaux/moments publiés, conserver les 153 boîtes fermées et leurs indécisions ; aucune reconstruction d’anciens critères ou sélection de candidat. Références cohérentes et lecteur indépendant nécessaires avant gel. Binaire, conversions writePrecision 16 et arrondis restent distincts.

Aucun évaluateur, natif ou solveur préparé. 084 demeure interdit de relance, prolongation, raccourcissement ou réglage.
