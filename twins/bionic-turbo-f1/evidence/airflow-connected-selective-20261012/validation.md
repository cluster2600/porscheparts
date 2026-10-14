# Validation et périmètre

Les reçus natifs, toutes les entrées préparées et les sorties sont relus par
SHA-256. Les lecteurs vérifient points, faces, owner/neighbour, rotorZone, cible
STL, déplacements et bilan géométrique par cellule. Les entrées 073/074 sont
identiques ; 074/075 ne diffèrent que par nSolveIter 100→0. Les coordonnées de
frontière 074/075 sont exactement identiques après projection. Dans 075, tous
les points des cellules tournantes sont identiques à leurs coordonnées initiales.

Les seuils géométriques restent inchangés ; l'identité observée vaut zéro écart,
non une tolérance élargie. 074 reste refusé pour la suite CFD. Les résidus
volumiques de rotation sont géométriques, jamais des débits d'air physiques.

Le nouveau test de repos 076 utilise le maillage 075. La comparaison avec 064
vérifie les mêmes critères et tous les fichiers préparés hors polyMesh identiques
obtenus depuis 026. Deux fichiers de maillage changent (points et boundary) ;
six fichiers auxiliaires polyMesh issus de snappy s'ajoutent. L'entrée de champ
defaultFaces devenue inutilisée est conservée. Le domaine synthétique diffère,
aucune comparaison de performances physiques n'en résulte.

Tests turbo : 109 exécutés en 15,981 s, 108 réussis et un ignoré.
make check : 3 896 tests en 224,936 s, 172 ignorés ; mêmes deux comparaisons
flottantes WE43/fan_stator en échec et trois erreurs rtree/networkx hors turbo.
Le contrôle local complet reste non vert ; journaux intégraux conservés.
Les assertions des lecteurs et de la vérification des membres officiels passent.

076 : fin native vérifiée, 200 échantillons jusqu'à 20 µs, 1 195,602 s dans
1 200 s inchangées. Tous les payloads, cinq champs finaux et entrées sont relus.
Les seuils restent 0,001 Pa, 1e−6 K et 1e−8 m/s. Repos respecté ; 800 plafonds
linéaires empêchent de qualifier la convergence. Le lecteur relit omega, l'axe
et l'origine dans MRFProperties ; les métriques géométriques sont concordantes.
