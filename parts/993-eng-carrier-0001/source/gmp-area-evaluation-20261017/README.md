# GMP — essai d'aire exacte sans adoption

Cet essai isolé compare la fonction `exact_area` existante à deux voies GMP.
Les **110 cas** rendent exactement la même `Fraction` réduite. Sur les deux
anneaux réels, la voie entière gagne respectivement **1,097× et 1,125×** ; la
voie `mpq` est plus lente, autour de **0,70×**. Ces mesures portent sur cette
seule fonction. Aucun gain de constructeur complet ou de région n'est établi.
Le résultat ne justifie pas une nouvelle dépendance de production.

Le [reçu documentaire](archive-summary.json) conserve les 110 valeurs exactes,
les 42 mesures brutes, les médianes, CPU, temps mural, RSS, sources et
empreintes. Chaque méthode est mesurée sept fois, dans un ordre alterné,
conversions vers GMP et retour comprises. Le poste partagé n'était pas isolé.
Le benchmark utilise 6,85 s CPU et 6,89 s murales ; son RSS maximal est
46,3 Mo. La capture séparée utilise 5,27 s CPU et 128,1 Mo de RSS maximal.

## Entrées et logiciel de l'essai

Une instance privée du constructeur `81422bc8` a capturé son premier appel
d'aire à plus de 5 000 points : **5 878 points**, puis arrêt avant évaluation.
Le domaine historique de **5 876 points**, lié au reçu `757b377d`, est un
second jeu distinct. Chaque comparaison réutilise exactement les mêmes
coordonnées rationnelles de son propre jeu. La référence scalaire est la
fonction extraite par AST de la source `69b32aee`.

Un environnement Python 3.11.15 séparé contient **gmpy2 2.3.2**,
licence **LGPL-3.0-or-later**, depuis la roue ARM64 officielle de 712 466 octets.
Son SHA-256 `287060194af46c3de0853a62e89e76acec7c211c40ac2c1d9fabb7216432b642`
correspond aux métadonnées PyPI sauvegardées. Les bibliothèques embarquées
sont GMP 6.3.0, MPFR 4.2.2 et MPC 1.4.1. Les sources officielles consultées
sont la [présentation](https://gmpy2.readthedocs.io/en/stable/overview.html),
l'[installation](https://gmpy2.readthedocs.io/en/stable/install.html), les
[entiers](https://gmpy2.readthedocs.io/en/stable/mpz.html) et les
[métadonnées PyPI](https://pypi.org/pypi/gmpy2/json).

Les sources de la capture et le préfixe GMP ont été empreintés avant/après.
Aucune installation ou écriture n'a été effectuée dans le runtime AM ; aucun
prélèvement rétrospectif d'une identité complète AM avant cet essai scalaire
n'est prétendu. La recette, les producteurs, les consommateurs, les contrôleurs
et les calculs régionaux existants ne sont pas modifiés.

## Portée de cette archive

Les [scripts de capture](capture.py), [benchmark](benchmark.py),
[plan](plan.json) et [exigence de roue](requirements.txt) sont des copies
historiques exactes. Ils calculent leurs chemins depuis la disposition
originale sous `work/` et **ne forment pas un lanceur autonome depuis ici**.
Le reçu compact contient les identités des évaluations originales ; les
anciens chemins absolus sont des métadonnées, pas des entrées portables.

Les deux anneaux rationnels, évaluations complètes, documentation téléchargée,
métadonnées PyPI, roue et environnement restent dans
`work/carrier-process-20261017/gmp-exact-area-001/`. Ils ne sont pas dupliqués
dans Git. Une nouvelle exécution demanderait ces entrées exactes et les
références historiques, en plus de l'environnement séparé décrit ci-dessus.
Aucun rejeu n'est lancé par cet archivage. Cet essai ne figure pas dans la
recette de fabrication du carrier.
