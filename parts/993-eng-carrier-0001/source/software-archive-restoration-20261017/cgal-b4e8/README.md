# CGAL expérimental b4e8 — restauration et smokes réels

L’unique séquence autorisée a terminé avec **RC0 réel**, session 70818, chunk terminal bddf15, en 38,526310 s. Le reçu `execution-receipt.json` SHA513bac7e11d9bcbc22306a5d33bfab66527e9b48ec2eaaf1d111e261e9e506b1 conserve chaque commande et son retour, les dépendances, sorties et fermeture des quatre scopes. Les huit selfchecks stdlib ont passé en0,988 s avant lancement ; aucune ancienne session n’a été pollée ou signalée.

| Phase | Retour réel | Temps mural SSH observé |
|---|---:|---:|
| Extraction |0|3,723493 s|
| Configuration |0|0,437581 s|
| Compilation |0|17,081170 s|
| Trois témoins |0|0,944587 s|
| Contrôle fermeture |0|0,307094 s|

Chaque phase native est passée sous son scope propre : un CPU, 6 Gio, aucun swap, réseau isolé, un seul thread, dépendances système montées en lecture seule. Le seul montage RW est le nouveau préfixe. Le budget global prévu était 900 s, avec 60 s réservées à la fermeture/collecte ; les caps extraction/configuration/compilation/smoke sont120/60/600/60 s. Les quatre scopes sont maintenant explicitement `LoadState=not-found`, `ActiveState=inactive`, `ControlGroup` vide. Une erreur de requête n’a pas été assimilée à cette preuve.

Préfixe conservé : `/home/lolman/carrier-software-restoration-smoke-20261017-001/cgal-b4e8`. Le token d’appartenance est 93c539d914414687. Aucun répertoire, archive, binaire ou tag historique n’a été remplacé.

L’archive source est le commit expérimental **b4e8c1887ce6a0abeb618634125e5cfcd301ce16**, SHA 1a5c2e9e3aa2b5e699536135ea7c1b0c46cde3343da9347720ad068632019a7f, identique à l’archive livrée. La copie déjà présente sur Kali a été réutilisée après hachage exact ; aucun téléchargement n’a été effectué. L’extraction neuve contient17 487 fichiers, avec le header API 15ac79840d22479570d0284fb7b4dc5b1b508ced0f3d76c2fe817e2d84f4d69d.

Le C++/CMake/worker/witnesses historiques sont byte-identiques. Compilation C++17, `-O1`, assertions conservées, `--parallel 1`. Binaire neuf SHA 48a0f21b8bfd585166f16ba5fce2fa84e50cc2cae5b972083c02ef0e538760b3. Les17 487 sources restaurées, les 14 entrées de provenance/runtime dont archive et MPFR, les outils GCC/CMake et les 2 932 headers / 8 bibliothèques du binaire sont liés aux reçus ; le binaire et ses dépendances sont identiques avant/après les smokes.

| Témoin existant | Volume rationnel exact mm³ | RC worker / natif | Gates |
|---|---:|---:|---|
| union-prisms |4000|0/0|PASS|
| intersection-prisms |2000|0/0|PASS|
| difference-prism-gap |3200|0/0|PASS|

Chaque cas exige les critères historiques : volume exact, achèvement natif, absence d’auto-intersections exactes et de collinéarités, filiation complète des faces, absence d’auto-intersections des coordonnées arrondies et topologie fermée orientée/manifold, sans sommets inutilisés. Les trois maillages ont zéro bord ouvert/nonmanifold/orientation incohérente/sommet nonmanifold. Les JSON natifs, audits, NPZ et géométrie rationnelle exacte sont collectés sous `collected/`. Aucun cas self_union ni calcul carrier n’a été lancé.

## Portée hors réseau réellement établie

**L’archive expérimentale source se restaure et son adaptateur C++ se compile puis passe les trois témoins sans accès réseau, sur cet hôte déjà équipé de son compilateur, Boost/GMP/MPFR et runtime NumPy/libigl attestés.** Le rootfs PyMesh et l’OCI CalculiX ont leurs preuves distinctes déjà conservées dans les dossiers voisins.

Cette exécution ne restaure pas CGAL stable 6.1.3, ne teste pas une machine vierge sans dépendances et ne ferme pas le manque de son archive 7d8580bb / paquet MPFR dans le paquet livré. Elle n’exécute pas l’ancien `run.py` à 2 CPU ni son installateur ; ces copies restent des sources historiques. Seul `worker.py` a été utilisé avec le binaire neuf sous le protocole borné. Aucun workflow carrier, aucune admission collective ou preuve de distance globale n’en découle.

Licences/provenance conservées : source expérimentale sloriot/cgal commit b4e8, API de booléens GPL-3.0-or-later ou licence commerciale ; noyau CGAL LGPL-3.0-or-later ou commerciale ; MPFR LGPL-3.0-or-later. Sources et archive originales restent inchangées.
