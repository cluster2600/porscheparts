# Bisection native d’une rangée extérieure — 085/086

Le sous-domaine fixe synthétique projeté 081 est raffiné avec l’outil natif `refineWallLayer`. Les 6 784 quadrilatères du raccord et les 6 784 faces extérieures restent intacts ; les 6 784 cellules de la rangée extérieure ont exactement deux descendants. Le maillage final passe `checkMesh -allTopology -allGeometry`. Aucun solveur d’écoulement n’est lancé.

## Opération et provenance

085 distingue `outerWall` par `createPatch`, `pointSync false`, à partir des faces natives et des trois niveaux radiaux de 078, eux-mêmes issus du profil 030 et des ratios 062. Les cellules touchant les sommets du patch sont explicitement comparées aux propriétaires de ses faces : les deux sélections contiennent exactement les mêmes 6 784 cellules. Toutes les coordonnées et cellules orientées de 081 sont conservées après renumérotation.

086 copie le maillage de 085 et applique `refineWallLayer '(outerWall)' 0.5 -overwrite`. La fraction 0,5 est la bisection des arêtes quittant le patch, décrite par le source officiel v2406 ; ce n’est pas un paramètre du solveur d’écoulement. `source-reference.json` référence et hache le membre officiel conservé. Le source sélectionne les cellules au contact des **points** du patch, pas seulement ses faces. La vérification de cette sélection précède le lancement.

L’outil natif nettoie des ensembles et des adresses de processeurs. 086 ne reçoit donc aucun ensemble ni fichier d’adressage hérité ; les originaux restent dans 085 et les copies initiales. Tous les inputs sont copiés avant exécution. Les deux conteneurs, journaux, intermédiaires, reçus et copies sont conservés. Aucun changement du code natif, de seuil de qualité ou de surface réelle du turbo.

## Résultats

| Contrôle | 085 | 086 |
|---|---:|---:|
| Fin native | 0, sans OOM | 0, sans OOM |
| Durée lanceur | 1,061 s | 0,951 s |
| Cellules | 13 568 | 20 352 |
| Points | 20 736 | 27 648 |
| Faces | 47 744 | 68 224 |
| Faces internes | 33 664 | 53 888 |
| Admission native | Mesh OK | Mesh OK |

Le déterminant minimal de 086 est 0,006220795333159227, au-dessus du critère 0,001 inchangé. Aucune concavité ni petit déterminant n’est signalé. Le domaine reste une région fluide fixe, sans rotor ni ports physiques.

`read_refinement.py` reconstruit indépendamment chaque cellule et chaque face orientée de la bisection, puis compare les propriétaires et voisins natifs. Les arêtes de chaque cellule s’annulent ; les volumes sont positifs. Toutes les coordonnées originales décodées sont exactement conservées. Les 6 912 points nouveaux correspondent aux milieux attendus à 1,012e−17 m près, après sérialisation.

Les 512 faces de fermeture deviennent 768 faces. Leur couverture est vérifiée par convexité des parents plans et annulation orientée des chaînes d’arêtes, après insertion des milieux. Les 6 784 faces du raccord et autant de faces extérieures sont inchangées. Le volume total reconstruit reste 2,333381635788176e−6 m³, identique à 081 ; cela ne restitue pas le volume original 079. La planéité globale maximale vaut 6,792080535e−7 m. Les faces fixes gauchies restent explicitement présentes.

Le raccord conserve une planéité de 1,062518129e−17 m et une normale géométrique de rotation maximale de 2,287947609e−12 m/s. Le sous-domaine est fixe : cette métrique géométrique n’est pas un débit physique et n’applique aucune rotation au domaine.

## Limites

`read_zones.py` prouve que les 7 424 membres originaux de `frozenPoints` restent présents exactement une fois, aux mêmes coordonnées. **Les 256 nouveaux points des fermetures ne sont pas ajoutés à cette zone.** Une projection ultérieure doit reconstruire explicitement sa sélection ; l’héritage de la zone ne garantit pas leur immobilité.

Cette bisection conserve le raccord pendant **cette opération native précise**. Elle ne qualifie ni la protection pendant `snappyHexMesh`/castellation, ni des couches de paroi physiques, ni les cellules autour des pales, ni un raccord global après raffinement. Aucun nouveau repos, stabilité de perturbations, convergence linéaire, débit, puissance ou calibration physique n’est validé. Le contrôle 084 reste incomplet à son budget, sans champs finaux ; ses seuils historiques jusqu’à 11,1 µs ne qualifient pas 20 µs.

Voir [validation.md](validation.md), [readback.json](readback.json), [zone-readback.json](zone-readback.json) et [next-scope.md](next-scope.md). Les payloads natifs complets sont dans l’archive de cette phase ; les petits lecteurs et preuves sont publiés dans le dépôt.
