# Sous-domaine à deux cellules radiales — 077 à 079

Le contrôle 079 est admis isolément, contrairement aux refus 071/072 à une seule
cellule radiale. Il conserve une face radiale interne par cellule sans déclarer
un couplage fictif et sans modifier le seuil natif de déterminant 0,001.
Il s'agit toujours d'une couronne synthétique : rotor et ports sont absents.
Aucune surface, pièce, connexion ou jeu du turbo réel n'est modifié.

## Maillage complet 077

Le seul changement préparé par rapport au dictionnaire 063 remplace (1 1 1) par
(2 1 1) dans les 6 784 blocs hexaédriques fixes dont la première direction est
radiale. Les 20 352 blocs prismatiques tournants, sommets, faces de frontière,
profil 030, ratios 062, stations axiales et gradations restent définis à
l'identique. Le blockMesh natif construit les subdivisions ; aucun générateur
de polyMesh, aucune projection, aucun raffinement snappy ou couche n'intervient.

077 termine en 58,826 s, code zéro sans OOM, Mesh OK : 33 920 cellules,
34 560 points, 102 400 faces dont 80 768 internes, une région fluide.
Déterminant minimal 0,038085656 ; non-orthogonalité maximale 47,81735 degrés.
Les 20 352 prismes tournants et 13 568 hexaèdres fixes sont retrouvés par une
bijection indépendante des sommets de cellules, des faces orientées et de leurs
propriétaires/voisins. Toutes les chaînes d'arêtes par cellule s'annulent.

Les coordonnées natives de tous les points d'origine sont exactement conservées
après réindexation. Les 6 912 points supplémentaires sont les milieux radiaux
attendus. Les 6 784 quadrilatères MRF correspondent exactement à ceux de 063.
Les faces de fermeture subdivisées couvrent la même frontière orientée ; les
parois latérales restent identiques. Le volume 4,611377236219329e−6 m³ est celui
de 063 et toutes les cellules ont un volume positif.

Planéité maximale 1,44199e−17 m ; normale géométrique MRF maximale
2,28795e−12 m/s ; bilan géométrique par cellule tournante maximal
1,49078e−19 m³/s. Ce ne sont pas des débits d'air. Le témoin conserve la position
certifiée de la couronne 062, mais ne qualifie ni le cœur adapté autour des pales,
ni les couches, ni le jeu euclidien/thermique.

## Séparation 078 et admission isolée 079

splitMeshRegions sépare les 20 352 cellules tournantes des 13 568 cellules fixes
en 2,619 s, code zéro sans OOM. Les cartes natives de cette NOUVELLE séparation
sont vérifiées intégralement : points, faces signées, cellules et propriétaires.
Toutes les 33 920 cellules sont couvertes une fois ; seules les 6 784 faces MRF
figurent dans les deux régions, avec orientations opposées. La séparation seule
ne constitue pas une admission native de chaque région.

079 copie les points/faces/owner/neighbour de domain1 sans changement. Les deux
patches contigus deviennent une unique paroi non couplée ; les métadonnées
mappedWall sont retirées, les zones sont vides et aucune carte héritée n'est
copiée. Toutes les entrées sont sauvegardées AVANT exécution et restent
byte-identiques après checkMesh. Il n'y a ni déplacement, ni snappy, ni solveur.

079 termine en 2,583 s, code zéro sans OOM : Mesh OK, une région fluide,
13 568 cellules, 20 736 points, 47 744 faces dont 33 664 internes. Aucun petit
déterminant ni concavité signalée. Déterminant minimal 0,1186509579869612,
moyenne 0,2356789354053831 ; non-orthogonalité maximale 23,23544 degrés.

La formule officielle du tenseur des aires internes/couplées est relue dans
l'archive v2406 exacte, puis reconstruite indépendamment. Minimum et moyenne
concordent avec les valeurs natives. Chaque cellule isolée dispose maintenant
d'une face radiale INTERNE, 6 784 au total, partagées deux à deux. Les refus
071/072 restent conservés : ils démontraient déjà que le déplacement n'était pas
nécessaire au rejet avec une seule cellule dans l'épaisseur. Aucun critère n'est
abaissé et aucun patch artificiellement couplé ne contourne ce diagnostic.

## Limites

Ce résultat qualifie une opération de maillage et l'admission géométrique d'un
sous-domaine synthétique sans traitement de paroi. Aucun nouveau test de repos,
de stabilité aux perturbations, de convergence linéaire ou de débit/puissance
n'a été exécuté. Les cas 077–079 sont terminés, conteneurs et sorties conservés.
La projection sélective puis la protection pendant le raffinement restent à
qualifier avant tout traitement du vrai turbo.

## Archive native

[Sources, entrées, maillages et reçus](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-radial-subdomain-2026-10-13).

```json
{
  "files": 138,
  "archive_bytes": 4768533,
  "archive_sha256": "f12a71a553cc98dfe1a0f64d6582a1d974119b0bb1bca6c56b42ed3ecafae6df",
  "manifest_sha256": "796d87860e42084a6474e680560db1cdcd6a71d947c61ed2f011a920536160b5",
  "all_payloads_verified": true,
  "performance_ranking_authorized": false,
  "scopes": [
    {
      "case": "work/bionic-airflow-20261012/radial-full-077",
      "scope": "all_native_inputs_mesh_logs_histories_fields_and_receipts",
      "performance_accepted": false
    },
    {
      "case": "work/bionic-airflow-20261012/radial-split-078",
      "scope": "all_native_inputs_mesh_logs_histories_fields_and_receipts",
      "performance_accepted": false
    },
    {
      "case": "work/bionic-airflow-20261012/radial-isolated-079",
      "scope": "all_native_inputs_mesh_logs_histories_fields_and_receipts",
      "performance_accepted": false
    },
    {
      "case": "work/bionic-radial-subdomain-20261013",
      "scope": "native_radial_subdivision_split_isolated_admission_readers_and_receipts",
      "performance_accepted": false
    }
  ]
}
```

Les cinq actifs distants sont vérifiés par tailles et digests GitHub. Tous les
payloads sont relus localement ; aucun second téléchargement intégral distant
n’est revendiqué. Sources et preuves de cette phase désormais épinglées.
