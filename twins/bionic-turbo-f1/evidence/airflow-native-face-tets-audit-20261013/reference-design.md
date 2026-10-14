# Références proposées avant tout évaluateur

Ce document prépare les références du futur contrôle ; aucun programme ni référence numérique n’est exécuté ici.

- Tétraèdre droit cohérent : sommets (0,0,0), (l,0,0), (0,l,0), (0,0,l), pour l=1, 1/1000, 1/1000000. Volume signé l³/6 et rayon sqrt(3)*l/2. Quand le plafond GREAT est inactif, la qualité exacte est (l³/6)/(l³/3+ROOTVSMALL). Vérifier les sommets, le volume, le rayon et la qualité, pas seulement une valeur finale. L’échange de deux sommets doit inverser le signe de qualité et conserver le rayon.
- Tétraèdre coplanaire cohérent : volume nul, garde du rayon dégénéré et retour GREAT, qualité nulle. Ne pas importer le comportement circumCentre, dont la branche dégénérée retourne le centroïde au lieu de GREAT.
- Paires de cubes adjacents cohérents à trois échelles, moments natifs calculés depuis les sommets. Vérifier séparément les signes opposés des éventails autour de Cf et les éventails de sommets de base avec inversion de cycle côté voisin. Aucun point ou triangle n’est ajouté au maillage réel.
- Références de fonctions explicitement non géométriques : comparaison |denom| avec ROOTVSMALL aux deux côtés et à l’égalité ; minimum du rayon avec GREAT ; conservation du très petit additif au dénominateur ; différence entre les comparaisons non strictes des éventails autour de Cf et les comparaisons strictes de choix de base. Ces tests doivent viser les branches et ne seront pas présentés comme des cubes ou tétraèdres reconstruits.

La formule de qualité emploie le volume signé. Les bornes de sqrt(3), la sélection conditionnelle de SMALL/GREAT/ROOTVSMALL et le traitement de sqr(SMALL) doivent être prescrits avant gel. Ne pas assimiler sans preuve le carré réel du littéral binary64 SMALL à son carré arrondi dans un futur binaire.

Le lecteur devra reconstruire indépendamment les incidences et vérifier chaque encadrement revendiqué. Une base positive sur tout un domaine suffit comme témoin d’existence, sans prétendre que le binaire choisirait ce même sommet en premier. Une base indécise ne prouve pas l’absence d’une autre base. Pour annoncer un refus certain de l’existence, toutes les bases possibles doivent être traitées ; sinon conserver l’indécision. Cette distinction et l’ordre des bases devront figurer dans la prescription finale, avant application.
