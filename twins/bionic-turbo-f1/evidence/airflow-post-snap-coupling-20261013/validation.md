# Validation 082/083

Les deux opérations natives sont terminées, code zéro sans OOM et Mesh OK,
sans solveur d’écoulement. Tous les payloads et les copies d’entrées prises
avant exécution sont relus avec SHA-256. Le lecteur de préparation vérifie
l’identité des fichiers fondamentaux aux parents, sauf le changement explicite
des seules métadonnées du patch temporaire tournant.

Le lecteur topologique revalide les cartes 078, la conservation de 082, puis
l’ensemble des cellules, faces orientées, propriétaires et voisins de 083 par
bijection indépendante. Il vérifie les coordonnées exactes du domaine composé,
rotorZone, les arêtes fermées et volumes positifs, les types par zone, les quads
MRF et les bilans géométriques. Le retrait des deux patches vides ne modifie
aucune géométrie. Les cartes héritées obsolètes ne sont pas copiées.

- Tests turbo : 109 exécutés en 18,755 s, 108 réussis et un ignoré.
- `PATH=work/bionic-tools/bin:$PATH make check` : 3 896 tests en 320,257 s,
  172 ignorés ; mêmes deux échecs flottants WE43/fan_stator et trois erreurs
  rtree/networkx hors turbo. Le contrôle global local n’est pas vert.
- Analyse AST des scripts et lecture JSON des rapports : réussies.

Aucun calcul natif répété, aucun test de repos nouveau. Les surfaces synthétiques
projetées et leur volume restent différents de la cible originale ; les faces
gauchies fixes persistent. Aucun contrôle de raffinement, de couches ou de
parois physiques n’est implicite dans le succès du raccord. Aucun débit, gain
de puissance, convergence ou stabilité de perturbations qualifié.
