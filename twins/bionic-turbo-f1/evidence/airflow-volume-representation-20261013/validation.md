# Validation

Lecture indépendante complète : 18560 faces, 6144 cellules et 282240 polynômes/encadrements, tous coefficients et bornes exactement identiques. Faces par gabarits hex réduits, algèbre creuse/Casteljau, produits triples par permutations ; volumes par origine fixe et écarts de flux par double somme. Le nouvel évaluateur n'est pas importé. Les sources et domaines de dix manifestes ancrés à PR240 et leurs 237 entrées sont vérifiés avant calcul. Tous les triangles de face ont une aire non nulle et les 119808 tétraèdres ont une orientation positive sur le domaine entier. Aucun ratio ponctuel, grille ou subdivision.

Aucune assertion refusée ni installation dans cette phase. Calcul principal 61,050 s ; lecture indépendante 63,271 s, pas des benchmarks CFD. Le lecteur structural read_totals.py confirme la somme constante des volumes signés et les 6144 bornes d'écart au volume natif exactement nulles. Il ne constitue pas une deuxième reconstruction indépendante.

108 tests turbo réussis, un ignoré, 15,393 s. make check : 3911 tests en 215,598 s, 172 ignorés, deux échecs flottants WE43/fan_stator et trois erreurs rtree/networkx hors turbo. Les cinq noms sont comparés exactement à PR240 dans validation.json. Le résultat local global n'est pas déclaré vert. Sources, journaux, codes de retour et modèles sont archivés.

La représentation des triangles/quads et l'égalité de volumes signés sont établies ; les centres volumiques ne sont pas remplacés ni déclarés égaux. La non-intersection globale, l'indice de la frontière 3D, les arrondis et branches natives, la qualité native, le repos et les performances restent ouverts. Aucun ancien calcul ou solveur relancé.
