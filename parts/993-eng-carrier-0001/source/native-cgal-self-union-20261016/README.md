# API CGAL expérimentales de booléens de soupes

Source primaire : [PR9363](https://github.com/CGAL/cgal/pull/9363), branche
`sloriot/cgal:PMP-autoref_boolops`, commit exact
`b4e8c1887ce6a0abeb618634125e5cfcd301ce16`. L'archive codeload fait
167177612 octets ; SHA256
`1a5c2e9e3aa2b5e699536135ea7c1b0c46cde3343da9347720ad068632019a7f`.
L'en-tête public `triangle_soup_boolean_operations_3.h` a le SHA256
`15ac79840d22479570d0284fb7b4dc5b1b508ced0f3d76c2fe817e2d84f4d69d`.
Aucun patch n'est appliqué à CGAL. La PR est ouverte et non publiée.

```sh
python3 parts/993-eng-carrier-0001/source/native-cgal-self-union-20261016/setup.py \
  /chemin/neuf/cgal-soup --archive CGAL-b4e8c188.tar.gz \
  --support-runtime /chemin/cgal-6.1.3 --audit-python /chemin/audit/bin/python
python3 /chemin/neuf/cgal-soup/run.py union A.npz \
  /chemin/neuf/cgal-soup/jobs/union-001 --second-input B.npz
```

Le support-runtime est une installation explicite de `native-cgal-20261016` :
seuls ses en-têtes MPFR et bibliothèques vérifiés sont réutilisés, sans mutation.
Le nouveau CGAL est extrait séparément. Les bibliothèques, 2932 dépendances
réellement compilées, adaptateur, lanceur et worker sont empreintés. Les
assertions CGAL restent actives. Installation et calculs sont bornés à deux CPU,
4 Gio, sans swap ; chaque calcul est sans réseau et limité à 600 s.

L'adaptateur utilise Epeck depuis les valeurs IEEE originales. Il ne convertit
qu'à la fin, conserve aussi les coordonnées rationnelles exactes et mesure
l'erreur de cette conversion. L'API retourne `void` : le reçu ne lui invente
pas de booléen de succès. La parenté est reconstruite en exact par la présence
des trois sommets de chaque triangle enfant dans un triangle parent convexe
réel. Cette première version conserve un parent témoin ; la version
`native-cgal-prism-free-20261016` conserve aussi toutes les ambiguïtés.

Les neuf témoins ont été exécutés. `compute_self_union` est **refusée** :

- Deux tétraèdres disjoints ou se touchant en un point perdent un composant :
  volume exact 1/6 au lieu de 1/3.
- Le chevauchement conserve cinq arêtes non manifold ; aucun volume d'une telle
  sortie n'est considéré comme volume d'un solide admis.
- Le contact par face et les prismes imbriqués déclenchent l'assertion de
  l'en-tête ligne985 sur des points extrêmes exactement dupliqués.

Les API binaires passent leurs témoins de prismes : union4000 mm³,
intersection2000 mm³ et différence avec intervalle Z8–Z12 retiré3200 mm³.
Ces sorties sont fermées, orientées, manifold, sans auto-intersection exacte,
avec parenté démontrée. L'API exige que chaque entrée soit sans auto-intersection :
la chaîne orientée de prismes potentiellement croisés n'est donc pas une entrée
admissible directement. Aucun support réel n'a été traité par ce prototype.

Les sources et tous les refus sont conservés dans `reproduction-results.json`
et les dossiers bruts référencés. Une première installation a compilé puis
échoué sur un chemin de Python d'audit fourni incorrectement ; le second
préfixe neuf a exécuté l'installation complète et les témoins.

Licence amont du paquet : GPLv3 ou ultérieure, ou licence commerciale CGAL ;
les fichiers de licence et copyright originaux sont copiés sans modification.
Le noyau CGAL et MPFR conservent leurs licences propres. Le moteur reste une
expérience logicielle, avec admission des vraies géométries indépendante.
