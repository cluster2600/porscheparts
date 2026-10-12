# Limite des points gelés pendant la projection native — 068 à 070

Déclarer `frozenPoints` ne conserve pas les coordonnées initiales lorsque le
lissage préalable de snappy est actif. Sur cette copie de la couronne 063,
les 20 992 points de frontière gelés bougent jusqu'à 0,357934 mm. Retirer
uniquement ce lissage dans le contrôle 070 conserve exactement les coordonnées
natives et passe le contrôle étendu. Ce résultat n'est pas une recette validée
pour traiter les parois du turbo.

## Périmètre et entrées

Les trois nouveaux cas reprennent le maillage natif 063 : 27 136 cellules,
27 648 points et 81 920 faces. Le STL cible est la triangulation des faces de
frontière du parent, avec les coordonnées exactes relues ; les faces du maillage
ne sont pas triangulées. Rotor et ports restent absents. Les parois latérales
et avant sont synthétiques. Les surfaces CFD du turbo ne sont pas modifiées.

Seule la projection est activée : `castellatedMesh false; snap true; addLayers
false;`. Les paramètres de projection et de qualité proviennent de 031,
y compris `nSmoothPatch 3`, `nSmoothInternal 3` et les seuils natifs inchangés.
Il n'y a pas de raffinement, couche ou solveur d'écoulement dans cette phase.

068 contient une pointZone frozenPoints vide. 069 contient les 20 992 labels
de frontière du parent dans cette zone : seul `constant/polyMesh/pointZones`
diffère entre les entrées préparées. 070 conserve ces labels et change
uniquement `nSmoothPatch 3` en `nSmoothPatch 0` dans snappyHexMeshDict.
`nSmoothInternal` reste à 3 ; la boucle de lissage préalable n'est plus exécutée.
Cette comparaison cible un mécanisme identifié dans le source, sans balayage
de paramètres, modification des équations ou assouplissement de seuils.

## Résultats terminés

| Cas | Contrôle natif étendu | Déplacement maximal de frontière | Normale géométrique MRF maximale |
| --- | --- | --- | --- |
| 068, zone vide et lissage | Mesh OK | 0,318713789 mm | 0,00268335429 m/s |
| 069, zone complète et lissage | Rejet | 0,357934149 mm | 2,21689334e−12 m/s |
| 070, zone complète sans lissage préalable | Mesh OK | 0, exactement après lecture | 2,28794761e−12 m/s |

Tous terminent avec code zéro, sans OOM, en 1,615 / 1,733 / 4,046 s.
Le code zéro et le message final de snappy ne valent pas admission.

068 déplace les 20 992 points de frontière ; malgré Mesh OK, il ne conserve
pas le raccord. Son interface se déplace jusqu'à 0,138244 mm et sa planéité
se dégrade à 5,16243e−8 m. Déterminant minimal 0,00331647238,
non-orthogonalité maximale 56,8845904°. Rejet pour la conservation demandée.

069 déplace aussi les 20 992 points de frontière et son interface jusqu'à
0,160748 mm. L'interface reste plane et tangente à la précision géométrique,
mais le domaine et les coordonnées initiaux ne sont plus conservés.
`checkMesh -allTopology -allGeometry` rejette 128 cellules au déterminant
inférieur à 0,001, minimum 7,17949177e−5, et 128 cellules concaves.
Le message de snappy « sans erreur » est conservé avec ce refus distinct ;
aucune explication unique de cet écart entre contrôles n'est affirmée.

070 conserve toutes les coordonnées décodées du parent, la connectivité des
faces, les propriétaires/voisins et les labels de rotorZone. Son déterminant
minimal vaut 0,03808565604766382, sa non-orthogonalité maximale 47,8173519°.
Volume natif 4,611377236219295e−6 m³, comme le parent. Aucun nouveau test au
repos : le résultat 064 reste attaché à son propre cas.

## Lectures et limites

`read_final.py` vérifie tous les payloads, les différences exactes d'entrées,
les coordonnées, les faces et owner/neighbour ; les premières lectures restent
conservées. `audit_zones_v2.py` vérifie les labels de zone, le STL cible et les
paramètres hérités. Le patch non vide walls est identique en métadonnées.
Snappy retire le patch defaultFaces vide, ce qui avait fait refuser le premier
auditeur trop strict ; ce refus et sa source restent conservés. Aucun patch
physique du turbo n'est changé.

La lecture officielle hachée confirme que `preSmoothPatch` précède
`freezeExposedPoints`. Celui-ci annule le déplacement demandé à son étape ;
il ne restaure pas nécessairement la position précédant le lissage.
Le contrôle 070 soutient le rôle du lissage dans cette paire, sans prouver
une protection générale des étapes de raffinement, des frontières non adaptées,
ou du maillage des pales. Les autres usages des zones dans la fermeture de
trous ne doivent pas être détournés pour changer les connexions physiques.

Toutes les frontières sont gelées en 070, et la surface cible correspond déjà
au parent. Il ne teste donc pas la projection non nulle d'une paroi voisine
avec un raccord seul gelé. Ce contrôle distinct reste nécessaire, puis une
preuve de protection du raffinement. Aucune CFD forcée, performance de débit
ou puissance, stabilité de perturbations ou calibration n'est accordée.
Les vitesses géométriques du tableau ne sont pas des vitesses d'air.

## Archives

L'[archive principale v2](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-frozen-boundary-2026-10-12)
contient 140 fichiers, 4 874 483 octets, SHA-256
`9c0a08395348037b680e28f074cf6decd4583d26c8fc45c70340a65dca5a86b6`.
Elle inclut les entrées préparées matérialisées séparément, vérifiées contre
leurs manifestes initiaux. Leur reconstitution documentée n'est pas présentée
comme un instantané capturé avant lancement.

Le premier paquet de 96 fichiers est également publié et conservé avec ses
reçus. Les neuf actifs GitHub sont vérifiés par tailles et digests ; les
payloads des deux paquets sont relus localement. Aucun second téléchargement
distant intégral n'est revendiqué. Les conteneurs terminés sont conservés.
