# Démarrage CFD du turbo bionique — preuves conservées

Les calculs concernent le compresseur de référence et la volute F1, à
100 000 tr/min, 101 325 Pa de pression totale d'entrée, 298,15 K et 121 590 Pa
de pression statique de sortie. Ce sont des conditions hypothétiques.

Les maillages diagnostiques comptent respectivement 2 114 975 et 2 141 833
cellules. Ils conservent les trois coquilles et les invariants d'Euler des
surfaces sources. Le contrôle étendu natif reste rejeté pour coplanarité.
Une vérification indépendante démontre la géométrie cartésienne de toutes les
cellules ; elle autorise uniquement le pilote séparé. Elle ne qualifie ni
les parois en escalier, ni leurs couches limites, ni une performance.

Les tentatives 001 à 007 sont terminées et rejetées : références de dictionnaire
incorrectes, erreurs numériques, non-convergence, puis températures ou pressions
absolues négatives selon la tentative. Tous ces échecs restent visibles.
Les deux calculs transsoniques `runtime-008` étaient en cours au moment de
la capture datée dans [snapshot-index.json](snapshot-index.json). Les fichiers
suffixés `.snapshot` sont des instantanés partiels, pas des rapports finaux.

Le [protocole et les commandes](../../cfd/CASTELLATED-PILOT.md) décrivent chaque
contre-essai. Les scripts ne changent pas les sources F1 historiques. Chaque
correction crée de nouvelles entrées et lie la preuve héritée aux empreintes
exactes du maillage inchangé.

## Sauvegarde distante vérifiée

La [prépublication GitHub](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-airflow-startup-2026-10-11)
contient 766 fichiers représentant 16 441 023 983 octets, dédupliqués dans une
archive de 371 045 382 octets. Les tentatives terminées sont archivées
intégralement. Seules les entrées immuables des calculs encore actifs sont
incluses, pas leurs futurs résultats.

Tous les contenus uniques et les références des liens physiques ont été
vérifiés contre [l'inventaire](file-manifest.json). Les quatre empreintes SHA-256
des assets GitHub correspondent aux fichiers locaux ; voir le
[reçu distant](remote-verification.json) et le [reçu d'archive](archive-receipt.json).
L'archive utilise des liens physiques : créer des copies indépendantes avant
toute modification des fichiers restaurés.

49 tests ciblés du turbo passent. Le contrôle global local rencontre encore
les deux dépendances absentes (`rtree`, `networkx`) et les deux différences
flottantes exactes WE43/stator déjà connues. Aucun résultat de ce dossier
n'établit une convergence CFD, un débit maximal, une puissance maximale,
un gain par rapport à la référence ou un jumeau numérique calibré.
