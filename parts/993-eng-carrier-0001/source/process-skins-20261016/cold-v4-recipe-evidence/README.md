# Revue de la recette v4 et des références du guide

Ces quatre reçus sont copiés sans modification depuis
`work/part-workflow/cold-v4-recipe-review-001/`. Le propriétaire de la chaîne
a revérifié les 278 empreintes et l’identité des 36 premières étapes avec v3.

- `assessment.json` relie la recette, les trois autres reçus et leur portée.
- `argv-results.json` vérifie 37 contrats : 36 preuves v3 réutilisées après
  égalité des étapes, arguments, sources et manifeste de runtime ; le nouvel
  argumentaire du guide v4 est réellement parsé.
- `closure-results.json` vérifie les dépendances consommées et les sorties.
- `retained-reference-readonly-binding.json` vérifie les identités réelles du
  maillage 9 et du jeu linéaire K1000 du passage `run-001`, puis les seize
  états conservés. Le bilan Piola passe ; le diagnostic ENER reste refusé.

Le guide v4 ajoute les résultats constitutifs et leur figure sans modifier
les générateurs de supports ni les admissions. Les exports STEP distincts ne
sont pas assimilés. Cette revue ne relance ni DAT, ni solveur, ni tranchage,
et ne produit aucun guide final. Les sorties réelles du carrier conservent
leurs admissions propres.
