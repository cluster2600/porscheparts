# Revue de la recette v3

La [recette](../../../../../manufacturing/workflows/993-carrier-lpbf-v3.json)
comporte 37 étapes et 271 fichiers épinglés. Le
[reçu](assessment.json) conserve la vérification des identités, des commandes
et de la fermeture des sources nécessaires aux calculs et aux installateurs.
Les douze premières étapes, les 45 entrées v1 et les 211 entrées v2 restent
identiques. Les archives logicielles binaires sont conservées hors Git.

Les [arguments](argv-results.json) ont été acceptés par 36 parseurs réellement
importés ; la CLI restante, à un seul chemin, a été vérifiée statiquement.
Aucun corps de commande, solveur ou tranchage n’a été exécuté par cette revue.
La [fermeture des sources](closure-results.json) distingue les dépendances
utilisées des fichiers de sortie et des anciens chemins optionnels.

Les trois reçus sont des copies exactes du contrôle effectué avant le gel.
Ils ne constituent pas un rejeu complet du carrier. Les passages réels et
leurs admissions gardent leurs résultats propres.
