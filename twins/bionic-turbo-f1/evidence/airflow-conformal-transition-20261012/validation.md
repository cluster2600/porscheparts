# Vérifications

108 tests turbo réussissent, un est ignoré (109 tests, 15,576 s).
Les nouvelles constructions et lectures comportent des assertions de
refus avant calcul : orientation, arêtes partagées, empreintes, topologie,
parois, interface, volumes, planéité et critères géométriques. Les trois
exécutions natives sont conservées, avec leurs reçus et leurs payloads.

057 échoue pendant la création de topologie, code 134 sans OOM. 058
corrige exclusivement l'encodage des faces de fermeture des blocs ;
read_pair.py vérifie les sommets, blocs, gradations, zones et ensembles
de sommets de frontière identiques. CheckMesh admet 058. Le lecteur de
058 contrôle tous les points et toutes les faces, ferme les chaînes
d'arêtes de chaque cellule et compare le volume à une intégrale analytique.

059 termine ses 200 pas en 181,148 s, code zéro sans OOM. Tous les champs
finaux p/T/U sont relus, finis et cohérents avec les extrema. Le repos
respecte les seuils inchangés ; 800 plafonds de pression empêchent une
qualification de convergence linéaire. Aucun gain de performance du turbo
n'est évalué. Les prismes restent hors zone tournante.

Le premier make check, lancé avec une variable PYTHON non utilisée par
la cible test du Makefile, a exécuté Python système 3.10 : 3 810 tests,
230 ignorés, deux échecs flottants et 26 erreurs, notamment imports SciPy.
Son journal est conservé. Une nouvelle invocation impose le PATH de
work/bionic-tools/bin pour sélectionner Python 3.11 et les dépendances
utilisées par les tests turbo. Cette invocation exécute 3 864 tests en 210,404 s, 172 ignorés :
les deux échecs flottants WE43/fan_stator et trois erreurs rtree/networkx
hors turbo déjà connus subsistent. Aucun nouveau problème turbo.

Les 75 fichiers de l'archive sont relus localement ; les cinq actifs
GitHub sont vérifiés par tailles et SHA-256. Aucun second téléchargement
intégral n'est revendiqué. L'archive conserve les sources, le refus 057,
les maillages et les champs natifs ; les contrôles Python et make sont
publiés séparément dans Git. Le premier appel de publication avec un SHA
abrégé est refusé par GitHub (422) ; le SHA complet publie la même archive.
Les fichiers natifs conservent leurs fins de lignes et espaces.
