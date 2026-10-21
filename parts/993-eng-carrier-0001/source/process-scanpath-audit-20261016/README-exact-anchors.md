# Contacts d'exposition décidés avant encodage

Le nouveau point d'entrée de l'audit complet est :

```sh
AM_PYTHON parts/993-eng-carrier-0001/source/process-scanpath-audit-20261016/audit_complete_supports_exact_anchors.py PROCESS OUTPUT --source-stl STL --part-cache CACHE
```

Il conserve les contrôles complets des vecteurs, leurs sections indépendantes,
les deux domaines des contacts, les graphes successifs et l'exposition d'au
moins une section de chaque groupe de matière. Les anciens auditeurs restent
inchangés et sont chargés isolément avec contrôle de leurs empreintes.

La décision d'ancrage utilise l'intersection rationnelle entre le contact et
les anneaux bruts de pièce du même plan. Elle n'arrondit pas le contact avant
ce test. La parité des anneaux définit la matière ; les coordonnées d'un
overlay GEOS ne servent pas de domaine de mesure. La longueur flottante publiée
dans le témoin est un diagnostic calculé après la décision exacte. Un contact
de point seul ne constitue pas un ancrage positif.

La connexité des vecteurs IEEE est contrôlée séparément après leur encodage
correctement arrondi. Ses ancrages proviennent des contacts rationnels
certifiés ; aucune largeur de faisceau ni distance de proximité n'est ajoutée.

Le [témoin négatif](exact-anchor-evidence/negative-ieee-hole.json) reproduit
l'erreur antérieure : un contact exact ne rencontre la matière qu'aux points
terminaux, mais son arrondi avant intersection donne à GEOS une longueur
positive d'environ `0,81397 mm`. La trace de contact du témoin est elle-même
obtenue par clipping exact et son encodage est vérifié, plutôt qu'injectée sous
forme d'une donnée privée incohérente. Le nouvel adaptateur refuse cet ancrage.
Ce témoin logiciel ne prétend pas décrire la future préparation réelle.

Le résumé `assessment.json` et `scanpaths/assessment.json` portent tous deux
`rational_part_contact_intersections=true` et
`part_contact_intermediate_encoding=false`. Le reçu
`group-exposure-coverage.json` garde son contrat précédent. Tous sont liés au
même SHA de `PROCESS/report.json` ; aucun nouveau reçu de géométrie de pièce
n'est nécessaire, ses NPZ de couches et le cache complet étant déjà vérifiés.

```sh
AM_PYTHON -B -m unittest tests.test_carrier_exact_exposure_anchors -v
```

Dix tests ciblés couvrent le défaut avant correction, son refus après correction,
les vrais contacts, la plaque à la première couche, les trous, les paramètres
rationnels non dyadiques, la feuille entre plans et les deux nouveaux champs.
La livraison de ce code ne constitue pas l'exécution de l'audit complet réel.
