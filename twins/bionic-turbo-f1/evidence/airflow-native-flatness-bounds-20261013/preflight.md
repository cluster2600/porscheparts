# Contrôle prescrit de planéité et gardes mathématiques

Domaine fermé identique aux 153 boîtes PR244, u=q_m source, sans nouveau ratio
ponctuel ni subdivision. Toutes les 18560 faces uniques seront traitées dans
l'ordre lexicographique de leurs labels triés. D'abord l'enveloppe complète,
puis uniquement les faces indécises sur chacune des 153 boîtes sources.

Coordonnées affines PR232; centres de faces issus des moments PR236 épinglés,
aucun centre libre ou aplanissement. Triangles : centre moyen, aire directe,
planéité native initialisée à 1 (pas de passage dans la branche quads).
Quads : somme W des normes des doubles triangles à moyenne arithmétique pour
la garde de centre; puis éventail autour du CENTRE NATIF pour la somme A des
normes des aires. Planéité |S|/(A+ROOTVSMALL), seuil d'appel source 0.8 conservé.
Garde active du contrôle |S|>ROOTVSMALL; garde du centre W>=ROOTVSMALL.

La constante utilisée est le rationnel exact du littéral décodé binary64
1e-150 (configuration WM_DP conditionnelle), VSMALL de même pour 1e-300.
Noyau 160 bits PR233 et moments PR236, erreurs d'encadrement dirigées.
Le terme additif est gardé même si son intervalle déborde sa petite valeur.
Le seuil 0.8 est celui du littéral binary64, pas un seuil assoupli.
Références avant application : triangle, carré et quad gauchi symétrique à
trois échelles; vérification rationnelle par mise au carré pour sqrt(2).

Garde déterminant : seule somme E des normes des faces internes, et nombre
m>0, sans recalculer les déterminants. Garde cellule : héritage des volumes
PR241 mathématiquement égaux au volume natif, comparaison de 3V à VSMALL;
ne pas relancer ses polynômes. Garder murs hors de E.

Lecteur indépendant : gabarits hex réduits, moments indépendants PR236 et noyau
192 bits PR238 épinglés, toutes bornes enregistrées relues et incluses dans
les bornes primaires, mêmes références. Treize manifestes ancrés à PR244 et
payloads vérifiés. Contrôles d'incidences/domaines et classement explicites.

Ces bornes concernent les EXPRESSIONS MATHÉMATIQUES natives conditionnelles
WM_DP. Elles ne modélisent ni arrondis d'une exécution, compilation, entrée
writePrecision 16, décomposition tétraédrique native, autres critères ou repos.
Pas d'admission native, candidat, dictionnaire, conteneur ou solveur. Docker
sans conteneur actif avant cette phase. Aucun ancien parcours géométrique rejoué.
