# Réparation locale : borne du déplacement sur toute la surface

7 septembre 2026. Référence géométrique issue du scan 935, cible future M64.
Ce contrôle indépendant concerne le raccord local de degré **10 × 11**,
pas une autorisation de fabrication ni une validation de culasse.

## Résultat non limité à une grille de points

Le champ scalaire de déplacement stocké satisfait, sur **tout le carré UV
normalisé [0,1] × [0,1]**, y compris la zone non retenue par le contour :

```text
|D(u,v)| ≤ 0,9512202009568349 unité du scan < 1 unité du scan
```

La borne est obtenue en **arithmétique rationnelle exacte** pour les nombres
flottants enregistrés dans le NPZ, avec 13 boîtes examinées, 10 feuilles
acceptées et une profondeur maximale de 2. Aucun sous-domaine non résolu.
L'affichage décimal de la borne est arrondi vers l'extérieur.

Le rapport conserve aussi sa valeur exacte :

```text
4710214291766205820975108389 / 4951760157141521099596496896
```

La valeur maximale trouvée auparavant sur une grille, environ 0,934757,
reste une observation échantillonnée. Elle n'est pas utilisée comme borne.

## Méthode et preuve

Le champ est représenté en base de Bernstein tensorielle. Dans le carré
paramétrique, les fonctions de base sont positives ou nulles et leur somme
vaut 1 : chaque valeur du champ est une combinaison convexe des coefficients.
Le maximum des valeurs absolues de ces coefficients majore donc |D|.
Le principe d'enveloppe convexe est également utilisé par
[OCCT pour borner les B-Splines](https://dev.opencascade.org/doc/refman/html/class_geom_bnd_lib___b_spline_surface.html).

L'enveloppe initiale est trop large. La subdivision de Casteljau à 1/2
produit quatre représentations du même polynôme sur quatre sous-carrés
couvrant exactement le domaine. Seuls les sous-carrés dont la borne dépasse
1 sont subdivisés à nouveau. Chaque moyenne est un calcul sur fractions,
sans arrondi flottant. Un dépassement à un coin fournit un contre-exemple
sur le carré complet ; une limite de travail produit **inconclusif**, jamais
« réussi ». Aucune modification de la CAO n'est effectuée par cet outil.

Les 9 tests principaux et 6 tests indépendants vérifient notamment les
identités polynomiales des quatre quadrants puis de 16 sous-carrés, les
grilles asymétriques, les maxima intérieurs et non dyadiques, les limites
de ressources, l'arrondi extérieur et la provenance. Le test indépendant
du hash remplace le NPZ pendant le calcul : le reçu doit rester lié aux
octets réellement lus, conservés en mémoire.

## Traçabilité

- Source STEP F53 : `700baea66bc72cdb6aee529e21b167270ebde11db94b06f8e1e55ee08bdd9bf2`.
- STEP du candidat local : `42057011e25ecc48b215a58e979a0d9bcf4769f2f96f9690b751a81a7bde2cd8`.
- Coefficients privés : `48447c3d5a65e9a4cde06cf946b8c4bd1ade835b404d6d0f36ff405f1ad9ad12`.
- Le reçu inclut le hash de l'implémentation réellement relue pour ce calcul.

[Reçu numérique expurgé](../../twins/m64-cylinder-head/evidence/bernstein-global-bound-20260907.json)
et [script reproductible](../../twins/m64-cylinder-head/bound_bernstein_displacement.py).
Le NPZ, les surfaces et les coordonnées de la pièce restent privés.

## Limites qui restent ouvertes

La preuve porte sur le **polynôme scalaire représenté par les coefficients
stockés**, pas sur une borne d'arrondi de chaque évaluation native OCCT.
Elle ne prouve ni l'injectivité de la surface, ni l'absence d'interférence
avec toute autre pièce, ni une épaisseur minimale globale. Les contrôles
de raccord, de topologie et de rayons restent des preuves distinctes.

L'unité du scan n'est pas certifiée en millimètres. Le seuil de déplacement
de cette recherche locale n'est donc pas un jeu fonctionnel M64. Aucune
conclusion de refroidissement, résistance, fatigue ou imprimabilité LPBF
n'est tirée de cette borne géométrique. Le nombre de boîtes et la profondeur
bornent le parcours de l'algorithme, pas une durée CPU ou une mémoire absolue.
