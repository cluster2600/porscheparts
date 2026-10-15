# Spécification préalable — représentation volumique

Domaine fermé PR240 des 153 boîtes, u source fixé, sans ratio ponctuel ni subdivision. Préserver les deux boîtes aux déterminants indécis. Lire et vérifier dix manifestes ancrés au commit PR240 avant application.

Pour chaque face, choisir le cycle orienté de sa première cellule, tourné au plus petit label ; l'autre occurrence utilise exactement les mêmes triangles en sens opposé. Éventail à la moyenne arithmétique des sommets : objets de preuve uniquement. Pour chaque cellule, prendre comme point auxiliaire la moyenne de ses sommets DISTINCTS, fonction affine du paramètre, sans le confondre avec le centre volumique natif. Construire les tétraèdres orientés (point auxiliaire, moyenne de face, sommets successifs). Encadrer leurs six-volumes polynomiaux par Bernstein rationnel sur tout le domaine ; conserver tous signes, y compris indécis/refus. Leur positivité ne sera PAS déclarée preuve de non-recouvrement global.

Pour chaque quad, calculer le produit triple exact des trois différences à son premier sommet. Un polynôme non nul interdit de présumer la planéité identique sur le domaine ; distinguer identiquement nul et intervalle de signe strict. Vérifier les aires non nulles de tous triangles de face.

Lier volume signé de l'éventail et volume natif par la formule dans derivation.md. Calculer les polynômes e_i=F−S·(g_i−c), F=Σ a_j·(g_j−c). Leur enveloppe borne l'écart de flux natif par combinaison convexe des poids normiques, sans substitution d'un centre plan. Somme orientée /3 par cellule : borne d'écart de volumes SIGNÉS, pas erreur physique ni équivalence des centres. Conserver modèles et bornes individuels dans flux compressé.

Lecture indépendante : gabarits hex réduits, algèbre creuse et Casteljau PR235, aucun import du nouvel évaluateur. Reconstituer chaque face, triangle, tétraèdre et tous polynômes/bornes ; comparer exactement. Aucune admission native ou géométrique globale. La preuve future de plongement devra encore établir l'indice de la frontière 3D et le non-recouvrement avec cette représentation, ou justifier une autre représentation. Pas de solveur, aucune relance 084.
