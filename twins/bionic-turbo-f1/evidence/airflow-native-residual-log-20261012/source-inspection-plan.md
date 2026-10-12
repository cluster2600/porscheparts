# Diagnostic natif : hypothèse à tester, sans modification C++

Lecture seule du source officiel v2406 dont la provenance est publiée dans airflow-native-binary-20261012. Aucun nouveau cas ni calcul lancé.

GAMGSolverSolve.C imprime le facteur de normalisation et les résidus de chaque cycle si `log >= 2`. lduMatrixSolver.C lit `log` dans le dictionnaire du solveur. Le produit du résidu normalisé et de ce facteur correspond à la somme L1 des valeurs absolues du résidu algébrique, à la précision du journal. Il ne donne ni le maximum par cellule ni une erreur physique. Vérifier la précision effectivement écrite, les unités issues de la matrice et l'association exacte facteur/résolution avant toute conclusion.

Prochain témoin minimal : copier uniquement les entrées vérifiées de 052 dans un nouveau cas, changer uniquement `log 2` dans le solveur p (pFinal hérite), conserver exécutable original/runtime/maillage/équations/pas/tolérances, deux pas bornés. Exiger identité octet pour octet des cinq champs finaux avec 052 et vérifier toutes les empreintes. Conserver journal complet et reçu natif. Ne pas relancer 052/053. Une comparaison courte ne prouvera pas la neutralité sur 20 µs.

Le functionObject natif solverInfo avec writeResidualFields existe aussi, mais est distinct et ne doit pas être ajouté au même témoin. Il initialise le stockage après la première itération. solverInfoTemplates.C publie la première résolution du dictionnaire, pas forcément la dernière. solverInfo.C écrit un champ de résidu initial étiqueté dimless : cette étiquette ne prouve pas une grandeur physique sans dimension. Examiner aussi lduMatrix::setResidualField et meshState avant usage ; ne jamais appeler cette sortie un résidu final.

Préférer ces diagnostics existants à l'instrumentation C++ tant qu'ils suffisent. Aucune qualification de convergence ou de performances n'est acquise par cette inspection.

Lecture complémentaire : lduMatrix::setResidualField ne remplit le résidu initial, en présence de meshState, que lorsque isFirstIteration() est vrai. Il ne remplit alors pas le stockage final. Le mode log 2 imprime aussi la résolution du niveau grossier : le futur lecteur doit distinguer explicitement les lignes GAMG de ces lignes secondaires, et vérifier le nombre de résolutions et de pas.
