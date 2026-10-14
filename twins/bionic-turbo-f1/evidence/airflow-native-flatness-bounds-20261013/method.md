# Encadrement de la planéité autour du centre natif

Le domaine est l'enveloppe fermée des 153 boîtes PR239/244, avec u=q_m
source. Les coordonnées sont les fonctions affines rationnelles PR232 issues
des binary64 archivés. Les cellules, stations, fermetures et interfaces sont
inchangées. Aucun ratio ponctuel n'est choisi.

## Expression et branches

La source officielle v2406 épinglée dans PR244 initialise la planéité à 1.
Elle évalue les faces à plus de trois sommets lorsque |S|>ROOTVSMALL. Pour
ces quads, on encadre d'abord le centre C_f avec les moments centrés PR236,
puis A = somme_i |(p_{i+1}-p_i) × (C_f-p_i)|/2 et f=|S|/(A+ROOTVSMALL).
C_f est le centre natif mathématique, différent en général de la moyenne
arithmétique utilisée par la triangulation de preuve PR241. Aucun quad n'est
aplanissé. Les triangles suivent leur branche native directe et f=1.

Le seuil est le rationnel du littéral 0.8 converti en binary64; le comparer à
une borne inférieure est conservateur. ROOTVSMALL et VSMALL sont également
les rationnels exacts des littéraux double 1e-150 et 1e-300. Cette lecture est
conditionnelle à WM_DP et à ces conversions, sans inspection d'un futur
exécutable. Les bornes ne sont pas une simulation d'arrondis OpenFOAM.

Pour le calcul de C_f, W est la somme des normes des doubles aires de
l'éventail à moyenne des sommets. La garde sumA<ROOTVSMALL est inactive si
W_lo>=ROOTVSMALL. La branche de planéité est atteinte si |S|_lo>ROOTVSMALL.
Le terme additif ROOTVSMALL demeure dans A+ROOTVSMALL. Son encadrement
160 bits contient la valeur source même si sa borne inférieure devient zéro;
l'opération ne le supprime donc pas. Un résultat positif ne qualifie pas la
formule d'orthogonalité, qui conserve son propre terme additif ouvert.

Pour les cellules, la garde native porte sur le triple volume avant /3.
Les bornes de volume signé PR241, déjà reconstruites indépendamment et liées
au volume natif mathématique, sont seulement multipliées par 3 et comparées
à VSMALL. Aucun ancien polynôme n'est réévalué. Pour le déterminant, E est la
somme des normes des seules faces internes (incidence deux); on contrôle
m>0 et E_lo>=ROOTVSMALL avant la division native par m. Ces nouveaux contrôles
ne recalculent aucun déterminant et ne lèvent pas les deux indécisions de
fermeture conservées dans PR238.

## Ordre et indépendance

Les faces uniques sont ordonnées par labels triés; leur cycle orienté est la
rotation lexicographique minimale du premier propriétaire. Le premier calcul
reconstruit prismes et hex selon leurs familles. Il encadre toutes les faces
sur l'enveloppe, puis les faces indécises sur chaque boîte source, sans
subdivision. La translation par un sommet source constant diminue la largeur
des intervalles sans modifier la formule, les coordonnées ou le centre.

Le lecteur indépendant reconstruit les six gabarits hex avec réduction des
répétitions, vérifie les cycles opposés et utilise les moments indépendants
PR236. Le noyau dyadic192 PR238 conserve les opérations Fraction 192 bits
publiées; sa dérivation n'est pas répétée. Chaque borne reconstruite doit être
incluse dans sa borne primaire, chaque signe positif revendiqué confirmé,
chaque domaine, rang et face relu. Tous les encadrements individuels restent
conservés. Les treize manifestes parents et leurs payloads sont reliés au
commit exact PR244.

Avant les applications, chaque programme contrôle un triangle, un carré et
un quad symétrique gauchi à trois échelles. Le carré donne 4s²/(4s²+ROOTVSMALL),
le quad donne 4s²/(4sqrt(2)s²+ROOTVSMALL). Les inclusions sont vérifiées par
comparaisons rationnelles et mise au carré avec contrôle du signe; aucune
valeur flottante de sqrt(2) ne sert de référence.

## Limites

C'est un certificat des expressions mathématiques indiquées, avec gardes et
terme additif conservés. Ce n'est ni l'admission d'une boîte, ni celle d'un
fichier natif. Conversion writePrecision 16, configuration/binaire, erreurs
flottantes, orthogonalité avec son terme additif, décomposition tétraédrique
native, poids, rapports, skewness, contacts internes de dimension inférieure,
qualité native, couches et repos restent des obligations distinctes.
