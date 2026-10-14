# Raccord natif après projection sélective — 082 et 083

083 réunit le sous-domaine fixe projeté 081 et la région tournante intacte de
078. Le raccord et le maillage final sont vérifiés indépendamment, puis admis
par checkMesh. Aucun solveur d’écoulement n’est lancé. Les parois extérieures
restent synthétiques ; rotor et ports physiques sont absents.

## Opérations et provenance

082 relit les payloads 078/081, compare leurs faces et propriétaires/voisins,
puis sélectionne les 6 784 faces du patch nommé `domain1_to_rotorZone` de 078.
Leurs points ont exactement les coordonnées conservées dans 081. Un faceSet
explicite transmet cette sélection à `createPatch`, avec `pointSync false`.
L’opération recrée un patch wall dédié, sans déplacer un point ni modifier une
cellule. Le lecteur vérifie la correspondance orientée après renumérotation.
082 termine en 2,737 s, code zéro sans OOM, Mesh OK.

083 copie uniquement les fichiers fondamentaux des deux maillages. Aucune carte
RegionAddressing héritée n’est copiée. Les points, faces, owner/neighbour et zones
de la région tournante sont identiques octet pour octet à 078. Son ancienne
métadonnée mappedWall devient wall et les trois entrées sampleMode/sampleRegion/
samplePatch sont retirées explicitement : ce raccord temporaire sera internalisé.
Aucune connexion du turbo physique n’est modifiée.

`mergeMeshes` réunit les deux régions, `stitchMesh -perfect` raccorde leurs
patches, puis `createPatch` retire uniquement les deux patches devenus vides.
Les maillages après fusion et après raccord sont sauvegardés séparément. Le
refus connu 066 pour référence à une région absente n’est pas reproduit : aucune
métadonnée mappedWall obsolète n’est transmise au contrôle final. La preuve
indépendante ne repose pas sur la tolérance de l’outil nommé perfect.

Toutes les entrées des deux cas sont copiées AVANT exécution. Les images,
commandes bornées, états Docker, journaux, reçus et empreintes sont conservés.
Le membre officiel createPatch.C de l’archive v2406 est haché pour documenter
la lecture des faceSet ; ce n’est pas à lui seul une preuve de l’application.

## Vérification du résultat

083 termine en 6,034 s, code zéro sans OOM : Mesh OK, une région fluide,
33 920 cellules, 34 560 points, 102 400 faces dont 80 768 internes et
21 632 de frontière. Le minimum du déterminant est 0,03808565604766382 ;
non-orthogonalité maximale 47,8173518952406 degrés. Aucun petit déterminant
ni concavité signalé. Les critères ne sont pas assouplis.

La lecture indépendante revalide les cartes natives 078 contre 077 : toutes les
cellules sont couvertes une fois, seules les 6 784 faces communes apparaissent
deux fois avec orientations opposées. Elle construit ensuite les coordonnées
attendues en conservant la région tournante et en insérant les points réels de
081 par la carte valide du sous-domaine fixe. Une bijection complète des cellules
par leurs faces orientées retrouve la topologie 077, avec exactement les mêmes
paires owner/neighbour. Les coordonnées décodées finales sont EXACTEMENT celles
de ce domaine composé après réindexation. Il ne s’agit pas de fichiers renumérotés
identiques octet pour octet.

Les 20 352 prismes tournants, leurs points et rotorZone sont conservés ; les
13 568 autres cellules sont des hexaèdres fixes. Toutes les chaînes d’arêtes
par cellule s’annulent et tous les volumes sont positifs. Le retrait des patches
vides ne change ni points, faces, owner/neighbour, ni zone. Aucune ancienne carte
régionale n’est présentée comme adressage global final.

Les 6 784 quadrilatères MRF restent plans et tangents : défaut de planéité
1,05718e−17 m, normale géométrique maximale de rotation 2,28795e−12 m/s.
Bilan géométrique maximal par cellule tournante : 1,49078e−19 m³/s.
Ces nombres ne sont pas des débits d’air.

## Limites conservées

La planéité globale maximale reste 1,35450e−6 m dans les cellules fixes ; le
bilan géométrique maximal calculé sur toutes les cellules vaut 9,01924e−11 m³/s.
La rotation n’est pas appliquée à ces cellules fixes : cette dernière mesure ne
constitue pas un flux physique ou un défaut d’écoulement démontré.

Le volume final est 4,610682341591068e−6 m³, concordant avec le natif
4,610682341591147e−6 m³. Il diffère du volume initial 077, car la paroi projetée
081 n’était pas restituée exactement. Les preuves ponctuelles et la borne sur
les triangulations appariées 080/081 restent dans leur périmètre ; aucune
tolérance physique, conservation exacte de toute la cible ou orientation de
paroi réelle n’est déduite.

Ce raccord après projection est nouveau par rapport à 065–067, où aucun
traitement de surface n’intervenait entre séparation et réunion. Il ne qualifie
pas le raffinement, les couches, les parois physiques, le repos global, la
convergence, la stabilité ou les performances du turbo. Les repos 064/076 ne
sont pas transposés à ce maillage différent. Aucun débit maximal, gain de
puissance ou jumeau calibré n’est validé.

## Archive

[Sources, entrées et sorties natives](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-post-snap-coupling-2026-10-13). Cinq actifs vérifiés par tailles et digests GitHub ; tous les payloads relus localement. Aucun second téléchargement intégral distant revendiqué.

```json
{
  "files": 157,
  "archive_bytes": 5699113,
  "archive_sha256": "4f3c9002d27ab0e79b9bb63445bace6df939a1cb9fd8492c782ae5c4cc433e81",
  "manifest_sha256": "c5c2a0df16f3c67e90c704636950f0bb4a71db81ce7ed009eb3da7e1ceabcf10",
  "all_payloads_verified": true,
  "performance_ranking_authorized": false,
  "scopes": [
    {
      "case": "work/bionic-airflow-20261012/post-snap-patches-082",
      "scope": "all_native_inputs_mesh_logs_histories_fields_and_receipts",
      "performance_accepted": false
    },
    {
      "case": "work/bionic-airflow-20261012/post-snap-stitch-083",
      "scope": "all_native_inputs_mesh_logs_histories_fields_and_receipts",
      "performance_accepted": false
    },
    {
      "case": "work/bionic-post-snap-coupling-20261013",
      "scope": "native_repatch_stitch_after_projection_independent_composite_topology_and_geometry",
      "performance_accepted": false
    }
  ]
}
```
