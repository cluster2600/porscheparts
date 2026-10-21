# Revue de la recette v5

Ces trois reçus sont copiés sans modification depuis
`work/part-workflow/cold-v5-recipe-review-001/`. Le propriétaire de la chaîne
a revérifié les 285 empreintes, dont les 278 entrées v4 inchangées.

- `assessment.json` relie la recette aux deux autres reçus et à leur portée.
- `argv-results.json` vérifie 37 contrats : les dix commandes modifiées sont
  réellement parsées ; les 27 autres preuves sont reprises après égalité des
  étapes, arguments, sources et manifeste de runtime.
- `closure-results.json` vérifie les dépendances consommées et les sorties.

Les générateurs v6 conservent les domaines et les paramètres de supports.
Une bande dirigée vers l'intérieur n'est omise que si son quadrilatère entier
est déjà contenu dans le domaine source, par preuve exacte. Les autres cas
restent refusés. Chaque appel de construction conserve désormais ses entrées
et son résultat complet. Le préparateur v5 choisit la construction d'après
l'autorité réellement enregistrée ; il ne réétiquette aucun ancien reçu.

Le guide v5 conserve les références constitutives et les contrôles du guide
v4 ; sa commande de reproduction désigne cette nouvelle recette. Cette revue
ne relance aucun calcul complet, tranchage ou solveur et ne produit pas de
guide final. Les sorties réelles gardent leurs admissions propres.
