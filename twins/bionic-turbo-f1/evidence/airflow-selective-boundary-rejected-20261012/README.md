# Région isolée refusée avant projection sélective — 071/072

Les deux contrôles natifs sont terminés, sans projection ni solveur d'écoulement.
Le sous-domaine extérieur issu de 065 ne peut pas servir tel quel au contrôle
sélectif : ses 6 784 cellules échouent au déterminant natif après transformation
de son raccord en paroi non couplée. Les seuils ne sont pas modifiés.

## Entrées et portée

La région domain1 contient 13 824 points, 27 264 faces et 13 440 faces internes.
Ses deux patches contigus sont réunis sous walls, sans modifier leurs faces ni
owner/neighbour ; les métadonnées mappedWall sont retirées explicitement.
Aucune carte RegionAddressing héritée n'est copiée. Les 6 912 points du raccord
sont déclarés frozenPoints. Il n'y a pas de zone tournante dans ce sous-domaine
extérieur. Toutes les limites sont synthétiques ; aucune pièce du turbo change.

071 déplace les 6 912 autres points vers l'intérieur d'un huitième de la largeur
radiale existante : maximum 0,056605625 mm. La cible STL est la triangulation
exacte des faces de frontière originales, pas une modification du maillage natif.
La configuration de projection reprend 070 mais n'est jamais exécutée : le
précontrôle échoue et arrête le préparateur avant le cas de projection prévu.
Le nom selective-snap-072 dans ce préparateur désigne un cas jamais créé.

072, selective-unshifted-072, est un nouveau contrôle de diagnostic, pas cette
projection prévue. Il ne change que les points préparés, restaurés exactement
à leurs coordonnées natives de 065. Toutes les autres entrées sont identiques.
Les copies des entrées ont été conservées AVANT chaque commande native.

| Cas | Durée native | Déterminant minimal | Cellules sous 0,001 | Résultat |
|---|---:|---:|---:|---|
| 071, décalage synthétique | 0,446 s | 0,00002642422372 | 6 784 | rejet |
| 072, coordonnées originales | 0,423 s | 0,00002636489851 | 6 784 | rejet |

Les conteneurs sortent avec code zéro, sans OOM ; cela ne vaut pas admission.
Aucun log snappy ni champ d'écoulement n'est créé. Conteneurs et refus conservés.

## Lecture du déterminant

Le source officiel v2406 polyMeshCheck.C transmet les faces internes ou couplées
à primitiveMeshTools::cellDeterminant. La formule utilise le tenseur des aires
de ces seules faces, normalisé par l'aire moyenne ; le déterminant absolu est
divisé par huit en 3D. Il dépend donc aussi des connexions, pas seulement de la
forme géométrique fermée d'une cellule. Les deux sources exactes sont archivées
avec empreintes et référence à l'archive officielle vérifiée.

La reconstruction retrouve les minima, moyennes et tous les labels rejetés des
deux cas. Dans le parent complet 063, les cellules correspondantes ont des
valeurs reconstruites entre 0,1830702993 et 0,5061045594. Leur face radiale de
raccord y est interne ; elle ne contribue plus dans la région isolée à parois.
Le contrôle 072 exclut le décalage synthétique comme condition nécessaire de ce
rejet. Il ne qualifie ni une projection sélective ni un écoulement.

Le premier lecteur appelait incorrectement le helper vectorisé geometry avec
deux arguments ; source et traceback conservés. La v2 groupe les polygones par
nombre de sommets et reproduit la formule officielle. Aucun calcul natif rejoué.

## Suite bornée

Conserver ces refus. Un nouveau témoin devra disposer d'une connexion radiale
interne suffisante avant toute projection. Réutiliser un domaine existant qui
possède ces connexions, ou construire une transition justifiée ; ne pas masquer
le contrôle par un patch fictivement couplé ou un critère abaissé. La protection
sélective avec déplacement non nul reste à tester, puis celle du raffinement.
Préserver séparément les parois physiques et le jeu roue–écrou 033.

## Archive native

[Sources, entrées, maillages, reçus et journaux](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-selective-boundary-rejected-2026-10-12).

```json
{
  "files": 90,
  "archive_bytes": 2730434,
  "archive_sha256": "78482e444297a2d037672e74aea2d5f8f643d80e5ade94f73f7b39cc082995d3",
  "manifest_sha256": "0bcd0f0e58ea3da60f66e80ea8bbd51ea08d60cde2cdf02bc7347d2c3c7cb254",
  "all_payloads_verified": true,
  "performance_ranking_authorized": false,
  "scopes": [
    {
      "case": "work/bionic-airflow-20261012/selective-initial-071",
      "scope": "all_native_inputs_mesh_logs_histories_fields_and_receipts",
      "performance_accepted": false
    },
    {
      "case": "work/bionic-airflow-20261012/selective-unshifted-072",
      "scope": "all_native_inputs_mesh_logs_histories_fields_and_receipts",
      "performance_accepted": false
    },
    {
      "case": "work/bionic-selective-boundary-20261012",
      "scope": "standalone_region_refusal_readers_sources_and_receipts",
      "performance_accepted": false
    }
  ]
}
```
