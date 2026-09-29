# Import des scans OBJ (Mac) — intake 2026-09-27

Inventory, provenance and integrity of the automotive scan meshes imported
under `/home/lolman/imports/mac-obj`, triaged by
`work/obj-intake-20260927/triage_obj.py` (host `python3`, trimesh 5.1.0,
pymeshlab 2025.7.post1). Machine-readable report:
`work/obj-intake-20260927/reports/obj-intake.json`.

The source trees are treated as read-only raw evidence. Nothing here is a
measurement certificate: scans stay `SINGLE_SOURCE` raw inputs until a twin
pipeline (contracts `M64-ACQ-*`) derives dimensions with stated uncertainty.
OBJ files carry no unit metadata; mm is assumed (scanner convention) and flagged.

## Mesh inventory (unique payloads)

| id | sha256 (prefix) | octets | triangles | bbox (mm supposés) | état |
|---|---|---|---|---|---|
| 935-xtreme-cylinder-head | `4623d5d3b73fe3d0` | 104 598 077 | 2 466 040 | 197,9 × 198,8 × 227,1 | 3 copies identiques, dont la copie de travail du dépôt (`work/mesh-repair-935-head/.../935-xtreme-cylinder-head-working-copy.obj`) → **déjà au pipeline** |
| 917-engine-case-with-cylinders | `428c4143d073f833` | 107 128 223 | 2 465 879 | 1 002,2 × 768,3 × 739,8 | 2 copies identiques (iCloud + raw-scans) → **déjà au pipeline 917** (`EXPECTED_SHA256` du `prepare_scan.py` 917 = ce hash) |
| 964-widebody-underside | `f397909141e5af25` | 210 972 101 | 4 684 929 | 2 074,7 × 4 283,5 × 894,4 | nouveau, 176 corps — scan de carrosserie, pas encore trié par composant |
| **Fan Drive 0.21 mm** | `6c0b12d4dd782fd4` | 105 090 339 | 2 484 656 | 325,2 × 398,6 × 450,1 | **nouvel actif moteur** → alimente le trou `M64-ACQ-0005` (géométrie ventilateur) |

Dupliquats : les fichiers `Downloads/` sont byte-identiques aux copies
`raw-scans/` correspondantes (935 : `Downloads/935+Xtreme+Cyl+head.obj` =
`raw-scans/wolfe-classics-935-cylinder-head/original/…` = copie de travail du
dépôt ; 917 : fichier iCloud = `raw-scans/917-engine/original/…`) ; les groupes
de duplication complets sont dans le JSON. Aucun de ces scans n'a encore de
fiche `catalog/sources/` — à créer avec l'acquisition qui les exploite, pas
avant.

État maillage (trimesh) : les 4 payloads ne sont pas watertight ; arêtes
non-multiiformes (>2 faces/partagées) 1,21–2,32 M par scan, 7 k–27 k arêtes de
bord, corps multiples (1 pour Fan Drive, 3–4 pour 917/935, 176 pour le 964) —
brut de scanner attendu, aucune réparation appliquée ici.

## Fan Drive (intérêt direct pour le jumeau M64)

- 1 seul corps, 1 256 836 sommets / 2 484 656 triangles, orientation inconnue
  (pas de frame de scan joint). Non watertight : 1,24 M d'arêtes
  non-multiiformes, 7 013 arêtes de bord. La géométrie utilisable viendra de
  coupes par tranches, pas d'un remaillage direct.
- Deux clusters nets à z ≈ 205 (probablement deux poulies/roues dentées de
  l'entraînement courroie du ventilateur) :
  - composant bas : 206,6 × 251,4 × 212,9, centroïde XY (26,3 ; −92,1), r max 146,9 ;
  - composant haut : 265,9 × 243,0 × 237,2, centroïde XY (−80,2 ; 51,7), r max 192,7.
- Ratio de rayons ≈ 1,31 pour le premier lot de coupes — cohérent avec un
  étage de démultiplication, **pas encore** confirmé comme le rapport
  1:1,6 (`FACT_public`) ; la courroie elastique et la poulie libre faussent
  les coupes. À reprendre dans un plan perpendiculaire à chaque axe.

### Extraction par composant (2ᵉ passe, `fan_drive_features.py`)

Segmentation par clustering z/y + profils de section radiaux
(`work/obj-intake-20260927/fan-drive-extract.json`). Unités mm supposées.

- Disque denté bas (axe XY ≈ (−11,6 ; −187,1)) : hauteur axiale totale
  67,9 ; OD sommet de dents ≈ 127,6 ; trou minimal au plan de dents
  ⌀ ≈ 5,3 mais couverture angulaire du vide seulement 0,34 à z<0 →
  probablement partiellement obstrué ou artefact de scan, **pilot non
  confirmé**. Les bords de vide par tranches (vide r≈21–29, rmax
  43–62 au-dessus du plan de dents) suggèrent un moyeu conique plus qu'un
  alésage cylindrique net.
- Poulie haute (centre dérivé par tranche, ≈ (−84 ; 55)) : hauteur axiale
  202,2 ; OD variable par tranche ⌀219–256 (flancs coniques / flasques
  multiples) ; trou ⌀ ≈ 17,3 à z∈[346,354] (1ᵉʳ percentile, borne basse).
- **Nombre de dents : NON résolu.** La couverture angulaire des bandes de
  dents est faible (0,03–0,24 sur 720 secteurs) : au pas de scan de 0,21 mm,
  des dents de ~1–3 mm sont sous-échantillonnées et les harmoniques
  dominants (6–16 selon la bande) sont incohérents entre tranches. Un
  comptage fiable exigera une coupe plane re-orientée perpendiculairement à
  chaque axe (plan local ajusté), puis seuillage crête/valley — ou une pièce
  physique.
- Ratio d'étage : ⌀denté ≈ 127,6 vs ⌀poulie 219–256 → ≈ 1,7–2,0, du même
  ordre que 1:1,6 (`FACT_public`) mais **non concluant** (poulie libre et
  courroie élastique incluses dans le scan).

Prochaine étape : segmenter les corps séparément, re-orienter chaque axe,
reprendre le comptage de dents sur section calibrée, puis fiche source et
valorisation `F2` du composant `m64_cooling_fan`.

## Intégrité

- Hôte : `kali2`, trimesh 5.1.0, pymeshlab 2025.7.post1, python 3.14
  (rapport JSON).
- sha256 complets dans le JSON ; aucun octet modifié dans les arbres sources.
- Rien n'est encore enregistré dans `catalog/sources/` (volontaire : la fiche
  source naîtra avec l'acquisition qui exploite le scan).
