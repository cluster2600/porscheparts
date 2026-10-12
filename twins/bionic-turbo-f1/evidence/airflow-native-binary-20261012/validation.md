# Vérification de la préparation native

108 tests turbo réussissent, un est ignoré. make check est exécuté ; le
journal complet est joint. Les deux échecs flottants cooling_impeller_we43
et fan_stator, ainsi que les trois erreurs de dépendances rtree/networkx
dans impeller_lpbf, organic_fan et picogk_exact_zero_countertrial restent
hors turbo. Aucun changement hors périmètre pour masquer ces résultats.

Vérifications propres à cette phase : 27 092 fichiers sources originaux
comparés à l'archive ; refus du système de fichiers insensible à la casse ;
compilation sans modification du solveur ; deux cas natifs neufs terminés
sans OOM ; entrées et commandes appariées ; tous les payloads hachés ;
cinq champs finaux identiques octet pour octet et relus comme valeurs finies.
Le lecteur v1 est conservé avec son refus de comptage owner seul ; v2 utilise
owner et neighbour, contrôle les effectifs et refuse un vecteur tronqué.

Les 134 fichiers de l'archive, dont les sources officielles, le binaire,
les journaux et refus de compilation, les recettes et les deux cas natifs,
sont relus localement. Les cinq actifs GitHub sont vérifiés par tailles et
SHA-256 distants. Aucun second téléchargement intégral n'est revendiqué.
Les volumes et conteneurs locaux sont conservés ; aucune suppression.

Les espaces natifs des journaux checkMesh sont conservés pour préserver
les empreintes. Aucun ancien fichier épinglé n'est modifié. Ce contrôle
logiciel dure deux pas et ne constitue pas une qualification de convergence,
de stabilité, d'indépendance au maillage ou de performances du turbo.
