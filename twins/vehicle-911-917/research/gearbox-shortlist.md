# Recherche de boîte pour la 911–917 — F0/F1

## Décision d’architecture F1

La priorité donnée au comportement routier/circuit inverse la décision F0 : le
flat-12 est avancé devant l’essieu arrière et la boîte-pont passe derrière. La
topologie publiée de la Hewland LWS-200 — couple conique vers l’avant, train
d’engrenages longitudinal derrière — sert uniquement de référence de dessin.
La LWS-200 n’est pas sélectionnée : son couple publié de 935 Nm est inférieur
au besoin de screening et ses cotes générales publiques restent insuffisantes.

Le dessin F1 conserve une réserve historique hypothétique de **650 × 500 × 460 mm**, avec la
face moteur 100 mm devant le plan du différentiel et 550 mm disponibles derrière
ce plan. Ces valeurs ne proviennent d’aucun fabricant et F9 ne les considère
plus comme une cible de conception. La capacité en couple et le spectre de
charge priment désormais sur la compacité. Une boîte sur mesure ou une
transmission à couple divisé peut s’avérer nécessaire si l’objectif de 1 600 ch
et le cycle d’utilisation sont maintenus.

## Rappel de l’architecture F0

La configuration alors étudiée suivait la 911 : la boîte-pont était placée devant le
flat-12, son différentiel restant voisin de l’axe arrière. La boîte occupe ainsi
une partie du volume libéré par la suppression des places arrière. Une
implantation de type 917, avec le moteur devant la boîte, reste dessinée comme
comparaison et empiétait davantage sur la zone des occupants à empattement
standard. F1 résout ce conflit par l’allongement d’empattement décrit ci-dessus.

## Candidats publics

| Candidat | Données publiées utiles | Limite pour ce projet | Décision actuelle |
|---|---|---|---|
| Porsche Type 920 | La documentation Porsche décrit une boîte longitudinale à quatre rapports sur la 917/30. | Aucun plan général coté, STEP, couple admissible actuel ou solution d’approvisionnement vérifiés. | Référence historique d’architecture uniquement. |
| D.M.A. 1071-W-2WD | Séquentielle 5/6 rapports, 1 200 Nm en 5 rapports et 900 Nm en 6 rapports ; D.M.A. annonce des montages moteur avant, central ou arrière et cite Porsche parmi les applications existantes. | Dimensions, position exacte du différentiel, cloche 917 et cycle de charge non publiés. | Candidat le plus directement compatible avec une étude « boîte devant », sous réserve du dossier constructeur. |
| D.M.A. S1098 | 6 rapports, 900 Nm en endurance ou 1 300 Nm en sprint/course de côte, 76 kg, disposition longitudinale avec train d’engrenages devant le différentiel. | La cote d’ensemble et les interfaces ne sont pas publiques ; 1 300 Nm ne fournit pas de marge démontrée pour la cible maximale. | Candidat haute charge à étudier, pas sélectionné. |
| Hewland LWS-200 | 6 rapports, 935 Nm, 69 kg en aluminium ou 63 kg en magnésium ; train longitudinal derrière le couple conique. | Couple publié inférieur au besoin de screening et aucune cote d’ensemble publique sur la page produit. | Bonne référence de compacité/topologie, capacité insuffisante. |
| Xtrac P1192 | 7 rapports transversale, 1 100 Nm selon cycle, environ 115 kg avec commande. | Architecture transversale différente de F1 et aucune cote d'ensemble publique. | Référence de capacité uniquement, pas candidate à l'implantation longitudinale actuelle. |

Sources primaires consultées :

- [Porsche — conduite de la 917/30 et boîte quatre rapports](https://newsroom.porsche.com/en_AU/2019/history/porsche-goodwood-members-meeting-andrew-frankel-917-19271.html)
- [D.M.A. Racing Gears — 1071-W-2WD](https://dmaracinggears.com/2wd-transaxle-sequential-1071-w-2wd/)
- [D.M.A. Racing Gears — S1098](https://dmaracinggears.com/2wd-transaxle-sequential-s1098/)
- [Hewland — LWS-200](https://motorsport.hewland.com/browse-products/?singleproduct=725)
- [Xtrac — P1192](https://www.xtrac.com/product/p1192-supercar-transverse-synchromesh-gearbox/)

## Screening de couple

F9 interprète provisoirement « 1 600 ch » comme 1 600 mechanical hp au
vilebrequin, soit 1 193,1 kW. Cette unité et ce point d'application doivent
encore être confirmés. La conversion mathématique donne :

| Régime | Couple équivalent | Couple de screening × 1,30 |
|---:|---:|---:|
| 7 000 tr/min | 1 627,6 Nm | 2 115,9 Nm |
| 7 500 tr/min | 1 519,1 Nm | 1 974,9 Nm |
| 8 000 tr/min | 1 424,2 Nm | 1 851,4 Nm |
| 8 500 tr/min | 1 340,4 Nm | 1 742,5 Nm |
| 9 000 tr/min | 1 265,9 Nm | 1 645,7 Nm |

Ce calcul n’est pas une courbe mesurée du moteur : chaque ligne suppose que la
puissance maximale est atteinte à ce régime. Le facteur 1,30 est un filtre de
screening provisoire, pas une règle de dimensionnement validée. Il montre
qu’aucune valeur publique ci-dessus ne permet de valider la boîte avec une
marge de service, les transitoires de suralimentation et le cycle thermique.
Même la S1098 à 1 300 Nm échoue au screening F9.

## Réserve utilisée dans le dessin

Faute de plan constructeur, F0 réserve un volume de **650 × 500 × 460 mm** :
550 mm devant le plan du différentiel et 100 mm entre ce plan et la face moteur.
Ce volume est volontairement identifié comme hypothèse ; il ne doit être ni
interprété comme une cote D.M.A./Hewland, ni utilisé pour fabriquer un berceau,
une cloche ou des cardans.

## Dossier à obtenir avant de figer F1

La demande technique au fabricant doit couvrir au minimum :

1. plan général coté ou STEP sous conditions de confidentialité acceptables ;
2. distance face moteur–axe de différentiel et enveloppe complète avec
   actionneur, pompe, filtre et raccords ;
3. hauteur relative de l’arbre primaire et des sorties de différentiel ;
4. sens de rotation admis, position du couple conique et compatibilité moteur
   central arrière ;
5. couple continu, transitoire et par rapport pour le régime, les pneus, la
   masse et le cycle d’utilisation prévus ;
6. cloche, arbre primaire, embrayage, démarreur et fixation au flat-12 ;
7. brides de cardans, angles et débattements admissibles ;
8. masse, centre de gravité, points porteurs et charges de suspension admises ;
9. débit d’huile, refroidissement, températures, capteurs et maintenance ;
10. validation spécifique du mode réduit et du mode 1 600 ch.

La sélection reste donc `null` dans les rapports F0 et F1. Le dessin choisit une
**architecture**, pas encore un produit.
