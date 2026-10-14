# Identités des moments centrés

Pour les sommets p_i d'une face, c est leur moyenne. Poser n_i=(p_{i+1}−p_i)×(c−p_i), w_i=|n_i| et W=Σw_i>0. Le membre officiel `primitiveMeshTools.C` v2406 accumule Σw_i(p_i+p_{i+1}+c), puis divise par 3W. Or :

    Σ w_i(p_i+p_{i+1}+c)
      = Σ w_i(p_i+p_{i+1}−2c) + 3Wc.
    C_f = c + Σ w_i(p_i+p_{i+1}−2c)/(3W).

Cette égalité utilise seulement Σw_i=W, sans hypothèse de planéité. L'aire conserve l'éventail Σn_i/2. Pour une face triangulaire non dégénérée, les trois produits d'éventail sont chacun un tiers du produit total : poids égaux et centre égal à la moyenne des trois sommets, ce qui correspond à la branche triangulaire directe native en arithmétique exacte.

Pour la cellule, s est la moyenne des centres des faces. Avec les aires orientées sortantes S_i, V_i=S_i·(C_fi−s)/3 et V=ΣV_i>0 :

    Σ V_i(3C_fi+s) = 3Σ V_i(C_fi−s) + 4Vs.
    C = s + 3Σ V_i(C_fi−s)/(4V).

Les V_i restent signés. Le source accumule 3V_i, facteur qui s'annule dans le quotient du centre, puis divise le volume total par trois. Le changement d'orientation côté voisin reproduit le signe sortant. Les translations locales fixes restent celles du lecteur PR233.

Il s'agit d'identités des expressions mathématiques non dégénérées. Les branches natives ROOTVSMALL/VSMALL, les arrondis machine et une exécution OpenFOAM ne sont pas certifiés par ces identités. Les encadrements doivent conserver des dénominateurs strictement positifs ; une singularité d'encadrement n'est pas une dégénérescence géométrique prouvée. Ni c ni s ne sont gelés. Les normes et corrélations restantes peuvent encore élargir les intervalles.

`prove_identities.py` développe les coefficients indépendants des poids/coordonnées pour les faces à 3/4 sommets et cellules à 5/6 faces, vérifie deux références à poids signés, puis cube et pyramide à trois échelles et un quadrilatère gauchi symétrique à trois échelles. Le source officiel exact est haché ; aucun fichier épinglé n'est modifié.
