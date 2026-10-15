# Validation

Les trois nouveaux conteneurs sont terminés et conservés, sans OOM. 066 reste
refusé malgré la réussite du raccord : son contrôle natif final s'arrête.
067 passe le contrôle étendu sans changement de seuil. Aucun champ physique,
condition du turbo réel ou solveur n'est modifié ; aucun écoulement lancé.

Les lecteurs comprennent des assertions de parenté, bijection, cycles orientés,
fermeture et volumes ; le contrôle de cycles refuse explicitement une inversion.
Tous les payloads sources et natifs sont hachés et relus. La reconstruction
indépendante et l'admission native sont distinctes.

Les tests et journaux de make check sont conservés dans l'archive. Les scripts
s'exécutent depuis la racine avec work/bionic-tools/bin/python. Pour make,
utiliser PATH=work/bionic-tools/bin:$PATH, et non la seule variable PYTHON.

La copie de read_geometry.py conserve son champ original_point_rounding_m :
il compare les sommets à la construction analytique de 063. La comparaison
native 063/067 dans topology-readback.json trouve au contraire zéro écart de
coordonnées. Ne pas confondre ces deux références.

Tests turbo : 109 exécutés en 15,575 s, 108 réussis et un ignoré.
make check : 3 896 tests en 225,574 s, 172 ignorés ; les deux échecs de
comparaison flottante WE43/fan_stator et trois erreurs rtree/networkx hors turbo
restent présents. Le contrôle global local n'est donc pas vert. Aucun de ces
cinq problèmes n'est corrigé dans cette phase.
