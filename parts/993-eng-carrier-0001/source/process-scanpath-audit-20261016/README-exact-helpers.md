# Prédicats convexes et normalisation locale des trous

Ces deux helpers sont distincts des sources gelées des générations précédentes.
Ils ne modifient aucun maillage, calendrier ni seuil d'admission.

`CompiledConvex(vertices)` dans [exact_convex_halfplanes.py](exact_convex_halfplanes.py)
valide une frontière convexe orientée en coordonnées `Fraction`, puis compile
ses demi-plans en coefficients entiers. `contains(point)` inclut le bord fermé ;
`contains_triangle(triangle)` contrôle les trois sommets d'un triangle de surface
exactement positive. Aucun point n'est arrondi. Lorsque la triangulation positive
est déjà certifiée, trois appels à `contains` évitent de refaire cette validation.

Le [reçu de comparaison](compiled-convex-results.json) porte sur les **mêmes
768 paires candidates**, soit 102 triangles et 95 convexes du témoin existant.
Toutes les réponses et les premières identités de convexes sont identiques à
celles du prédicat rationnel générique. Sur trois répétitions, la recherche par
trois points passe de 50,67 à 2,61 ms en médiane ; la compilation prend 15,99 ms,
soit un gain de 2,72 avec compilation sur ce petit témoin. Ce n'est pas une
mesure du temps total du générateur. Le helper n'a pas été intégré dans un job
déjà lancé.

`normalize_holes(result, primitives, allowed)` dans
[exact_intended_holes_v2.py](exact_intended_holes_v2.py) reprend le partitionneur
rationnel gelé, vérifié par son SHA. Il peut examiner un trou auto-croisé ou
non convexe, mais conserve un extérieur valide. Le hull proposé est certifié
par ses sommets d'origine et tous ses demi-plans fermés. Chaque segment du trou
est donc entièrement dans ce hull, par linéarité. Le trou est retiré uniquement
si le **hull entier** est couvert par l'union intentionnelle et par `allowed`.
Un trou sans certificat reste conservé ; un résultat final invalide est refusé.
La reconstruction reprend les coordonnées de l'extérieur et des trous retenus,
puis vérifie leur égalité exacte. Aucun nouveau sommet, `buffer` ou `make_valid`
n'est utilisé. Le reçu lie chaque primitive, `allowed`, l'entrée et le résultat
par leurs SHA WKB.

Le [témoin réel source008](hull-hole-evidence/source008-inputs.json), lui-même lié
par son SHA dans le test, contient deux trous dont un auto-croisé. Le
[rejeu compact](hull-hole-evidence/results.json) conserve les preuves de hull,
l'identité du résultat et une contrepreuve rationnelle du contrôle final.
Les deux trous sont retirés avec certificat, l'extérieur reste identique et
le polygone devient valide. `D ⊆ R` et `R ⊆ allowed` passent.

**Le confinement final de ce R dans la bande intentionnelle exacte reste
REFUSÉ.** Le premier triangle refusé garde une aire non couverte strictement
positive d'environ `2,00646e-22 mm²`, avec sa valeur rationnelle et les cellules
témoins conservées. La normalisation seule réussit ; cette région de supports
n'est pas admise. Les inclusions finales restent obligatoires chez l'appelant.

Les preuves brutes du rejeu sont conservées sous
`work/carrier-process-20261016/intended-holes-v2-002/`, avec leurs SHA dans le
reçu compact. Aucun générateur de supports ni calcul natif n'a été relancé.

Vérification ciblée depuis la racine du dépôt :

```sh
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  work/part-workflow/runtimes/pyslm-coverage-011/env/bin/python -B -m unittest \
  tests.test_carrier_exact_convex_halfplanes tests.test_carrier_intended_holes_v2 -v
```

Les 15 tests passent : orientation et bords fermés, fractions non dyadiques,
lamelle positive sans epsilon, entrées invalides, immutabilité, équivalence
réelle, trous authentiques ou partiellement couverts conservés, hull falsifié
refusé, conservation des coordonnées et capture source008. Les témoins qui
requièrent Shapely sont ignorés lorsque ce runtime optionnel manque.
