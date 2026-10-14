# Raffinement du passage roue–écrou — 033

Le témoin 033 corrige la connexion artificielle identifiée dans 031/032 :
les deux composantes rotor fermées sont à nouveau distinctes. Le maillage
reste rejeté ; aucune simulation d'écoulement n'a été lancée.

## Modification contrôlée

Le STL est identique octet pour octet à celui de 032. La projection et les
couches restent désactivées. Le seul changement du dictionnaire ajoute une
boîte de raffinement locale, dérivée des bornes de la petite composante rotor
et du jeu axial source de 0,490064621 mm. Les bornes de cette boîte sont
conservées dans `case-manifest.json` ; sa marge est une cellule du fond.

La taille axiale maximale des blocs couvrant le jeu est relue dans le vrai
blockMeshDict : 0,780555556 mm. Le niveau minimal permettant théoriquement
quatre cellules dans le jeu est trois, soit 0,097569444 mm. Ce nombre est une
prévision de résolution, pas une mesure du jeu physique ni une garantie de
qualité des cellules après découpe. Les transitions natives peuvent étendre
le raffinement au-delà de la boîte. Aucun seuil de qualité n'est assoupli.

## Résultats natifs

L'exécution termine en 427,779 s, code zéro, sans OOM. Le contrôle étendu
rejette 74 103 cellules concaves, contre 38 405 dans le témoin 032.
Le déterminant minimal reste 0,00109821568. Le journal snappyHexMesh signale
aussi 4 231 415 faces illégales selon ses propres contrôles ; ce diagnostic
est conservé et ne doit pas être remplacé par le seul code de sortie.

L'audit des faces natives retrouve trois coquilles, leurs patches et leurs
caractéristiques d'Euler attendues : 2 pour la frontière extérieure et 0
pour chacune des deux coquilles rotor. Les propriétaires rotor sont dans
la zone tournante et les deux ports hors zone. L'inventaire du patch rotor
conserve également les deux petites composantes ouvertes parasites.

La grande composante fermée s'arrête à z = 24,977430556 mm ; la petite
commence à 25,463686040 mm. Leur séparation axiale maillée est donc
0,486255485 mm avant projection. Cela confirme la correction de connexion,
sans qualifier la fidélité dimensionnelle, les jeux euclidiens ou thermiques.

Les 12 416 faces entre repères présentent les mêmes métriques que 032 :
composante normale géométrique maximale 4,111922306 m/s et flux géométrique
absolu 0,000206667008 m³/s. Ce ne sont pas des mesures de débit d'air.
Le raffinement local résout ici la topologie du passage, pas la tangence MRF.

## Conservation et reproduction

`run_gap.py` prépare un cas neuf avec `prepare_gap_control.py`, puis exécute
les outils OpenFOAM v2406 épinglés, sous les mêmes limites que 032 : deux CPU,
8 Gio, 1 800 secondes, réseau désactivé, sans solveur. Le conteneur terminé
`bionic-gap-033` est conservé. `inventory_rotor_033.py` et l'auditeur épinglé
`../../cfd/audit_frame_interface_v2.py` relisent les maillages natifs.

Les 44 fichiers du cas sont conservés dans
[l'archive native](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-gap-control-2026-10-12),
avec inventaire et empreintes. Tous les payloads sont relus localement et
les tailles/SHA-256 des cinq actifs GitHub sont vérifiés ; aucun second
téléchargement intégral distant n'est revendiqué.

97 tests turbo réussissent, un est ignoré. `make check` a exécuté 3 807 tests
avec 170 ignorés, les deux échecs flottants et trois erreurs de dépendances
rtree/networkx hors turbo déjà connus. Journaux joints ; CI contrôlée avant
fusion. Les espaces natifs des journaux sont conservés pour leurs empreintes.

## Suite

Préserver une interface conforme pendant le raffinement et la projection,
puis vérifier qualité native, connexions, couches et repos global. Le
raffinement 033 est un candidat de correction à conserver dans ces nouveaux
cas, pas une autorisation de lancer le solveur. Aucun débit maximal, gain de
puissance, indépendance au maillage ou jumeau numérique calibré n'est validé.
