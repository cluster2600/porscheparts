# Vérifications

108 tests turbo réussissent, un est ignoré (109 tests en 15,470 s).
make check, lancé avec PATH=work/bionic-tools/bin:$PATH, exécute 3 869
tests en 216,217 s, 172 ignorés. Les deux échecs flottants WE43/fan_stator
et les trois erreurs rtree/networkx hors turbo déjà connus subsistent.
Aucun nouveau problème turbo n'est identifié.

Le constructeur vérifie les orientations de section et l'annulation des
arêtes avant blockMesh. Le lecteur indépendant reprend tous les points,
faces, cellules et zones natifs, vérifie les parois, les quadrilatères MRF,
les volumes positifs, l'intégrale analytique et les chaînes d'arêtes.
La version 2 ajoute la vérification des types de cellules par zone et
conserve la première version, sans modifier le maillage.

Le comparateur établit l'identité octet pour octet de toutes les entrées
préparées hors maillage entre 059 et 061. Il vérifie aussi l'égalité exacte
des coordonnées des faces MRF après réindexation. Les parois polygonales
et le volume du domaine changent : ce n'est pas une comparaison de
performance à géométrie constante.

060 passe l'admission native ; 061 termine et respecte les seuils de
repos sur 200 pas. Les p/T/U natifs sont relus sur les 5 120 cellules,
finis et concordants avec l'historique. Les 800 plafonds de pression
interdisent de qualifier la convergence linéaire. Aucune CFD du turbo
réel, stabilité de perturbations ni calibration physique n'est établie.

Les 63 fichiers de l'archive sont relus et hachés localement. Les cinq
actifs distants sont vérifiés par tailles et SHA-256 GitHub ; aucun second
téléchargement intégral n'est revendiqué. Journaux et conteneurs conservés,
aucune suppression, aucune preuve antérieure modifiée. Les espaces des
journaux natifs sont préservés pour leurs empreintes.
