# Porsche 917 — F47, comparaison interne B-Rep 2V / 4V

## Décision

F47 établit deux géométries internes candidates dans une seule et même peau
F43 non ovale, mais **ne produit pas une culasse imprimable**. Les booléens ont
créé un solide topologiquement fermé dans chaque variante; leurs p-courbes ne
sont toutefois pas propres et Gmsh refuse le maillage volumique. La livraison
est volontairement bloquée.

## Ce qui est commun

- peau externe et ailettes issues des 44 contours du scan F43, même SHA-256;
- aucune ellipse, aucun ovale et aucune boîte globale dans le constructeur;
- alésage circulaire candidat de 90 unités scan;
- bougie, sièges, guides, soupapes, conduits circulaires et galeries d'huile;
- galerie d'huile traversante avec deux accès supérieurs de nettoyage;
- noyaux gaz et huile exportés séparément et sans intersection;
- aucune déformation, aucun offset ou lissage de la peau F43.

Les dimensions internes reprennent F45 lorsqu'elles existent. Les conduits
droits, longueurs, profondeurs et la bougie 2V sont des hypothèses F47. L'unité
du scan est interprétée comme un millimètre uniquement pour construire le
candidat; ni l'échelle absolue ni les interfaces Porsche 917 ne sont certifiées.

## Variante 2V

Le candidat comprend une soupape d'admission, une soupape d'échappement, deux
sièges et deux guides séparés, plus une bougie latérale candidate. Le ligament
analytique limitant entre alésage et enveloppe de siège d'admission vaut
exactement 1,5 unité scan : aucune marge de fabrication n'est démontrée.

## Variante 4V

Le candidat comprend deux soupapes d'admission, deux d'échappement, quatre
sièges, quatre guides et une bougie centrale. Le ligament analytique nominal
limitant vaut 3,160 unités scan entre bougie et siège d'admission. Cela ne
remplace pas un calcul d'épaisseur peau-vers-cavités.

## Audits indépendants

OCCT 7.8.1.1 relit les deux STEP privés comme un solide / une coque, avec zéro
bord libre et zéro bord non-manifold. `BRepCheck` exact passe après 20 651
sous-formes pour le 2V et 20 431 pour le 4V. `BOPAlgo` trouve cependant 8 puis
32 p-courbes invalides. Gmsh 4.12.1 refuse les deux maillages 3D avec des erreurs
PLC segment/facet et facet/facet.

Les noyaux huile sont propres sous `BOPAlgo`. Les noyaux gaz sont fermés et
passent `BRepCheck`, mais portent respectivement 4 et 22 défauts de p-courbes.
Les volumes communs gaz/huile sont nuls; la distance minimale est 15,688 unités
scan en 2V et 19,391 en 4V.

## Portes qui restent fermées

- reconstruction locale des p-courbes et maillage Gmsh 3D;
- carte exhaustive d'épaisseur >= 1,5 mm sur une échelle certifiée;
- vérification indépendante de chaque chemin d'accès et essai de dépoudrage;
- interfaces, tolérances, usinages, joints et distribution réels;
- CFD/CHT, structure, fatigue thermomécanique, coupons matière et bancs;
- fabrication additive et démarrage moteur.

Les métriques, empreintes et commandes sont détaillées dans
`twins/reference-917-engine/evidence/f47-internal-brep/`.
