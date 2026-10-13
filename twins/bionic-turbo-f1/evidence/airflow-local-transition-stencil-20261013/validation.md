# Validation

- Tous les payloads des reçus 086/091 sont relus avant extraction ; aucun OOM enregistré dans ces reçus. Aucun nouveau calcul natif, aucun solveur ou conteneur créé pour cette phase.
- L'extracteur v2 reconstruit globalement 16 832 parents avec un descendant et 3 520 parents avec huit descendants. Il sélectionne deux ensembles complets et vérifie les chaînes d'arêtes et la connexion par faces.
- Le lecteur indépendant v2 confirme tous les points, faces orientées, owner/neighbour, incidences des cellules, signes des coupes, ancres de parenté et règle exacte de sélection. Les fichiers independent-readback.json et independent-readback-v2.json distinguent les deux lectures.
- L'échec de sérialisation NumPy de l'extracteur v1 est conservé dans extraction.log ; v2 ne change que la conversion des labels parents en int Python. Le premier lecteur indépendant réussissait déjà ; v2 ajoute le contrôle du voisinage sélectionné.
- Tests turbo : 109 exécutés en 15,362 s, 108 réussis et un ignoré.
- `PATH=work/bionic-tools/bin:$PATH make check` : 3 896 tests en 210,656 s, 172 ignorés ; deux échecs d'égalité flottante WE43/fan_stator et trois erreurs de dépendances rtree/networkx hors turbo, déjà présents dans les phases parentes. La validation locale générale n'est pas verte. Journal complet conservé.

Les complexes n'ont pas passé checkMesh et ne sont pas présentés comme des cas OpenFOAM. Aucun stencil correctif, admission d'écoulement, convergence, stabilité ou performance physique n'est établi. Les données 091 restent rejetées et le contrôle de repos 084 reste incomplet.
