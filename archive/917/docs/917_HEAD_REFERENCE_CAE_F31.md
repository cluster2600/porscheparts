# F31 — calcul EF de référence des concepts de culasse 917 2V/4V

## Résultat livré

F31 remplace le proxy de plaque F29 par une campagne CalculiX 3D réellement
exécutée. Quatre concepts ont été comparés sous les mêmes règles : moteur
Type 912 5,0 l atmosphérique et 917/30 5,374 l turbo, chacun en 2 et 4
soupapes. Chaque concept utilise trois tailles de maille et trois cas de charge.

| Contrôle | Résultat |
|---|---:|
| géométries comparées | 4 |
| maillages Gmsh | 12 |
| résolutions CalculiX | 36 |
| tailles maximales | 8,0 / 6,5 / 5,5 mm |
| convergence des quatre variantes | réussie |
| équilibre pression–réaction des douze maillages | réussi, erreur < 5 × 10⁻⁸ |

Le statut publié est
`passed_reference_solver_screening_not_physical_validation`. Il signifie que
la chaîne numérique et la comparaison sont cohérentes ; il ne signifie pas que
la culasse est validée pour un moteur réel.

## Pourquoi un modèle de deck défeaturé

La tétraédrisation directe des concepts complets F29 a échoué dans Gmsh sur des
intersections segment–facette. Le STEP demeure un solide OCCT fermé, mais cette
propriété ne suffit pas à produire un volume CAE robuste. F31 ne maquille pas ce
défaut : il reconstruit un volume solveur de 22 mm à partir des paramètres F29.

Le volume conserve :

- l'enveloppe cylindrique du deck ;
- la chambre sphérique ;
- les deux ou quatre puits de soupapes à leurs positions F29 ;
- le puits de bougie central ;
- les quatre perçages de fixation.

Les ailettes, conduits horizontaux, guides, sièges, porte-arbres, galeries
d'huile, filetages et contacts sont exclus. Les résultats servent donc à
comparer le chemin de charge du deck, pas la culasse complète.

## Cas de charge

Pour chaque maille, CalculiX résout séparément :

1. la pression seule, avec un effort axial total égal à la pression crête F29
   multipliée par l'aire projetée de l'alésage ;
2. la dilatation seule, avec un champ de température prescrit entre le côté
   chambre et le haut du coupon ;
3. le cas combiné pression + température.

La pression et les températures restent des hypothèses de dimensionnement non
corrélées. Le champ thermique n'est ni une conduction résolue ni un transfert
conjugué avec l'air de refroidissement.

## Résultats sur la maille 5,5 mm

La contrainte P95 est utilisée pour la comparaison. Le maximum brut se trouve
au voisinage des contraintes cinématiques et n'est pas un critère de
dimensionnement convergé.

| Scénario | Architecture | Tétraèdres | déplacement combiné [mm] | von Mises P95 [MPa] | marge P95 / 250 MPa |
|---|---:|---:|---:|---:|---:|
| Type 912 5,0 l NA | 2V | 10 844 | 0,3096 | 96,6 | 2,59 |
| Type 912 5,0 l NA | 4V | 12 481 | 0,3018 | 105,3 | 2,37 |
| 917/30 5,374 l turbo | 2V | 10 977 | 0,4714 | 170,7 | 1,46 |
| 917/30 5,374 l turbo | 4V | 12 460 | 0,4599 | 195,5 | 1,28 |

À conditions identiques, le deck 4V fléchit environ 2,5 % de moins, mais sa
contrainte P95 augmente de 9,0 % en atmosphérique et de 14,5 % en turbo. Le gain
d'aire effective moyenne de 19,6 % trouvé en F29 reste donc intéressant, mais la
version 4V turbo ne doit pas être figée sans renforcer les chemins de charge
autour des sièges et de la bougie.

![Comparaison EF 2V/4V](../twins/reference-917-engine/evidence/f31/figures/reference-fea-2v-4v.png)

![Convergence de maille](../twins/reference-917-engine/evidence/f31/figures/mesh-convergence.png)

## Décision matière et distribution

AlF357 LPBF reste le candidat de criblage de la culasse grâce au compromis
résistance/ductilité retenu en F29. La ligne à 250 MPa du graphique est une
valeur de comparaison à température ambiante, pas une limite admissible à
chaud. La nuance, l'orientation, le traitement thermique et la porosité devront
être qualifiés avec des coupons produits sur la même machine que la culasse.

Les composants fortement sollicités ne sont pas proposés en impression 3D :

- soupapes d'admission Ti-6Al-4V forgées ou usinées et achetées ;
- soupapes d'échappement INCONEL 751 achetées ;
- ressorts acier silicium-chrome trempé, nitruré et grenaillé, achetés.

Les dimensions finales, revêtements, sièges, guides et fournisseurs restent à
valider par dynamique de distribution et essais à chaud.

## Ce qui bloque encore un produit moteur final

Un produit final exige encore, dans cet ordre :

1. la campagne physique F27 et le layout mesuré F30 sur un moteur et une
   culasse identifiés ;
2. une CAO fonctionnelle avec tolérances, sièges, guides, conduits, ailettes,
   fixation, huile et porte-arbres ;
3. des cartes matériau à chaud, fatigue et fatigue thermomécanique issues de
   coupons représentatifs du procédé ;
4. CFD de banc de flux, CHT, FEA non linéaire avec précharges et contacts,
   dynamique des soupapes et étude de fatigue convergées ;
5. CT, CND, métrologie, étanchéité, pression, banc de flux et banc moteur
   instrumenté ;
6. corrélation des modèles, revue indépendante et autorisation de fabrication.

Omniverse vient après la CAO fonctionnelle et les sorties solveurs pour composer
le jumeau et visualiser ses champs. PhysX ne remplace pas CalculiX, OpenFOAM ni
les essais physiques.

Le préflight CAD-to-SimReady F31 a été exécuté avant toute conversion. Il est
bloqué sur cette machine : API OpenUSD et Asset Validator absents, checkouts
`usd-convert-cad` et SimReady Foundation absents, services OVRTX, Material et
Physics non sains. Aucun USD, aucune affectation automatique de propriétés et
aucun rendu Omniverse n'ont donc été produits. Le rapport assaini est publié
avec les preuves F31.

## Reproduction

```bash
make 917-head-reference-cae-f31-image
make 917-head-reference-cae-f31
make 917-head-reference-cae-f31-publish
```

Le calcul refuse d'écraser un run existant. Le conteneur fonctionne sans réseau,
en lecture seule, sans capacités Linux et avec un espace temporaire borné.
