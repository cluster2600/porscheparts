# Suite — portée du raccord raffiné

087/088 sont terminés et ne doivent pas être relancés. La réunion du sous-domaine raffiné avec les prismes tournants conservés est vérifiée topologiquement et admise nativement. Aucun nouveau test de repos n’est effectué et les résultats 064/076 ne se transposent pas à ce domaine. 084 reste incomplet au budget, sans champs finaux : ne pas prolonger, relancer ou changer les seuils pour obtenir un succès.

Avant de passer aux surfaces réelles, il faut définir une opération de construction de sous-domaine qui préserve les faces du raccord pendant création/raffinement des cellules autour des parois. La bisection d’une rangée hexaédrique complète est prouvée ici, pas la castellation sur un STL de pales ni un maillage général. Lire les contraintes des outils natifs et construire un nouveau témoin borné seulement s’il teste cette opération distincte. Ne pas détourner les zones de fermeture de trous ou imposer un couplage fictif.

Une projection ultérieure doit reconstruire les points gelés des fermetures, y compris les nouveaux milieux de 086. Les couches physiques et leur admission doivent être traitées séparément ; les faces fixes gauchies restent à considérer. Les surfaces réelles, le profil 027/030, l’anneau arrière, la séparation roue–écrou de 033, les patches et connexions doivent être conservés. Le vrai maillage 033 reste rejeté ; aucun écoulement forcé complet n’est autorisé avant admission et repos global.

Un changement de protocole d’exécution pour qualifier le repos serait une expérience distincte à justifier et comparer, sans continuation invisible de 084. Aucune nouvelle exécution, perturbation, dimension physique ou réglage de solveur n’est préparé ici.
