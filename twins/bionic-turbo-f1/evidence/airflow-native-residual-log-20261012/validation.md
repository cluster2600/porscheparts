# Vérification

Les tests turbo donnent 108 réussites et un ignoré. make check exécute
3 859 tests en 213,604 s, avec 172 ignorés, deux échecs flottants et trois
erreurs rtree/networkx hors turbo. Les journaux sont conservés. Aucun seuil
ni test extérieur n'est modifié pour obtenir un succès.

Le lecteur de journal possède un témoin avec produit L1 connu, une ligne
secondaire à ignorer et un refus de cycle manquant. Les contrôles natifs
vérifient les reçus et toutes les empreintes, les modifications exactes des
entrées, les effectifs owner/neighbour et les champs finaux finis. La parité
requise est octet pour octet, sans tolérance ajoutée.

La précision affichée du facteur et des résidus est d'environ 16 chiffres
significatifs. Le produit n'est donc pas une relecture indépendante du
vecteur résidu en mémoire ; les chiffres présentés dans le README sont
arrondis. Les traces intermédiaires complètes restent archivées. Les valeurs
algébriques ne reçoivent pas d'unité physique non mesurée et ne suffisent
pas à établir convergence, stabilité ou performances.
