# Éventail partagé et écart au volume natif

Soit c la moyenne des sommets d'une face orientée. Les triangles (c,p_i,p_{i+1}) ont vecteurs a_i=((p_i−c)×(p_{i+1}−c))/2 et centroïdes g_i=(c+p_i+p_{i+1})/3. Posons S=Σa_i et w_i=|a_i|, W=Σw_i>0. La formule native publiée et épinglée PR236 donne C_f=Σw_i g_i/W ; elle n'implique pas que les triangles soient coplanaires. Les facteurs deux des normales natives s'annulent dans cette moyenne.

Le flux du champ x−c à travers l'éventail vaut F=Σa_i·(g_i−c). Le flux représenté par la face native vaut S·(C_f−c). Ainsi

ε=F−S·(C_f−c)=Σ (w_i/W) [F−S·(g_i−c)].

Les poids sont positifs et de somme un. Pour tous les paramètres de la boîte, min_i inf(e_i) ≤ ε ≤ max_i sup(e_i), e_i=F−S·(g_i−c). Les e_i sont polynomiaux même lorsque les w_i contiennent des racines. Ce résultat ne suppose ni petite déformation ni planéité, et ne remplace pas les moments natifs par ceux de l'éventail. Pour une face plane, tous les flux relatifs sont nuls, donc ε=0. La réciproque n'est pas supposée.

La somme des vecteurs aire des faces d'une cellule fermée vaut zéro, par annulation des arêtes (identité d'aire polynomiale PR235 et incidences PR240). Pour n'importe quel point auxiliaire s prescrit, V_fan=Σ_fΣ_i a_fi·(g_fi−s)/3 est la somme SIGNÉE des volumes des tétraèdres (s,c_f,p_i,p_{i+1}). Le volume natif mathématique vaut V_native=Σ_f S_f·(C_f−s)/3 ; il est indépendant de s, même si le calcul natif choisit la moyenne des C_f. Donc V_fan−V_native=Σ_f ε_f/3. Retourner une face retourne ε ; deux cellules partagées utilisent le même éventail, avec signes opposés.

Cette identité concerne le volume, pas le centre volumique : aucune égalité des premiers moments ou des centres n'en découle. Les arrondis, branches ROOTVSMALL/VSMALL et critères natifs restent ouverts. Une somme de tétraèdres positifs ne prouve pas à elle seule l'absence de recouvrement ; il manque encore une preuve d'indice un de la frontière volumique. Aucun changement du maillage ni de ses sommets n'est effectué.
