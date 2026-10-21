# Inclusion exacte des domaines continus

`exact_polygon_coverage.prove_polygon_covered(source_polygon, target_polygon)`
renvoie un reçu `passed` ou `refused`, avec empreintes WKB et témoins rationnels.
Les deux entrées doivent être des `Polygon` valides et non vides, contrôlés par
GEOS. Les `MultiPolygon` sont explicitement refusés : le constructeur appelle
ce contrôle séparément pour chaque intervalle libre connecté.

La preuve n'utilise aucun overlay ni seuil de proximité. Chaque arête source
est découpée à toutes les intersections rationnelles avec la cible ; ses sommets
et chaque intervalle entier sont contrôlés. Une fois toute la frontière source
couverte, une composante du complément de la cible ne peut traverser cette
frontière. Un point rationnel intérieur de chaque trou cible suffit alors à
détecter un trou entièrement contenu dans la matière source. Le complément
extérieur, relié à l'infini, ne peut être contenu dans une source bornée.
Le noyau `exact_contacts.py` est chargé par chemin avec son SHA figé.

Le [témoin réel chart35](polygon-coverage-evidence/chart35-assessment.json)
conserve le refus de l'union GEOS initiale : elle crée un trou d'aire exacte
positive, environ `7,494598039e-18 mm²`. Le hull des triangles décalés n'est pas
en cause : pour une pénétration positive, les deux arrondis IEEE `z-p` et `z+p`
encadrent toujours `z`.

Sur ce seul témoin, la construction
`D.union(union_all(sweeps).intersection(allowed))` passe les deux inclusions
`D ⊆ résultat ⊆ allowed`. Ces reçus locaux ne constituent pas une admission du
support complet. Le constructeur doit reproduire les deux preuves pour chaque
intervalle réel et conserver leurs liens de géométrie jusqu'au scellement.

Vérification ciblée :

```sh
work/part-workflow/runtimes/pyslm-coverage-011/env/bin/python -B -m unittest tests.test_carrier_exact_polygon_coverage -v
```

Les dix tests couvrent notamment un bord qui traverse une encoche malgré ses
sommets couverts, un trou d'une ULP de large, les trous de la source, le refus
des îlots `MultiPolygon` et la reproduction intégrale des quatre reçus réels.
