# Crochet de ressort de lampe 993 — concept métallique F0

Le crochet de réparation est un meilleur cas d'usage de la fabrication additive
que la bague pilote : petite série, cavité de reprise, bras et gorge réunis en
une pièce, sans outillage. Roadster-Fashion vend cette fonction pour le 993 en
aluminium ou inox imprimé, ce qui établit l'intérêt industriel du procédé.

La source ne publie toutefois aucune cote. Ce dépôt ne copie donc pas le produit
commercial. Il définit un **concept indépendant F0**, avec des variables de
conception visibles dans le script build123d. Le modèle n'est ni ajusté au phare
ni autorisé à retenir une lampe.

## Modèles mathématiques exécutés

- flexion du bras : `sigma = M c / I`, avec `I = b t³ / 12` ;
- cisaillement maximal rectangulaire : `tau = 1,5 F / (b t)` ;
- contrainte équivalente : `sqrt(sigma² + 3 tau²)` ;
- flèche de console : `delta = F L³ / (3 E I)` ;
- cisaillement moyen de la liaison : `F / A_collage` ;
- dilatation libre : `delta_L = alpha L delta_T` ;
- volume analytique, masse indicative et contrôle du volume OCCT après relecture
  du STEP.

Le cas `30 N / +100 K` est une entrée synthétique de régression. Il vérifie le
code et montre quelles grandeurs devront être remplacées ; il ne valide aucune
charge de ressort, température de lampe ou résistance de colle du 993.

## Pourquoi LPBF

La cavité est ouverte, donc la poudre peut être extraite. La géométrie consolide
le fourreau de reprise et le crochet, alors qu'un usinage monobloc exigerait des
reprises et un accès outil difficiles. L'orientation, les supports, la racine du
bras et la rugosité de gorge restent à qualifier avec coupons et contrôle.

PhysicsNeMo n'apporte pas de preuve à ce stade : un surrogate nécessite d'abord
des cas CAE ou des essais corrélés. Le maître F0 reste sous l'autorité des
équations déterministes et du BREP OCCT.
