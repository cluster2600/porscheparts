# Projection sélective dans une couronne connectée — 073 à 076

Cette phase réutilise le domaine complet 063 pour garder une contribution radiale
interne, perdue lors de l'isolement 071/072. Elle ne modifie aucune surface CFD du
turbo réel. Rotor et ports restent absents ; les limites après projection sont
celles d'un nouveau témoin synthétique, pas une preuve de paroi physique conservée.

## Contrôles de maillage terminés

La carte pointRegionAddressing valide de 065 retrouve exactement les coordonnées
063. Elle sélectionne 6 912 points extérieurs et 14 080 autres points de frontière.
Les premiers sont rapprochés radialement d'un huitième de la largeur existante,
au maximum 0,056605625 mm ; les autres sont déclarés frozenPoints. La cible STL
est exactement la triangulation des faces de frontière originales 063. Les
points, faces et paramètres initiaux sont conservés séparément avant exécution.

073 passe checkMesh sur ce maillage initial : 27 136 cellules, une région fluide,
minimum du déterminant 0,038085656, non-orthogonalité maximale 47,81735 degrés.
La connectivité, la zone tournante et ses coordonnées sont conservées. Les
entrées de 074 sont strictement identiques ; seule l'opération native ajoute
snappyHexMesh avant checkMesh. Castellation et couches sont désactivées.

074 conserve exactement les 14 080 points gelés et déplace la paroi extérieure
jusqu'à 0,055450663 mm. Il passe aussi Mesh OK, mais les points MRF internes
bougent jusqu'à 0,020063206 mm. La normale de rotation maximale devient
0,0009352577 m/s et le défaut de planéité MRF 1,80517e−8 m. Le bilan géométrique
maximal par cellule tournante atteint 2,34296e−10 m³/s. Ce n'est pas un débit
physique. **074 est refusé pour la suite CFD**, malgré l'admission checkMesh.

075 ne change qu'une entrée de 074 : nSolveIter passe de 100 à 0 dans les
snapControls. Il s'agit des itérations de lissage du déplacement du MAILLAGE,
pas d'une tolérance ou équation du solveur d'écoulement. Le source officiel
snapParameters relie nSolveIter à nSmoothDispl ; snappySnapDriver appelle ce
lissage après l'attribution des déplacements de frontière. Les trois membres
sources sont relus et hachés. Ce contre-essai isole cette étape, sans balayage.

075 conserve exactement tous les points des cellules tournantes, y compris les
6 912 points MRF. Les 20 992 points de frontière ont exactement les mêmes
coordonnées après projection dans 074 et 075 : le déplacement extérieur est
maintenu. Minimum déterminant 0,038085656, non-orthogonalité maximale 47,81735°,
Mesh OK. MRF : normale maximale 2,28795e−12 m/s, planéité 1,05718e−17 m ; bilan
maximal tournant 1,49078e−19 m³/s. La connectivité et rotorZone sont inchangées.
Le défaut de planéité maximal sur toutes les faces reste 1,35450e−6 m, hors de
la géométrie tournante conservée. Ce n'est pas une recette de production qualifiée.

Les trois commandes terminent avec code zéro sans OOM : 073 en 0,793 s,
074 en 1,613 s, 075 en 1,552 s. Les conteneurs et tous les diagnostics sont
conservés ; aucune source ou preuve antérieure n'est modifiée.

## Limite de la cible

La distance à un sommet source portant le même label n'est PAS la distance à
la surface cible. Elle reste au maximum 0,056605625 mm après projection ; hors
extrémités, elle atteint 0,022433753 mm. Les sommets communs aux parois latérales
et aux fermetures peuvent se projeter sur ces dernières. Le pire sommet est au
plan arrière source et présente aussi un petit écart axial après projection.
On ne revendique donc ni la récupération exacte de toute la frontière 063, ni
la conservation complète de son anneau arrière physique. Le volume natif 075
est 4,608189605996772e−6 m³, contre 4,611377236219295e−6 m³ pour 063.

Les deux critères démontrés sont la conservation du raccord déclaré et un
déplacement extérieur non nul, avec géométrie tournante intacte dans 075.
La conservation des parois physiques, le raffinement protégé et les couches
restent des contrôles distincts. Aucun gain de débit ou puissance n'est déduit.

## Repos 076 terminé et relu

076 termine les 200 pas de 1e−7 s jusqu'à 20 µs en 1 195,602 s, dans la limite
inchangée de 1 200 s, code zéro sans OOM. Les seuils préalables sont respectés :
écart de pression maximal 1,1350494e−9 Pa, de température 1,2676082e−11 K,
vitesse maximale historique 3,2659879e−12 m/s. Le maximum du seul champ final
est 3,0484018e−12 m/s ; Courant maximal 0,0859544233.

Les 800 résolutions de pression atteignent 1 000 itérations : aucune convergence
linéaire qualifiée. Le lecteur relit toutes les valeurs de p/T/U/rho sur les
27 136 cellules et phi sur les 60 544 faces internes, ainsi que tous les payloads
et entrées hachés. Valeurs finies, p/T/rho positives. phi est un flux massique
RELATIF, pas le débit d'air physique d'un turbo. Aucun contrôle de perturbation,
indépendance au maillage ou au temps, ni performance forcée ou calibration.

## Archive native

[Sources, entrées, champs, maillages et reçus](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-connected-selective-2026-10-12).

```json
{
  "files": 183,
  "archive_bytes": 6744761,
  "archive_sha256": "a2ae7fb013f65218b81d490f0f1dfa3924db00794df9f38b7527e5b95df07f5d",
  "manifest_sha256": "bcf41a7b7db27ceac31a092cb1bcb2063c52d6a749fe9184710f9f57e7d2af37",
  "all_payloads_verified": true,
  "performance_ranking_authorized": false,
  "scopes": [
    {
      "case": "work/bionic-airflow-20261012/connected-initial-073",
      "scope": "all_native_inputs_mesh_logs_histories_fields_and_receipts",
      "performance_accepted": false
    },
    {
      "case": "work/bionic-airflow-20261012/connected-snap-074",
      "scope": "all_native_inputs_mesh_logs_histories_fields_and_receipts",
      "performance_accepted": false
    },
    {
      "case": "work/bionic-airflow-20261012/connected-nosmooth-075",
      "scope": "all_native_inputs_mesh_logs_histories_fields_and_receipts",
      "performance_accepted": false
    },
    {
      "case": "work/bionic-airflow-20261012/connected-equilibrium-076",
      "scope": "all_native_inputs_mesh_logs_histories_fields_and_receipts",
      "performance_accepted": false
    },
    {
      "case": "work/bionic-connected-selective-20261012",
      "scope": "connected_selective_motion_rest_readers_sources_and_receipts",
      "performance_accepted": false
    }
  ]
}
```
