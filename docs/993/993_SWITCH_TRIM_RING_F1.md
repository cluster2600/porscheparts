# Bague de commutateur 993 — jumeau F1

Cette bague aluminium non critique est le premier pilote métallique du flux
993. La fiche commerciale fournit quatre cotes : Ø extérieur 30,5 mm,
profondeur 10,5 mm, Ø intérieur avant 23 mm et arrière 28 mm. Le maître
`build123d` reconstruit un anneau à alésage conique et confronte son volume OCCT
au volume analytique d'un cylindre moins un tronc de cône.

Le résultat est volontairement au niveau **F1 / concept**. Le cône intérieur est
une interprétation, pas une mesure. Les tolérances, rayons, ouverture du tableau
de bord, état de surface et nuance d'aluminium restent inconnus. Le STEP ne doit
donc pas être envoyé en fabrication ni monté sur un véhicule.

## Calculs exécutés

- paroi radiale avant : `(30,5 - 23) / 2` ;
- paroi radiale arrière : `(30,5 - 28) / 2` ;
- volume : cylindre extérieur moins tronc de cône intérieur ;
- masse indicative : volume multiplié par 2,67 g/cm³, densité de criblage
  AlSi10Mg explicitement non attribuée à la pièce d'origine ;
- croissance thermique et pression de serrage laissées bloquées jusqu'à la
  mesure de l'ouverture OEM et à la sélection d'une carte matière qualifiée.

La géométrie est imprimable en LPBF en première lecture, mais sa forme
axisymétrique rend le tournage CNC probablement plus rationnel. Le pilote sert à
valider la chaîne numérique ; le choix industriel reste ouvert.

## Reproduction

```sh
python3 parts/993-int-switch-trim-ring-f1-0001/source/switch_trim_ring.py \
  --report parts/993-int-switch-trim-ring-f1-0001/evidence/geometry-screen.json
```

L'export STEP exige l'image CAO verrouillée du dépôt. PhysicsNeMo et un GPU Vast
ne sont pas requis ici : il n'existe ni champ complexe ni données d'entraînement
justifiant un surrogate. Les formules déterministes et OCCT sont l'autorité de
ce premier contrôle.

## Étapes 02 et 03 du pipeline AM — 2026-09-09

La bague est la première des 21 pièces suivies par
[`am-validation-policy.json`](../../catalog/manufacturing/am-validation-policy.json)
dont aucune étape n'était renseignée à être menée au criblage géométrique. Elle a
été choisie parce qu'elle est la seule `non_critical` du lot, et qu'elle possède
déjà un master paramétrique et un STEP relu.

**Étape 02 — intégrité BREP et maillage : `passed`.** Le master exporte
désormais aussi une surface d'analyse STL, à tolérance de corde déclarée de
0,03 mm et tolérance angulaire de 0,08 rad. Le maillage est **étanche**, en une
seule composante, 2 054 triangles. Son volume vaut 2 294,6 mm³ contre
2 291,9 mm³ au BREP, soit 0,12 % — l'écart attendu d'une facettisation de
surfaces courbes à cette tolérance. Master, STEP et STL sont liés par SHA-256
dans le rapport.

**Étape 03 — tranchage intégral et supports : `completed_screening`.**

| grandeur | valeur |
|---|---|
| orientation retenue | `roll_y_45` |
| couches réellement tranchées | **580** à 0,05 mm |
| hauteur de construction | 29,0 mm |
| couches vides internes | 0 |
| nouveaux îlots | **0** |
| couches à aire non soutenue | 10 |
| aire non soutenue maximale | **0,079 mm²** |
| volume de poudre piégé | aucun détecté au pas du criblage |
| épaisseur médiane de paroi | 2,06 mm |

Zéro nouvel îlot signifie qu'aucune couche ne fait apparaître de matière
détachée du reste : à cette orientation, la pièce se construit sans support
interne. Les 0,079 mm² d'aire non soutenue au pire sont un ordre de grandeur en
dessous de ce qu'un support devrait reprendre.

**Pourquoi ce n'est pas `passed`.** L'orientation n'est pas revue par un
ingénieur, les supports fournisseur n'existent pas, et le criblage recoater reste
fermé faute de champ de distorsion et de jeu de lame. Les portes de procédé du
rapport sont toutes fermées, et un test le vérifie explicitement :
`tests/test_993_switch_trim_ring_lpbf_f1.py` échoue si l'une d'elles s'ouvrait
sans coupon ni fichier machine.

**Reproduction** — la chaîne demande `numpy`, `matplotlib`, `trimesh`, `shapely`
et `rtree` :

```bash
python3 parts/993-int-switch-trim-ring-f1-0001/source/switch_trim_ring.py \
  --out parts/993-int-switch-trim-ring-f1-0001/derived/switch_trim_ring_f1.step \
  --surface parts/993-int-switch-trim-ring-f1-0001/derived/switch_trim_ring_f1.stl
python3 scripts/run_metal_am_geometry_screen.py \
  --part-id 993-INT-SWITCH-TRIM-RING-F1-0001 \
  --master parts/993-int-switch-trim-ring-f1-0001/derived/switch_trim_ring_f1.step \
  --master-sha256 <sha256-step> \
  --surface parts/993-int-switch-trim-ring-f1-0001/derived/switch_trim_ring_f1.stl \
  --surface-sha256 <sha256-stl> \
  --machine-card catalog/manufacturing/machines/eos-m290.json \
  --material "EOS AlSi10Mg" \
  --expected-envelope-mm 30.5 30.5 10.5 \
  --output twins/993-switch-trim-ring-alsi10mg-f1/evidence/lpbf-f1
```
