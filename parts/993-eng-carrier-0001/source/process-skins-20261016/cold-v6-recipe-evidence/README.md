# Revue de la recette froide v6

Ces quatre JSON sont des copies exactes des reçus conservés dans
`work/part-workflow/cold-v6-recipe-review-001/`. Ils décrivent les commandes,
leurs dépendances et leurs identités ; ils ne constituent pas un rejeu complet
de la pièce. Les références aux scripts ponctuels et journaux du dossier de
travail restent des références à cette exécution, pas des fichiers fournis ici.

- [Bilan](assessment.json) : 37 étapes, 293 empreintes et les 285 anciennes conservées.
- [Commandes](argv-results.json) : dix commandes effectivement parsées ; 27 contrats repris après identité stricte de leurs objets, sources et runtime.
- [Dépendances](closure-results.json) : nouvelles dépendances couvertes, snapshots des générateurs, fichiers bootstrap et absence de collision de sorties.
- [Différence exacte](exact-delta.json) : huit sources ajoutées, douze premières étapes inchangées, neuf budgets de 14 400 s et nouveau reçu d’exécution des admissions déclaré.

Le lanceur v2 change seulement sa borne de durée et le texte correspondant,
de 3 600 à 14 400 s. Les contrôles de chemins, d’empreintes, de journaux et
d’arrêt du groupe de processus restent identiques. Les nouvelles générations
utilisent les producteurs v7, puis le préparateur et le guide v6.

La campagne en cours garde ses véritables versions productrices antérieures
et son extension de ressources distincte. Ni les checkpoints ni les anciens
refus ne sont réétiquetés par cette recette. Les sept régions, les six
admissions et les deux audits de trajectoires doivent être réussis sur les
fichiers effectivement remis avant de produire le guide final.
