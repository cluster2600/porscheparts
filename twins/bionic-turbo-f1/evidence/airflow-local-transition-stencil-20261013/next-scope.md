# Suite bornée

Les deux ensembles exacts sont disponibles pour évaluer un stencil conforme, mais aucun stencil correctif n'est encore construit. Avant une opération native, expliciter les faces conservées et divisées, les contraintes de partage avec les cellules voisines, les points nouveaux et les volumes. Une correction locale ne peut laisser des faces incompatibles à la frontière de la sélection.

Ne pas utiliser splitCells comme correction automatique des 6 700 labels : ses hypothèses et sa coupe géométrique ne qualifient pas ces faces gauchies. Une expérimentation éventuelle devra être une nouvelle version, avec critère et opération explicités avant lancement, et préserver les rejets. La présente extraction ne prouve ni qu'une correction locale suffira ni qu'elle sera impossible.

Conserver les quads du raccord, toutes les surfaces réelles, les connexions et la séparation roue–écrou 033. Aucun balayage d'angle, de niveaux ou de tolérances ; aucun assouplissement des seuils. Ne pas relancer 091 ou 084. Le repos 20 µs de 084 reste incomplet. Aucun écoulement du vrai turbo avant toutes les admissions requises.
