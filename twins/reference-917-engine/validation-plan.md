# Plan de validation du jumeau 917

## Niveaux

| Niveau | Contenu | Passage requis |
|---|---|---|
| F0 | scan brut et empreinte | provenance, licence et identité documentées |
| F1 | surfaces, enveloppe et interfaces visibles | unité et trois cotes physiques confirmées |
| F2 | assemblage sémantique | chaque sous-ensemble identifié et recalé |
| F3 | volumes internes | CT, démontage ou métrologie directe |
| F4 | thermique, structure et écoulement | matières, contacts et conditions mesurées |
| F5 | corrélation | essai physique instrumenté et incertitude publiée |

Le projet actuel s'arrête à `F1_exterior_reference`. Le STL d'exposition est un
produit dérivé du F1 et ne fait pas progresser la fidélité moteur.

## Impression de maquette

1. contrôler la cote physique qui fixe l'échelle ;
2. comparer visuellement le STL fermé au scan de référence ;
3. mesurer les détails minimaux après mise à l'échelle ;
4. simuler supports, temps, matière et collisions dans le slicer réel ;
5. imprimer un secteur test comportant ailettes, alésage et goujons ;
6. corriger le modèle avant l'impression complète.

Pour un modèle métal d'exposition, ajouter la poudre prisonnière, les supports,
la distorsion, la découpe du plateau, le grenaillage et l'usinage éventuel. Cela
ne transforme pas le scan en conception de moteur fonctionnelle.

## CFD de refroidissement externe

Le premier cas sert uniquement à qualifier la chaîne de maillage. Avant un
solveur :

1. réparer les faces dupliquées et les connexions de surface ambiguës ;
2. raffiner localement les ailettes et passages d'air importants ;
3. obtenir `checkMesh` sans échec ;
4. confirmer l'échelle, l'orientation et la direction réelle du flux ;
5. définir les débits, pressions et températures avec leurs sources ;
6. ajouter le solide et les matières pour un calcul thermique conjugué ;
7. corréler pression, débit et température sur un essai physique.

## Données bloquantes

- texte exact de la licence Wolfe Classics, droit de redistribution et rapport
  indépendant sur la précision déclarée de 0,5 mm ;
- variante exacte du 917 représentée et signification de `0.5mm` ;
- unité du scan et au moins trois dimensions de contrôle ;
- nomenclature des deux composants détachés ;
- géométrie interne, matières, masses et contacts ;
- conditions aérodynamiques et thermiques mesurées.
