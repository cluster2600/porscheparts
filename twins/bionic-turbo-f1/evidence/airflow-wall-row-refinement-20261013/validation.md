# Validation de 085/086

- Deux exécutions natives distinctes, reçus relus : code zéro, aucun OOM, `Mesh OK`, aucun solveur d’écoulement. Aucun cas antérieur relancé.
- `read_refinement.py` : toutes les empreintes de sortie et les copies préalables vérifiées ; bisection reconstruite indépendamment, bijections de points/cellules/faces orientées, propriétaires/voisins, fermeture par cellule, volumes positifs, conservation du raccord et de la frontière orientée.
- `read_zones.py` : les 7 424 anciens membres de frozenPoints restent exactement présents une fois ; aucun des 256 nouveaux points des fermetures n’est inclus.
- 109 tests turbo exécutés en 15,857 s : 108 réussites, un ignoré.
- `PATH="$PWD/work/bionic-tools/bin:$PATH" make check` : 3 896 tests en 221,481 s, 172 ignorés, deux échecs et trois erreurs. Ce contrôle local n’est pas entièrement vert.

Les problèmes hors turbo sont inchangés : comparaisons flottantes WE43 et fan_stator ; dépendances `rtree`/`networkx` dans les tests thermiques et le contre-essai PicoGK. Le journal complet est conservé. Aucune correction opportuniste ni aucun seuil abaissé.

Le défaut de planéité global de 086 reste 6,79208e−7 m dans ce domaine fixe. Le résultat n’est pas une qualification de parois physiques ou de couches, de protection de la castellation, de repos global, de convergence linéaire, de stabilité ou de performance du turbo. Les métriques de rotation du raccord sont purement géométriques.

Les inputs, les maillages natifs, les logs, les reçus, la référence officielle et les lecteurs sont archivés avec inventaire SHA-256. Les payloads du paquet sont relus localement ; les cinq actifs publiés sont contrôlés par tailles et digests GitHub, sans prétendre à un second téléchargement distant intégral. Le reçu distant est livré séparément après publication.
