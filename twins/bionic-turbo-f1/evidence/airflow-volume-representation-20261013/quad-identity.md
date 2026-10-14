# Annulation exacte observée et explication pour triangles/quads

Cette explication est rédigée APRÈS le premier calcul des bornes prescrit dans preflight.md. Elle n'a pas été substituée à ces bornes : tous les polynômes e_i effectivement calculés sont conservés et relus séparément. Aucune égalité approchée ou seuil de planéité n'intervient.

Pour un triangle, c et tous g_i sont dans le plan du triangle et S est normal à ce plan. Donc S·(g_i−c)=0. Par définition de chaque triangle d'éventail, a_i est perpendiculaire à p_i−c et p_{i+1}−c ; ainsi a_i·(g_i−c)=0 et F=0. Les e_i sont donc tous nuls.

Pour un quad quelconque p0,p1,p2,p3, poser c=(p0+p1+p2+p3)/4, u=(p0−p2)/2, v=(p1−p3)/2 et w=(p0+p2−p1−p3)/4. Les quatre sommets relatifs à c sont w+u, −w+v, w−u, −w−v. La somme des quatre produits croisés successifs divisée par deux est S=2u×v : les termes en w s'annulent exactement. Les centroïdes g_i−c sont respectivement (u+v)/3, (v−u)/3, (−u−v)/3, (u−v)/3. Ils appartiennent tous au plan vectoriel engendré par u,v, même si les quatre sommets ne sont pas coplanaires. Donc S·(g_i−c)=0. Comme pour tout éventail, chaque a_i·(g_i−c)=0, donc F=0 et tous e_i=0.

Il en résulte, si W>0 et pour ces faces à trois ou quatre sommets seulement, ε=0 exactement pour la moyenne native pondérée par les normes. Pour les cellules fermées constituées de telles faces, le volume natif mathématique égale donc la somme signée des tétraèdres de l'éventail à moyenne ARITHMÉTIQUE des sommets. Cette égalité ne dépend pas de la planéité des quads. Elle ne s'étend pas sans preuve aux faces à cinq sommets ou davantage, aux autres triangulations, aux premiers moments, aux centres volumiques, aux arrondis ou aux branches de secours natives.

La représentation reste explicitement un éventail à c partagé de part et d'autre d'une face. Cette égalité des volumes ne démontre ni l'indice de la frontière 3D, ni l'absence de recouvrement entre tétraèdres/cellules, ni une admission OpenFOAM. Les 7416 polynômes de non-planéité de signe strict sont conservés : ils ne sont pas transformés en faces planes.
