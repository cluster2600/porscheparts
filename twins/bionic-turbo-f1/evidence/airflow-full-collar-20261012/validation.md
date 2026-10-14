# Vérifications et limites

Les constructeurs et lecteurs précédents sont réutilisés dans de nouveaux
fichiers, sans modifier aucune source ou preuve épinglée. Le constructeur
vérifie les orientations de section et l'annulation des arêtes avant
blockMesh. Le lecteur indépendant vérifie les points contre 062, les faces,
les zones, les types de cellules, les chaînes d'arêtes et les volumes.
La comparaison au volume natif retrouve un écart relatif de 7,33e-15.

Le lecteur arrière v2 ajoute explicitement la convexité à la première
version avant le test d'exclusion de l'origine. Chaque face est alors bornée
par ses arêtes et sommets dans les deux anneaux sources certifiés. Les
512 faces sont exactement dans le plan −3,75 mm. Les lecteurs v1/v2 et leurs
sorties sont conservés ; aucune coordonnée native n'a été corrigée.

Le comparateur relit et hache toutes les entrées préparées de 061/064 : seuls
six fichiers de maillage changent. Équations, conditions initiales, pas et
critères sont identiques. Le domaine et le nombre de cellules changent :
cette comparaison d'entrées ne mesure pas un gain physique.

108 tests turbo réussissent, un est ignoré (109 tests en 15,522 s).
make check avec PATH=work/bionic-tools/bin:$PATH exécute 3 889 tests en 220,882 s,
172 ignorés. Les deux échecs flottants WE43/fan_stator et les trois erreurs
rtree/networkx hors turbo connus restent présents ; le contrôle local global
n'est pas vert. Journaux complets conservés dans l'archive.

Le témoin représente la couronne seulement. Les parois latérales et avant
restent synthétiques, rotor et ports absents. Les couches de paroi et le
raccord au cœur adapté autour des pales ne sont pas qualifiés. Les critères
natifs et numériques ne sont jamais assouplis.

064 termine avec code zéro sans OOM et respecte les seuils de repos sur
200 pas. Le lecteur final v2 vérifie aussi rho et phi, en distinguant le
nombre de cellules de celui des faces internes. p/T/U/rho et phi sont
relus, finis, et leurs empreintes enregistrées. Tous les payloads natifs
sont vérifiés. Le lecteur original est conservé ; les sources antérieures
n'ont pas été modifiées. Les 800 plafonds de pression empêchent de qualifier
la convergence linéaire. Aucune stabilité aux perturbations ou performance
du turbo réel n'est démontrée.

L'archive conserve les sources, entrées, maillages, historiques, cinq champs
finaux, journaux et reçus. Les 74 payloads sont relus localement ; les cinq
actifs GitHub sont vérifiés par tailles et SHA-256. Aucun second téléchargement
intégral distant n'est revendiqué. Aucun fichier natif n'a été supprimé.

Un espace final dans le README publié est conservé afin de garder son
empreinte identique à l'actif de release. Les sources Python et les
rapports JSON passent le contrôle des espaces de Git.
