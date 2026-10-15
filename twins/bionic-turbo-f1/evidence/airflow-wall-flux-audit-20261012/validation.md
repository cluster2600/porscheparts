# Vérifications

Les deux lecteurs sont exécutés sur les payloads natifs conservés. Toutes
les empreintes des reçus sont vérifiées ; les résultats JSON reproduisent
exactement les lectures initiales. La version v2 conserve les nombres et
corrige seulement la formulation sur la densité d'assemblage inconnue.
Le lecteur scalaire accepte un témoin connu et refuse une liste tronquée.
Aucun fichier des cas natifs n'est écrit et aucun solveur n'est lancé.

108 tests turbo réussis, un ignoré. make check exécute 3 851 tests en
233,892 s, 172 ignorés : mêmes deux échecs de comparaison flottante et
mêmes trois erreurs rtree/networkx hors turbo. Les journaux complets sont
conservés. Le nombre global a augmenté sur main depuis la phase 051,
sans changement des tests turbo dans cette phase.

Les petits lecteurs et rapports sont dans Git. Les champs volumineux
restent dans les archives antérieures déjà publiées ; leurs empreintes
sont vérifiées localement, sans prétendre à un téléchargement distant
supplémentaire. Les sources officielles consultées sont référencées par
URL, taille et SHA-256. Aucun changement des anciens fichiers épinglés.

Ce contrôle ne qualifie ni le résidu de matrice à l'assemblage, ni la
stabilité de perturbations, ni le maillage ou les performances du turbo.
