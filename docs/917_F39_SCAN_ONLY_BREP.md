# Culasse Porsche 917 F39 — reconstruction B-Rep scan-only

> Limite de forme identifiée : le noyau publié utilise des rayons elliptiques
> globaux de 55 × 71 mm et des ailettes jusqu'à 62,6 × 98 mm. Cet ovale vient
> de l'ajustement à la boîte englobante, pas d'une exigence thermique ou d'une
> cote Porsche. Avec un écart scan → analytique P95 de 16,02 unités, cette peau
> doit être reconstruite par contours locaux avant toute prétention de fidélité.

## Verdict

F39 livre un **STEP analytique OpenCASCADE réimportable et maillable**, construit
sans publier le scan propriétaire. Il reste un prototype géométrique bloqué :
l'échelle absolue, l'ajustement Porsche 917, l'épaisseur minimale globale, la
qualité minimale du maillage et toutes les validations physiques restent non
certifiés. Il n'est autorisé ni à l'impression métal ni au démarrage moteur.

La seule convention dimensionnelle disponible est `1 unité du scan = 1 mm`.
Elle permet des calculs reproductibles mais ne constitue pas une métrologie.

## Définition reconstruite

Le contrat paramétrique
[`f39-brep-scan-only.json`](../twins/reference-917-engine/f39-brep-scan-only.json)
décrit :

- une enveloppe lisse à noyau et douze ailettes elliptiques, ajustée à
  l'enveloppe du scan local ;
- une chambre conique ouverte au deck, quatre conduits, quatre poches de siège,
  quatre passages de guide et deux pilotes de bougie ;
- des galeries d'huile et perçages de goujons ouverts ;
- des bossages d'admission et d'échappement séparés afin d'éviter les poches
  fermées entre ailettes ;
- des surfaces OCCT analytiques, et non un B-Rep facetté issu du scan.

Le STEP publié est donc une nouvelle géométrie paramétrique. Le STL et le
maillage `.msh` utilisés pour les contrôles restent des dérivés locaux non
versionnés.

## Preuves géométriques

| Contrôle | Résultat F39 | Porte |
|---|---:|---:|
| Solides après réimport STEP | 1 | 1 — réussi |
| Composantes de peau STEP | 1 | 1 — réussi |
| Coques internes fermées | 0 | 0 — réussi |
| Flood-fill voxel 2,0 / 1,5 / 1,0 mm | 0 / 0 / 0 mm³ | 0 — écran réussi |
| Maillage Gmsh | 382 602 tétraèdres | génération réussie |
| `minSICN` minimum | 0,02049 | > 0,1 — **échec** |
| Tétraèdres `minSICN < 0,1` | 34 sur 382 602 | 0 — **échec** |
| Tétraèdres `minSICN <= 0` | 0 | 0 — réussi |
| Épaisseur analytique des fonctions nommées | min. 2,0 mm | >= 1,5 mm — localement réussi |
| Épaisseur maillée, 2 400 rayons, P01 | 1,075 mm | >= 1,5 mm — **échec** |
| Épaisseur maillée, P05 / médiane | 2,000 / 3,041 mm | information |

Le contrôle d'épaisseur par rayons inclut les lèvres et raccords des ouvertures.
Il est non exhaustif, mais son P01 sous 1,5 mm interdit de transformer les cotes
nominales des ailettes et bossages en preuve globale. Une reconstruction locale
avec congés, puis une métrologie réelle ou CT, reste nécessaire.

Le flood-fill voxel est indépendant du graphe déclaré des conduits. Son résultat
zéro à trois pas est cohérent avec l'unique composante de peau OCCT, mais ne
remplace ni CT, ni étude de dépoudrage qualifiée machine.

## Écart au scan

Deux nuages déterministes de 20 000 points donnent une distance bidirectionnelle
approchée, pas un Hausdorff exact :

- B-Rep vers scan : moyenne 5,05 unités, P95 11,74, maximum 26,09 ;
- scan vers B-Rep : moyenne 5,80 unités, P95 16,02, maximum 26,56.

Ces écarts expriment honnêtement la perte des détails organiques du scan lors de
la reconstruction analytique. Ils ne certifient ni l'échelle ni l'ajustement.

## Reproduction locale

La construction exige l'image CAE arm64 locale utilisée par le projet et les
trois entrées dont les SHA-256 sont verrouillés dans le contrat. Exemple :

```sh
f39_scan_root=/absolute/path/to/local/f37-worktree
docker run --rm \
  -v "$PWD:/workspace" \
  -v "$f39_scan_root:/scan:ro" \
  -w /workspace --entrypoint python3 \
  3dprinting993-cae-integrated-f33:dev \
  twins/reference-917-engine/source/f39-brep-build.py \
  --contract twins/reference-917-engine/f39-brep-scan-only.json \
  --f37-mesh /scan/work/917-scan-conforming-f37/head-mesh-proof/917-head-f37-printable-proof.local.stl \
  --f36-geometry /scan/work/917-scan-conforming-f36/run-013/geometry-report.json \
  --f38-report twins/reference-917-engine/evidence/f38-brep-lpbf/f38-brep-lpbf-report.json \
  --output work/917-f39-brep-scan-only/run-015 \
  --mesh-size-mm 2.5
```

Le rapport publié est
[`f39-brep-validation-report.json`](../twins/reference-917-engine/evidence/f39-brep-scan-only/f39-brep-validation-report.json).

## Blocages avant fabrication

Il faut encore disposer de cotes d'interface traçables, reconstruire les zones
sous 1,5 mm avec congés et surépaisseurs d'usinage, obtenir un maillage dont la
qualité minimale franchit la porte, valider matière/procédé/coupons à chaud,
réaliser CHT et fatigue thermomécanique, préparer une stratégie LPBF qualifiée,
puis corréler CT/CND, banc de flux et banc moteur. L'absence annoncée de nouvelles
cotes signifie que l'ajustement OEM ne peut pas être certifié par F39.
