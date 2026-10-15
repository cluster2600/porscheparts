# Contraintes cellulaires sur les boîtes restantes

Les contrôles nécessaires des déterminants, plans et volumes ne produisent **aucune exclusion supplémentaire** : 153 boîtes restent non exclues sur la restriction u=q_m source. **151 boîtes satisfont les 3840 déterminants variables** ; dans chacune des deux dernières, 256 déterminants restent indécis. Les **92160 paires ordonnées de plans et les 3840 volumes variables** sont positivement encadrés sur chacune des 153 boîtes. Cela ne constitue ni une solution admise, ni une géométrie nouvelle, ni une qualification CFD.

Aucun ratio ponctuel, subdivision, candidat, dictionnaire, natif ou solveur. Les stations, ruptures, deux fermetures et interfaces sont conservées dans les sources. Les contraintes constantes ne sont héritées que dans leur périmètre prouvé. Les bornes angulaires positives de PR237 ne sont toujours pas toutes relues indépendamment.

## Déterminants

`preflight.md` fixe l'ordre avant calcul : déterminant archivé PR231 croissant, puis label cellule. Les 3840 cellules variables sont reconstruites depuis les incidences PR229 et les coefficients PR232 ; les quatre témoins PR235 sont retirés du nouveau parcours, soit **3836 modèles supplémentaires**. Seules les faces internes partagées contribuent au tenseur. Aucun mur non couplé n'est ajouté.

Le calcul réutilise les fonctions épinglées d'aire polynomiale, Cauchy–Binet, Bernstein rationnel et racines extérieures à 160 bits de PR235. Chaque nouvelle application vérifie les aires contre l'éventail et le déterminant contre le Gram direct. Le résidu reste 125*m^6*detG/E^6−1, avec seuil natif 0,001 inchangé.

Les 153 boîtes étant contiguës, chaque contrainte est d'abord encadrée sur leur enveloppe fermée exacte. **3581 modèles passent sur cette enveloppe**. Les 255 autres sont repris sur les boîtes d'origine : 38505 bornes positives et 510 indécises, sans nouveau découpage. Ces 510 indécisions sont 255 cellules dans chacune des feuilles 1929 et 1930. Le témoin hérité 2036 reste aussi indécis sur ces deux feuilles : 256 cellules par feuille, toutes hexaédriques de fermeture basse. Il s'agit d'une indécision des encadrements, pas d'un rejet physique.

`verify_determinants.py` reconstruit séparément les faces par gabarits hex réduits, les aires par éventail et polynômes creux, et le déterminant par permutations de matrice. Il vérifie les cycles opposés, les incidences, l'ordre, **3836 modèles, 18160 applications d'aire et les 42851 encadrements enregistrés**, avec Casteljau rationnel et racines à 192 bits. Les bornes indépendantes sont incluses dans les principales ; tous les signes positifs revendiqués sont confirmés. Aucun sous-ensemble n'est transformé en admission.

## Plans et volumes

`planes-preflight.md` est fixé après le parcours des déterminants et avant ce second calcul. Ordre : score de plans archivé décroissant puis label ; paires i,j dans l'ordre des faces, i≠j. Les moments centrés PR236 sont réutilisés sans approximation plane ni centre libre. Pour δ=C_j−C_i et L=S_i·δ, garder L<0 et L²/(|S_i|²|δ|²)−10^-12≥0, avec dénominateur positif. Le critère natif incluant les configurations planaires n'est pas assoupli.

Les volumes sont les sommes signées des pyramides natives autour de la moyenne des centres de faces. Les murs restent présents pour les plans et la géométrie, distinctement de leur exclusion du tenseur de déterminant. **2304 cellules passent sur l'enveloppe** ; pour les 1536 hex extérieurs, l'enveloppe reste indécise et les **235008 contrôles locaux** passent. Toutes les boîtes d'origine sont conservées. Le calcul principal dure 580,108 s ; celui des déterminants 146,422 s. Ces durées ne sont ni un benchmark OpenFOAM ni un coût d'écoulement.

Le lecteur indépendant v2 reconstruit les faces et utilise les moments indépendants PR236. Il relit **toutes les bornes enregistrées**, y compris celles de l'enveloppe indécises : 7142400 paires et 238848 volumes. Son reçu est `planes-independent-readback-v2.json`.

## Représentation du lecteur et traces conservées

Deux premières invocations de lecteurs ont eu lieu avant la disponibilité de leur reçu final : elles s'arrêtent avec `FileNotFoundError`, sans assertion scientifique ni résultat de validation. Leurs journaux sont conservés. La reprise des déterminants est complète.

Le lecteur des plans en représentation Fraction a ensuite été interrompu explicitement pour son coût, avant achèvement ; source et journal `KeyboardInterrupt` sont conservés. Sa version v2 représente les mêmes bornes à 192 bits par des entiers. `representation-proof.md` démontre les identités d'arrondi : somme, opposé, produit, carré, réciproque arrondie suivie du produit, racine entière. La division garde les deux étapes du noyau Fraction. Ce changement ne modifie pas les expressions des moments, les boîtes ou les seuils.

Avant application aux bornes de cette phase, `verify_representation.py` confirme **624 comparaisons arithmétiques de bornes exactement identiques** et neuf comparaisons géométriques exactes (cube, pyramide, quadrilatère gauchi, trois échelles). Aucune de ces références n'est un ratio ponctuel de la couronne. La version v2 remplace uniquement la représentation en mémoire du noyau importé ; tous les fichiers parents restent immuables. Aucun échec scientifique n'est effacé.

## Portée

Les manifestes parents sont ancrés au commit exact PR237 et tous leurs payloads sont vérifiés. Les modèles, ordres, boîtes et bornes complets sont archivés, sans dupliquer les gros fichiers dans Git. Le résumé combine les quatre déterminants hérités PR235 avec les nouveaux modèles, sur leurs mêmes feuilles exactes. La largeur exclue reste **3943/4096**, la largeur non exclue **153/4096** : ni probabilités, ni mesure du système à deux inconnues.

Ce sont des encadrements des expressions mathématiques, pas des arrondis OpenFOAM ni des branches ROOTVSMALL/VSMALL. Restent la vérification indépendante complète des angles revendiqués, les indécisions, les obligations de partage, frontière, couverture orientée, non-intersection, planéité et bilan, puis la qualité native et le repos global. Les succès nécessaires ne prouvent pas l'absence d'intersections. Parois gauchies 086/091, parois physiques et couches restent distinctes. 084 demeure incomplet et n'est pas relancé. Aucun débit, puissance ou calibration validé.
