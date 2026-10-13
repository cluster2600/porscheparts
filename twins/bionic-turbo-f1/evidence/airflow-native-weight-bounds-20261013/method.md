# Encadrement des poids avec centres natifs

Les coordonnées sont les affines rationnels PR232 sur u fixé à q_m. Les moments de faces et cellules sont ceux de PR236, avec volumes pyramidaux signés et centres auxiliaires prescrits. Les gardes mathématiques des sources sont couvertes par PR245 dans ce domaine ; cela ne qualifie pas les arrondis d'un binaire. Le primaire emploie le noyau160 PR233 ; le lecteur indépendant, les moments PR236 séparés et la représentation192 PR238. Aucun ancien parcours de critères n'est exécuté.

L'évaluation translate chaque cellule par son premier sommet source constant pour limiter la dépendance des intervalles. Elle remet ensuite le centre et les centres de faces dans les mêmes coordonnées globales avant les projections. Cette translation est une identité des moments, pas une rotation ou déformation du domaine.

Pour les projections signées x et y, calculer leurs intervalles absolus a et b. Pour chaque valeur admissible, le poids est min(a/(a+b+s), b/(a+b+s)), s=VSMALL exact. La première fraction croît en a et décroît en b ; la seconde a les monotonies inverses. Les bornes de preflight.md suivent immédiatement ces monotonies. Les corrélations entre a et b n'invalident pas l'inclusion. Le plafond 1/2 est mathématique car 2min(a,b)<=a+b<a+b+s lorsque min(a,b)>0 ; zéro est également couvert.

Les quotients finaux sont des Fraction exactes contenant s, puis arrondis vers l'extérieur. Le lecteur utilise la forme complémentaire 1-(b+s)/(a+b+s). Le petit additif n'est jamais remplacé par zéro, même si le résultat arrondi coïncide numériquement à un quantum près avec une formule sans additif. Deux références exactes à l'échelle s donnent 1/3 et 1/4 ; leur résultat changerait sans s.

Douze références par programme précèdent l'application : les deux références exactes précédentes, six projections ponctuelles analytiques, un intervalle signé traversant zéro et trois paires de cubes adjacents à échelles 1, 1e-3 et 1e-6. Ces données analytiques ne choisissent aucun ratio géométrique du domaine.

Les enregistrements sont [domaine,rang,bornes,statut]. Domaine=envelope ou label de boîte PR239. Pour une face interne, bornes=[x_lo,x_hi,y_lo,y_hi,w_lo,w_hi], entiers divisés par2^160 ; pour une paroi, [w_lo,w_hi]=[2^160,2^160]. null signifie que le noyau n'a pas établi un dénominateur de moment strictement positif ; ce cas demeure indécis. Les rangs suivent les labels de faces triés, reconstruit séparément par le lecteur. Ce dernier vérifie l'ordre des domaines, l'ordre des rangs, chaque inclusion192dans160 et les signes revendiqués. Les comptes/minima sont également relus structurellement, sans leur attribuer une troisième reconstruction géométrique.

La conformité de ce seul critère mathématique ne prouve ni l'admission native, ni la qualité complète du maillage, ni les surfaces physiques, ni la convergence/repos, ni une comparaison débit/puissance.
