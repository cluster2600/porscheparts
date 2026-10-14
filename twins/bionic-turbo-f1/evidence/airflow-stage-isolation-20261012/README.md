# Isolation du raffinement — essai 032 rejeté

Le cas 032 reprend les entrées épinglées de 031 avec une seule modification :
`snap true` devient `snap false`. Aucune surface, tolérance, couche ou équation
n'est changée. Aucun solveur d'écoulement n'est lancé.

## Résultats

L'exécution native termine en 199,605 s avec code zéro, mais checkMesh rejette
38 405 cellules concaves. Le déterminant minimal est 0,00109821568.
Le code de sortie zéro ne vaut pas admission.

L'inventaire exact des arêtes des facettes sources identifie deux composantes
rotor fermées de caractéristique d'Euler nulle et une composante ouverte.
La grande composante fermée s'arrête à z = 25,0000133514 mm ; la petite commence
à 25,4900779724 mm et finit à 31,5001926422 mm. Leur séparation axiale dans
cette géométrie source est 0,490064621 mm, sans qualification dimensionnelle
physique. Dans 031 comme 032, une seule composante fermée couvre les deux
étendues : une connexion artificielle apparaît déjà avant projection. Le
constat précise la « composante perdue » de 031 ; il ne signifie pas que
l'écrou entier a disparu. Les petites composantes ouvertes parasites restent
inventoriées, sans réparation ni suppression.

Les 12 416 faces entre repères donnent une composante normale géométrique de
rotation maximale de 4,111922306 m/s avant projection, contre 10,992224833 m/s
après projection dans 031 et 8,2338e-12 m/s dans le fond 030. Le flux géométrique
absolu est 0,000206667008 m³/s dans 032 : ce n'est pas un débit physique.
Le raffinement altère donc déjà la tangence ; désactiver la projection ne suffit
pas. Les rapports conservent les empreintes des surfaces, sources et faces.

## Reproduction et conservation

`run_castellated.py` prépare un cas neuf et exécute les outils natifs bornés.
`inventory_rotor.py` et `inventory_rotor_032.py` comparent les composantes exactes.
L'auditeur épinglé `../../cfd/audit_frame_interface_v2.py` lit les faces natives.
Les reçus, entrées, journaux et tout le maillage 032 sont conservés dans
[l'archive native](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-stage-isolation-2026-10-12).
Le manifeste décrit chaque fichier et son SHA-256 ; le paquet est relu localement
et les tailles/empreintes des actifs GitHub sont vérifiées. Il ne s'agit pas
d'un second téléchargement intégral distant.

## Validation et limites

96 tests turbo réussissent, un est ignoré (97 au total). `make check` exécute
3 806 tests : deux comparaisons flottantes échouent et trois erreurs de
dépendances rtree/networkx persistent hors turbo ; 170 tests sont ignorés.
Les journaux complets sont joints. La CI est contrôlée avant fusion.

La suite doit préserver séparément les coquilles et la tangence lors du
raffinement, puis vérifier projection, couches et équilibre global avant
écoulement forcé. Aucun débit maximal, puissance, convergence ou jumeau
numérique calibré n'est validé par ce diagnostic.
