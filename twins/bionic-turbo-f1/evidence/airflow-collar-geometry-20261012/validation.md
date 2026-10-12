# Vérifications et portée

Le nouvel auditeur appelle les lecteurs et bornes épinglés, sans les modifier.
Il refuse les entrées dont l'empreinte a changé, les profils hors domaine et
toute violation d'une borne. Ses auto-contrôles incluent un profil dont le
minimum est une station intérieure, un intervalle affine, un point et le
refus d'un intervalle non couvert. Le second lecteur parcourt séparément
les segments pour retrouver les 712 bornes publiées.

Les STL complets sont relus par audit_collar.py, avec vérification des
empreintes, des quatre patches et des comptes. Le lecteur readback.py
relit le rapport, les empreintes de ses sources et de ses entrées, toutes
les bandes, les comptes d'intersection et les résultats d'enroulement.
Il ne prétend pas relire une seconde fois les facettes du STL. Le reçu
execution-receipt.json conserve les deux commandes terminées avec code zéro.

Les 516 216 facettes rotor de chaque variante sont bornées entièrement,
y compris aux changements de pente. Les coordonnées de la facette la plus
restrictive sont conservées. Les sélections d'intersection sont des
candidates conservatives, pas des intersections exactes mesurées.

Aucun nouveau maillage natif ni solveur. La couronne traverse volontairement
le plan arrière du stator ; sa partie sous ce plan est hors fluide. Les
bornes de distance sont radiales, pas des distances euclidiennes minimales,
ni une qualification mécanique ou thermique. Les cellules adaptées autour
des pales, les couches, la convergence et les performances restent ouvertes.

## Tests du dépôt

108 tests turbo réussissent, un est ignoré (109 tests en 16,117 s).
make check avec PATH=work/bionic-tools/bin:$PATH exécute 3 889 tests en
235,373 s, avec 172 ignorés. Les deux échecs flottants WE43/fan_stator et
les trois erreurs rtree/networkx hors turbo déjà connus subsistent ; la
vérification globale locale n'est donc pas verte. Aucun défaut turbo
nouveau n'est identifié. Les journaux complets sont conservés dans l'archive.

## Archive

La version 1 du paquet avait conservé une deuxième étiquette de périmètre
issue du paquet précédent. Les payloads étaient corrects ; l'étiquette
était erronée. Source et reçus initiaux sont conservés. La version 2 retire
uniquement cette entrée de périmètre, sans changer le résultat géométrique.
L'archive finale contient 22 fichiers, 325 624 octets ; tous ses payloads
sont relus localement. Aucun second téléchargement intégral distant n'est
revendiqué ; les actifs GitHub sont vérifiés par tailles et SHA-256.
