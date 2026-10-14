# Orthogonalité additive — application et lecture achevées

La nouvelle application conserve ROOTVSMALL dans D/(sqrt(Q)+ROOTVSMALL), avec D signé et centres issus des moments natifs. Les 153 boîtes fermées sources, u=q_m, sont toutes conservées. Aucun ratio ponctuel, subdivision, candidat, natif ou solveur.

Les 1 453 440 lignes comportent 1 444 498 bornes positives et 8 942 indécises, zéro refus certain. Les 9 470 angles variables réutilisent leurs D,Q PR239 : 1 440 051 positives et 8 859 indécises. Les deux témoins récupèrent Q par D²/(R+kappa) : 223 positives et 83 indécises. Les 4 224 faces internes constantes ont toutes une borne positive sur l'enveloppe. Les 4 864 walls non couplées restent à la valeur source 1 ; les 384 MRF sont internes constantes.

Le lecteur confirme chacune des 1 453 440 bornes par inclusion et chaque signe revendiqué, ainsi que 8 448 intervalles D,Q des constantes. Pour la matrice et les témoins, c'est une vérification indépendante de la nouvelle application arithmétique et de sa jointure ; leur géométrie héritée n'est pas rejouée. Pour les constantes, incidences et moments sont reconstruits indépendamment avec les gabarits réduits et les sources PR236/238 épinglées.

read_summary.py confirme structurellement la couverture de 18 560 faces par boîte : 83 boîtes, labels 1848–1930, sont entièrement positives pour cette expression additive. Ce n'est pas une admission. Les autres boîtes restent indécises, sans exclusion nouvelle. La récupération de Q des témoins élargit conservativement les intervalles ; elle ne réfute pas les anciens certificats d'angles sans additif. Les deux boîtes 1929/1930 conservent leurs indécisions de déterminants. Aucune boîte n'est sélectionnée comme candidat.

La plus petite borne inférieure positive utilisée vaut environ 0.3420215798000612, dans la matrice, boîte 1813, rang 72 ; elle n'est pas une valeur à un ratio choisi. Les minima indécis sont conservés séparément. Le comparateur est le cosinus mathématique de 70 degrés via sqrt(kappa) épinglé. Le seuil source est mutable ; degToRad, libm, configuration effective, conversion writePrecision 16 et arrondis du futur binaire ne sont pas qualifiés.

Quatorze références par programme passent AVANT application, dont trois paires de cubes cohérents dont volumes, centres, aires, D,Q sont vérifiés. Les autres références sont explicitement arithmétiques. Six membres officiels sont relus ; 17 manifestes et 419 entrées sont ancrés au commit b18528da4ac7abc26ce6114b3720e8d1d91fc8d3. Programmes et prescription figés avant application, aucun refus scientifique ni installation. Primaire 88.734 s ; lecteur 102.847 s. Les tests chevauchent ces calculs : ces durées ne sont pas des benchmarks CFD.

Tests turbo : 108 réussis, un ignoré. make check conserve les six labels de diagnostic hors turbo de PR250 ; validation.md précise les comptes et durées. La matrice, les D,Q constants, les Q récupérés et les journaux sont archivés, seuls les reçus et scripts légers vont dans Git.

Aucune admission native, repos, convergence, stabilité, indépendance maillage/temps, CFD, débit, puissance ou calibration validés. Voir next-scope.md pour checkFaceTets et les autres obligations ouvertes. 084 n'est pas rejoué.
